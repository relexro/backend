import functions_framework
import logging
import firebase_admin
from firebase_admin import auth as firebase_auth_admin
from firebase_admin import firestore
import flask
from pydantic import BaseModel, ValidationError, validator, Field
from google.oauth2 import id_token
from google.auth.transport import requests as google_auth_requests  # Alias to avoid confusion with http 'requests'
import base64
import json
import os # To potentially get Cloud Run URL if passed as env var
from functools import wraps

# Changed field_validator to validator
from typing import Dict, Set, Tuple, Any, Literal, Optional

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

    # Changed field_validator to validator and removed @classmethod
    @validator('resourceType')
    def validate_resource_type(cls, v: str) -> str:
        if v not in VALID_RESOURCE_TYPES:
            raise ValueError(f"Invalid resourceType. Must be one of: {', '.join(VALID_RESOURCE_TYPES)}")
        return v

class AuthContext:
    def __init__(self, authenticated=False, user_id=None, email=None, email_verified=False, firebase_claims=None, authenticated_by=None, gateway_sa_verified=False, error_message=None, status_code=None):
        self.authenticated = authenticated
        self.user_id = user_id
        self.email = email
        self.email_verified = email_verified
        self.firebase_claims = firebase_claims
        self.authenticated_by = authenticated_by
        self.gateway_sa_verified = gateway_sa_verified
        self.error_message = error_message
        self.status_code = status_code

# Set the expected audience to the Cloud Run URL for relex-backend-get-user-profile
EXPECTED_GATEWAY_TOKEN_AUDIENCE = os.environ.get("SELF_SERVICE_URL") or "https://relex-backend-get-user-profile-dev-apmzkjwhqq-ew.a.run.app"
EXPECTED_GATEWAY_SA_EMAIL = "relex-functions-dev@relexro.iam.gserviceaccount.com"
EXPECTED_FIREBASE_ISSUER_PREFIX = "https://securetoken.google.com/"

def _get_firestore_client() -> firestore.Client:
    return firestore.client()

def get_document_data(db: firestore.Client, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
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
def get_membership_data(db: firestore.Client, user_id: str, org_id: str) -> Optional[Dict[str, Any]]:
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

def get_authenticated_user(request: flask.Request):
    """
    Authenticates the request based on the Relex backend auth flow:
    1. Validates the Google OIDC ID token from API Gateway (identifying the Gateway's SA).
    2. Extracts the original end-user's Firebase identity from 'X-Endpoint-API-Userinfo'.
    """
    # Dynamically construct the expected Firebase issuer using project_id from firebaseConfig
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "relexro") 
    expected_firebase_issuer = f"{EXPECTED_FIREBASE_ISSUER_PREFIX}{firebase_project_id}"

    # Fallback for audience if not set by env var (Planner will replace this if needed)
    current_expected_gateway_audience = EXPECTED_GATEWAY_TOKEN_AUDIENCE
    if not current_expected_gateway_audience:
        logging.warning("SELF_SERVICE_URL env var not set for Gateway token audience. Using placeholder to be replaced by Planner.")
        current_expected_gateway_audience = "YOUR_CLOUD_RUN_SERVICE_URL_PLACEHOLDER" # Planner to replace

    auth_context = AuthContext()

    # Step 1: Validate the Google OIDC ID token from API Gateway SA
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        auth_context.error_message = "Authorization token missing or malformed"
        auth_context.status_code = 401
        logging.warning(f"Auth failure: {auth_context.error_message}")
        return auth_context, 401, auth_context.error_message
    
    gateway_sa_token = auth_header.split('Bearer ')[1]
    if not gateway_sa_token:
        auth_context.error_message = "Empty token in Authorization header"
        auth_context.status_code = 401
        logging.warning(f"Auth failure: {auth_context.error_message}")
        return auth_context, 401, auth_context.error_message

    try:
        gateway_identity = google_oauth2_id_token.verify_oauth2_token(
            gateway_sa_token,
            google_auth_requests.Request(),
            audience=current_expected_gateway_audience 
        )
        auth_context.gateway_sa_verified = True
        logging.info(f"Gateway SA token successfully validated. SA email: {gateway_identity.get('email')}")

        # Optional: Check if the SA email is the expected one
        if gateway_identity.get('email') != EXPECTED_GATEWAY_SA_EMAIL:
            logging.warning(
                f"Caller SA '{gateway_identity.get('email')}' is not the expected Gateway SA '{EXPECTED_GATEWAY_SA_EMAIL}'. Proceeding with caution."
            )
    except ValueError as e:
        auth_context.error_message = f"Invalid Gateway SA token: {e}"
        auth_context.status_code = 401
        logging.error(f"Auth failure: {auth_context.error_message} (Audience checked: {current_expected_gateway_audience})")
        return auth_context, 401, auth_context.error_message
    except Exception as e: # Catch any other unexpected errors during SA token validation
        auth_context.error_message = f"Unexpected error validating Gateway SA token: {e}"
        auth_context.status_code = 500
        logging.error(f"Auth failure: {auth_context.error_message}", exc_info=True)
        return auth_context, 500, auth_context.error_message

    # Step 2: Extract and decode X-Endpoint-API-Userinfo header for end-user Firebase claims
    user_info_header = request.headers.get("X-Endpoint-API-Userinfo")
    if not user_info_header:
        auth_context.error_message = "X-Endpoint-API-Userinfo header missing"
        auth_context.status_code = 401 # If Gateway SA is valid, but user info is missing, it's an issue.
        logging.error(f"Auth failure: {auth_context.error_message}. Gateway SA was verified, but no end-user claims provided.")
        return auth_context, 401, auth_context.error_message

    try:
        # Add padding if necessary for base64 decoding
        padding = '=' * (-len(user_info_header) % 4)
        user_info_claims_str = base64.urlsafe_b64decode(user_info_header + padding).decode('utf-8')
        user_info_claims = json.loads(user_info_claims_str)
        auth_context.firebase_claims = user_info_claims
    except Exception as e:
        auth_context.error_message = f"Failed to decode X-Endpoint-API-Userinfo: {e}"
        auth_context.status_code = 400 # Bad request if header is malformed
        logging.error(f"Auth failure: {auth_context.error_message}. Header value: {user_info_header[:100]}...") # Log snippet
        return auth_context, 400, auth_context.error_message
    
    # Step 3: Extract and validate end-user details from decoded claims
    end_user_id = user_info_claims.get("sub") or user_info_claims.get("user_id")
    end_user_email = user_info_claims.get("email")
    firebase_token_issuer = user_info_claims.get("iss")

    if not end_user_id:
        auth_context.error_message = "User ID ('sub' or 'user_id') missing in X-Endpoint-API-Userinfo claims"
        auth_context.status_code = 401
        logging.error(f"Auth failure: {auth_context.error_message}. Claims: {user_info_claims}")
        return auth_context, 401, auth_context.error_message

    if firebase_token_issuer != expected_firebase_issuer:
        auth_context.error_message = (
            f"Issuer mismatch in X-Endpoint-API-Userinfo. Expected '{expected_firebase_issuer}', "
            f"got '{firebase_token_issuer}'"
        )
        auth_context.status_code = 401
        logging.error(f"Auth failure: {auth_context.error_message}. Claims: {user_info_claims}")
        return auth_context, 401, auth_context.error_message

    # If all checks pass for the end-user claims from X-Endpoint-API-Userinfo
    auth_context.authenticated = True
    auth_context.user_id = end_user_id
    auth_context.email = end_user_email
    auth_context.email_verified = user_info_claims.get("email_verified", False)
    auth_context.authenticated_by = "firebase_via_gateway_userinfo"
    auth_context.status_code = 200
    
    logging.info(f"Successfully authenticated end-user: {end_user_id} via X-Endpoint-API-Userinfo.")
    return auth_context, 200, None


def _is_action_allowed(
    permissions_map: Dict[str, Set[str]],
    role: str,
    action: str
) -> bool:
    allowed_actions = permissions_map.get(role, set())
    return action in allowed_actions

def _check_case_permissions(db: firestore.Client, user_id: str, req: PermissionCheckRequest) -> Tuple[bool, str]:
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


def _check_organization_permissions(db: firestore.Client, user_id: str, req: PermissionCheckRequest) -> Tuple[bool, str]:
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


def _check_party_permissions(db: firestore.Client, user_id: str, req: PermissionCheckRequest) -> Tuple[bool, str]:
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


def _check_document_permissions(db: firestore.Client, user_id: str, req: PermissionCheckRequest) -> Tuple[bool, str]:
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
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        user_id = user_data.user_id

        try:
            # Changed model_validate to parse_obj for Pydantic v1
            req_data = PermissionCheckRequest.parse_obj(data)
            logging.info(f"Validated permission check request for user {user_id}")
        except ValidationError as e:
            logging.error(f"Bad Request: Validation failed: {e}")
            return flask.jsonify({"error": "Bad Request", "message": "Validation Failed", "details": e.errors()}), 400

        allowed, message = check_permission(user_id=user_id, req=req_data)

        return flask.jsonify({"allowed": allowed, "message": message}), 200

    except Exception as e:
        logging.error(f"Error checking permissions: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": "Failed to check permissions"}), 500


# Note: This function is designed to be called by the main.py entry point
def validate_user(request: flask.Request):
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}
    user_data, status_code, error_message = get_authenticated_user(request)

    if status_code != 200:
        return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code, headers

    # Optionally fetch more user details from Firestore if needed
    # db = _get_firestore_client()
    # user_profile = get_document_data(db, "users", user_data["userId"])
    # combined_data = {**user_data, **(user_profile or {})}

    return flask.jsonify(user_data), 200, headers

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
        requesting_user_id = requesting_user_data.user_id

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