import functions_framework
import flask

@functions_framework.http
def cases_create_case(request):
    """HTTP Cloud Function for creating a case."""
    return flask.jsonify({"status": "success", "message": "Function is working"}), 200 