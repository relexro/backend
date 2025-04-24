"""
Integration Tests for Agent Module
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio

from functions.src.agent import Agent, handle_agent_request
from functions.src.agent_orchestrator import AgentState

# Test Data Fixtures
@pytest.fixture
def sample_case_details():
    return {
        "case_id": "case_123",
        "user_id": "user_456",
        "title": "Contract Dispute",
        "description": "Dispute regarding service contract terms",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "parties": [
            {"name": "Reclamant SA", "role": "plaintiff"},
            {"name": "Pârât SRL", "role": "defendant"}
        ]
    }

@pytest.fixture
def sample_agent_result():
    return {
        "status": "success",
        "response": "Legal analysis completed for your contract dispute.",
        "confidence_score": 0.85,
        "execution_time": 2.5,
        "risks": ["Interpretare neclară a clauzelor", "Lipsa dovezilor"]
    }

@pytest.fixture
def sample_request():
    class MockRequest:
        def __init__(self):
            self.path = "/cases/case_123/agent/messages"
            self.user_id = "user_456"
            self.user_email = "user@example.com"
            self._json = {"message": "Analyze my contract dispute"}

        def get_json(self, silent=False):
            return self._json

    return MockRequest()

# Agent Class Tests
@pytest.mark.asyncio
async def test_agent_process_message_success(sample_case_details, sample_agent_result):
    """Test successful processing of a message by the Agent class."""
    with patch("google.cloud.firestore.Client") as mock_firestore, \
         patch("agent_orchestrator.create_agent_graph") as mock_create_graph:

        # Mock Firestore document
        mock_doc = MagicMock()
        mock_doc.get.return_value.exists = True
        mock_doc.get.return_value.to_dict.return_value = sample_case_details
        mock_firestore.return_value.collection.return_value.document.return_value = mock_doc

        # Mock subcollection documents
        mock_processing_doc = MagicMock()
        mock_processing_doc.get.return_value.exists = False
        mock_firestore.return_value.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_processing_doc

        # Mock chat collection
        mock_chat_ref = MagicMock()
        mock_firestore.return_value.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_chat_ref

        # Mock agent graph
        mock_graph = MagicMock()
        mock_graph.execute = AsyncMock(return_value=sample_agent_result)
        mock_create_graph.return_value = mock_graph

        # Create agent and process message
        agent = Agent()
        agent.db = mock_firestore()
        agent.agent_graph = mock_graph

        result = await agent.process_message(
            case_id="case_123",
            user_message="Analyze my contract dispute",
            user_id="user_456",
            user_info={"email": "user@example.com"}
        )

        # Verify result
        assert result["status"] == "success"
        assert result["message"] == sample_agent_result["response"]
        assert "metadata" in result
        assert result["metadata"]["confidence_score"] == sample_agent_result["confidence_score"]

        # Verify Firestore interactions
        mock_firestore.return_value.collection.assert_called_with('cases')
        mock_firestore.return_value.collection.return_value.document.assert_called_with('case_123')
        mock_processing_doc.set.assert_called_once()

        # Verify chat history was saved (2 entries - user message and agent response)
        assert mock_chat_ref.set.call_count >= 2

@pytest.mark.asyncio
async def test_agent_process_message_case_not_found():
    """Test processing a message for a non-existent case."""
    with patch("google.cloud.firestore.Client") as mock_firestore:
        # Mock non-existent case
        mock_doc = MagicMock()
        mock_doc.get.return_value.exists = False
        mock_firestore.return_value.collection.return_value.document.return_value = mock_doc

        # Create agent and process message
        agent = Agent()
        agent.db = mock_firestore()

        result, status_code = await agent.process_message(
            case_id="nonexistent_case",
            user_message="Analyze my contract dispute",
            user_id="user_456"
        )

        # Verify result
        assert result["status"] == "error"
        assert "not found" in result["message"]
        assert status_code == 404

# Handler Function Tests
def test_handle_agent_request_success(sample_request, sample_agent_result):
    """Test successful handling of an agent request with authenticated and authorized user."""
    with patch("agent.agent.process_message") as mock_process_message, \
         patch("asyncio.run") as mock_asyncio_run, \
         patch("agent.agent.db.collection") as mock_collection, \
         patch("auth.check_permission") as mock_check_permission:

        # Mock Firestore document snapshot for authorization check
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.get.return_value = "org_123"  # organizationId
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection.return_value.document.return_value = mock_doc_ref

        # Mock permission check to return success
        mock_check_permission.return_value = (True, None)  # has_permission, error_message

        # Mock asyncio.run to return the expected result
        mock_asyncio_run.return_value = {
            "status": "success",
            "message": sample_agent_result["response"],
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "confidence_score": sample_agent_result["confidence_score"],
                "execution_time": sample_agent_result["execution_time"],
                "risks": sample_agent_result["risks"]
            }
        }

        # Call the handler with authenticated request
        # Note: In a real scenario, authentication would be handled by _authenticate_and_call
        result = handle_agent_request(sample_request)

        # Verify result
        assert result["status"] == "success"
        assert "message" in result
        assert "metadata" in result

        # Verify authorization check was performed
        mock_collection.assert_called_with("cases")
        mock_collection.return_value.document.assert_called_with("case_123")
        mock_check_permission.assert_called_once()

        # Verify asyncio.run was called with process_message
        mock_asyncio_run.assert_called_once()

        # Verify user_id and user_info were passed correctly
        args, _ = mock_asyncio_run.call_args
        process_message_call = args[0]
        assert "user_456" in str(process_message_call)  # user_id should be passed
        assert "user@example.com" in str(process_message_call)  # user_email should be in user_info

def test_handle_agent_request_unauthorized():
    """Test handling a request where the user is not authorized to access the case."""
    class MockAuthorizedRequest:
        def __init__(self):
            self.path = "/cases/case_123/agent/messages"
            self.user_id = "unauthorized_user"
            self.user_email = "unauthorized@example.com"
            self._json = {"message": "Analyze my contract dispute"}

        def get_json(self, silent=False):
            return self._json

    with patch("agent.agent.db.collection") as mock_collection, \
         patch("auth.check_permission") as mock_check_permission:

        # Mock Firestore document snapshot for authorization check
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.get.return_value = "org_123"  # organizationId
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection.return_value.document.return_value = mock_doc_ref

        # Mock permission check to return failure
        mock_check_permission.return_value = (False, "User does not have access to this case")  # has_permission, error_message

        # Call the handler
        result, status_code = handle_agent_request(MockAuthorizedRequest())

        # Verify result
        assert result["status"] == "error"
        assert "Forbidden" in result["message"]
        assert status_code == 403

        # Verify authorization check was performed
        mock_collection.assert_called_with("cases")
        mock_collection.return_value.document.assert_called_with("case_123")
        mock_check_permission.assert_called_once()

def test_handle_agent_request_case_not_found():
    """Test handling a request where the case does not exist."""
    class MockCaseNotFoundRequest:
        def __init__(self):
            self.path = "/cases/nonexistent_case/agent/messages"
            self.user_id = "user_456"
            self.user_email = "user@example.com"
            self._json = {"message": "Analyze my contract dispute"}

        def get_json(self, silent=False):
            return self._json

    with patch("agent.agent.db.collection") as mock_collection:
        # Mock Firestore document snapshot for authorization check
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection.return_value.document.return_value = mock_doc_ref

        # Call the handler
        result, status_code = handle_agent_request(MockCaseNotFoundRequest())

        # Verify result
        assert result["status"] == "error"
        assert "not found" in result["message"]
        assert status_code == 404

def test_handle_agent_request_invalid_path():
    """Test handling a request with an invalid path."""
    class MockInvalidRequest:
        def __init__(self):
            self.path = "/invalid/path"
            self._json = {"message": "Test message"}

        def get_json(self, silent=False):
            return self._json

    result, status_code = handle_agent_request(MockInvalidRequest())

    # Verify result
    assert result["status"] == "error"
    assert "Invalid URL path" in result["message"]
    assert status_code == 400

def test_handle_agent_request_no_json():
    """Test handling a request with no JSON data."""
    class MockNoJsonRequest:
        def __init__(self):
            self.path = "/cases/case_123/agent/messages"

        def get_json(self, silent=False):
            return None

    result, status_code = handle_agent_request(MockNoJsonRequest())

    # Verify result
    assert result["status"] == "error"
    assert "No JSON data provided" in result["message"]
    assert status_code == 400
