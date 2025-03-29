import functions_framework
import json
import flask
import logging
from flask import Request

# Import function modules
from auth import validate_user, check_permissions, get_user_role, get_authenticated_user
from cases import create_case, get_case, list_cases, archive_case, delete_case, upload_file, download_file, attach_party_to_case, detach_party_from_case
from organization import create_organization, get_organization, add_organization_user, set_user_role, update_organization, list_organization_users, remove_organization_user
from chat import receive_prompt, send_to_vertex_ai, store_conversation, enrich_prompt
from payments import create_payment_intent, create_checkout_session, handle_stripe_webhook, cancel_subscription
from organization_membership import add_organization_member, set_organization_member_role, list_organization_members, remove_organization_member, get_user_organization_role, list_user_organizations
from user import get_user_profile, update_user_profile
from party import create_party, get_party, update_party, delete_party, list_parties

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Centralized authentication wrapper
def authenticate_request(request: Request):
    """Authenticate a request using Firebase token validation.
    
    Args:
        request (Request): The HTTP request
        
    Returns:
        tuple: (user_data, status_code, error_message)
    """
    user_data, status_code, error_message = get_authenticated_user(request)
    
    if status_code != 200:
        logging.error(f"Authentication failed: {error_message}")
        return None, status_code, error_message
    
    return user_data, 200, None

@functions_framework.http
def cases_create_case(request: Request):
    """HTTP Cloud Function for creating a case."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Call the business logic function
        return create_case(request)
    except Exception as e:
        logging.error(f"Error in cases_create_case: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_get_case(request: Request):
    """HTTP Cloud Function for retrieving a case by ID."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return get_case(request)
    except Exception as e:
        logging.error(f"Error in cases_get_case: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_list_cases(request: Request):
    """HTTP Cloud Function for listing cases."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return list_cases(request)
    except Exception as e:
        logging.error(f"Error in cases_list_cases: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_archive_case(request: Request):
    """HTTP Cloud Function for archiving a case."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return archive_case(request)
    except Exception as e:
        logging.error(f"Error in cases_archive_case: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_delete_case(request: Request):
    """HTTP Cloud Function for deleting a case."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return delete_case(request)
    except Exception as e:
        logging.error(f"Error in cases_delete_case: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_upload_file(request: Request):
    """HTTP Cloud Function for uploading a file to a case."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return upload_file(request)
    except Exception as e:
        logging.error(f"Error in cases_upload_file: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_download_file(request: Request):
    """HTTP Cloud Function for downloading a file."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return download_file(request)
    except Exception as e:
        logging.error(f"Error in cases_download_file: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def auth_validate_user(request):
    """HTTP Cloud Function for validating a user's token."""
    try:
        return validate_user(request)
    except Exception as e:
        logging.error(f"Error in auth_validate_user: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def auth_check_permissions(request):
    """HTTP Cloud Function for checking permissions."""
    try:
        return check_permissions(request)
    except Exception as e:
        logging.error(f"Error in auth_check_permissions: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def auth_get_user_role(request):
    """HTTP Cloud Function for retrieving a user's role in an organization."""
    try:
        return get_user_role(request)
    except Exception as e:
        logging.error(f"Error in auth_get_user_role: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_create_organization(request: Request):
    """HTTP Cloud Function for creating a new organization account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return create_organization(request)
    except Exception as e:
        logging.error(f"Error in organization_create_organization: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_get_organization(request: Request):
    """HTTP Cloud Function for retrieving an organization account by ID."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return get_organization(request)
    except Exception as e:
        logging.error(f"Error in organization_get_organization: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_update_organization(request: Request):
    """HTTP Cloud Function for updating an organization account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return update_organization(request)
    except Exception as e:
        logging.error(f"Error in organization_update_organization: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_add_organization_user(request):
    """HTTP Cloud Function for adding a user to an organization account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return add_organization_user(request)
    except Exception as e:
        logging.error(f"Error in organization_add_organization_user: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_set_user_role(request):
    """HTTP Cloud Function for updating a user's role in an organization."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return set_user_role(request)
    except Exception as e:
        logging.error(f"Error in organization_set_user_role: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_list_organization_users(request):
    """HTTP Cloud Function for listing users in an organization account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return list_organization_users(request)
    except Exception as e:
        logging.error(f"Error in organization_list_organization_users: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_remove_organization_user(request):
    """HTTP Cloud Function for removing a user from an organization account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return remove_organization_user(request)
    except Exception as e:
        logging.error(f"Error in organization_remove_organization_user: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def chat_receive_prompt(request):
    """HTTP Cloud Function for receiving a prompt from a user."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return receive_prompt(request)
    except Exception as e:
        logging.error(f"Error in chat_receive_prompt: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def chat_send_to_vertex_ai(request):
    """HTTP Cloud Function for sending a prompt to Vertex AI."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return send_to_vertex_ai(request)
    except Exception as e:
        logging.error(f"Error in chat_send_to_vertex_ai: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def chat_store_conversation(request):
    """HTTP Cloud Function for storing a conversation."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return store_conversation(request)
    except Exception as e:
        logging.error(f"Error in chat_store_conversation: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def chat_enrich_prompt(request):
    """HTTP Cloud Function for enriching a prompt with context."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return enrich_prompt(request)
    except Exception as e:
        logging.error(f"Error in chat_enrich_prompt: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def payments_create_payment_intent(request: Request):
    """HTTP Cloud Function for creating a Stripe Payment Intent."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return create_payment_intent(request)
    except Exception as e:
        logging.error(f"Error in payments_create_payment_intent: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def payments_create_checkout_session(request: Request):
    """HTTP Cloud Function for creating a Stripe Checkout Session."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return create_checkout_session(request)
    except Exception as e:
        logging.error(f"Error in payments_create_checkout_session: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def payments_handle_stripe_webhook(request: Request):
    """HTTP Cloud Function for handling Stripe webhook events."""
    try:
        # Webhook requests are not authenticated - they come directly from Stripe
        return handle_stripe_webhook(request)
    except Exception as e:
        logging.error(f"Error in payments_handle_stripe_webhook: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def payments_cancel_subscription(request: Request):
    """HTTP Cloud Function for canceling a Stripe subscription."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return cancel_subscription(request)
    except Exception as e:
        logging.error(f"Error in payments_cancel_subscription: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def org_membership_add_member(request: Request):
    """HTTP Cloud Function for adding a member to an organization."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return add_organization_member(request)
    except Exception as e:
        logging.error(f"Error in org_membership_add_member: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def org_membership_set_role(request: Request):
    """HTTP Cloud Function for setting a member's role in an organization."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return set_organization_member_role(request)
    except Exception as e:
        logging.error(f"Error in org_membership_set_role: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def user_get_profile(request: Request):
    """HTTP Cloud Function for retrieving the authenticated user's profile."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return get_user_profile(request)
    except Exception as e:
        logging.error(f"Error in user_get_profile: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def user_update_profile(request: Request):
    """HTTP Cloud Function for updating the authenticated user's profile."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        # Call the business logic function
        return update_user_profile(request)
    except Exception as e:
        logging.error(f"Error in user_update_profile: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def party_create_party(request: Request):
    """Create a new party."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return create_party(request)
    except Exception as e:
        logging.error(f"Error in party_create_party: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def party_get_party(request: Request):
    """Get a party by ID."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return get_party(request)
    except Exception as e:
        logging.error(f"Error in party_get_party: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def party_update_party(request: Request):
    """Update a party."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return update_party(request)
    except Exception as e:
        logging.error(f"Error in party_update_party: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def party_delete_party(request: Request):
    """Delete a party."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return delete_party(request)
    except Exception as e:
        logging.error(f"Error in party_delete_party: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def party_list_parties(request: Request):
    """HTTP Cloud Function for listing parties."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return list_parties(request)
    except Exception as e:
        logging.error(f"Error in party_list_parties: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_attach_party(request: Request):
    """HTTP Cloud Function for attaching a party to a case."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return attach_party_to_case(request)
    except Exception as e:
        logging.error(f"Error in cases_attach_party: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_detach_party(request: Request):
    """HTTP Cloud Function for detaching a party from a case."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = authenticate_request(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
        
        # Add user_id to request
        request.user_id = user_data["userId"]
        
        return detach_party_from_case(request)
    except Exception as e:
        logging.error(f"Error in cases_detach_party: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500
