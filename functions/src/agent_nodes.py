"""
Agent Nodes - LangGraph-based nodes for the Relex Legal Assistant
"""
from typing import Dict, Any, List, Optional, TypeVar, Tuple
from datetime import datetime
import logging
from pydantic import BaseModel, Field
from langgraph.graph import Graph, StateGraph
from langgraph.prebuilt import ToolExecutor

from agent_tools import (
    check_quota,
    verify_payment,
    search_legal_database,
    get_relevant_legislation,
    update_quota_usage
)

# Import AgentState from llm_nodes to avoid circular dependency
from llm_nodes import AgentState

# Import LLM node functions
from llm_nodes import (
    legal_analysis_node,
    expert_consultation_node,
    document_planning_node,
    document_generation_node,
    final_review_node
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type for state
StateType = TypeVar("StateType", bound=Dict[str, Any])

async def determine_tier_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Determine the case tier and check quota.
    """
    try:
        # Check user quota
        quota_result = await check_quota(state.user_id)
        state.quota_status = quota_result

        if not quota_result['has_quota']:
            state.response_data = {
                'status': 'quota_exceeded',
                'message': 'Quota depășită. Vă rugăm să achiziționați credite suplimentare.',
                'required_credits': quota_result['required_credits']
            }
            return 'end', state

        state.completed_nodes.append('determine_tier')
        return 'verify_payment', state

    except Exception as e:
        logger.error(f"Error in determine_tier_node: {str(e)}")
        state.errors.append({
            'node': 'determine_tier',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def verify_payment_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Verify payment status for the case.
    """
    try:
        # Check payment status
        payment_status = await verify_payment(state.case_id)

        if not payment_status.get('paid', False):
            state.response_data = {
                'status': 'payment_required',
                'message': 'Este necesară plata pentru a continua.',
                'payment_details': payment_status['payment_details']
            }
            return 'end', state

        state.completed_nodes.append('verify_payment')
        return 'process_input', state

    except Exception as e:
        logger.error(f"Error in verify_payment_node: {str(e)}")
        state.errors.append({
            'node': 'verify_payment',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def process_input_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Process user input and perform initial legal analysis.
    """
    try:
        # Perform legal analysis
        next_node, updated_state = await legal_analysis_node(state)
        state = updated_state

        # Update quota usage
        await update_quota_usage(state.user_id, 'analysis')

        state.completed_nodes.append('process_input')
        return next_node, state

    except Exception as e:
        logger.error(f"Error in process_input_node: {str(e)}")
        state.errors.append({
            'node': 'process_input',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def research_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Perform legal research based on analysis.
    """
    try:
        # Get analysis results
        analysis = state.input_analysis.get('legal_analysis', {})

        # Search legal database
        search_query = f"domain:{analysis['domains']['main']} AND {' OR '.join(analysis.get('keywords', []))}"
        search_results = await search_legal_database(search_query)

        # Get relevant legislation
        legislation = await get_relevant_legislation(analysis['domains']['main'])

        # Update state
        state.research_results = {
            'search_results': search_results,
            'legislation': legislation,
            'timestamp': datetime.now().isoformat()
        }

        state.completed_nodes.append('research')
        return 'expert_consultation', state

    except Exception as e:
        logger.error(f"Error in research_node: {str(e)}")
        state.errors.append({
            'node': 'research',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def error_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Handle errors and determine retry strategy.
    """
    try:
        current_node = state.current_node
        retry_count = state.retry_count.get(current_node, 0)

        if retry_count < 2:  # Allow up to 2 retries
            # Increment retry count
            state.retry_count[current_node] = retry_count + 1
            logger.info(f"Retrying node {current_node}, attempt {retry_count + 1}")
            return current_node, state

        # If max retries reached, prepare error response
        state.response_data = {
            'status': 'error',
            'message': 'Ne pare rău, a apărut o eroare. Am creat un tichet de suport pentru rezolvarea problemei.',
            'support_ticket': {
                'case_id': state.case_id,
                'errors': state.errors
            }
        }
        return 'end', state

    except Exception as e:
        logger.error(f"Error in error_node: {str(e)}")
        state.response_data = {
            'status': 'critical_error',
            'message': 'Eroare critică în procesarea cererii.'
        }
        return 'end', state

def create_agent_graph() -> Graph:
    """
    Create and configure the LangGraph workflow.
    """
    # Create graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("determine_tier", determine_tier_node)
    workflow.add_node("verify_payment", verify_payment_node)
    workflow.add_node("process_input", process_input_node)
    workflow.add_node("research", research_node)
    workflow.add_node("expert_consultation", expert_consultation_node)
    workflow.add_node("document_planning", document_planning_node)
    workflow.add_node("generate_documents", document_generation_node)
    workflow.add_node("final_review", final_review_node)
    workflow.add_node("error", error_node)

    # Define edges
    workflow.add_edge("start", "determine_tier")
    workflow.add_edge("determine_tier", "verify_payment")
    workflow.add_edge("verify_payment", "process_input")
    workflow.add_edge("process_input", "research")
    workflow.add_edge("research", "expert_consultation")
    workflow.add_edge("expert_consultation", "document_planning")
    workflow.add_edge("document_planning", "generate_documents")
    workflow.add_edge("generate_documents", "final_review")
    workflow.add_edge("final_review", "end")

    # Error handling edges
    workflow.add_edge("error", "determine_tier")
    workflow.add_edge("error", "verify_payment")
    workflow.add_edge("error", "process_input")
    workflow.add_edge("error", "research")
    workflow.add_edge("error", "expert_consultation")
    workflow.add_edge("error", "document_planning")
    workflow.add_edge("error", "generate_documents")
    workflow.add_edge("error", "final_review")
    workflow.add_edge("error", "end")

    # Conditional edges based on analysis
    workflow.add_conditional_edges(
        "process_input",
        lambda x: x["current_node"],
        {
            "expert_consultation": lambda x: x["input_analysis"].get("legal_analysis", {}).get("complexity", {}).get("level", 1) >= 2,
            "document_planning": lambda x: x["input_analysis"].get("legal_analysis", {}).get("complexity", {}).get("level", 1) < 2
        }
    )

    return workflow.compile()