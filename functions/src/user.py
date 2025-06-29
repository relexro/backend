#
import logging
import firebase_admin
import functions_framework
from firebase_admin import firestore # Use Firestore from firebase_admin
from firebase_admin import auth as firebase_auth_admin  # Renamed to avoid conflict if needed
from flask import Request
import auth as local_auth_module # Import local auth module for get_authenticated_user
import flask
import uuid
import datetime
from common.database import db
from common.clients import get_db_client

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK (if not already initialized)
# This should ideally run only once per instance.
try:
    firebase_admin.get_app()
except ValueError:
    # Use the application default credentials when running in GCP
    firebase_admin.initialize_app()

# Initialize Firestore client
# FIXED: use firestore.client() to get client from firebase-admin app
# db = firestore.client()

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
def get_user_profile(request: Request, user_id_for_profile):
    """Retrieves the profile of the authenticated user. If not found, creates it."""
    logging.info(f"logic_get_user_profile called for end_user_id: {user_id_for_profile}")

    if not user_id_for_profile:
        return flask.jsonify({"error": "Unauthorized", "message": "User authentication context missing"}), 401

    db = get_db_client()
    user_ref = db.collection('users').document(user_id_for_profile)
    user_doc = user_ref.get()

    if not user_doc.exists:
        # Try to get email and displayName from request context (set by auth)
        email = getattr(request, 'end_user_email', None)
        display_name = getattr(request, 'end_user_display_name', None)
        # Attempt to get locale from request context; this assumes the auth middleware populates it.
        user_locale = getattr(request, 'end_user_locale', None)

        preferred_language = "en"  # Default language
        if user_locale and isinstance(user_locale, str) and user_locale.lower().startswith("ro"):
            preferred_language = "ro"
            logging.info(f"Setting language preference to 'ro' based on user locale: {user_locale}")
        else:
            logging.info(f"Setting default language preference 'en'. User locale: {user_locale}")

        now = datetime.datetime.utcnow()
        user_data = {
            "userId": user_id_for_profile,
            "email": email or "",
            "displayName": display_name or "",
            "createdAt": now,
            "updatedAt": now,
            "role": "user",
            "subscriptionStatus": None,
            "languagePreference": preferred_language # Set based on locale or default
        }
        user_ref.set(user_data)
        logging.info(f"Created new user profile for {user_id_for_profile}: {user_data}")
        return flask.jsonify(user_data), 200

    user_data = user_doc.to_dict()
    user_data["userId"] = user_id_for_profile
    return flask.jsonify(user_data), 200

# This is the HTTP function exposed via main.py
def update_user_profile(request: Request, user_id_for_profile):
    """Updates the profile fields for the authenticated user.

    Args:
        request (flask.Request): HTTP request object with JSON body containing fields to update.
        user_id_for_profile (str): The Firebase UID of the end-user whose profile to update.

    Returns:
        tuple: (response_body, status_code)
    """
    logging.info(f"logic_update_user_profile called for end_user_id: {user_id_for_profile}")

    if not user_id_for_profile:
        return ({"error": "Bad Request", "message": "User ID for profile update is missing"}, 400)

    try:
        # Extract JSON data from request body
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided for update")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)

        # Get user document reference
        db = get_db_client()
        user_ref = db.collection("users").document(user_id_for_profile)
        user_doc = user_ref.get() # Check if profile exists before updating

        # Define fields allowed for update and any validation rules
        updatable_fields = {"displayName", "photoURL", "languagePreference"}
        valid_languages = ["en", "ro"] # Restricted to only English and Romanian

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
             logging.warning(f"Ignoring attempts by user {user_id_for_profile} to update non-allowed fields: {', '.join(ignored_fields)}")

        # Check if there are any valid fields to update
        if not update_data:
            logging.info(f"No valid fields provided to update for user: {user_id_for_profile}")
            # Return 400 Bad Request as the request didn't contain actionable data
            return ({"error": "Bad Request", "message": "No valid fields provided for update"}, 400)

        # Add updatedAt timestamp to track the update time
        update_data["updatedAt"] = firestore.SERVER_TIMESTAMP

        # Check if the user document exists
        if not user_doc.exists:
            return ({"error": "Not Found", "message": "User profile not found"}, 404)
        else:
            # Update the existing document in Firestore
            user_ref.update(update_data)

            # Get the updated document to return the latest state
            updated_doc = user_ref.get() # Read after write
            updated_data = updated_doc.to_dict()
            updated_data["userId"] = user_id_for_profile # Ensure userId is present

            # Return the updated profile data
            logging.info(f"Successfully updated profile for user: {user_id_for_profile}")
            return (updated_data, 200) # 200 OK

    except Exception as e:
        # Log unexpected errors
        logging.error(f"Error updating user profile for user {user_id_for_profile}: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to update user profile"}, 500)