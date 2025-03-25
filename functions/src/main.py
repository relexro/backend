import functions_framework
from cases import create_case, get_case, list_cases, archive_case, delete_case
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
def test_function(request):
    """Test function to verify deployment."""
    return flask.jsonify({"status": "success", "message": "Test function is working!"}), 200
