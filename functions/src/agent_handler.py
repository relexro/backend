"""
Agent Handler - Main entry point for the Relex Legal Assistant
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import asyncio
import json
from google.cloud import firestore
from pydantic import BaseModel

from agent_nodes import (
    AgentState,
    create_agent_graph
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentHandler:
    """Handles incoming requests and manages the LangGraph agent workflow."""

    def __init__(self):
        """Initialize the agent handler."""
        self.db = firestore.AsyncClient()
        self.agent_graph = create_agent_graph()

    async def handle_user_input(
        self,
        case_id: str,
        user_id: str,
        input_text: str,
        user_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle user input by initializing or restoring agent state and executing the graph.

        Args:
            case_id: The unique identifier for the case
            user_id: The unique identifier for the user
            input_text: The user's input text
            user_info: Optional additional user information

        Returns:
            Dict containing the agent's response and any generated documents
        """
        try:
            # Get or create case details
            case_ref = self.db.collection('cases').document(case_id)
            case_doc = await case_ref.get()

            if case_doc.exists:
                case_details = case_doc.to_dict()
                # Update with new input
                case_details['input'] = input_text
                case_details['last_updated'] = datetime.now().isoformat()
            else:
                case_details = {
                    'case_id': case_id,
                    'user_id': user_id,
                    'input': input_text,
                    'status': 'new',
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
                await case_ref.set(case_details)

            # Initialize agent state
            state = AgentState(
                case_id=case_id,
                user_id=user_id,
                case_details=case_details,
                user_info=user_info or {},
                messages=[{'role': 'user', 'content': input_text}]
            )

            # Execute the agent graph
            final_state = await self._execute_graph(state)

            # Save final state
            await self._save_state(final_state)

            return self._prepare_response(final_state)

        except Exception as e:
            logger.error(f"Error in handle_user_input: {str(e)}")
            return {
                'status': 'error',
                'message': 'A apărut o eroare în procesarea solicitării.',
                'error': str(e)
            }

    async def handle_payment_webhook(
        self,
        case_id: str,
        payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle payment webhook notifications and continue processing if payment is successful.

        Args:
            case_id: The case ID associated with the payment
            payment_data: Payment verification data

        Returns:
            Dict containing the processing status and next steps
        """
        try:
            # Get case details
            case_ref = self.db.collection('cases').document(case_id)
            case_doc = await case_ref.get()

            if not case_doc.exists:
                raise ValueError(f"Case {case_id} not found")

            case_details = case_doc.to_dict()

            # Verify payment status
            if not payment_data.get('status') == 'successful':
                return {
                    'status': 'error',
                    'message': 'Plata nu a fost confirmată.'
                }

            # Update case details with payment info
            case_details['payment_status'] = 'paid'
            case_details['payment_details'] = payment_data
            case_details['last_updated'] = datetime.now().isoformat()

            # Initialize state from saved details
            state = AgentState(
                case_id=case_id,
                user_id=case_details['user_id'],
                case_details=case_details,
                user_info=case_details.get('user_info', {})
            )

            # Execute graph from process_input node
            state.current_node = 'process_input'
            final_state = await self._execute_graph(state)

            # Save final state
            await self._save_state(final_state)

            return self._prepare_response(final_state)

        except Exception as e:
            logger.error(f"Error in handle_payment_webhook: {str(e)}")
            return {
                'status': 'error',
                'message': 'Eroare la procesarea plății.',
                'error': str(e)
            }

    async def _execute_graph(self, state: AgentState) -> AgentState:
        """
        Execute the LangGraph workflow with the given state.

        Args:
            state: The initial AgentState

        Returns:
            The final AgentState after graph execution
        """
        try:
            # Convert state to dict for graph input
            state_dict = state.dict()

            # Execute graph
            final_state_dict = await self.agent_graph.arun(state_dict)

            # Convert back to AgentState
            final_state = AgentState(**final_state_dict)

            return final_state

        except Exception as e:
            logger.error(f"Error in _execute_graph: {str(e)}")
            # Update state with error
            state.errors.append({
                'node': state.current_node,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            state.response_data = {
                'status': 'error',
                'message': 'Eroare la executarea workflow-ului.',
                'error_details': str(e)
            }
            return state

    async def _save_state(self, state: AgentState):
        """
        Save the agent state to case details in Firestore.

        Args:
            state: The AgentState to save
        """
        try:
            # Prepare state for saving
            save_data = {
                'last_updated': datetime.now().isoformat(),
                'current_node': state.current_node,
                'completed_nodes': state.completed_nodes,
                'execution_state': {
                    'quota_status': state.quota_status,
                    'input_analysis': state.input_analysis,
                    'research_results': state.research_results,
                    'ai_guidance': state.ai_guidance
                },
                'response_data': state.response_data,
                'errors': state.errors
            }

            # Update case document
            case_ref = self.db.collection('cases').document(state.case_id)
            await case_ref.update(save_data)

        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")

    def _prepare_response(self, state: AgentState) -> Dict[str, Any]:
        """
        Prepare the final response from the agent state.

        Args:
            state: The final AgentState

        Returns:
            Dict containing the response data
        """
        try:
            response = {
                'status': state.response_data.get('status', 'success'),
                'message': state.response_data.get('message'),
                'documents': state.response_data.get('documents', []),
                'completed_steps': state.completed_nodes,
                'timestamp': datetime.now().isoformat()
            }

            # Add error details if present
            if state.errors:
                response['errors'] = state.errors

            return response

        except Exception as e:
            logger.error(f"Error preparing response: {str(e)}")
            return {
                'status': 'error',
                'message': 'Eroare la pregătirea răspunsului.',
                'error': str(e)
            }

# Create singleton instance
agent_handler = AgentHandler()

async def handle_request(request_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process incoming requests based on type.

    Args:
        request_json: The request data

    Returns:
        Dict containing the response
    """
    try:
        request_type = request_json.get('type')

        if request_type == 'user_input':
            return await agent_handler.handle_user_input(
                case_id=request_json['case_id'],
                user_id=request_json['user_id'],
                input_text=request_json['input'],
                user_info=request_json.get('user_info')
            )
        elif request_type == 'payment_webhook':
            return await agent_handler.handle_payment_webhook(
                case_id=request_json['case_id'],
                payment_data=request_json['payment_data']
            )
        else:
            return {
                'status': 'error',
                'message': f'Tip de cerere nesuportat: {request_type}'
            }

    except Exception as e:
        logger.error(f"Error in handle_request: {str(e)}")
        return {
            'status': 'error',
            'message': 'Eroare la procesarea cererii.',
            'error': str(e)
        }

def cloud_function_handler(request) -> Dict[str, Any]:
    """
    Cloud Function entry point.

    Args:
        request: The cloud function request object

    Returns:
        Dict containing the response
    """
    try:
        # Parse request JSON
        request_json = request.get_json()

        # Create event loop and run request handler
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(handle_request(request_json))
        loop.close()

        return response

    except Exception as e:
        logger.error(f"Error in cloud_function_handler: {str(e)}")
        return {
            'status': 'error',
            'message': 'Eroare la procesarea cererii.',
            'error': str(e)
        }