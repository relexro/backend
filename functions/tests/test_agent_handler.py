"""
Integration Tests for Agent Handler Module
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.agent_handler import AgentHandler
from src.agent_tools import DatabaseError

# Test Data Fixtures
@pytest.fixture
def sample_auth_data():
    return {
        "user_id": "user_456",
        "organization_id": "org_789",
        "roles": ["lawyer", "admin"],
        "subscription": {
            "status": "active",
            "plan": "professional"
        }
    }

@pytest.fixture
def sample_case_state():
    return {
        "case_id": "case_123",
        "user_id": "user_456",
        "organization_id": "org_789",
        "current_node": "input_analysis",
        "completed_nodes": [],
        "conversation_history": [
            {
                "role": "user",
                "content": "Initial query about contract dispute",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "metadata": {
            "case_type": "civil",
            "parties": [
                {"name": "Reclamant SA", "role": "plaintiff"},
                {"name": "Pârât SRL", "role": "defendant"}
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    }

@pytest.fixture
def sample_agent_response():
    return {
        "response": {
            "content": "Legal analysis completed",
            "recommendations": [
                "File preliminary objections",
                "Request additional documents"
            ],
            "next_steps": ["document_review", "legal_research"]
        },
        "state_updates": {
            "current_node": "response_generation",
            "completed_nodes": ["input_analysis", "legal_analysis"],
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": "Legal analysis completed",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
    }

# Authentication Tests
@pytest.mark.asyncio
async def test_authentication_success(sample_auth_data):
    """Test successful authentication and handler initialization."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_auth_data)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)
        
        handler = AgentHandler(firestore_client=mock_firestore())
        auth_result = await handler.authenticate("user_456", "org_789")
        
        assert auth_result["authenticated"] is True
        assert auth_result["user_id"] == "user_456"
        assert "roles" in auth_result

@pytest.mark.asyncio
async def test_authentication_invalid_user():
    """Test authentication with invalid user."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=False)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)
        
        handler = AgentHandler(firestore_client=mock_firestore())
        
        with pytest.raises(DatabaseError) as exc_info:
            await handler.authenticate("invalid_user", "org_789")
        assert "User not found" in str(exc_info.value)

# State Management Tests
@pytest.mark.asyncio
async def test_load_initial_state(sample_case_state):
    """Test loading initial state from Firestore."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_case_state)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)
        
        handler = AgentHandler(firestore_client=mock_firestore())
        state = await handler.load_state("case_123")
        
        assert state["case_id"] == "case_123"
        assert state["current_node"] == "input_analysis"
        assert len(state["conversation_history"]) == 1

@pytest.mark.asyncio
async def test_save_state_success(sample_case_state):
    """Test saving state to Firestore."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.set = AsyncMock()
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)
        
        handler = AgentHandler(firestore_client=mock_firestore())
        result = await handler.save_state("case_123", sample_case_state)
        
        assert result["status"] == "success"
        mock_doc.set.assert_called_once()

# Agent Invocation Tests
@pytest.mark.asyncio
async def test_handle_user_input_success(sample_case_state, sample_agent_response):
    """Test successful handling of user input."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore, \
         patch("src.agent_handler.create_agent_graph") as mock_create_graph:
        
        # Mock Firestore
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_case_state)
        mock_doc.set = AsyncMock()
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)
        
        # Mock agent graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = sample_agent_response
        mock_create_graph.return_value = mock_graph
        
        handler = AgentHandler(firestore_client=mock_firestore())
        result = await handler.handle_user_input(
            case_id="case_123",
            user_input="Analyze contract dispute",
            user_id="user_456",
            organization_id="org_789"
        )
        
        assert result["status"] == "success"
        assert "response" in result
        assert "recommendations" in result["response"]
        mock_graph.ainvoke.assert_called_once()

@pytest.mark.asyncio
async def test_handle_user_input_with_error():
    """Test handling of user input with error."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore, \
         patch("src.agent_handler.create_agent_graph") as mock_create_graph:
        
        mock_graph = AsyncMock()
        mock_graph.ainvoke.side_effect = Exception("Agent processing error")
        mock_create_graph.return_value = mock_graph
        
        handler = AgentHandler(firestore_client=mock_firestore())
        result = await handler.handle_user_input(
            case_id="case_123",
            user_input="Invalid query",
            user_id="user_456",
            organization_id="org_789"
        )
        
        assert result["status"] == "error"
        assert "error_message" in result

# Payment Webhook Tests
@pytest.mark.asyncio
async def test_handle_payment_webhook_success():
    """Test successful handling of payment webhook."""
    payment_data = {
        "payment_id": "payment_123",
        "status": "completed",
        "amount": 1000,
        "currency": "RON",
        "case_id": "case_123"
    }
    
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore, \
         patch("src.agent_handler.verify_payment") as mock_verify_payment:
        
        mock_verify_payment.return_value = {"is_verified": True}
        
        handler = AgentHandler(firestore_client=mock_firestore())
        result = await handler.handle_payment_webhook(payment_data)
        
        assert result["status"] == "success"
        assert result["payment_verified"] is True

@pytest.mark.asyncio
async def test_handle_payment_webhook_invalid():
    """Test handling of invalid payment webhook."""
    invalid_payment = {
        "payment_id": "payment_123",
        "status": "failed"
    }
    
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        handler = AgentHandler(firestore_client=mock_firestore())
        result = await handler.handle_payment_webhook(invalid_payment)
        
        assert result["status"] == "error"
        assert "payment_verified" in result
        assert result["payment_verified"] is False

# Response Formatting Tests
@pytest.mark.asyncio
async def test_format_response_success(sample_agent_response):
    """Test successful response formatting."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        handler = AgentHandler(firestore_client=mock_firestore())
        formatted = handler.format_response(sample_agent_response)
        
        assert "content" in formatted
        assert "recommendations" in formatted
        assert "next_steps" in formatted
        assert len(formatted["recommendations"]) == 2

@pytest.mark.asyncio
async def test_format_response_with_error():
    """Test response formatting with error."""
    error_response = {
        "error": True,
        "error_message": "Processing failed",
        "error_type": "AgentError"
    }
    
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        handler = AgentHandler(firestore_client=mock_firestore())
        formatted = handler.format_response(error_response)
        
        assert "error" in formatted
        assert formatted["status"] == "error"
        assert "error_message" in formatted

# Concurrent Processing Tests
@pytest.mark.asyncio
async def test_concurrent_requests_handling():
    """Test handling of concurrent requests for the same case."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: {
            "is_processing": True,
            "started_at": datetime.now().isoformat()
        })
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)
        
        handler = AgentHandler(firestore_client=mock_firestore())
        result = await handler.handle_user_input(
            case_id="case_123",
            user_input="Test query",
            user_id="user_456",
            organization_id="org_789"
        )
        
        assert result["status"] == "error"
        assert "concurrent_processing" in result
        assert result["concurrent_processing"] is True

# Cleanup Tests
@pytest.mark.asyncio
async def test_cleanup_on_completion(sample_case_state, sample_agent_response):
    """Test cleanup of processing state after completion."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore, \
         patch("src.agent_handler.create_agent_graph") as mock_create_graph:
        
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_case_state)
        mock_doc.set = AsyncMock()
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)
        
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = sample_agent_response
        mock_create_graph.return_value = mock_graph
        
        handler = AgentHandler(firestore_client=mock_firestore())
        await handler.handle_user_input(
            case_id="case_123",
            user_input="Final query",
            user_id="user_456",
            organization_id="org_789"
        )
        
        # Verify cleanup
        final_state = mock_doc.set.call_args[0][0]
        assert "is_processing" in final_state
        assert final_state["is_processing"] is False
        assert "completion_time" in final_state 