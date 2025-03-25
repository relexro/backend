import functions_framework
from cases import create_case, get_case, list_cases, archive_case, delete_case, upload_file, download_file
from auth import validate_user, check_permissions, get_user_role
from business import create_business, get_business, add_business_user, set_user_role
from chat import receive_prompt, send_to_vertex_ai, store_conversation
import flask

@functions_framework.http
def cases_create_case(request):
    """HTTP Cloud Function for creating a case."""
    try:
        return create_case(request)
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
