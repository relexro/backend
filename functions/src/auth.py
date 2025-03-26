import functions_framework
import logging
import firebase_admin
from firebase_admin import auth
from firebase_admin import firestore
import json
import flask

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK (if not already initialized)
try:
    firebase_admin.get_app()
except ValueError:
    # Use the application default credentials
    firebase_admin.initialize_app()

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
            decoded_token = auth.verify_id_token(token)
            
            # Get user ID from the token
            user_id = decoded_token.get('uid')
            email = decoded_token.get('email', '')
            
            logging.info(f"Successfully validated token for user: {user_id}")
            return {"userId": user_id, "email": email}, 200, None
        except auth.InvalidIdTokenError as e:
            logging.error(f"Invalid token error: {str(e)}")
            return None, 401, f"Invalid token: {str(e)}"
        except auth.ExpiredIdTokenError:
            return None, 401, "Token expired"
        except auth.RevokedIdTokenError:
            return None, 401, "Token revoked"
        except auth.CertificateFetchError:
            return None, 401, "Certificate fetch error"
        except ValueError as e:
            return None, 401, str(e)
    except Exception as e:
        logging.error(f"Error validating user: {str(e)}")
        return None, 500, f"Failed to validate token: {str(e)}"

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
def check_permissions(request):
    """Check if a user can perform an action on a resource.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to check permissions")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "userId" not in data:
            logging.error("Bad Request: Missing userId")
            return ({"error": "Bad Request", "message": "userId is required"}, 400)
        
        if "resourceId" not in data:
            logging.error("Bad Request: Missing resourceId")
            return ({"error": "Bad Request", "message": "resourceId is required"}, 400)
        
        if "action" not in data:
            logging.error("Bad Request: Missing action")
            return ({"error": "Bad Request", "message": "action is required"}, 400)
        
        # Extract fields
        user_id = data["userId"]
        resource_id = data["resourceId"]
        action = data["action"]
        resource_type = data.get("resourceType", "case")
        organization_id = data.get("organizationId")
        
        # Validate action is supported
        valid_actions = ["read", "update", "delete", "upload_file", "manage_access", "create_case"]
        if action not in valid_actions:
            logging.error(f"Bad Request: Invalid action: {action}")
            return ({"error": "Bad Request", "message": f"Invalid action. Supported actions: {', '.join(valid_actions)}"}, 400)
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Simple permission check implementation
        allowed = False
        
        # For case resources
        if resource_type == "case":
            try:
                # Get the case document
                case_doc = db.collection("cases").document(resource_id).get()
                
                # Check if the case exists
                if case_doc.exists:
                    case_data = case_doc.to_dict()
                    
                    # If user is the case owner, they have full access
                    if case_data.get("userId") == user_id:
                        allowed = True
                        logging.info(f"User {user_id} is the owner of case {resource_id}. Access granted.")
                    # Check if this is an individual case (no organizationId)
                    elif case_data.get("organizationId") is None:
                        # For individual cases, only the owner has access
                        # This is a redundant check since we already checked if user is owner above,
                        # but it's explicit for clarity and future modifications
                        allowed = False
                        logging.info(f"Case {resource_id} is an individual case and user {user_id} is not the owner. Access denied.")
                    # If case is associated with an organization, check organization membership
                    elif case_data.get("organizationId"):
                        case_org_id = case_data.get("organizationId")
                        
                        # Query the organization_memberships collection
                        query = db.collection("organization_memberships").where("organizationId", "==", case_org_id).where("userId", "==", user_id).limit(1)
                        memberships = list(query.stream())
                        
                        if memberships:
                            membership_data = memberships[0].to_dict()
                            user_role = membership_data.get("role")
                            
                            # Administrator role has full access to case
                            if user_role == "administrator":
                                allowed = True
                                logging.info(f"User {user_id} is an administrator in organization {case_org_id}. Access granted for action {action} on case {resource_id}.")
                            # Staff role has limited access
                            elif user_role == "staff":
                                # Staff can read, update, and upload files, but cannot delete or manage access
                                if action in ["read", "update", "upload_file"]:
                                    allowed = True
                                    logging.info(f"User {user_id} is staff in organization {case_org_id}. Access granted for action {action} on case {resource_id}.")
                                else:
                                    logging.info(f"User {user_id} is staff in organization {case_org_id} but does not have permission for action {action} on case {resource_id}.")
                            else:
                                logging.info(f"User {user_id} has role {user_role} in organization {case_org_id} but does not have permission for action {action} on case {resource_id}.")
                        else:
                            logging.info(f"User {user_id} is not a member of organization {case_org_id}. Access denied.")
                else:
                    logging.error(f"Resource not found: Case with ID {resource_id} does not exist")
            except Exception as e:
                logging.error(f"Error checking case permissions: {str(e)}")
        
        # For organization resources
        elif resource_type == "organization":
            # For organization resources, resourceId is the organizationId
            organization_id = resource_id
            
            try:
                # Query the organization_memberships collection
                query = db.collection("organization_memberships").where("organizationId", "==", organization_id).where("userId", "==", user_id).limit(1)
                memberships = list(query.stream())
                
                if memberships:
                    membership_data = memberships[0].to_dict()
                    user_role = membership_data.get("role")
                    
                    # Administrator role has full access to the organization
                    if user_role == "administrator":
                        allowed = True
                        logging.info(f"User {user_id} is an administrator in organization {organization_id}. Access granted for action {action}.")
                    # Staff role has limited access to the organization
                    elif user_role == "staff":
                        # Staff can read organization information and create cases
                        if action in ["read", "create_case"]:
                            allowed = True
                            logging.info(f"User {user_id} is staff in organization {organization_id}. Access granted for action {action}.")
                        else:
                            logging.info(f"User {user_id} is staff in organization {organization_id} but does not have permission for action {action}.")
                    else:
                        logging.info(f"User {user_id} has role {user_role} in organization {organization_id} but does not have permission for action {action}.")
                else:
                    logging.info(f"User {user_id} is not a member of organization {organization_id}. Access denied.")
            except Exception as e:
                logging.error(f"Error checking organization permissions: {str(e)}")
        
        # Return the permission check result
        logging.info(f"Permission check: userId={user_id}, resourceId={resource_id}, resourceType={resource_type}, action={action}, allowed={allowed}")
        return ({"allowed": allowed}, 200)
    except Exception as e:
        logging.error(f"Error checking permissions: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to check permissions"}, 500)

@functions_framework.http
def get_user_role(request):
    """Retrieve a user's role in an organization.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to get user role")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "userId" not in data:
            logging.error("Bad Request: Missing userId")
            return ({"error": "Bad Request", "message": "userId is required"}, 400)
        
        if "organizationId" not in data:
            logging.error("Bad Request: Missing organizationId")
            return ({"error": "Bad Request", "message": "organizationId is required"}, 400)
        
        # Extract fields
        user_id = data["userId"]
        organization_id = data["organizationId"]
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Check if the organization exists
        organization_doc = db.collection("organizations").document(organization_id).get()
        if not organization_doc.exists:
            logging.error(f"Not Found: Organization with ID {organization_id} not found")
            return ({"error": "Not Found", "message": "Organization not found"}, 404)
        
        # Get the user's role in the organization
        user_role_doc = db.collection("organizations").document(organization_id).collection("users").document(user_id).get()
        
        # If user is not in the organization, return null role
        if not user_role_doc.exists:
            logging.info(f"User {user_id} has no role in organization {organization_id}")
            return ({"role": None}, 200)
        
        # Get the user's role
        user_role_data = user_role_doc.to_dict()
        role = user_role_data.get("role", None)
        
        # Return the user's role
        logging.info(f"Successfully retrieved role for user {user_id} in organization {organization_id}: {role}")
        return ({"role": role}, 200)
    except Exception as e:
        logging.error(f"Error getting user role: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to get user role"}, 500) 