import functions_framework
import logging
import firebase_admin
from firebase_admin import auth as firebase_auth_admin  # Renamed to avoid conflict
from firebase_admin import firestore
import flask
from pydantic import BaseModel, ValidationError, field_validator, Field
from typing import Dict, Set, Tuple, Any, Literal, Optional

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK (if not already initialized)
try:
    firebase_admin.get_app()
except ValueError:
    # Use the application default credentials
    firebase_admin.initialize_app()

# --- Constants and Configuration ---

# Define roles
ROLE_ADMIN = "administrator"
ROLE_STAFF = "staff"
ROLE_OWNER = "owner"  # Implicit role based on userId match

# Define resource types
TYPE_CASE = "case"
TYPE_ORGANIZATION = "organization" 
TYPE_PARTY = "party"
TYPE_DOCUMENT = "document"

# Define permissions mapping: resourceType -> role -> set(allowed_actions)
PERMISSIONS: Dict[str, Dict[str, Set[str]]] = {
    TYPE_CASE: {
        # Owner implicitly gets all relevant actions if they own the case
        ROLE_ADMIN: {
            "read", "update", "delete", "archive",
            "upload_file", "download_file",
            "attach_party", "detach_party",
            "assign_case",  # Admin can assign any org case
        },
        ROLE_STAFF: {
            # Staff permissions are further restricted by assignment
            "read", "update",
            "upload_file", "download_file",
            "attach_party", "detach_party",
        },
        ROLE_OWNER: {  # Actions owner can perform even if just Staff in org
            "read", "update", "delete", "archive",
            "upload_file", "download_file",
            "attach_party", "detach_party",
        }
    },
    TYPE_ORGANIZATION: {
        # Actions performed on the organization itself
        ROLE_ADMIN: {
            "read", "update", "delete",  # Org details
            "manage_members",  # Add/remove/change roles
            "create_case",  # Create a case belonging to this org
            "list_cases",  # List cases belonging to this org
            "assign_case",  # Assign org cases to staff
        },
        ROLE_STAFF: {
            "read",  # Read basic org details
            "create_case",
            "list_cases",  # List cases (filtered by assignment later)
        },
        # No owner concept for org actions, based on membership role
    },
    TYPE_PARTY: {
        # Only owner has permissions for parties they created
        ROLE_OWNER: {"read", "update", "delete"},
    },
    TYPE_DOCUMENT: {
        # Document permissions are derived from case permissions
        ROLE_ADMIN: {"read", "delete"},  # Requires corresponding case permission
        ROLE_STAFF: {"read"},          # Requires corresponding case permission (and assignment)
        ROLE_OWNER: {"read", "delete"},  # Requires corresponding case permission
    }
}

VALID_RESOURCE_TYPES = set(PERMISSIONS.keys())

# --- Input Validation Schema ---

class PermissionCheckRequest(BaseModel):
    resourceId: str
    action: str
    resourceType: str
    organizationId: Optional[str] = None  # Relevant for org cases/actions

    @field_validator('resourceType')
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        if v not in VALID_RESOURCE_TYPES:
            raise ValueError(f"Invalid resourceType. Must be one of: {', '.join(VALID_RESOURCE_TYPES)}")
        return v

# --- Firestore Interaction Helpers ---

def _get_firestore_client() -> firestore.Client:
    """Returns an initialized Firestore client."""
    return firestore.client()

def get_document_data(db: firestore.Client, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a Firestore document safely."""
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
    """Fetches organization membership for a user."""
    # TODO: Optimize with custom claims once implemented
    try:
        query = db.collection("organization_memberships").where(
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

# --- Authentication Helper ---

def get_authenticated_user(request):
    """Helper function to validate a user's authentication token and return user info.
    
    Args:
        request (flask.Request): HTTP request object with Authorization header.
        
    Returns:
        dict: User information if authenticated, None otherwise
        int: HTTP status code
        str: Error message (if any)
    """
    try:
        # Extract the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None, 401, "No authorization token provided"
        
        # Check if the header starts with 'Bearer '
        if not auth_header.startswith('Bearer '):
            return None, 401, "Invalid authorization header format"
        
        # Extract the token
        token = auth_header.split('Bearer ')[1]
        if not token:
            return None, 401, "Empty token"
        
        # Verify the token
        try:
            decoded_token = firebase_auth_admin.verify_id_token(token)
            
            # Get user ID from the token
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
            return None, 401, str(e)
    except Exception as e:
        logging.error(f"Error validating user: {str(e)}")
        return None, 500, f"Failed to validate token: {str(e)}"

# --- Permission Checking Logic ---

def _is_action_allowed(
    permissions_map: Dict[str, Set[str]],  # PERMISSIONS[resource_type]
    role: str,
    action: str
) -> bool:
    """Checks if a role has permission for a specific action."""
    allowed_actions = permissions_map.get(role, set())
    return action in allowed_actions

def _check_case_permissions(db: firestore.Client, user_id: str, req: PermissionCheckRequest) -> bool:
    """Checks permissions for 'case' resources."""
    case_data = get_document_data(db, "cases", req.resourceId)
    if not case_data:
        logging.warning(f"Permission denied: Case {req.resourceId} not found.")
        return False

    is_owner = case_data.get("userId") == user_id
    case_org_id = case_data.get("organizationId")  # Can be None for individual cases

    # 1. Check Individual Case Ownership (if orgId is None)
    if not case_org_id:
        if is_owner:
            # Owner of individual case can perform party owner actions + upload/download
            allowed = _is_action_allowed(PERMISSIONS[TYPE_CASE], ROLE_OWNER, req.action)
            logging.info(f"Individual Case: Owner {user_id} attempting action '{req.action}' on {req.resourceId}. Allowed: {allowed}")
            return allowed
        else:
            logging.info(f"Individual Case: User {user_id} is not owner of {req.resourceId}. Denied.")
            return False  # Only owner can access individual cases

    # 2. Check Organization Case Permissions (orgId is present)
    membership = get_membership_data(db, user_id, case_org_id)
    user_role_in_org = membership.get("role") if membership else None

    # Owner check (even within an org context, owner might have specific rights)
    if is_owner:
        allowed = _is_action_allowed(PERMISSIONS[TYPE_CASE], ROLE_OWNER, req.action)
        if allowed:
            logging.info(f"Org Case: Owner {user_id} allowed action '{req.action}' on {req.resourceId}.")
            return True
        # If owner check fails, fall through to role check

    # Role check (Admin / Staff)
    if user_role_in_org:
        allowed_by_role = _is_action_allowed(PERMISSIONS[TYPE_CASE], user_role_in_org, req.action)

        # Additional check for Staff: Must be assigned to the case
        if user_role_in_org == ROLE_STAFF and allowed_by_role:
            assigned_user_id = case_data.get("assignedUserId")
            is_assigned = assigned_user_id == user_id
            if not is_assigned:
                logging.info(f"Org Case: Staff {user_id} allowed action '{req.action}' by role, but not assigned to case {req.resourceId}. Denied.")
                return False  # Staff not assigned, deny access
            else:
                logging.info(f"Org Case: Assigned Staff {user_id} allowed action '{req.action}' on {req.resourceId}.")
                return True  # Staff assigned and action allowed by role
        elif allowed_by_role:
            # Admin doesn't need assignment check
            logging.info(f"Org Case: User {user_id} (Role: {user_role_in_org}) allowed action '{req.action}' on {req.resourceId}.")
            return True
        else:
            # Role doesn't grant permission
            logging.info(f"Org Case: User {user_id} (Role: {user_role_in_org}) denied action '{req.action}' on {req.resourceId}.")
            return False
    else:
        # User is not the owner and not a member of the organization
        logging.info(f"Org Case: User {user_id} is not owner and not member of org {case_org_id} for case {req.resourceId}. Denied.")
        return False

def _check_organization_permissions(db: firestore.Client, user_id: str, req: PermissionCheckRequest) -> bool:
    """Checks permissions for 'organization' resources."""
    org_id = req.resourceId  # For org resource, resourceId *is* the organizationId

    membership = get_membership_data(db, user_id, org_id)
    if not membership:
        logging.info(f"Permission denied: User {user_id} is not a member of organization {org_id}.")
        return False

    user_role = membership.get("role")
    if not user_role:
        logging.warning(f"User {user_id} is member of {org_id} but has no role assigned. Denying access.")
        return False

    allowed = _is_action_allowed(PERMISSIONS[TYPE_ORGANIZATION], user_role, req.action)

    if allowed:
        logging.info(f"User {user_id} (Role: {user_role}) allowed action '{req.action}' on organization {org_id}.")
    else:
        logging.warning(f"Permission denied: User {user_id} (Role: {user_role}) denied action '{req.action}' on organization {org_id}.")

    return allowed

def _check_party_permissions(db: firestore.Client, user_id: str, req: PermissionCheckRequest) -> bool:
    """Checks permissions for 'party' resources."""
    party_data = get_document_data(db, "parties", req.resourceId)
    if not party_data:
        logging.warning(f"Permission denied: Party {req.resourceId} not found.")
        return False

    is_owner = party_data.get("userId") == user_id
    allowed = is_owner and _is_action_allowed(PERMISSIONS[TYPE_PARTY], ROLE_OWNER, req.action)

    if allowed:
        logging.info(f"User {user_id} is owner of party {req.resourceId}. Action '{req.action}' allowed.")
    elif is_owner:
        logging.warning(f"User {user_id} is owner of party {req.resourceId}, but action '{req.action}' is invalid for resource type '{req.resourceType}'.")
    else:
        logging.info(f"Permission denied: User {user_id} is not the owner of party {req.resourceId}.")

    return allowed

def _check_document_permissions(db: firestore.Client, user_id: str, req: PermissionCheckRequest) -> bool:
    """Checks permissions for 'document' resources by checking permissions on the parent case."""
    document_data = get_document_data(db, "documents", req.resourceId)
    if not document_data:
        logging.warning(f"Permission denied: Document {req.resourceId} not found.")
        return False

    case_id = document_data.get("caseId")
    if not case_id:
        logging.error(f"Document {req.resourceId} has no associated caseId. Denying access.")
        return False

    # Map document action to required case action
    action_map = {
        "read": "read",
        "delete": "delete"
    }
    required_case_action = action_map.get(req.action)

    if not required_case_action:
        logging.warning(f"Action '{req.action}' on document type is not mapped to a case action. Denying.")
        return False

    # Create a modified request object to check permissions on the *case*
    case_permission_req = PermissionCheckRequest(
        resourceId=case_id,
        action=required_case_action,
        resourceType=TYPE_CASE
    )

    logging.info(f"Checking permission for document {req.resourceId} by checking action '{required_case_action}' on parent case {case_id}.")
    return _check_case_permissions(db, user_id, case_permission_req)

# --- Main Permission Check Function ---

@functions_framework.http
def check_permissions(request):
    """HTTP Cloud Function to check if a user can perform an action on a resource."""
    logging.info("Received request to check permissions")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400
        
        # Authenticate user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code

        user_id = user_data["userId"]
        
        # Validate input data using Pydantic
        try:
            # Add userId from token to request data - this ensures we check permissions
            # for the authenticated user, not an arbitrary userId that could be passed
            req_data = PermissionCheckRequest.model_validate(data)
            logging.info(f"Validated permission check request for user {user_id}")
        except ValidationError as e:
            logging.error(f"Bad Request: Validation failed: {e}")
            return flask.jsonify({"error": "Bad Request", "message": "Validation Failed", "details": e.errors()}), 400
        
        # Map resource types to their permission check functions
        permission_check_functions = {
            TYPE_CASE: _check_case_permissions,
            TYPE_ORGANIZATION: _check_organization_permissions,
            TYPE_PARTY: _check_party_permissions,
            TYPE_DOCUMENT: _check_document_permissions,
        }
        
        # Execute permission check
        try:
            db = _get_firestore_client()
            checker_func = permission_check_functions[req_data.resourceType]
            
            # Pass db client, authenticated user_id, and validated request data
            allowed = checker_func(db=db, user_id=user_id, req=req_data)
            
            log_message = (
                f"Permission check result: "
                f"userId={user_id}, resourceId={req_data.resourceId}, "
                f"resourceType={req_data.resourceType}, action={req_data.action}, "
                f"orgId={req_data.organizationId}, allowed={allowed}"
            )
            logging.info(log_message)
            return flask.jsonify({"allowed": allowed}), 200
            
        except KeyError:
            # Should not happen due to Pydantic validation
            logging.error(f"Internal Error: No permission checker for validated resource type '{req_data.resourceType}'.")
            return flask.jsonify({"error": "Internal Server Error", "message": "Invalid resource type configuration"}), 500
    except Exception as e:
        logging.error(f"Error checking permissions: {str(e)}")
        return flask.jsonify({"error": "Internal Server Error", "message": "Failed to check permissions"}), 500

# --- Other Auth Functions ---

@functions_framework.http
def validate_user(request):
    """HTTP Cloud Function to validate a user's token."""
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*'
    }
    
    user_data, status_code, error_message = get_authenticated_user(request)
    if status_code != 200:
        return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code, headers
    
    return flask.jsonify(user_data), 200, headers

@functions_framework.http
def get_user_role(request):
    """Retrieve a user's role in an organization."""
    logging.info("Received request to get user role")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400
        
        # Validate required fields
        if "userId" not in data:
            logging.error("Bad Request: Missing userId")
            return flask.jsonify({"error": "Bad Request", "message": "userId is required"}), 400
        
        if "organizationId" not in data:
            logging.error("Bad Request: Missing organizationId")
            return flask.jsonify({"error": "Bad Request", "message": "organizationId is required"}), 400
        
        # Extract fields
        user_id = data["userId"]
        organization_id = data["organizationId"]
        
        # Get the user's role in the organization
        db = _get_firestore_client()
        membership_data = get_membership_data(db, user_id, organization_id)
        
        role = None
        if membership_data:
            role = membership_data.get("role")
        
        # Return the user's role
        logging.info(f"Successfully retrieved role for user {user_id} in organization {organization_id}: {role}")
        return flask.jsonify({"role": role}), 200
    except Exception as e:
        logging.error(f"Error getting user role: {e}")
        return flask.jsonify({"error": "Internal Server Error", "message": "Failed to get user role"}), 500 