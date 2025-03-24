import functions_framework
import flask

# Import the create_case function
from cases import create_case

@functions_framework.http
def cases_create_case(request):
    """HTTP Cloud Function for creating a case."""
    response = create_case(request)
    # Handle the returned tuple correctly
    if isinstance(response, tuple) and len(response) == 2:
        resp_data, status_code = response
        if isinstance(resp_data, dict):
            return flask.jsonify(resp_data), status_code
        else:
            return str(resp_data), status_code
    return response 