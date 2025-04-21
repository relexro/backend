"""
Test suite for agent nodes and specialized domain nodes
"""
import pytest
from datetime import datetime
from typing import Dict, Any

from functions.src.agent_nodes import (
    AgentState,
    determine_tier_node,
    verify_payment_node,
    process_input_node,
    research_node,
    error_node
)
from functions.src.domain_nodes import (
    civil_law_node,
    commercial_law_node,
    administrative_law_node,
    labor_law_node
)

# Test fixtures
@pytest.fixture
def base_state():
    """Create a base AgentState for testing."""
    return AgentState(
        case_id="test_case_123",
        user_id="test_user_456",
        case_details={
            "title": "Test Case",
            "description": "Test case description"
        },
        user_info={
            "name": "Test User",
            "email": "test@example.com"
        }
    )

@pytest.fixture
def civil_case_state(base_state):
    """Create a state for civil law case testing."""
    base_state.input_analysis = {
        "legal_analysis": {
            "parties": ["John Doe", "Jane Smith"],
            "claim_value": 50000,
            "jurisdiction": "Bucharest",
            "multiple_parties": True,
            "international_elements": False,
            "precedent_cases": True
        }
    }
    return base_state

@pytest.fixture
def commercial_case_state(base_state):
    """Create a state for commercial law case testing."""
    base_state.input_analysis = {
        "legal_analysis": {
            "company_details": {
                "name": "Test Corp SRL",
                "registration": "J40/123/2020"
            },
            "contract_value": 500000,
            "business_domain": "banking",
            "multiple_jurisdictions": True
        }
    }
    return base_state

# Test core nodes
@pytest.mark.asyncio
async def test_determine_tier_node_with_quota():
    """Test tier determination with available quota."""
    state = AgentState(
        case_id="test_case",
        user_id="test_user",
        quota_status={"has_quota": True, "remaining_credits": 100}
    )

    next_node, updated_state = await determine_tier_node(state)

    assert next_node == "verify_payment"
    assert "determine_tier" in updated_state.completed_nodes
    assert updated_state.quota_status["has_quota"] is True

@pytest.mark.asyncio
async def test_determine_tier_node_without_quota():
    """Test tier determination without quota."""
    state = AgentState(
        case_id="test_case",
        user_id="test_user",
        quota_status={"has_quota": False, "required_credits": 50}
    )

    next_node, updated_state = await determine_tier_node(state)

    assert next_node == "end"
    assert updated_state.response_data["status"] == "quota_exceeded"

@pytest.mark.asyncio
async def test_error_node_with_retries():
    """Test error handling with retries."""
    state = AgentState(
        case_id="test_case",
        user_id="test_user",
        current_node="process_input",
        retry_count={"process_input": 1}
    )

    next_node, updated_state = await error_node(state)

    assert next_node == "process_input"
    assert updated_state.retry_count["process_input"] == 2

# Test domain-specific nodes
@pytest.mark.asyncio
async def test_civil_law_node_complex_case(civil_case_state):
    """Test civil law node with a complex case."""
    next_node, updated_state = await civil_law_node(civil_case_state)

    assert next_node == "expert_consultation"
    assert updated_state.input_analysis["domain_specific"]["type"] == "civil"
    assert updated_state.input_analysis["domain_specific"]["complexity_score"] >= 2

@pytest.mark.asyncio
async def test_commercial_law_node_high_value(commercial_case_state):
    """Test commercial law node with high-value contract."""
    next_node, updated_state = await commercial_law_node(commercial_case_state)

    assert next_node == "expert_consultation"
    assert updated_state.input_analysis["domain_specific"]["type"] == "commercial"
    assert updated_state.input_analysis["regulatory_requirements"]["industry"] == "banking"

@pytest.mark.asyncio
async def test_administrative_law_node_urgent():
    """Test administrative law node with urgent case."""
    state = AgentState(
        case_id="test_case",
        user_id="test_user",
        input_analysis={
            "legal_analysis": {
                "authority": "Local Council",
                "decision_details": "Building permit denial",
                "legal_basis": "Law 50/1991",
                "urgency": True,
                "public_interest": True
            }
        }
    )

    next_node, updated_state = await administrative_law_node(state)

    assert next_node == "expert_consultation"
    assert updated_state.input_analysis["domain_specific"]["urgent_procedure"] is True
    assert "cerere_suspendare" in updated_state.input_analysis["domain_specific"]["required_documents"]

@pytest.mark.asyncio
async def test_labor_law_node_discrimination():
    """Test labor law node with discrimination case."""
    state = AgentState(
        case_id="test_case",
        user_id="test_user",
        input_analysis={
            "legal_analysis": {
                "employer": "Company XYZ",
                "employee": "John Doe",
                "contract_type": "full_time",
                "discrimination": True,
                "workplace_safety": True
            }
        }
    )

    next_node, updated_state = await labor_law_node(state)

    assert next_node == "expert_consultation"
    assert updated_state.input_analysis["domain_specific"]["complexity_score"] == 3
    assert updated_state.input_analysis["domain_specific"]["special_conditions"]["discrimination"] is True

# Test error handling
@pytest.mark.asyncio
async def test_civil_law_node_missing_fields():
    """Test civil law node with missing required fields."""
    state = AgentState(
        case_id="test_case",
        user_id="test_user",
        input_analysis={
            "legal_analysis": {
                "parties": ["John Doe"]  # Missing claim_value and jurisdiction
            }
        }
    )

    next_node, updated_state = await civil_law_node(state)

    assert next_node == "error"
    assert len(updated_state.errors) == 1
    assert "Câmpuri obligatorii lipsă" in updated_state.errors[0]["error"]

# Test integration
@pytest.mark.asyncio
async def test_full_workflow_civil_case(civil_case_state):
    """Test full workflow for a civil case."""
    # Start with tier determination
    next_node, state = await determine_tier_node(civil_case_state)
    assert next_node == "verify_payment"

    # Process through civil law node
    next_node, state = await civil_law_node(state)
    assert next_node == "expert_consultation"

    # Verify state consistency
    assert "civil_law" in state.completed_nodes
    assert state.input_analysis["domain_specific"]["type"] == "civil"
    assert isinstance(state.input_analysis["domain_specific"]["complexity_score"], int)