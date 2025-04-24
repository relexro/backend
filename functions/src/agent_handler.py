"""
Agent Handler - Main entry point for the Relex Legal Assistant
"""
import logging
from datetime import datetime
from agent import agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def logic_agent_handler(request):
    """Logic for the agent handler function.

    This function handles requests to the Lawyer AI Agent endpoint.
    It processes user messages, manages the agent state, and returns responses.

    The endpoint expects a POST request to /cases/{caseId}/agent/messages with a JSON body
    containing the user's message and any additional context.

    Args:
        request: The HTTP request object

    Returns:
        A JSON response containing the agent's reply and any additional data
    """
    # Parse request data
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return {
                'status': 'error',
                'message': 'No JSON data provided',
                'timestamp': datetime.now().isoformat()
            }, 400

        # Extract case ID from path parameters
        path_parts = request.path.split('/')
        case_id_index = path_parts.index('cases') + 1 if 'cases' in path_parts else -1

        if case_id_index == -1 or case_id_index >= len(path_parts):
            return {
                'status': 'error',
                'message': 'Invalid URL path. Expected /cases/{caseId}/agent/messages',
                'timestamp': datetime.now().isoformat()
            }, 400

        case_id = path_parts[case_id_index]
        user_message = request_json.get('message', '')
        user_id = getattr(request, 'user_id', request_json.get('user_id', 'anonymous'))

        # Prepare user info if available
        user_info = {}
        if hasattr(request, 'user_email'):
            user_info['email'] = request.user_email

        # Process the message using the agent
        return await agent.process_message(case_id, user_message, user_id, user_info)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in agent handler: {str(e)}\n{error_details}")
        return {
            'status': 'error',
            'message': f'Error processing agent request: {str(e)}',
            'error_details': error_details,
            'timestamp': datetime.now().isoformat()
        }, 500
