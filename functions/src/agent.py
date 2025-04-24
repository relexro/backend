"""
Agent - Core implementation of the Relex Legal Assistant
"""
import logging
from datetime import datetime
import asyncio
from flask import Request
from google.cloud import firestore
from agent_orchestrator import create_agent_graph, AgentState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Agent:
    """
    Agent class that implements the core functionality of the Relex Legal Assistant.

    This class handles:
    - Processing user messages
    - Managing agent state
    - Executing the agent workflow graph
    - Saving responses to Firestore
    """

    def __init__(self):
        """Initialize the agent with required clients."""
        self.db = firestore.Client()
        self.agent_graph = create_agent_graph()

    async def process_message(self, case_id, user_message, user_id, user_info=None):
        """
        Process a user message and generate a response.

        Args:
            case_id: The ID of the case
            user_message: The message from the user
            user_id: The ID of the user
            user_info: Additional user information (optional)

        Returns:
            A dictionary containing the agent's response and metadata
        """
        try:
            # Get case details
            case_ref = self.db.collection('cases').document(case_id)
            case_doc = case_ref.get()

            if not case_doc.exists:
                return {
                    'status': 'error',
                    'message': f'Case {case_id} not found',
                    'timestamp': datetime.now().isoformat()
                }, 404

            case_details = case_doc.to_dict()

            # Get or initialize case processing state
            processing_state_ref = case_ref.collection('processing').document('agent_state')
            processing_state_doc = processing_state_ref.get()

            if processing_state_doc.exists:
                # Resume from existing state
                state_dict = processing_state_doc.to_dict()
                agent_state = AgentState.from_dict(state_dict)
            else:
                # Initialize new state
                agent_state = AgentState(
                    case_id=case_id,
                    user_id=user_id,
                    case_details={
                        **case_details,
                        'input': user_message  # Add current message to case details
                    },
                    user_info=user_info or {}
                )

            # Execute agent graph
            result = await self.agent_graph.execute(agent_state)

            # Save updated state
            processing_state_ref.set(agent_state.to_dict())

            # Save message to chat history
            chat_ref = case_ref.collection('chat').document()
            chat_ref.set({
                'message': user_message,
                'sender': 'user',
                'sender_id': user_id,
                'timestamp': firestore.SERVER_TIMESTAMP
            })

            # Save agent response to chat history
            agent_response = result.get('response', 'No response generated')
            agent_chat_ref = case_ref.collection('chat').document()
            agent_chat_ref.set({
                'message': agent_response,
                'sender': 'agent',
                'sender_id': 'agent',
                'timestamp': firestore.SERVER_TIMESTAMP,
                'metadata': {
                    'confidence_score': result.get('confidence_score', 0.0),
                    'execution_time': result.get('execution_time', 0.0),
                    'risks': result.get('risks', [])
                }
            })

            # Return response
            return {
                'status': 'success',
                'message': agent_response,
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'confidence_score': result.get('confidence_score', 0.0),
                    'execution_time': result.get('execution_time', 0.0),
                    'risks': result.get('risks', [])
                }
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error in agent processing: {str(e)}\n{error_details}")
            return {
                'status': 'error',
                'message': f'Error processing agent request: {str(e)}',
                'error_details': error_details,
                'timestamp': datetime.now().isoformat()
            }, 500

# Create a singleton instance
agent = Agent()

async def handle_agent_request(request: Request):
    """
    Top-level function to handle agent requests.

    This function takes a Flask request object, extracts the necessary information,
    and delegates to the Agent class for processing.

    Args:
        request: The Flask request object

    Returns:
        A JSON response containing the agent's reply and any additional data
    """
    try:
        # Parse request data
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
        logger.error(f"Error in agent request handler: {str(e)}\n{error_details}")
        return {
            'status': 'error',
            'message': f'Error processing agent request: {str(e)}',
            'error_details': error_details,
            'timestamp': datetime.now().isoformat()
        }, 500
