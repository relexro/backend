"""
Agent Node Definitions
Defines all node functions for the workflow graph.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from pydantic import BaseModel, Field
from langgraph.graph import Graph, StateGraph, END
import json

from agent_tools import (
    check_quota,
    verify_payment,
    search_legal_database,
    get_relevant_legislation,
    update_quota_usage
)

from gemini_util import create_gemini_model, analyze_gemini_response
from agent_state import AgentState
from agent_config import load_system_prompt, get_system_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Node Functions
async def determine_tier_node(state: AgentState) -> AgentState:
    """
    Determine the appropriate pricing tier for the client.
    """
    try:
        logger.info("Processing determine_tier node")
        state.current_node = "determine_tier"
        # Use check_quota instead of determine_pricing_tier
        quota_result = await check_quota(state.user_id, state.organization_id if hasattr(state, 'organization_id') else None)
        state.tier = quota_result.get("subscription_tier", "basic")
        state.tier_details = quota_result
        logger.info(f"Determined tier: {state.tier}")
        return state
    except Exception as e:
        logger.error(f"Error in determine_tier_node: {str(e)}")
        state.has_error = True
        state.error_message = f"Failed to determine pricing tier: {str(e)}"
        return state

async def verify_payment_node(state: AgentState) -> AgentState:
    """
    Verify payment status for the case.
    """
    try:
        # Check payment status using verify_payment from agent_tools
        payment_status = await verify_payment(state.case_id)

        if not payment_status.get('paid', False):
            state.response_data = {
                'status': 'payment_required',
                'message': 'Este necesară plata pentru a continua.',
                'payment_details': payment_status['payment_details']
            }
            return state

        return state

    except Exception as e:
        logger.error(f"Error in verify_payment_node: {str(e)}")
        state.has_error = True
        state.error_message = f"Failed to verify payment: {str(e)}"
        return state

async def process_input_node(state: AgentState) -> AgentState:
    """
    Process user input and perform initial legal analysis.
    """
    try:
        # Process the input using gemini model
        model = create_gemini_model()
        system_prompt = get_system_prompt("legal_analysis")
        
        # Create user message from the input data
        user_message = f"Case details: {json.dumps(state.case_details)}"
        
        # Get response from Gemini
        response = await model.generate_content_async(
            system_prompt,
            user_message
        )
        
        # Process the response
        analysis_result = analyze_gemini_response(response, "legal_analysis")
        
        # Update state with analysis results
        state.input_analysis = {
            'legal_analysis': analysis_result,
            'timestamp': datetime.now().isoformat()
        }
        
        return state

    except Exception as e:
        logger.error(f"Error in process_input_node: {str(e)}")
        state.has_error = True
        state.error_message = f"Failed to process input: {str(e)}"
        return state

async def research_node(state: AgentState) -> AgentState:
    """
    Perform legal research based on analysis.
    """
    try:
        # Get analysis results
        analysis = state.input_analysis.get('legal_analysis', {})

        # Search legal database using the actual function from agent_tools
        search_query = f"domain:{analysis['domains']['main']} AND {' OR '.join(analysis.get('keywords', []))}"
        search_results = await search_legal_database(search_query)

        # Get relevant legislation using the actual function from agent_tools
        legislation = await get_relevant_legislation(analysis['domains']['main'])

        # Update state
        state.research_results = {
            'search_results': search_results,
            'legislation': legislation,
            'timestamp': datetime.now().isoformat()
        }

        return state

    except Exception as e:
        logger.error(f"Error in research_node: {str(e)}")
        state.has_error = True
        state.error_message = f"Failed to perform research: {str(e)}"
        return state

async def expert_consultation_node(state: AgentState) -> AgentState:
    """
    Consult with an expert for further analysis.
    """
    try:
        # Use Gemini model to simulate expert consultation
        model = create_gemini_model()
        system_prompt = get_system_prompt("expert_consultation")
        
        # Create user message with research context
        user_message = f"Research results: {json.dumps(state.research_results)}"
        
        # Get response from Gemini
        response = await model.generate_content_async(
            system_prompt,
            user_message
        )
        
        # Process the response
        expert_response = analyze_gemini_response(response, "expert_consultation")
        
        # Update state
        state.expert_consultation_results = {
            'expert_response': expert_response,
            'timestamp': datetime.now().isoformat()
        }

        return state

    except Exception as e:
        logger.error(f"Error in expert_consultation_node: {str(e)}")
        state.has_error = True
        state.error_message = f"Failed to consult expert: {str(e)}"
        return state

async def document_planning_node(state: AgentState) -> AgentState:
    """
    Plan and create a document.
    """
    try:
        # Use Gemini model for document planning
        model = create_gemini_model()
        system_prompt = get_system_prompt("document_planning")
        
        # Create user message with context
        user_message = f"""
        Research results: {json.dumps(state.research_results)}
        Expert consultation: {json.dumps(state.expert_consultation_results)}
        """
        
        # Get response from Gemini
        response = await model.generate_content_async(
            system_prompt,
            user_message
        )
        
        # Process the response
        document_plan = analyze_gemini_response(response, "document_planning")
        
        # Update state
        state.document_plan = document_plan

        return state

    except Exception as e:
        logger.error(f"Error in document_planning_node: {str(e)}")
        state.has_error = True
        state.error_message = f"Failed to plan document: {str(e)}"
        return state

async def document_generation_node(state: AgentState) -> AgentState:
    """
    Generate legal documents based on the document plan.
    """
    try:
        # Use Gemini model for document generation
        model = create_gemini_model()
        system_prompt = get_system_prompt("document_generation")
        
        # Create user message with document plan
        user_message = f"Document plan: {json.dumps(state.document_plan)}"
        
        # Get response from Gemini
        response = await model.generate_content_async(
            system_prompt,
            user_message
        )
        
        # Process the response
        generated_documents = analyze_gemini_response(response, "document_generation")
        
        # Update state
        state.generated_documents = generated_documents

        return state

    except Exception as e:
        logger.error(f"Error in document_generation_node: {str(e)}")
        state.has_error = True
        state.error_message = f"Failed to generate documents: {str(e)}"
        return state

async def final_review_node(state: AgentState) -> AgentState:
    """
    Perform final review of the generated documents.
    """
    try:
        # Use Gemini model for final review
        model = create_gemini_model()
        system_prompt = get_system_prompt("final_review")
        
        # Create user message with generated documents
        user_message = f"Generated documents: {json.dumps(state.generated_documents)}"
        
        # Get response from Gemini
        response = await model.generate_content_async(
            system_prompt,
            user_message
        )
        
        # Process the response
        review_result = analyze_gemini_response(response, "final_review")
        
        # Update state
        state.final_review_results = review_result
        
        # Update quota usage for the completed workflow
        await update_quota_usage(state.user_id)

        return state

    except Exception as e:
        logger.error(f"Error in final_review_node: {str(e)}")
        state.has_error = True
        state.error_message = f"Failed to perform final review: {str(e)}"
        return state

async def error_node(state: AgentState) -> AgentState:
    """
    Handle errors in the workflow.
    """
    try:
        logger.info(f"Processing error node for error in: {state.current_node}")
        
        # Increment retry count for the current node
        if state.current_node not in state.retry_count:
            state.retry_count[state.current_node] = 0
        state.retry_count[state.current_node] += 1
        
        # Log the error
        logger.error(f"Error in {state.current_node}: {state.error_message}")
        logger.info(f"Retry count for {state.current_node}: {state.retry_count[state.current_node]}")
        
        # Reset error flag for retry
        state.has_error = False
        state.error_message = ""
        
        return state
    except Exception as e:
        logger.error(f"Error in error_node: {str(e)}")
        state.error_message = f"Failed to process error node: {str(e)}"
        return state

def create_agent_graph() -> Graph:
    """
    Create and configure the LangGraph workflow using the absolute minimum approach.
    This stripped-down version focuses just on fixing the 'ValueError: Already found path for node error' issue.
    """
    # Create graph
    workflow = StateGraph(AgentState)

    # Add essential nodes
    workflow.add_node("determine_tier", determine_tier_node)
    workflow.add_node("verify_payment", verify_payment_node)
    workflow.add_node("process_input", process_input_node)
    workflow.add_node("final_review", final_review_node)
    workflow.add_node("error", error_node)
    
    # Set entry point
    workflow.set_entry_point("determine_tier")
    
    # Define minimal flow
    workflow.add_edge("determine_tier", "verify_payment")
    workflow.add_edge("verify_payment", "process_input")
    workflow.add_edge("process_input", "final_review")
    workflow.add_edge("final_review", END)
    
    # Error handling from each node - avoid conditions that might cause issues
    workflow.add_conditional_edges(
        "determine_tier",
        lambda state: "error" if state.get("has_error", False) else "continue",
        {
            "error": "error",
            "continue": "verify_payment"
        }
    )
    
    workflow.add_conditional_edges(
        "verify_payment",
        lambda state: "error" if state.get("has_error", False) else "continue",
        {
            "error": "error",
            "continue": "process_input"
        }
    )
    
    workflow.add_conditional_edges(
        "process_input",
        lambda state: "error" if state.get("has_error", False) else "continue",
        {
            "error": "error",
            "continue": "final_review"
        }
    )
    
    # Handle errors - no conditional branching to keep it simple
    workflow.add_edge("error", "determine_tier")  # Always retry from the beginning

    return workflow.compile()