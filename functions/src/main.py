import functions_framework
import json
import flask
import logging

# Import function modules
from auth import validate_user, check_permissions, get_user_role, get_authenticated_user
from cases import create_case, get_case, list_cases, archive_case, delete_case, upload_file, download_file
from organization import create_organization, get_organization, add_organization_user, set_user_role, update_organization, list_organization_users, remove_organization_user
from chat import receive_prompt, send_to_vertex_ai, store_conversation, enrich_prompt
from payments import create_payment_intent, create_checkout_session, handle_stripe_webhook
from organization_membership import add_organization_member, set_organization_member_role, list_organization_members, remove_organization_member, get_user_organization_role, list_user_organizations

# Initialize logging
logging.basicConfig(level=logging.INFO)

@functions_framework.http
def cases_create_case(request):
    """HTTP Cloud Function for creating a case."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request JSON
        if request.is_json:
            request_json = request.get_json()
        else:
            request_json = {}
            
        # Create a new request with the user ID added
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
            
        # Call the create_case function with the authenticated user
        return create_case(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_get_case(request):
    """HTTP Cloud Function for retrieving a case by ID."""
    try:
        return get_case(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_list_cases(request):
    """HTTP Cloud Function for listing cases."""
    try:
        return list_cases(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_archive_case(request):
    """HTTP Cloud Function for archiving a case."""
    try:
        return archive_case(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_delete_case(request):
    """HTTP Cloud Function for marking a case as deleted."""
    try:
        return delete_case(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_upload_file(request):
    """HTTP Cloud Function for uploading a file to a case."""
    try:
        return upload_file(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def cases_download_file(request):
    """HTTP Cloud Function for downloading a file."""
    try:
        return download_file(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def test_function(request):
    """Test function to verify deployment."""
    return flask.jsonify({"status": "success", "message": "Test function is working!"}), 200

# Auth Functions
@functions_framework.http
def auth_validate_user(request):
    """HTTP Cloud Function for validating a user's authentication token."""
    try:
        return validate_user(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def auth_check_permissions(request):
    """HTTP Cloud Function for checking a user's permissions for a resource."""
    try:
        return check_permissions(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def auth_get_user_role(request):
    """HTTP Cloud Function for retrieving a user's role in an organization."""
    try:
        return get_user_role(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

# Organization Functions (renamed from Business Functions)
@functions_framework.http
def organization_create_organization(request):
    """HTTP Cloud Function for creating a new organization account."""
    try:
        return create_organization(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_get_organization(request):
    """HTTP Cloud Function for retrieving an organization account by ID."""
    try:
        return get_organization(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_add_organization_user(request):
    """HTTP Cloud Function for adding a user to an organization account."""
    try:
        return add_organization_user(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_set_user_role(request):
    """HTTP Cloud Function for updating a user's role in an organization."""
    try:
        return set_user_role(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_update_organization(request):
    """HTTP Cloud Function for updating an organization account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return update_organization(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_list_organization_users(request):
    """HTTP Cloud Function for listing users in an organization account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return list_organization_users(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_remove_organization_user(request):
    """HTTP Cloud Function for removing a user from an organization account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return remove_organization_user(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

# Chat Functions
@functions_framework.http
def chat_receive_prompt(request):
    """HTTP Cloud Function for receiving a prompt from a user."""
    try:
        return receive_prompt(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def chat_send_to_vertex_ai(request):
    """HTTP Cloud Function for sending a prompt to Vertex AI."""
    try:
        return send_to_vertex_ai(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def chat_store_conversation(request):
    """HTTP Cloud Function for storing a conversation."""
    try:
        return store_conversation(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def chat_enrich_prompt(request):
    """HTTP Cloud Function for enriching a prompt with context."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return enrich_prompt(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

# Payment Functions
@functions_framework.http
def payments_create_payment_intent(request):
    """HTTP Cloud Function for creating a Stripe Payment Intent."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return create_payment_intent(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def payments_create_checkout_session(request):
    """HTTP Cloud Function for creating a Stripe Checkout Session."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return create_checkout_session(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

# Organization Membership Functions
@functions_framework.http
def organization_membership_add_organization_member(request):
    """HTTP Cloud Function for adding a member to an organization."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return add_organization_member(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_membership_set_organization_member_role(request):
    """HTTP Cloud Function for setting a member's role in an organization."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return set_organization_member_role(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_membership_list_organization_members(request):
    """HTTP Cloud Function for listing members of an organization."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return list_organization_members(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_membership_remove_organization_member(request):
    """HTTP Cloud Function for removing a member from an organization."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return remove_organization_member(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_membership_get_user_organization_role(request):
    """HTTP Cloud Function for getting a user's role in an organization."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return get_user_organization_role(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def organization_membership_list_user_organizations(request):
    """HTTP Cloud Function for listing organizations a user belongs to."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return list_user_organizations(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500
