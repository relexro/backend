"""
Test suite for agent nodes and specialized domain nodes
"""
import pytest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

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
from functions.src.gemini_util import analyze_gemini_response, build_gemini_contents

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

# Mock fixtures for external dependencies
@pytest.fixture
def mock_check_quota():
    """Mock the check_quota function from agent_nodes."""
    with patch('functions.src.agent_nodes.check_quota') as mock:
        mock.return_value = {
            'status': 'success',
            'available_requests': 100,
            'requires_payment': False,
            'subscription_tier': 'basic',
            'quota_limit': 100,
            'quota_used': 0
        }
        yield mock

@pytest.fixture
def mock_verify_payment():
    """Mock the verify_payment function from agent_nodes."""
    with patch('functions.src.agent_nodes.verify_payment') as mock:
        mock.return_value = {
            'paid': True,
            'payment_details': {
                'status': 'completed',
                'amount': 100,
                'currency': 'RON'
            }
        }
        yield mock

@pytest.fixture
def mock_search_legal_database():
    """Mock the search_legal_database function from agent_nodes."""
    with patch('functions.src.agent_nodes.search_legal_database') as mock:
        mock.return_value = {
            'status': 'success',
            'results': [
                {'title': 'Test Document 1', 'content': 'Test content 1'},
                {'title': 'Test Document 2', 'content': 'Test content 2'}
            ]
        }
        yield mock

@pytest.fixture
def mock_get_relevant_legislation():
    """Mock the get_relevant_legislation function from agent_nodes."""
    with patch('functions.src.agent_nodes.get_relevant_legislation') as mock:
        mock.return_value = {
            'status': 'success',
            'legislation': [
                {'title': 'Law 1', 'content': 'Law content 1'},
                {'title': 'Law 2', 'content': 'Law content 2'}
            ]
        }
        yield mock

@pytest.fixture
def mock_gemini_model():
    """Mock the create_gemini_model function as used in agent_nodes."""
    with patch('functions.src.agent_nodes.create_gemini_model') as mock:
        model_mock = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Legal analysis response"
        model_mock.generate_content_async = AsyncMock(return_value=mock_response)
        mock.return_value = model_mock
        yield mock

@pytest.fixture
def mock_analyze_gemini_response():
    """Mock the analyze_gemini_response function as used in agent_nodes."""
    with patch('functions.src.agent_nodes.analyze_gemini_response') as mock:
        mock.return_value = {
            'domains': {'main': 'civil', 'secondary': ['contract', 'property']},
            'keywords': ['contract', 'breach', 'damages'],
            'complexity': 'medium'
        }
        yield mock

# Test core nodes
@pytest.mark.asyncio
async def test_determine_tier_node_with_quota(mock_check_quota):
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
    # Verify the mock was called with the right arguments
    mock_check_quota.assert_called_once_with(state.user_id, None)

@pytest.mark.asyncio
async def test_determine_tier_node_without_quota(mock_check_quota):
    """Test tier determination without quota."""
    # Configure the mock to return a quota exceeded response
    mock_check_quota.return_value = {
        'status': 'success',
        'available_requests': 0,
        'requires_payment': True,
        'subscription_tier': 'basic',
        'quota_limit': 100,
        'quota_used': 100
    }

    state = AgentState(
        case_id="test_case",
        user_id="test_user",
        quota_status={"has_quota": False, "required_credits": 50}
    )

    next_node, updated_state = await determine_tier_node(state)

    assert next_node == "end"
    assert updated_state.response_data["status"] == "quota_exceeded"
    # Verify the mock was called with the right arguments
    mock_check_quota.assert_called_once_with(state.user_id, None)

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

@pytest.mark.asyncio
async def test_process_input_node(mock_gemini_model, mock_analyze_gemini_response):
    """Test processing user input with Gemini model."""
    # Setup
    state = AgentState(
        case_id="test_case",
        user_id="test_user",
        case_details={
            "title": "Contract dispute",
            "description": "Client is facing a breach of contract situation"
        }
    )

    # Configure mocks
    model_mock = mock_gemini_model.return_value
    mock_analyze_gemini_response.return_value = {
        "domains": {"main": "civil", "secondary": ["contract"]},
        "keywords": ["breach", "contract", "damages"],
        "complexity": "medium"
    }

    # Execute
    _, updated_state = await process_input_node(state)

    # Verify
    assert "legal_analysis" in updated_state.input_analysis
    assert updated_state.input_analysis["legal_analysis"]["domains"]["main"] == "civil"
    assert "timestamp" in updated_state.input_analysis

    # Verify mocks were called correctly
    mock_gemini_model.assert_called_once()
    model_mock.generate_content_async.assert_called_once()
    mock_analyze_gemini_response.assert_called_once()

# Test domain-specific nodes
@pytest.mark.asyncio
async def test_civil_law_node_complex_case(civil_case_state, mock_gemini_model, mock_analyze_gemini_response):
    """Test civil law node with a complex case."""
    next_node, updated_state = await civil_law_node(civil_case_state)

    assert next_node == "expert_consultation"
    assert updated_state.input_analysis["domain_specific"]["type"] == "civil"
    assert updated_state.input_analysis["domain_specific"]["complexity_score"] >= 2

@pytest.mark.asyncio
async def test_commercial_law_node_high_value(commercial_case_state, mock_gemini_model, mock_analyze_gemini_response):
    """Test commercial law node with high-value contract."""
    next_node, updated_state = await commercial_law_node(commercial_case_state)

    assert next_node == "expert_consultation"
    assert updated_state.input_analysis["domain_specific"]["type"] == "commercial"
    assert updated_state.input_analysis["regulatory_requirements"]["industry"] == "banking"

@pytest.mark.asyncio
async def test_administrative_law_node_urgent(mock_gemini_model, mock_analyze_gemini_response):
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
async def test_labor_law_node_discrimination(mock_gemini_model, mock_analyze_gemini_response):
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
async def test_civil_law_node_missing_fields(mock_gemini_model, mock_analyze_gemini_response):
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

@pytest.mark.asyncio
async def test_research_node(mock_search_legal_database, mock_get_relevant_legislation):
    """Test research node with mocked external services."""
    # Setup
    state = AgentState(
        case_id="test_case",
        user_id="test_user",
        input_analysis={
            "legal_analysis": {
                "domains": {"main": "civil", "secondary": ["contract"]},
                "keywords": ["breach", "contract", "damages"]
            }
        }
    )

    # Execute
    updated_state = await research_node(state)

    # Verify
    assert "search_results" in updated_state.research_results
    assert "legislation" in updated_state.research_results
    assert "timestamp" in updated_state.research_results

    # Verify mocks were called correctly
    mock_search_legal_database.assert_called_once()
    mock_get_relevant_legislation.assert_called_once_with("civil")

# Test integration
@pytest.mark.asyncio
async def test_full_workflow_civil_case(civil_case_state, mock_check_quota, mock_gemini_model,
                                       mock_analyze_gemini_response, mock_search_legal_database,
                                       mock_get_relevant_legislation):
    """Test full workflow for a civil case."""
    # Start with tier determination
    next_node, state = await determine_tier_node(civil_case_state)
    assert next_node == "verify_payment"
    mock_check_quota.assert_called_once_with(civil_case_state.user_id, None)

    # Process through civil law node
    next_node, state = await civil_law_node(state)
    assert next_node == "expert_consultation"

    # Verify state consistency
    assert "civil_law" in state.completed_nodes
    assert state.input_analysis["domain_specific"]["type"] == "civil"
    assert isinstance(state.input_analysis["domain_specific"]["complexity_score"], int)