"""
Agent - Core implementation of the Relex Legal Assistant
"""
import logging
import firebase_admin
from firebase_admin import firestore
import functions_framework
from flask import Request
from agent_orchestrator import AgentOrchestrator
from common.database import db
from common.clients import get_db_client, get_storage_client, initialize_stripe

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_agent_request(request: Request):
    """
    Main entry point for handling agent requests.
    """
    logging.info("Agent request received")

    # Extract end_user_id from the request context set by the auth wrapper
    end_user_id = getattr(request, 'end_user_id', None)
    if not end_user_id:
        return {"error": "Unauthorized", "message": "User context is missing."}, 401
    
    # Extract caseId from query parameters
    case_id = request.args.get('caseId')
    if not case_id:
        return {"error": "Bad Request", "message": "caseId query parameter is required."}, 400

    # Create an instance of the orchestrator
    orchestrator = AgentOrchestrator(end_user_id=end_user_id, case_id=case_id)
    
    # Start the agent loop
    final_response = orchestrator.run()
    
    logging.info("Agent request processing complete")
    return final_response, 200
