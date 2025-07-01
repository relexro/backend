"""
Agent - Core implementation of the Relex Legal Assistant
"""
import logging
import firebase_admin
from firebase_admin import firestore
import functions_framework
from flask import Request
from agent_orchestrator import AgentGraph, AgentState
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
        return {"status": "error", "message": "Unauthorized: User context is missing."}, 401
    
    # Extract caseId from query parameters
    case_id = request.args.get('caseId')
    if not case_id:
        return {"status": "error", "message": "Bad Request: caseId query parameter is required."}, 400

    # Fetch the case from Firestore
    db_client = get_db_client()
    case_ref = db_client.collection("cases").document(case_id)
    case_doc = case_ref.get()
    if not case_doc.exists:
        return {"status": "error", "message": "Case not found."}, 404
    case_data = case_doc.to_dict()

    # Authorization: check if user is owner or org member
    is_owner = case_data.get("userId") == end_user_id
    org_id = case_data.get("organizationId")
    is_org_member = False
    if org_id:
        # Check organization membership
        membership_query = db_client.collection("organization_memberships").where("organizationId", "==", org_id).where("userId", "==", end_user_id).limit(1)
        memberships = list(membership_query.stream())
        is_org_member = bool(memberships)
    if not (is_owner or is_org_member):
        return {"status": "error", "message": "Forbidden: User does not have access to this case."}, 403

    # Parse the user's message from the request body
    try:
        body = request.get_json(silent=True)
        user_message = body.get("message") if body else None
    except Exception as e:
        logging.error(f"Failed to parse request body: {e}")
        return {"status": "error", "message": "Bad Request: Invalid JSON body."}, 400
    if not user_message:
        return {"status": "error", "message": "Bad Request: 'message' is required in the request body."}, 400

    # Prepare case_details and user_info for the agent
    case_details = case_data.copy()
    case_details["input"] = user_message
    user_info = {"id": end_user_id}

    # Create agent state
    state = AgentState(case_id=case_id, user_id=end_user_id, case_details=case_details, user_info=user_info)
    graph = AgentGraph()

    # Run the agent workflow (must run async)
    import asyncio
    try:
        final_response = asyncio.run(graph.execute(state))
        if not isinstance(final_response, dict):
            final_response = {"status": "error", "message": "Agent did not return a valid response."}
        if "status" not in final_response:
            final_response["status"] = "success"
        return final_response, 200
    except Exception as e:
        logging.error(f"Agent execution error: {e}")
        return {"status": "error", "message": str(e)}, 500
