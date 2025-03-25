import functions_framework
import logging
import firebase_admin
from firebase_admin import auth
from firebase_admin import firestore
import json

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
            user_id = decoded_token.get('uid')
            email = decoded_token.get('email', '')
            
            logging.info(f"Successfully validated token for user: {user_id}")
            return {"userId": user_id, "email": email}, 200, None
        except auth.InvalidIdTokenError:
            return None, 401, "Invalid token"
        except auth.ExpiredIdTokenError:
            return None, 401, "Token expired"
        except auth.RevokedIdTokenError:
            return None, 401, "Token revoked"
        except auth.CertificateFetchError:
            return None, 500, "Certificate fetch error"
        except ValueError as e:
            return None, 401, str(e)
    except Exception as e:
        logging.error(f"Error validating user: {str(e)}")
        return None, 500, f"Failed to validate token: {str(e)}"

@functions_framework.http
def validate_user(request):
    """Validate a user's authentication token.
    
    Args:
        request (flask.Request): HTTP request object with Authorization header.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to validate user token")
    
    try:
        # Extract the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            logging.error("Unauthorized: No Authorization header provided")
            return ({"error": "Unauthorized", "message": "No token provided"}, 401)
        
        # Check if the header starts with 'Bearer '
        if not auth_header.startswith('Bearer '):
            logging.error("Unauthorized: Invalid Authorization header format")
            return ({"error": "Unauthorized", "message": "Invalid token format"}, 401)
        
        # Extract the token
        token = auth_header.split('Bearer ')[1]
        if not token:
            logging.error("Unauthorized: Empty token")
            return ({"error": "Unauthorized", "message": "Empty token"}, 401)
        
        # Verify the token
        try:
            decoded_token = auth.verify_id_token(token)
            user_id = decoded_token.get('uid')
            email = decoded_token.get('email', '')
            
            logging.info(f"Successfully validated token for user: {user_id}")
            return ({"userId": user_id, "email": email}, 200)
        except auth.InvalidIdTokenError:
            logging.error("Unauthorized: Invalid token")
            return ({"error": "Unauthorized", "message": "Invalid token"}, 401)
        except auth.ExpiredIdTokenError:
            logging.error("Unauthorized: Expired token")
            return ({"error": "Unauthorized", "message": "Token expired"}, 401)
        except auth.RevokedIdTokenError:
            logging.error("Unauthorized: Revoked token")
            return ({"error": "Unauthorized", "message": "Token revoked"}, 401)
        except auth.CertificateFetchError:
            logging.error("Internal Server Error: Certificate fetch error")
            return ({"error": "Internal Server Error", "message": "Certificate fetch error"}, 500)
        except ValueError as e:
            logging.error(f"Unauthorized: {str(e)}")
            return ({"error": "Unauthorized", "message": str(e)}, 401)
    except Exception as e:
        logging.error(f"Error validating user: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to validate token"}, 500)

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
        
        # Validate action is supported
        valid_actions = ["read", "write", "delete"]
        if action not in valid_actions:
            logging.error(f"Bad Request: Invalid action: {action}")
            return ({"error": "Bad Request", "message": f"Invalid action. Supported actions: {', '.join(valid_actions)}"}, 400)
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the resource type from request if provided, default to "case"
        resource_type = data.get("resourceType", "case")
        
        # Simple permission check implementation
        allowed = False
        
        # For simplicity - check if the user is an admin
        try:
            # Get user role from user profile
            user_doc = db.collection("users").document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                # Admins have full access to all resources
                if user_data.get("role") == "admin":
                    allowed = True
        except Exception as e:
            logging.error(f"Error checking admin status: {str(e)}")
            # Continue with normal permission check
        
        # If not already allowed as admin, check direct ownership
        if not allowed and resource_type == "case":
            try:
                # Get the case document
                case_doc = db.collection("cases").document(resource_id).get()
                
                # Check if the case exists
                if case_doc.exists:
                    case_data = case_doc.to_dict()
                    # Check if the user owns the case
                    if case_data.get("userId") == user_id:
                        allowed = True
                    # Check business membership for business cases
                    elif case_data.get("businessId"):
                        business_id = case_data.get("businessId")
                        user_role_doc = db.collection("businesses").document(business_id).collection("users").document(user_id).get()
                        if user_role_doc.exists:
                            user_role_data = user_role_doc.to_dict()
                            # Business admins have full access, members have read access only
                            if user_role_data.get("role") == "admin":
                                allowed = True
                            elif user_role_data.get("role") == "member" and action == "read":
                                allowed = True
            except Exception as e:
                logging.error(f"Error checking resource ownership: {str(e)}")
                # Continue with default (not allowed)
        
        # Return the permission check result
        logging.info(f"Permission check: userId={user_id}, resourceId={resource_id}, action={action}, allowed={allowed}")
        return ({"allowed": allowed}, 200)
    except Exception as e:
        logging.error(f"Error checking permissions: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to check permissions"}, 500)

@functions_framework.http
def get_user_role(request):
    """Retrieve a user's role in a business.
    
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
        
        if "businessId" not in data:
            logging.error("Bad Request: Missing businessId")
            return ({"error": "Bad Request", "message": "businessId is required"}, 400)
        
        # Extract fields
        user_id = data["userId"]
        business_id = data["businessId"]
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Check if the business exists
        business_doc = db.collection("businesses").document(business_id).get()
        if not business_doc.exists:
            logging.error(f"Not Found: Business with ID {business_id} not found")
            return ({"error": "Not Found", "message": "Business not found"}, 404)
        
        # Get the user's role in the business
        user_role_doc = db.collection("businesses").document(business_id).collection("users").document(user_id).get()
        
        # If user is not in the business, return null role
        if not user_role_doc.exists:
            logging.info(f"User {user_id} has no role in business {business_id}")
            return ({"role": None}, 200)
        
        # Get the user's role
        user_role_data = user_role_doc.to_dict()
        role = user_role_data.get("role", None)
        
        # Return the user's role
        logging.info(f"Successfully retrieved role for user {user_id} in business {business_id}: {role}")
        return ({"role": role}, 200)
    except Exception as e:
        logging.error(f"Error getting user role: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to get user role"}, 500) 