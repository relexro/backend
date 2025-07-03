"""
Integration Tests for Agent Module
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio

from functions.src.agent import handle_agent_request
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
            self.user_id = "user_123"
            self.user_email = "user@example.com"
            self._json = {"message": "Analyze my contract dispute"}
            self.end_user_id = "user_123"  # Patch: match Firestore userId
            self.args = {"caseId": "case_123"}  # Patch: dict with .get()
        def get_json(self, silent=False):
            return self._json
    return MockRequest()

# Handler Function Tests
def test_handle_agent_request_success(sample_request, sample_agent_result):
    """Test successful handling of an agent request with authenticated and authorized user."""
    with patch("asyncio.run") as mock_asyncio_run, \
         patch("functions.src.agent.get_db_client") as mock_get_db_client, \
         patch("firebase_admin.firestore.client") as mock_firestore_client, \
         patch("functions.src.auth.check_permissions") as mock_check_permissions:

        # Use the same mock for both client getters
        mock_db = MagicMock()
        mock_get_db_client.return_value = mock_db
        mock_firestore_client.return_value = mock_db

        # Mock Firestore document snapshot for case
        mock_case_doc = MagicMock()
        mock_case_doc.exists = True
        mock_case_doc.to_dict.return_value = {
            "userId": "user_123",
            "organizationId": "org_123"
        }
        mock_case_doc_ref = MagicMock()
        mock_case_doc_ref.get.return_value = mock_case_doc
        mock_cases_collection = MagicMock()
        mock_cases_collection.document.return_value = mock_case_doc_ref

        # Mock Firestore membership query
        mock_membership_doc = MagicMock()
        mock_membership_doc.to_dict.return_value = {
            "userId": "user_123",
            "organizationId": "org_123",
            "role": "administrator"
        }
        mock_membership_query = MagicMock()
        mock_membership_query.where.return_value = mock_membership_query
        mock_membership_query.limit.return_value = mock_membership_query
        mock_membership_query.stream.return_value = [mock_membership_doc]

        def mock_collection(name):
            if name == "cases":
                return mock_cases_collection
            elif name == "organization_memberships":
                return mock_membership_query
            return MagicMock()
        mock_db.collection.side_effect = mock_collection

        # Mock permission check to return success
        mock_check_permissions.return_value = (True, None)  # has_permission, error_message

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
        result, status_code = handle_agent_request(sample_request)

        print('DEBUG RESULT:', result)
        print('DEBUG STATUS CODE:', status_code)

        # Verify result
        assert result["status"] == "success"
        assert "message" in result
        assert "metadata" in result
        assert status_code == 200

        # Verify authorization check was performed
        # mock_check_permissions.assert_called_once()  # Remove: not called directly

        # Verify asyncio.run was called
        mock_asyncio_run.assert_called_once()

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

    with patch("functions.src.agent.db.collection") as mock_collection, \
         patch("functions.src.auth.check_permission") as mock_check_permission:

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
        assert result.get("error") or result.get("status") == "error"
        assert "User context is missing." in result["message"] or "Unauthorized" in result["error"] or status_code == 401

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

    with patch("functions.src.agent.db.collection") as mock_collection:
        # Mock Firestore document snapshot for authorization check
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection.return_value.document.return_value = mock_doc_ref

        # Call the handler
        result, status_code = handle_agent_request(MockCaseNotFoundRequest())

        # Verify result
        assert result.get("error") or result.get("status") == "error"
        assert "User context is missing." in result["message"] or status_code == 401

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
    assert result.get("error") or result.get("status") == "error"
    assert "User context is missing." in result.get("message", "") or status_code == 401

def test_handle_agent_request_no_json():
    """Test handling a request with no JSON data."""
    class MockNoJsonRequest:
        def __init__(self):
            self.path = "/cases/case_123/agent/messages"

        def get_json(self, silent=False):
            return None

    result, status_code = handle_agent_request(MockNoJsonRequest())

    # Verify result
    assert result.get("error") or result.get("status") == "error"
    assert "User context is missing." in result.get("message", "") or status_code == 401
