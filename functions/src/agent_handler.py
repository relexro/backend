"""
Agent Handler - Main entry point for the Relex Legal Assistant
"""
import functions_framework
import flask
import logging
import os
import json
import sys
from datetime import datetime
from typing import Dict, Any, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Google Cloud authentication for AI services
# When running in Google Cloud, we use IAM service accounts for authentication
if os.environ.get('GOOGLE_CLOUD_PROJECT'):
    logger.info(f"Running in Google Cloud project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
    # We'll use the GEMINI_API_KEY from the secret environment variables
    if 'GEMINI_API_KEY' in os.environ:
        logger.info("GEMINI_API_KEY found in environment variables")
    else:
        logger.warning("GEMINI_API_KEY not found in environment variables. Gemini features will be disabled.")
else:
    logger.warning("Not running in Google Cloud. AI features may be limited.")

# Create a Flask app
app = flask.Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request() -> Union[flask.Response, tuple[flask.Response, int]]:
    """
    Handle incoming requests to the agent handler.

    Returns:
        Flask response with JSON data and appropriate status code
    """
    try:
        # Log request information
        logger.info(f"Received request: {flask.request.method} {flask.request.path}")

        # Parse request JSON
        request_json = flask.request.get_json(silent=True)

        if not request_json:
            logger.warning("No JSON data in request")
            return flask.jsonify({
                'status': 'error',
                'message': 'No JSON data provided',
            }), 400

        # Log request data (excluding sensitive info)
        logger.info(f"Request type: {request_json.get('type')}")

        # Simple response for now
        response: Dict[str, Any] = {
            'status': 'success',
            'message': 'Agent handler received request successfully',
            'request_type': request_json.get('type'),
            'timestamp': datetime.now().isoformat()
        }

        # Add environment info for debugging
        response['environment'] = {
            'python_version': os.environ.get('PYTHON_VERSION', 'unknown'),
            'function_region': os.environ.get('FUNCTION_REGION', 'unknown'),
            'function_name': os.environ.get('FUNCTION_NAME', 'unknown'),
            'port': os.environ.get('PORT', 'unknown')
        }

        return flask.jsonify(response)

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}", exc_info=True)
        return flask.jsonify({
            'status': 'error',
            'message': 'Invalid JSON format',
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error in agent_handler: {str(e)}", exc_info=True)
        return flask.jsonify({
            'status': 'error',
            'message': 'An error occurred while processing the request',
            'error': str(e)
        }), 500

@functions_framework.http
def relex_backend_agent_handler(request) -> Union[flask.Response, tuple[flask.Response, int]]:
    """
    Cloud Function entry point for the agent handler.

    Args:
        request: The HTTP request object from functions-framework

    Returns:
        Flask response with JSON data and appropriate status code
    """
    try:
        # Forward the request to the Flask app handler
        with app.test_request_context(method=request.method, path='/',
                                    json=request.get_json(silent=True),
                                    headers=request.headers):
            return handle_request()
    except Exception as e:
        logger.error(f"Error in Cloud Function entry point: {str(e)}", exc_info=True)
        return flask.jsonify({
            'status': 'error',
            'message': 'An error occurred in the Cloud Function entry point',
            'error': str(e)
        }), 500


if __name__ == "__main__":
    try:
        # Get the port from the environment variable
        port = int(os.environ.get('PORT', 8080))
        # Run the Flask app
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Error starting Flask app: {str(e)}", exc_info=True)
        sys.exit(1)
