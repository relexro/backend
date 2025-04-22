#
import logging
import firebase_admin
import functions_framework
from firebase_admin import firestore # Use Firestore from firebase_admin
from firebase_admin import auth as firebase_auth_admin  # Renamed to avoid conflict if needed
from flask import Request
import auth as local_auth_module # Import local auth module for get_authenticated_user

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK (if not already initialized)
# This should ideally run only once per instance.
try:
    firebase_admin.get_app()
except ValueError:
    # Use the application default credentials when running in GCP
    firebase_admin.initialize_app()

# Initialize Firestore client (using the client from firebase_admin)
db = firestore.client()

# NOTE: This function (`create_user_profile_trigger`) seems intended as a Firebase Authentication *trigger*,
#       not a standard HTTP function. It should be deployed differently.
#       Deploy Command: gcloud functions deploy FUNCTION_NAME --trigger-event=google.firebase.auth.user.create --runtime=python3XX ...
#       The signature and decorator below are for *HTTP* functions.
#       If this IS meant to be an Auth trigger, remove @functions_framework.http and use the correct trigger signature.
#       Keeping the HTTP structure for now based on original code, but flagging it as likely incorrect for its purpose.
#@functions_framework.http # <--- Likely INCORRECT decorator for an Auth trigger
#def create_user_profile(request: Request): # <--- Likely INCORRECT signature for an Auth trigger
# A typical Auth trigger signature looks like: def create_user_profile_trigger(event, context):
def create_user_profile_logic(user_record): # Separated logic for clarity or potential trigger use
    """
    Handles the creation of a user profile upon Firebase Auth user creation.
    Triggered by: providers/firebase.auth/eventTypes/user.create
    """
    # This function is currently deactivated as the corresponding Firebase Auth trigger
    # is not configured in the Terraform deployment. If the trigger is added,
    # uncomment and verify the logic below.
    pass
    # user_id = user_record.get('uid')
    # email = user_record.get('email') or "" # Handle missing email
    # display_name = user_record.get('displayName') or "" # Handle missing displayName
    # photo_url = user_record.get('photoURL') or "" # Handle missing photoURL
    #
    # logging.info(f"Creating user profile for new user: {user_id}")
    #
    # # Get Firestore user document reference
    # user_ref = db.collection("users").document(user_id)
    #
    # # Prepare user data for Firestore document
    # user_data = {
    #     "userId": user_id, # Store userId explicitly in the document
    #     "email": email,
    #     "displayName": display_name,
    #     "photoURL": photo_url,
    #     "role": "user", # Assign a default role
    #     "subscriptionStatus": None, # Initialize subscription status
    #     "languagePreference": "en", # Default language preference
    #     "createdAt": firestore.SERVER_TIMESTAMP, # Record creation time
    #     "updatedAt": firestore.SERVER_TIMESTAMP  # Also set updatedAt on creation
    # }
    #
    # # Write to Firestore (set will overwrite if doc somehow exists)
    # user_ref.set(user_data)
    #
    # logging.info(f"User profile created successfully for user: {user_id}")

# This is the HTTP function exposed via main.py
def get_user_profile(request: Request):
    """Retrieves the profile of the authenticated user.

    Args:
        request (flask.Request): HTTP request object. Expects 'user_id' attribute from wrapper.

    Returns:
        tuple: (response_body, status_code)
    """
    logging.info("Received request to get user profile")

    try:
        # The authentication wrapper in main.py should have already run and set request.user_id
        # We rely on that here. If not using the wrapper, call get_authenticated_user directly.
        user_id = getattr(request, 'user_id', None)

        if not user_id:
            # This indicates an issue with the authentication wrapper or function setup
            logging.error("Authorization Error: User ID not found in request context for get_user_profile.")
            # Return 401 as the user effectively isn't authenticated for this function's context
            return ({"error": "Unauthorized", "message": "User authentication context missing"}, 401)

        logging.info(f"Authenticated user for get_user_profile: {user_id}")

        # Get the user document from Firestore
        user_doc_ref = db.collection("users").document(user_id)
        user_doc = user_doc_ref.get()

        # Check if the user document exists
        if not user_doc.exists:
            logging.warning(f"User profile for {user_id} not found in Firestore.")
            # Potentially handle this case - maybe create a default profile if one is expected?
            # For now, return 404 Not Found.
            return ({"error": "Not Found", "message": "User profile not found"}, 404)

        # Get the user data from the document
        user_data = user_doc.to_dict()
        user_data["userId"] = user_id # Ensure userId is included in the response

        # Return the user profile data
        logging.info(f"Successfully retrieved profile for user: {user_id}")
        return (user_data, 200) # Return data and 200 OK

    except Exception as e:
        # Log unexpected errors
        logging.error(f"Error retrieving user profile for user {user_id if 'user_id' in locals() else 'UNKNOWN'}: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to retrieve user profile"}, 500)

# This is the HTTP function exposed via main.py
def update_user_profile(request: Request):
    """Updates the profile fields for the authenticated user.

    Args:
        request (flask.Request): HTTP request object with JSON body containing fields to update.
                                 Expects 'user_id' attribute from wrapper.

    Returns:
        tuple: (response_body, status_code)
    """
    logging.info("Received request to update user profile")

    try:
        # Rely on authentication wrapper in main.py to set user_id
        user_id = getattr(request, 'user_id', None)

        if not user_id:
            logging.error("Authorization Error: User ID not found in request context for update_user_profile.")
            return ({"error": "Unauthorized", "message": "User authentication context missing"}, 401)

        logging.info(f"Authenticated user for update_user_profile: {user_id}")

        # Extract JSON data from request body
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided for update")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)

        # Get user document reference
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get() # Check if profile exists before updating

        # Check if the user document exists
        if not user_doc.exists:
            logging.error(f"Not Found: User profile for {user_id} not found during update attempt")
            return ({"error": "Not Found", "message": "User profile not found"}, 404)

        # --- Field Validation ---
        # Define fields allowed for update and any validation rules
        updatable_fields = {"displayName", "photoURL", "languagePreference"}
        valid_languages = ["en", "ro", "fr", "de", "es"] # Example list, adjust as needed

        update_data = {} # Dictionary to hold validated fields for Firestore update
        ignored_fields = [] # Track fields that were requested but not allowed

        # Validate and extract fields to update
        if "displayName" in data:
            if not isinstance(data["displayName"], str):
                logging.error("Bad Request: displayName must be a string")
                return ({"error": "Bad Request", "message": "Display name must be a string"}, 400)
            # Allow empty string if needed by application logic
            update_data["displayName"] = data["displayName"]

        if "photoURL" in data:
            if not isinstance(data["photoURL"], str):
                logging.error("Bad Request: photoURL must be a string")
                return ({"error": "Bad Request", "message": "Photo URL must be a string"}, 400)
            # Basic validation - could add URL format check if needed
            # Allow empty string if user wants to remove photo URL
            update_data["photoURL"] = data["photoURL"]

        if "languagePreference" in data:
            lang_pref = data["languagePreference"]
            if not isinstance(lang_pref, str) or lang_pref not in valid_languages:
                logging.error(f"Bad Request: languagePreference '{lang_pref}' must be one of: {', '.join(valid_languages)}")
                return ({"error": "Bad Request", "message": f"Language preference must be one of: {', '.join(valid_languages)}"}, 400)
            update_data["languagePreference"] = lang_pref

        # Identify any requested fields that are not allowed to be updated
        for field in data:
            if field not in updatable_fields:
                ignored_fields.append(field)

        if ignored_fields:
             logging.warning(f"Ignoring attempts by user {user_id} to update non-allowed fields: {', '.join(ignored_fields)}")

        # Check if there are any valid fields to update
        if not update_data:
            logging.info(f"No valid fields provided to update for user: {user_id}")
            # Return 400 Bad Request as the request didn't contain actionable data
            return ({"error": "Bad Request", "message": "No valid fields provided for update"}, 400)

        # Add updatedAt timestamp to track the update time
        update_data["updatedAt"] = firestore.SERVER_TIMESTAMP

        # Update the document in Firestore
        user_ref.update(update_data)

        # Get the updated document to return the latest state
        updated_doc = user_ref.get() # Read after write
        updated_data = updated_doc.to_dict()
        updated_data["userId"] = user_id # Ensure userId is present

        # Return the updated profile data
        logging.info(f"Successfully updated profile for user: {user_id}")
        return (updated_data, 200) # 200 OK

    except Exception as e:
        # Log unexpected errors
        user_id_for_log = getattr(request, 'user_id', 'UNKNOWN') # Safely get user_id for logging
        logging.error(f"Error updating user profile for user {user_id_for_log}: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to update user profile"}, 500)