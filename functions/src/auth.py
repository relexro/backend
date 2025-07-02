import functions_framework
import logging
import firebase_admin
from firebase_admin import auth as firebase_auth_admin
from firebase_admin import firestore
import flask
from pydantic import BaseModel, ValidationError, field_validator, Field
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_auth_requests  # Alias to avoid confusion with http 'requests'
import base64
import json
import os # To potentially get Cloud Run URL if passed as env var
from functools import wraps
from dataclasses import dataclass
from typing import Dict, Set, Tuple, Any, Literal, Optional
from flask import Request, jsonify
import datetime
from common.clients import get_db_client

logging.basicConfig(level=logging.INFO)

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

ROLE_ADMIN = "administrator"
ROLE_STAFF = "staff"
ROLE_OWNER = "owner"

TYPE_CASE = "case"
TYPE_ORGANIZATION = "organization"
TYPE_PARTY = "party"
TYPE_DOCUMENT = "document"

# Action constants
ACTION_READ = "read"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_CREATE = "create"
ACTION_LIST = "list"

PERMISSIONS: Dict[str, Dict[str, Set[str]]] = {
    TYPE_CASE: {
        ROLE_ADMIN: {
            "read", "update", "delete", "archive",
            "upload_file", "download_file",
            "attach_party", "detach_party",
            "assign_case",
            "create", # Added create permission
            "list" # Added list permission
        },
        ROLE_STAFF: {
            "read", "update",
            "upload_file", "download_file",
            "attach_party", "detach_party",
            "create",
            "list"
        },
        ROLE_OWNER: {
            "read", "update", "delete", "archive",
            "upload_file", "download_file",
            "attach_party", "detach_party",
            "create",
            "list"
        }
    },
    TYPE_ORGANIZATION: {
        ROLE_ADMIN: {
            "read", "update", "delete",
            "manage_members", "addMember", "setMemberRole", "removeMember", "listMembers", # Consolidated member actions
            "create_case",
            "list_cases",
            "assign_case",
        },
        ROLE_STAFF: {
            "read",
            "create_case",
            "list_cases",
            "listMembers" # Allow staff to see other members
        },
    },
    TYPE_PARTY: {
        ROLE_OWNER: {"read", "update", "delete", "create", "list"}, # Added create/list for consistency
    },
    TYPE_DOCUMENT: {
        ROLE_ADMIN: {"read", "delete"},
        ROLE_STAFF: {"read"},
        ROLE_OWNER: {"read", "delete"},
    }
}

VALID_RESOURCE_TYPES = set(PERMISSIONS.keys())

class PermissionCheckRequest(BaseModel):
    resourceId: Optional[str] = None # Made optional for creation/listing actions
    action: str
    resourceType: str
    organizationId: Optional[str] = None

    # Using field_validator (Pydantic v2 style)
    @field_validator('resourceType')
    def validate_resource_type(cls, v: str) -> str:
        if v not in VALID_RESOURCE_TYPES:
            raise ValueError(f"Invalid resourceType. Must be one of: {', '.join(VALID_RESOURCE_TYPES)}")
        return v

@dataclass
class AuthContext:
    is_authenticated_call_from_gateway: bool
    firebase_user_id: str
    firebase_user_email: str
    gateway_sa_subject: Optional[str] = None
    additional_headers: Optional[dict] = None
    firebase_user_locale: Optional[str] = None


# Constants
EXPECTED_HEALTH_CHECK_HEADER = "X-Google-Health-Check"
EXPECTED_GATEWAY_SA_EMAIL = "relex-functions-dev@relexro.iam.gserviceaccount.com"
EXPECTED_FIREBASE_ISSUER_PREFIX = "https://securetoken.google.com/"

# Optional env override that can predefine the expected audience (primarily useful in local
# development).  In most cases we rely on the dynamic audience extracted from the JWT itself,
# but we keep this for backward-compatibility with existing log messages.
EXPECTED_GATEWAY_TOKEN_AUDIENCE = os.environ.get("SELF_SERVICE_URL")

def add_cors_headers(f):
    """Add CORS headers to the response."""
    @wraps(f)
    def wrapped_function(*args, **kwargs):
        # Get the response from the wrapped function
        response = f(*args, **kwargs)

        # If the response is a tuple (data, status_code), add headers as the third element
        if isinstance(response, tuple):
            if len(response) == 2:
                data, status_code = response
                headers = {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                }
                return data, status_code, headers

        # If it's just the response data, return it as is
        return response

    return wrapped_function

def _get_firestore_client():
    """Get the Firestore client instance from firebase_admin."""
    return firestore.client()

def get_document_data(db, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
    try:
        doc_ref = db.collection(collection).document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            logging.debug(f"Document {collection}/{doc_id} found.")
            return doc.to_dict()
        else:
            logging.warning(f"Document not found: {collection}/{doc_id}")
            return None
    except Exception as e:
        logging.error(f"Firestore error fetching {collection}/{doc_id}: {e}", exc_info=True)
        raise
def get_membership_data(db, user_id: str, org_id: str) -> Optional[Dict[str, Any]]:
    try:
        query = db.collection("organization_memberships").where( # Corrected collection name
            "organizationId", "==", org_id).where(
            "userId", "==", user_id).limit(1)
        memberships = list(query.stream())
        if memberships:
            logging.debug(f"Membership found for user {user_id} in org {org_id}.")
            return memberships[0].to_dict()
        else:
            logging.debug(f"No membership found for user {user_id} in org {org_id}.")
            return None
    except Exception as e:
        logging.error(f"Firestore error fetching membership for user {user_id} in org {org_id}: {e}", exc_info=True)
        raise

def get_authenticated_user(request: Request) -> Tuple[Optional[AuthContext], int, Optional[str]]:
    """Authenticate the user.

    Handles both:
    1. Gateway-forwarded auth (JWT validated by API gateway, forwarded as X-Endpoint-API-Userinfo)
    2. Direct auth (validate Firebase JWT directly) - used in local dev or direct-to-function calls

    Returns a tuple of (auth_context, status_code, error_message)
    where auth_context is None if authentication failed.
    """
    # --- NEW: Log all headers and highlight any that look like they contain auth or jwt ---
    all_headers = {k: v for k, v in request.headers.items()}
    logging.info("[AUTH-DEBUG] --- Incoming HTTP Headers ---")
    for k, v in all_headers.items():
        logging.info(f"[AUTH-DEBUG] HEADER: {k}: {v}")
    for k, v in all_headers.items():
        if 'auth' in k.lower() or 'jwt' in k.lower():
            logging.info(f"[AUTH-DEBUG] *** POSSIBLE AUTH/JWT HEADER: {k}: {v}")
    logging.info("[AUTH-DEBUG] --- End of Headers ---")
    # --- END NEW ---

    logging.info("[ULTRA-DEBUG] get_authenticated_user called")
    # Log all headers, including Authorization
    all_headers = {k: v for k, v in request.headers.items()}
    logging.info(f"[ULTRA-DEBUG] ALL incoming headers: {all_headers}")

    # Skip auth for health check requests
    if request.headers.get(EXPECTED_HEALTH_CHECK_HEADER):
        logging.info("[ULTRA-DEBUG] Health check request, skipping authentication.")
        return None, 200, "Health check request"

    # Debug: Log all headers except Authorization
    safe_headers = {k: v for k, v in request.headers.items() if k.lower() != 'authorization'}
    logging.info(f"[DEBUG] Incoming headers (except Authorization): {safe_headers}")

    # Check for the userinfo header from API Gateway
    userinfo_header = None
    logging.info("[ULTRA-DEBUG] Checking for API Gateway userinfo headers...")

    for header_key, header_val in request.headers.items():
        key_lower = header_key.lower()
        if key_lower in ("x-endpoint-api-userinfo", "x-apigateway-api-userinfo"):
            logging.info(f"[ULTRA-DEBUG] Found userinfo header: {header_key} = {header_val}")
            userinfo_header = header_val
            break

    if userinfo_header:
        logging.info(f"[ULTRA-DEBUG] Using userinfo header path. Raw value: {userinfo_header}")
        try:
            # Log the raw header (truncated if too long)
            if len(userinfo_header) > 100:
                logging.debug(f"[ULTRA-DEBUG] Raw userinfo_header (truncated): {userinfo_header[:50]}...{userinfo_header[-50:]}")
            else:
                logging.debug(f"[ULTRA-DEBUG] Raw userinfo_header: {userinfo_header}")

            # API Gateway passes user info in a base64-encoded header after validating the Firebase token
            try:
                # Log the raw header before attempting to decode
                logging.info("[ULTRA-DEBUG] Attempting to decode userinfo_header...")

                # Add padding if necessary
                padding_needed = len(userinfo_header) % 4
                if padding_needed > 0:
                    userinfo_header += '=' * (4 - padding_needed)
                    logging.info(f"[ULTRA-DEBUG] Added {4 - padding_needed} padding characters. New header: '{userinfo_header}'")

                decoded_userinfo_bytes = base64.b64decode(userinfo_header)
                logging.info(f"[ULTRA-DEBUG] Successfully base64 decoded userinfo_header. Length: {len(decoded_userinfo_bytes)} bytes")
            except Exception as decode_err:
                logging.error(f"[ULTRA-DEBUG] Failed to base64 decode userinfo_header ('{userinfo_header}') even after padding: {str(decode_err)}")
                # Print the problematic header for debugging
                logging.error(f"[ULTRA-DEBUG] Problematic userinfo_header value: {userinfo_header}")
                raise ValueError(f"Base64 decoding failed: {str(decode_err)}")

            try:
                decoded_userinfo_str = decoded_userinfo_bytes.decode("utf-8")
                logging.info(f"[ULTRA-DEBUG] Successfully UTF-8 decoded userinfo_header. Length: {len(decoded_userinfo_str)} chars")
                logging.debug(f"[ULTRA-DEBUG] Decoded userinfo_header (str): {decoded_userinfo_str[:100]}..." if len(decoded_userinfo_str) > 100 else f"[ULTRA-DEBUG] Decoded userinfo_header (str): {decoded_userinfo_str}")
            except Exception as utf8_err:
                logging.error(f"[ULTRA-DEBUG] Failed to UTF-8 decode userinfo_header: {str(utf8_err)}")
                logging.error(f"[ULTRA-DEBUG] Problematic decoded bytes: {decoded_userinfo_bytes}")
                raise ValueError(f"UTF-8 decoding failed: {str(utf8_err)}")

            try:
                decoded_userinfo = json.loads(decoded_userinfo_str)
                logging.info(f"[ULTRA-DEBUG] Successfully JSON parsed decoded userinfo_header. Keys: {list(decoded_userinfo.keys())}")
                logging.debug(f"[ULTRA-DEBUG] Parsed userinfo_header (JSON): {decoded_userinfo}")
            except Exception as json_err:
                logging.error(f"[ULTRA-DEBUG] Failed to JSON parse decoded userinfo_header: {str(json_err)}")
                logging.error(f"[ULTRA-DEBUG] Problematic decoded string: {decoded_userinfo_str}")
                raise ValueError(f"JSON parsing failed: {str(json_err)}")

            firebase_uid = decoded_userinfo.get("sub")
            email = decoded_userinfo.get("email")
            locale = decoded_userinfo.get("locale")

            logging.info(f"[ULTRA-DEBUG] Extracted from userinfo: firebase_uid='{firebase_uid}', email='{email}', locale='{locale}'")

            if not firebase_uid:
                logging.warning("[ULTRA-DEBUG] Missing subject (user ID) in userinfo header after parsing.")
                return None, 401, "Missing subject (user ID) in userinfo header"

            # Successfully authenticated via API Gateway-forwarded user info
            auth_context = AuthContext(
                is_authenticated_call_from_gateway=True,
                firebase_user_id=firebase_uid,
                firebase_user_email=email or "",
                firebase_user_locale=locale
            )

            logging.info(f"[ULTRA-DEBUG] AuthContext created from userinfo_header: {auth_context}")
            return auth_context, 200, None

        except Exception as e:
            # Enhanced logging for the exception
            logging.error(f"[ULTRA-DEBUG] Error processing X-Endpoint-API-Userinfo header: {str(e)}", exc_info=True)

            # Try to log a sample of the header if it exists
            if userinfo_header:
                sample_length = min(30, len(userinfo_header))
                logging.error(f"[ULTRA-DEBUG] Header sample (first {sample_length} chars): {userinfo_header[:sample_length]}")

            return None, 500, "Error processing authentication information"

    # If we reach here, always try direct Firebase JWT validation (even for API Gateway requests)
    logging.info("[ULTRA-DEBUG] No userinfo header found. Checking for direct Firebase token authentication.")
    auth_header = request.headers.get("Authorization", "")
    logging.info(f"[ULTRA-DEBUG] Authorization header: {auth_header}")
    if not auth_header.startswith("Bearer "):
        logging.warning("[ULTRA-DEBUG] Missing or invalid Authorization header format (should start with 'Bearer ')")
        logging.error(f"[ULTRA-DEBUG] All headers at failure: {all_headers}")
        return None, 401, "Missing or invalid Authorization header"
    token = auth_header[7:]  # Remove "Bearer " prefix
    logging.info("[ULTRA-DEBUG] Found Bearer token. Attempting to validate.")
    try:
        # First, try to validate as a Firebase token
        try:
            logging.info("[ULTRA-DEBUG] Attempting to validate as Firebase ID token...")
            firebase_claims = validate_firebase_id_token(token)
            logging.info(f"[ULTRA-DEBUG] Firebase token validation successful. Claims: {firebase_claims}")
            firebase_uid = firebase_claims.get("sub")
            email = firebase_claims.get("email", "")
            locale = firebase_claims.get("locale")

            logging.info(f"[ULTRA-DEBUG] Extracted from Firebase token: firebase_uid='{firebase_uid}', email='{email}', locale='{locale}'")

            if not firebase_uid:
                logging.warning("[ULTRA-DEBUG] Firebase token validation succeeded but missing subject claim")
                return None, 401, "Invalid Firebase token: missing subject claim"

            # Successfully authenticated directly using Firebase token
            logging.info(f"[ULTRA-DEBUG] Authenticated user {firebase_uid} directly using Firebase token")
            auth_context = AuthContext(
                is_authenticated_call_from_gateway=False,  # Direct Firebase token
                firebase_user_id=firebase_uid,
                firebase_user_email=email,
                firebase_user_locale=locale
            )

            return auth_context, 200, None

        except Exception as firebase_err:
            # If Firebase validation fails, try Google SA token validation instead
            logging.warning(f"[ULTRA-DEBUG] Firebase token validation failed: {str(firebase_err)}")
            logging.info("[ULTRA-DEBUG] Attempting to validate as Google Service Account token...")

            # This will only succeed for tokens from the Gateway SA
            try:
                gateway_claims = validate_gateway_sa_token(token)
                logging.info(f"[ULTRA-DEBUG] Gateway SA token validation successful. Claims: {gateway_claims}")
                # We need to extract the end-user ID from the Gateway token
                # This is usually stored in custom claims
                if "sub" not in gateway_claims:
                    logging.warning("[ULTRA-DEBUG] Gateway token validation succeeded but missing subject claim")
                    return None, 401, "Invalid Gateway token: missing subject claim"

                gateway_sa_subject = gateway_claims.get("sub")
                logging.info(f"[ULTRA-DEBUG] Gateway SA subject: {gateway_sa_subject}")

                # Accept any service account in production
                # We're being called through the API Gateway, and the token has been validated,
                # so we can trust it regardless of the exact service account being used

                # Successfully authenticated via Gateway SA token
                logging.info(f"[ULTRA-DEBUG] Authenticated via Gateway SA: {gateway_sa_subject}")

                # Gateway SA token doesn't contain the Firebase user ID directly, so
                # we should reject the request if we're missing the userinfo header
                logging.warning("[ULTRA-DEBUG] Gateway SA token found but missing required userinfo header")
                logging.error(f"[ULTRA-DEBUG] All headers at failure: {all_headers}")
                return None, 401, "Missing required X-Endpoint-API-Userinfo or X-Apigateway-Api-Userinfo header"
            except Exception as gateway_err:
                logging.error(f"[ULTRA-DEBUG] Gateway SA token validation failed: {str(gateway_err)}")
                logging.error(f"[ULTRA-DEBUG] All headers at failure: {all_headers}")
                return None, 401, f"Invalid Gateway token: {str(gateway_err)}"
    except Exception as e:
        logging.error(f"[ULTRA-DEBUG] Error during token validation: {str(e)}")
        logging.error(f"[ULTRA-DEBUG] All headers at failure: {all_headers}")
        return None, 500, f"Error during token validation: {str(e)}"

    # At the end, log the result
    logging.info(f"[ULTRA-DEBUG] get_authenticated_user result: status_code={status_code}, error_message={error_message}, auth_context={auth_context}")

def _is_action_allowed(
    permissions_map: Dict[str, Set[str]],
    role: str,
    action: str
) -> bool:
    allowed_actions = permissions_map.get(role, set())
    return action in allowed_actions

def _check_case_permissions(db, user_id: str, req: PermissionCheckRequest) -> Tuple[bool, str]:
    # Handle creation/listing first (no resourceId)
    if req.action in ["create", "list"] and req.resourceType == TYPE_CASE:
        if not req.organizationId: # Individual case creation/listing
            logging.info(f"Individual Case: Owner {user_id} attempting action '{req.action}'. Allowed.")
            return True, "" # User can always create/list their own individual cases

        # Organization case creation/listing
        membership = get_membership_data(db, user_id, req.organizationId)
        user_role_in_org = membership.get("role") if membership else None
        if not user_role_in_org:
             return False, f"User {user_id} is not a member of organization {req.organizationId}."

        allowed_by_role = _is_action_allowed(PERMISSIONS[TYPE_CASE], user_role_in_org, req.action)
        if allowed_by_role:
            logging.info(f"Org Case: User {user_id} (Role: {user_role_in_org}) allowed action '{req.action}' in org {req.organizationId}.")
            return True, ""
        else:
            return False, f"User {user_id} (Role: {user_role_in_org}) does not have permission for action '{req.action}' on cases in org {req.organizationId}."

    # --- Existing Resource Checks (Requires resourceId) ---
    if not req.resourceId:
         return False, "resourceId is required for this action."

    case_data = get_document_data(db, "cases", req.resourceId)
    if not case_data:
        return False, f"Case {req.resourceId} not found."

    is_owner = case_data.get("userId") == user_id
    case_org_id = case_data.get("organizationId")

    # 1. Individual Case (no orgId)
    if not case_org_id:
        if is_owner:
            allowed = _is_action_allowed(PERMISSIONS[TYPE_CASE], ROLE_OWNER, req.action)
            if allowed:
                 return True, ""
            else:
                 return False, f"Action '{req.action}' not permitted for owner on individual case {req.resourceId}."
        else:
            return False, f"User {user_id} is not the owner of individual case {req.resourceId}."

    # 2. Organization Case (has orgId)
    membership = get_membership_data(db, user_id, case_org_id)
    user_role_in_org = membership.get("role") if membership else None

    # Check Owner permissions first (might override role limits)
    if is_owner:
        owner_allowed = _is_action_allowed(PERMISSIONS[TYPE_CASE], ROLE_OWNER, req.action)
        if owner_allowed:
            logging.info(f"Org Case: Owner {user_id} allowed action '{req.action}' on {req.resourceId}.")
            return True, ""

    # Check Role permissions
    if user_role_in_org:
        role_allowed = _is_action_allowed(PERMISSIONS[TYPE_CASE], user_role_in_org, req.action)

        if not role_allowed:
             return False, f"User {user_id} (Role: {user_role_in_org}) denied action '{req.action}' by role on org case {req.resourceId}."

        # Additional check for Staff: Must be assigned (unless it's read/list)
        if user_role_in_org == ROLE_STAFF and req.action not in ["read", "list", "create"]: # Allow reading/listing/creating assigned or unassigned
             assigned_user_id = case_data.get("assignedUserId")
             is_assigned = assigned_user_id == user_id
             if not is_assigned:
                 return False, f"Staff user {user_id} must be assigned to case {req.resourceId} for action '{req.action}'."
             else:
                 logging.info(f"Org Case: Assigned Staff {user_id} allowed action '{req.action}' on {req.resourceId}.")
                 return True, "" # Staff assigned and action allowed

        # Admin or other roles don't need assignment check if action is allowed by role
        logging.info(f"Org Case: User {user_id} (Role: {user_role_in_org}) allowed action '{req.action}' on {req.resourceId}.")
        return True, "" # Role grants permission

    # User is not owner and not member
    return False, f"User {user_id} is not owner or member of org {case_org_id} for case {req.resourceId}."


def _check_organization_permissions(db, user_id: str, req: PermissionCheckRequest) -> Tuple[bool, str]:
    org_id = req.resourceId if req.resourceId else req.organizationId # Use organizationId for create/list actions

    if not org_id:
        return False, "organizationId is required for this action."

    membership = get_membership_data(db, user_id, org_id)
    if not membership:
        return False, f"User {user_id} is not a member of organization {org_id}."

    user_role = membership.get("role")
    if not user_role:
        logging.warning(f"User {user_id} in org {org_id} has no role. Denying.")
        return False, f"User {user_id} has no role assigned in organization {org_id}."

    # Map potentially more granular user-facing actions to internal permission flags
    action_map = {
        "manage_members": ["addMember", "setMemberRole", "removeMember", "listMembers"],
         "addMember": ["manage_members"],
         "setMemberRole": ["manage_members"],
         "removeMember": ["manage_members"],
         "listMembers": ["manage_members", "read"], # Admins can manage, staff can read (view members)
         "create_case": ["create_case"],
         "list_cases": ["list_cases", "read"], # Staff can list cases if they can read org details
         "assign_case": ["assign_case"],
         "read": ["read"],
         "update": ["update"],
         "delete": ["delete"],
    }

    required_permissions = action_map.get(req.action, [req.action]) # Default to action itself if not mapped

    has_permission = False
    for perm in required_permissions:
        if _is_action_allowed(PERMISSIONS[TYPE_ORGANIZATION], user_role, perm):
            has_permission = True
            break # Found one required permission

    if has_permission:
        return True, ""
    else:
        return False, f"User {user_id} (Role: {user_role}) denied action '{req.action}' on organization {org_id}."


def _check_party_permissions(db, user_id: str, req: PermissionCheckRequest) -> Tuple[bool, str]:
     # Handle creation/listing first (no resourceId)
    if req.action in ["create", "list"] and req.resourceType == TYPE_PARTY:
         # User can always create/list their own parties
         return True, ""

    # --- Existing Resource Checks (Requires resourceId) ---
    if not req.resourceId:
        return False, "resourceId is required for this action."

    party_data = get_document_data(db, "parties", req.resourceId)
    if not party_data:
        return False, f"Party {req.resourceId} not found."

    is_owner = party_data.get("userId") == user_id
    allowed = is_owner and _is_action_allowed(PERMISSIONS[TYPE_PARTY], ROLE_OWNER, req.action)

    if allowed:
        return True, ""
    elif is_owner:
        return False, f"Action '{req.action}' is invalid for resource type '{req.resourceType}' even for the owner."
    else:
        return False, f"User {user_id} is not the owner of party {req.resourceId}."


def _check_document_permissions(db, user_id: str, req: PermissionCheckRequest) -> Tuple[bool, str]:
    if not req.resourceId:
         return False, "resourceId is required for this action."

    document_data = get_document_data(db, "documents", req.resourceId)
    if not document_data:
        return False, f"Document {req.resourceId} not found."

    case_id = document_data.get("caseId")
    if not case_id:
        logging.error(f"Document {req.resourceId} has no caseId. Denying.")
        return False, "Document has no associated case ID."

    action_map = {
        "read": "read",
        "delete": "delete"
    }
    required_case_action = action_map.get(req.action)

    if not required_case_action:
        return False, f"Action '{req.action}' on document type is not mapped to a case action."

    # Check permissions on the parent *case*
    case_ref = db.collection("cases").document(case_id)
    case_doc = case_ref.get()
    if not case_doc.exists:
        return False, f"Parent case {case_id} for document {req.resourceId} not found."

    case_permission_req = PermissionCheckRequest(
        resourceId=case_id,
        action=required_case_action,
        resourceType=TYPE_CASE,
        organizationId=case_doc.to_dict().get("organizationId") # Pass orgId for case check
    )

    logging.info(f"Checking doc perm by checking case perm: action='{required_case_action}' on case='{case_id}'")
    return _check_case_permissions(db, user_id, case_permission_req)


def check_permission(user_id: str, req: PermissionCheckRequest) -> Tuple[bool, str]:
    """Checks if a user has permission to perform an action. Returns (allowed, message)."""
    permission_check_functions = {
        TYPE_CASE: _check_case_permissions,
        TYPE_ORGANIZATION: _check_organization_permissions,
        TYPE_PARTY: _check_party_permissions,
        TYPE_DOCUMENT: _check_document_permissions,
    }
    try:
        db = _get_firestore_client()
        checker_func = permission_check_functions[req.resourceType]
        allowed, message = checker_func(db=db, user_id=user_id, req=req)

        log_message = (
            f"Permission check result: "
            f"userId={user_id}, resourceId={req.resourceId}, "
            f"resourceType={req.resourceType}, action={req.action}, "
            f"orgId={req.organizationId}, allowed={allowed}, message='{message}'"
        )
        logging.info(log_message)
        return allowed, message
    except KeyError:
        msg = f"No permission checker configured for resource type '{req.resourceType}'."
        logging.error(msg)
        return False, msg
    except Exception as e:
        logging.error(f"Error during permission check: {e}", exc_info=True)
        return False, f"An internal error occurred during permission check: {e}"


# Note: This function is designed to be called by the main.py entry point
# The main.py entry point handles the HTTP request/response and calls this logic.
def check_permissions(request: flask.Request):
    logging.info("Logic function check_permissions called")
    try:
        data = request.get_json(silent=True)
        if not data:
            return {"error": "Bad Request", "message": "Validation Failed: No JSON data provided"}, 400

        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return {"error": "Unauthorized", "message": error_message}, status_code
        user_id = user_data.firebase_user_id

        try:
            # Use model_validate for Pydantic v2
            req_data = PermissionCheckRequest.model_validate(data)
            logging.info(f"Validated permission check request for user {user_id}")
        except ValidationError as e:
            logging.error(f"Bad Request: Validation failed: {e}")
            return {"error": "Bad Request", "message": "Validation Failed", "details": e.errors()}, 400

        allowed, message = check_permission(user_id=user_id, req=req_data)

        return {"allowed": allowed, "message": message}, 200

    except Exception as e:
        logging.error(f"Error checking permissions: {str(e)}", exc_info=True)
        return {"error": "Internal Server Error", "message": "Failed to check permissions"}, 500


@functions_framework.http
@add_cors_headers
def validate_user(request: Request):
    """
    Validate a user's token and create a record if it doesn't exist.
    This function is called directly by the API Gateway.
    """
    try:
        # Handle CORS preflight requests
        if request.method == "OPTIONS":
            return "", 204

        auth_context, status_code, error_message = get_authenticated_user(request)
        logging.info(f"validate_user auth result: context={auth_context}, status={status_code}, error={error_message}")

        # Handle auth failures
        if error_message or not auth_context:
            return jsonify({"error": "Unauthorized", "message": error_message or "Authentication failed"}), status_code or 401

        # At this point auth_context is valid
        user_id = auth_context.firebase_user_id
        logging.info(f"validate_user: original user_id={user_id}")

        email = auth_context.firebase_user_email

        if not user_id:
            return jsonify({"error": "Bad Request", "message": "Missing user identification"}), 400

        # Create or update user record in Firestore
        db = _get_firestore_client()
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        logging.info(f"validate_user: Firestore lookup for user_id={user_id}, exists={user_doc.exists}")

        if not user_doc.exists:
            # Create new user
            user_data = {
                'user_id': user_id,
                'email': email or "",
                'created_at': datetime.datetime.now(),
                'updated_at': datetime.datetime.now()
            }
            user_ref.set(user_data)
            logging.info(f"Created new user record for {user_id}: {user_data}")
        else:
            # Update existing user
            update_data = {
                'updated_at': datetime.datetime.now(),
                # Only update email if provided and different
                **({"email": email} if email and email != user_doc.get('email') else {})
            }
            user_ref.update(update_data)
            logging.info(f"Updated existing user record for {user_id}: {update_data}")

        return jsonify({
            "user_id": user_id,
            "is_authenticated": True
        })

    except Exception as e:
        logging.error(f"Error in validate_user: {str(e)}")
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

# Note: This function is designed to be called by the main.py entry point
def get_user_role(request: flask.Request):
    logging.info("Logic function get_user_role called")
    try:
        data = request.get_json(silent=True)
        if not data:
             return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        target_user_id = data.get("userId") # User whose role we want to check
        organization_id = data.get("organizationId")

        if not target_user_id:
             return flask.jsonify({"error": "Bad Request", "message": "userId is required"}), 400
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "organizationId is required"}), 400

        # Authenticate the *requesting* user
        requesting_user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        requesting_user_id = requesting_user_data.firebase_user_id

        # Check if requesting user has permission to view roles in this org
        # (Unless they are checking their own role)
        if requesting_user_id != target_user_id:
             perm_check_req = PermissionCheckRequest(
                 resourceType=TYPE_ORGANIZATION,
                 resourceId=organization_id,
                 action="listMembers", # If user can list members, they can see roles
                 organizationId=organization_id
             )
             allowed, message = check_permission(requesting_user_id, perm_check_req)
             if not allowed:
                 logging.warning(f"User {requesting_user_id} tried to get role for {target_user_id} in org {organization_id} without permission.")
                 # Return a less specific error to the client
                 return flask.jsonify({"error": "Forbidden", "message": "Permission denied to view user roles for this organization."}), 403


        db = _get_firestore_client()
        membership_data = get_membership_data(db, target_user_id, organization_id)

        role = None
        if membership_data:
            role = membership_data.get("role")

        logging.info(f"Successfully retrieved role for user {target_user_id} in organization {organization_id}: {role}")
        return flask.jsonify({"role": role}), 200
    except Exception as e:
        logging.error(f"Error getting user role: {e}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": "Failed to get user role"}), 500

def validate_firebase_id_token(token: str) -> dict:
    """Validate a Firebase ID token.

    Args:
        token: The Firebase ID token to validate

    Returns:
        The decoded token payload if valid

    Raises:
        ValueError: If the token is invalid
    """
    # Use Google's firebase token verification
    request = google_auth_requests.Request()

    # Get the project ID from the environment
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "relexro")
    logging.info(f"[ULTRA-DEBUG] Validating Firebase token using project_id: {project_id}")
    logging.info(f"[ULTRA-DEBUG] Token to validate: {token[:30]}...{token[-30:]}")

    try:
        # Verify the token
        logging.info("[ULTRA-DEBUG] Calling verify_firebase_token...")
        decoded_token = google_id_token.verify_firebase_token(
            token,
            request,
            audience=project_id
        )

        if not decoded_token:
            logging.warning("[ULTRA-DEBUG] verify_firebase_token returned None")
            raise ValueError("Invalid Firebase token")

        logging.info(f"[ULTRA-DEBUG] Firebase token verified successfully. Token keys: {list(decoded_token.keys())}")

        # Verify that the token is from the expected issuer
        issuer = decoded_token.get("iss")
        expected_issuer = f"{EXPECTED_FIREBASE_ISSUER_PREFIX}{project_id}"
        logging.info(f"[ULTRA-DEBUG] Checking token issuer. Found: '{issuer}', Expected: '{expected_issuer}'")

        if not issuer:
            logging.warning("[ULTRA-DEBUG] Token is missing 'iss' claim")
            raise ValueError("Token is missing issuer claim")

        if issuer != expected_issuer:
            logging.warning(f"[ULTRA-DEBUG] Token issuer mismatch. Expected: '{expected_issuer}', Got: '{issuer}'")
            raise ValueError(f"Invalid token issuer: {issuer}")

        logging.info("[ULTRA-DEBUG] Firebase token issuer verification successful")
        return decoded_token

    except Exception as ve:
        logging.error(f"[ULTRA-DEBUG] Firebase token validation failed with Exception: {str(ve)}", exc_info=True)
        raise

def validate_gateway_sa_token(token: str) -> dict:
    """Validate a token issued by the API Gateway service account.

    Args:
        token: The ID token to validate

    Returns:
        The decoded token payload if valid

    Raises:
        ValueError: If the token is invalid
    """
    request = google_auth_requests.Request()
    logging.info("Validating Gateway Service Account token")

    try:
        # For Google-issued tokens, we don't have a fixed audience like with Firebase.
        # First, we need to extract the audience claim from the token to use it for validation.
        token_parts = token.split('.')
        logging.info(f"JWT token has {len(token_parts)} parts")

        if len(token_parts) != 3:
            logging.warning("Malformed JWT token: does not have 3 parts")
            raise ValueError("Malformed JWT token received in Authorization header")

        try:
            # Decode the payload (second segment) to read the audience
            logging.info("Decoding JWT payload to extract audience")

            # Add padding to the base64 string if needed
            # Base64 strings should have a length that is a multiple of 4
            # If not, add '=' characters as padding
            padding_needed = len(token_parts[1]) % 4
            padded_payload = token_parts[1]
            if padding_needed > 0:
                padded_payload += '=' * (4 - padding_needed)
                logging.info(f"Added {4 - padding_needed} padding characters to JWT payload")

            try:
                decoded_bytes = base64.urlsafe_b64decode(padded_payload)
                logging.info(f"Successfully base64 decoded JWT payload. Length: {len(decoded_bytes)} bytes")
            except Exception as decode_err:
                logging.error(f"Failed to base64 decode JWT payload: {str(decode_err)}")
                raise ValueError(f"Failed to decode JWT payload: {str(decode_err)}")

            try:
                decoded_str = decoded_bytes.decode('utf-8')
                logging.info(f"Successfully UTF-8 decoded JWT payload. Length: {len(decoded_str)} chars")
            except Exception as utf8_err:
                logging.error(f"Failed to UTF-8 decode JWT payload: {str(utf8_err)}")
                raise ValueError(f"Failed to decode JWT payload as UTF-8: {str(utf8_err)}")

            try:
                payload_json = json.loads(decoded_str)
                logging.info(f"Successfully JSON parsed JWT payload. Keys: {list(payload_json.keys())}")
            except Exception as json_err:
                logging.error(f"Failed to JSON parse JWT payload: {str(json_err)}")
                raise ValueError(f"Failed to parse JWT payload as JSON: {str(json_err)}")

            token_audience = payload_json.get('aud')
            logging.info(f"Extracted audience from token: '{token_audience}'")

            if not token_audience:
                logging.warning("Token is missing 'aud' claim")
                raise ValueError("Token missing 'aud' claim")

            # Now verify the token with the audience extracted above
            logging.info(f"Calling verify_oauth2_token with audience: '{token_audience}'")
            decoded_token = google_id_token.verify_oauth2_token(
                token,
                request,
                audience=token_audience
            )

            if not decoded_token:
                logging.warning("verify_oauth2_token returned None")
                raise ValueError("Invalid OAuth2 token")

            logging.info(f"Gateway SA token verified successfully. Token keys: {list(decoded_token.keys())}")
            return decoded_token

        except ValueError:
            # Re-raise ValueError exceptions
            raise

        except Exception as inner_e:
            # Convert other exceptions to ValueError with a message
            logging.error(f"Error processing JWT payload: {str(inner_e)}", exc_info=True)
            raise ValueError(f"Error processing JWT payload: {str(inner_e)}")

    except ValueError as ve:
        # Re-raise ValueError with the same message
        logging.warning(f"Gateway SA token validation failed with ValueError: {str(ve)}")
        raise

    except Exception as e:
        # Convert other exceptions to ValueError with a message
        logging.error(f"Gateway SA token validation failed with unexpected error: {str(e)}", exc_info=True)
        raise ValueError(f"Gateway SA token validation error: {str(e)}")

def requires_auth(func):
    """
    Decorator for Flask cloud function endpoints to require authentication.
    Passes the authenticated user to the decorated function.
    """
    @wraps(func)
    def wrapper(request: Request, *args, **kwargs):
        # Handle OPTIONS request for CORS
        if request.method == 'OPTIONS':
            return '', 204

        auth_context, status_code, error_message = get_authenticated_user(request)

        # If authentication failed, return an error
        if error_message or not auth_context:
            return jsonify({"error": "Unauthorized", "message": error_message or "Authentication failed"}), status_code or 401

        # Call the decorated function with the authenticated user context
        return func(request, auth_context, *args, **kwargs)

    return wrapper