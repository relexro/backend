import functions_framework
from cases import create_case, get_case, list_cases, archive_case, delete_case, upload_file, download_file
from auth import validate_user, check_permissions, get_user_role, get_authenticated_user
from business import create_business, get_business, add_business_user, set_user_role, update_business, list_business_users, remove_business_user
from chat import receive_prompt, send_to_vertex_ai, store_conversation, enrich_prompt
from payments import create_payment_intent, create_checkout_session
import flask
import json
import logging

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
    """HTTP Cloud Function for retrieving a user's role in a business."""
    try:
        return get_user_role(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

# Business Functions
@functions_framework.http
def business_create_business(request):
    """HTTP Cloud Function for creating a new business account."""
    try:
        return create_business(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def business_get_business(request):
    """HTTP Cloud Function for retrieving a business account by ID."""
    try:
        return get_business(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def business_add_business_user(request):
    """HTTP Cloud Function for adding a user to a business account."""
    try:
        return add_business_user(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def business_set_user_role(request):
    """HTTP Cloud Function for updating a user's role in a business."""
    try:
        return set_user_role(request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def business_update_business(request):
    """HTTP Cloud Function for updating a business account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return update_business(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def business_list_business_users(request):
    """HTTP Cloud Function for listing users in a business account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return list_business_users(modified_request)
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500

@functions_framework.http
def business_remove_business_user(request):
    """HTTP Cloud Function for removing a user from a business account."""
    try:
        # Authenticate the user
        user_data, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            
        # Add the authenticated user ID to the request
        modified_request = request.environ.get('werkzeug.request', request)
        modified_request.user_id = user_data.get('userId')
        
        return remove_business_user(modified_request)
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
