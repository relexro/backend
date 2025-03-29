import functions_framework
import logging
import firebase_admin
from firebase_admin import auth as firebase_auth_admin
from firebase_admin import firestore
import flask
from pydantic import BaseModel, ValidationError, field_validator, Field
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
            "manage_members", "addUser", "setRole", "removeUser", "listUsers", # Consolidated member actions
            "create_case",
            "list_cases",
            "assign_case",
        },
        ROLE_STAFF: {
            "read",
            "create_case",
            "list_cases",
            "listUsers" # Allow staff to see other members
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

    @field_validator('resourceType')
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        if v not in VALID_RESOURCE_TYPES:
            raise ValueError(f"Invalid resourceType. Must be one of: {', '.join(VALID_RESOURCE_TYPES)}")
        return v

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
        query = db.collection("organizationMembers").where( # Corrected collection name
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

def get_authenticated_user(request):
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None, 401, "No authorization token provided"
        if not auth_header.startswith('Bearer '):
            return None, 401, "Invalid authorization header format"
        token = auth_header.split('Bearer ')[1]
        if not token:
            return None, 401, "Empty token"
        try:
            decoded_token = firebase_auth_admin.verify_id_token(token)
            user_id = decoded_token.get('uid')
            email = decoded_token.get('email', '')
            logging.info(f"Successfully validated token for user: {user_id}")
            return {"userId": user_id, "email": email}, 200, None
        except firebase_auth_admin.InvalidIdTokenError as e:
            logging.error(f"Invalid token error: {str(e)}")
            return None, 401, f"Invalid token: {str(e)}"
        except firebase_auth_admin.ExpiredIdTokenError:
            return None, 401, "Token expired"
        except firebase_auth_admin.RevokedIdTokenError:
            return None, 401, "Token revoked"
        except firebase_auth_admin.CertificateFetchError:
            return None, 401, "Certificate fetch error"
        except ValueError as e:
            # Handle potential errors during token decoding not caught by specific exceptions
            logging.error(f"Token verification value error: {str(e)}")
            return None, 401, f"Token verification error: {str(e)}"
    except Exception as e:
        logging.error(f"Error validating user: {str(e)}", exc_info=True)
        return None, 500, f"Failed to validate token: {str(e)}"


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
        "manage_members": ["addUser", "setRole", "removeUser", "listUsers"],
         "addUser": ["manage_members"],
         "setRole": ["manage_members"],
         "removeUser": ["manage_members"],
         "listUsers": ["manage_members", "read"], # Admins can manage, staff can read (view members)
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
        user_id = user_data["userId"]

        try:
            req_data = PermissionCheckRequest.model_validate(data)
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
        requesting_user_id = requesting_user_data["userId"]

        # Check if requesting user has permission to view roles in this org
        # (Unless they are checking their own role)
        if requesting_user_id != target_user_id:
             perm_check_req = PermissionCheckRequest(
                 resourceType=TYPE_ORGANIZATION,
                 resourceId=organization_id,
                 action="listUsers", # If user can list users, they can see roles
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