import logging
import firebase_admin
import functions_framework
from firebase_admin import firestore
from firebase_admin import auth as firebase_auth
from flask import Request
import auth  # Import our local auth module

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK (if not already initialized)
try:
    firebase_admin.get_app()
except ValueError:
    # Use the application default credentials
    firebase_admin.initialize_app()

# Note: The identity_fn decorator is commented out because it's not available in the current firebase_functions version
# We would use the on_user_created decorator from firebase_functions in a newer version
def create_user_profile(user_record):
    """Creates a user profile document in Firestore when a new user signs up.
    
    This function is triggered when a new user is created in Firebase Authentication.
    It creates a corresponding document in the Firestore 'users' collection to store
    application-specific user data.
    
    Args:
        user_record: The user record containing the user data.
    """
    try:
        user_id = user_record.uid
        email = user_record.email or ""
        display_name = user_record.display_name or ""
        photo_url = user_record.photo_url or ""
        
        logging.info(f"Creating user profile for new user: {user_id}")
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Create user profile document
        user_ref = db.collection("users").document(user_id)
        
        # Prepare user data
        user_data = {
            "userId": user_id,
            "email": email,
            "displayName": display_name,
            "photoURL": photo_url,
            "role": "user",
            "subscriptionStatus": None,
            "languagePreference": "en",
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        
        # Write to Firestore
        user_ref.set(user_data)
        
        logging.info(f"User profile created successfully for user: {user_id}")
    except Exception as e:
        logging.error(f"Error creating user profile: {str(e)}")
        # We don't raise the exception since we don't want the trigger to retry
        # as it might lead to duplicate attempts to create the user profile 

@functions_framework.http
def get_user_profile(request: Request):
    """Retrieves the profile of the authenticated user.
    
    Args:
        request (flask.Request): HTTP request object with Authorization header.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to get user profile")
    
    try:
        # Get the authenticated user
        user_info, status_code, error_message = auth.get_authenticated_user(request)
        
        if status_code != 200:
            logging.error(f"Unauthorized: {error_message}")
            return ({"error": "Unauthorized", "message": error_message}, status_code)
        
        user_id = user_info["userId"]
        logging.info(f"Authenticated user: {user_id}")
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the user document
        user_doc = db.collection("users").document(user_id).get()
        
        # Check if the user document exists
        if not user_doc.exists:
            logging.error(f"Not Found: User profile for {user_id} not found")
            return ({"error": "Not Found", "message": "User profile not found"}, 404)
        
        # Get the user data
        user_data = user_doc.to_dict()
        
        # Return the user profile
        logging.info(f"Successfully retrieved profile for user: {user_id}")
        return (user_data, 200)
    except Exception as e:
        logging.error(f"Error retrieving user profile: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to retrieve user profile"}, 500)

@functions_framework.http
def update_user_profile(request: Request):
    """Updates the profile of the authenticated user.
    
    Args:
        request (flask.Request): HTTP request object with Authorization header.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to update user profile")
    
    try:
        # Get the authenticated user
        user_info, status_code, error_message = auth.get_authenticated_user(request)
        
        if status_code != 200:
            logging.error(f"Unauthorized: {error_message}")
            return ({"error": "Unauthorized", "message": error_message}, status_code)
        
        user_id = user_info["userId"]
        logging.info(f"Authenticated user: {user_id}")
        
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the user document reference
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        # Check if the user document exists
        if not user_doc.exists:
            logging.error(f"Not Found: User profile for {user_id} not found")
            return ({"error": "Not Found", "message": "User profile not found"}, 404)
        
        # Validate and extract updatable fields
        updatable_fields = ["displayName", "photoURL", "languagePreference"]
        valid_languages = ["en", "ro", "fr", "de", "es"] # Add more as needed
        
        update_data = {}
        
        # Validate and add fields to update
        if "displayName" in data:
            if not isinstance(data["displayName"], str):
                logging.error("Bad Request: displayName must be a string")
                return ({"error": "Bad Request", "message": "Display name must be a string"}, 400)
            update_data["displayName"] = data["displayName"]
        
        if "photoURL" in data:
            if not isinstance(data["photoURL"], str):
                logging.error("Bad Request: photoURL must be a string")
                return ({"error": "Bad Request", "message": "Photo URL must be a string"}, 400)
            update_data["photoURL"] = data["photoURL"]
        
        if "languagePreference" in data:
            if not isinstance(data["languagePreference"], str) or data["languagePreference"] not in valid_languages:
                logging.error(f"Bad Request: languagePreference must be one of: {', '.join(valid_languages)}")
                return ({"error": "Bad Request", "message": f"Language preference must be one of: {', '.join(valid_languages)}"}, 400)
            update_data["languagePreference"] = data["languagePreference"]
        
        # Reject any attempt to update non-updatable fields
        for field in data:
            if field not in updatable_fields:
                logging.warning(f"Ignoring attempt to update non-updatable field: {field}")
        
        # If no valid fields to update, return an error
        if not update_data:
            logging.error("Bad Request: No valid fields to update")
            return ({"error": "Bad Request", "message": "No valid fields to update"}, 400)
        
        # Add updatedAt timestamp
        update_data["updatedAt"] = firestore.SERVER_TIMESTAMP
        
        # Update the document
        user_ref.update(update_data)
        
        # Get the updated document
        updated_doc = user_ref.get()
        updated_data = updated_doc.to_dict()
        
        # Return the updated profile
        logging.info(f"Successfully updated profile for user: {user_id}")
        return (updated_data, 200)
    except Exception as e:
        logging.error(f"Error updating user profile: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to update user profile"}, 500) 