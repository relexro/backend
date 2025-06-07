import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from functions.src.agent_orchestrator import AgentState, AgentGraph, create_agent_graph
from functions.src.agent_tools import (
    query_bigquery,
    get_party_id_by_name,
    generate_draft_pdf,
    check_quota,
    get_case_details,
    update_case_details,
    create_support_ticket,
    consult_grok
)
from functions.src.template_validation import ValidationError
from functions.src.draft_templates import DraftTemplates
from functions.src.response_templates import format_response

# Test data
MOCK_CASE_DETAILS = {
    "input": "I need help with a rental agreement dispute in Bucharest.",
    "case_id": "case_123",
    "user_id": "user_456"
}

MOCK_USER_INFO = {
    "name": "Test User",
    "email": "test@example.com"
}

@pytest.fixture
def mock_agent_state():
    """Create a test AgentState instance."""
    return AgentState(
        case_id="case_123",
        user_id="user_456",
        case_details=MOCK_CASE_DETAILS,
        user_info=MOCK_USER_INFO
    )

@pytest.fixture
def mock_agent_graph():
    """Create a test AgentGraph instance with mocked dependencies."""
    with patch("functions.src.agent_orchestrator.DraftTemplates") as mock_draft_gen:
        graph = AgentGraph()
        graph.draft_generator = mock_draft_gen.return_value
        return graph

@pytest.mark.asyncio
async def test_agent_state_initialization():
    """Test AgentState initialization and basic properties."""
    state = AgentState(
        case_id="case_123",
        user_id="user_456",
        case_details=MOCK_CASE_DETAILS,
        user_info=MOCK_USER_INFO
    )
    
    assert state.case_id == "case_123"
    assert state.user_id == "user_456"
    assert state.current_node == "start"
    assert state.completed_nodes == []
    assert isinstance(state.execution_start, datetime)
    assert isinstance(state.last_updated, datetime)
    assert state.quota_status == {}
    assert state.input_analysis == {}
    assert state.research_results == {}
    assert state.ai_guidance == {}
    assert state.response_data == {}
    assert state.errors == []
    assert state.retry_count == {}

@pytest.mark.asyncio
async def test_agent_state_serialization():
    """Test AgentState serialization to/from dict."""
    state = AgentState(
        case_id="case_123",
        user_id="user_456",
        case_details=MOCK_CASE_DETAILS,
        user_info=MOCK_USER_INFO
    )
    
    # Test to_dict
    state_dict = state.to_dict()
    assert state_dict["case_id"] == "case_123"
    assert state_dict["user_id"] == "user_456"
    assert isinstance(state_dict["execution_start"], str)
    
    # Test from_dict
    restored_state = AgentState.from_dict(state_dict)
    assert restored_state.case_id == "case_123"
    assert restored_state.user_id == "user_456"
    assert isinstance(restored_state.execution_start, datetime)

@pytest.mark.asyncio
async def test_agent_state_update_node():
    """Test updating node results in AgentState."""
    state = AgentState(
        case_id="case_123",
        user_id="user_456",
        case_details=MOCK_CASE_DETAILS,
        user_info=MOCK_USER_INFO
    )
    
    # Test updating quota node
    quota_result = {"status": "success", "quota": {"available": 10}}
    state.update_node("check_quota", quota_result)
    assert state.current_node == "check_quota"
    assert "check_quota" in state.completed_nodes
    assert state.quota_status == quota_result
    
    # Test updating input analysis node
    analysis_result = {"names": ["John Doe"], "query": "rental dispute"}
    state.update_node("analyze_input", analysis_result)
    assert state.current_node == "analyze_input"
    assert "analyze_input" in state.completed_nodes
    assert state.input_analysis == analysis_result

@pytest.mark.asyncio
async def test_agent_state_error_handling():
    """Test error tracking in AgentState."""
    state = AgentState(
        case_id="case_123",
        user_id="user_456",
        case_details=MOCK_CASE_DETAILS,
        user_info=MOCK_USER_INFO
    )
    
    # Add an error
    error = ValueError("Test error")
    state.add_error("check_quota", error)
    
    assert len(state.errors) == 1
    assert state.errors[0]["node"] == "check_quota"
    assert "Test error" in state.errors[0]["error"]
    assert state.retry_count["check_quota"] == 1
    
    # Add another error to same node
    state.add_error("check_quota", error)
    assert state.retry_count["check_quota"] == 2

@pytest.mark.asyncio
async def test_agent_graph_execution_success(mock_agent_graph, mock_agent_state):
    """Test successful execution of the agent workflow."""
    # Start from the first executable node
    mock_agent_state.current_node = "check_quota"
    # Mock all node execution methods
    mock_agent_graph._check_quota_node = AsyncMock(return_value={
        "status": "success",
        "quota": {"available": 10}
    })
    mock_agent_graph._analyze_input_node = AsyncMock(return_value={
        "status": "success",
        "names": ["John Doe"],
        "query": "rental dispute"
    })
    mock_agent_graph._research_node = AsyncMock(return_value={
        "status": "success",
        "results": ["result1", "result2"]
    })
    mock_agent_graph._guidance_node = AsyncMock(return_value={
        "status": "success",
        "guidance": "Legal advice"
    })
    mock_agent_graph._generate_response_node = AsyncMock(return_value={
        "status": "success",
        "response": "Final response"
    })
    
    # Execute workflow
    result = await mock_agent_graph.execute(mock_agent_state)
    
    # Verify execution flow
    assert result["status"] == "success"
    assert mock_agent_state.current_node == "generate_response"
    assert len(mock_agent_state.completed_nodes) == 5
    assert "check_quota" in mock_agent_state.completed_nodes
    assert "analyze_input" in mock_agent_state.completed_nodes
    assert "research" in mock_agent_state.completed_nodes
    assert "guidance" in mock_agent_state.completed_nodes
    assert "generate_response" in mock_agent_state.completed_nodes

@pytest.mark.asyncio
async def test_agent_graph_execution_error(mock_agent_graph, mock_agent_state):
    """Test error handling during agent workflow execution."""
    # Start from the first executable node
    mock_agent_state.current_node = "check_quota"
    # Mock quota check to fail
    mock_agent_graph._check_quota_node = AsyncMock(side_effect=ValueError("Insufficient quota"))
    mock_agent_graph._create_support_ticket = AsyncMock()
    
    # Execute workflow
    result = await mock_agent_graph.execute(mock_agent_state)
    
    # Verify error handling
    assert result["status"] == "error"
    assert "Insufficient quota" in result["error"]
    assert result["node"] == "check_quota"
    assert len(mock_agent_state.errors) == 1
    assert mock_agent_state.retry_count["check_quota"] == 1
    mock_agent_graph._create_support_ticket.assert_not_called()  # Not called until max retries

@pytest.mark.asyncio
async def test_agent_graph_max_retries(mock_agent_graph, mock_agent_state):
    """Test max retries handling in agent workflow."""
    # Start from the first executable node
    mock_agent_state.current_node = "check_quota"
    # Mock quota check to fail consistently
    mock_agent_graph._check_quota_node = AsyncMock(side_effect=ValueError("Insufficient quota"))
    mock_agent_graph._create_support_ticket = AsyncMock()
    
    # Set retry count to max
    mock_agent_state.retry_count["check_quota"] = mock_agent_graph.max_retries
    
    # Execute workflow
    with pytest.raises(RuntimeError) as exc_info:
        await mock_agent_graph.execute(mock_agent_state)
    
    # Verify max retries handling
    assert "Max retries exceeded" in str(exc_info.value)
    mock_agent_graph._create_support_ticket.assert_called_once()

@pytest.mark.asyncio
async def test_agent_graph_node_methods(mock_agent_graph, mock_agent_state):
    """Test individual node execution methods."""
    # Ensure prerequisite analysis data is present
    mock_agent_state.input_analysis = {
        "query": "test query",
        "context": {"legal_domain": "civil"}
    }
    # Test quota check node
    with patch("functions.src.agent_orchestrator.check_quota") as mock_check_quota:
        mock_check_quota.return_value = {"available_requests": 10}
        result = await mock_agent_graph._check_quota_node(mock_agent_state)
        assert result["status"] == "success"
        assert result["quota"]["available_requests"] == 10
    
    # Test input analysis node
    result = await mock_agent_graph._analyze_input_node(mock_agent_state)
    assert result["status"] == "success"
    assert "names" in result
    assert "query" in result
    assert "required_documents" in result
    
    # Test research node
    with patch("functions.src.agent_orchestrator.query_bigquery") as mock_query:
        mock_query.return_value = [{"result": "test"}]
        result = await mock_agent_graph._research_node(mock_agent_state)
        assert result["status"] == "success"
        assert "case_law" in result
        assert "legal_references" in result
        assert "legislation" in result
        assert "relevance_scores" in result
    
    # Test guidance node
    with patch("functions.src.agent_orchestrator.consult_grok") as mock_grok:
        mock_grok.return_value = {"guidance": "test guidance"}
        result = await mock_agent_graph._guidance_node(mock_agent_state)
        assert result["status"] == "success"
        assert "guidance" in result

    # Prepare ai_guidance for response generation node
    mock_agent_state.ai_guidance = {
        "confidence_score": 0.95,
        "risks": ["risk1", "risk2"]
    }
    # Test response generation node
    with patch("functions.src.agent_orchestrator.format_response") as mock_format:
        mock_format.return_value = {"response": "test response"}
        result = await mock_agent_graph._generate_response_node(mock_agent_state)
        assert result["status"] == "success"
        assert "response" in result
        assert "confidence_score" in result
        assert "risks" in result

@pytest.mark.asyncio
async def test_create_agent_graph():
    """Test factory function for creating AgentGraph instance."""
    with patch("functions.src.agent_orchestrator.DraftTemplates") as mock_templates:
        graph = create_agent_graph()
        assert isinstance(graph, AgentGraph)
        assert graph.max_retries == 3
        # The DraftTemplates class should have been replaced by a MagicMock
        assert isinstance(graph.draft_generator, MagicMock) 