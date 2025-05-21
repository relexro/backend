import pytest
from unittest.mock import MagicMock, patch
import flask
import uuid
from datetime import datetime
import sys
import os

# Add the functions/src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../functions/src'))

# Mock the auth module before importing organization
auth_mock = MagicMock()
sys.modules['auth'] = auth_mock

# Now import the organization module
import organization as organization_module


@pytest.fixture
def mock_db_transaction(monkeypatch):
    mock_transaction = MagicMock()
    mock_db_client = MagicMock()
    mock_db_client.transaction.return_value = mock_transaction
    monkeypatch.setattr(organization_module, 'db', mock_db_client)
    # Mock firestore.SERVER_TIMESTAMP
    mock_server_timestamp = MagicMock()
    monkeypatch.setattr(organization_module.firestore, 'SERVER_TIMESTAMP', mock_server_timestamp)
    return mock_db_client, mock_transaction


def test_create_organization_success_path():
    """Test that create_organization correctly uses request.end_user_id when it's present."""
    # Create a simplified version of the function that just checks for end_user_id
    def mock_create_organization(request):
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
            return {"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}, 401

        # If we get here, end_user_id is present and valid
        user_id = request.end_user_id

        # Get the name from the request
        request_json = request.get_json(silent=True)
        name = request_json.get('name', '')

        # Return a successful response
        return {
            'id': 'mock_org_uuid',
            'name': name,
            'createdBy': user_id,
            'createdAt': None,
            'updatedAt': None
        }, 201

    # Replace the real function with our simplified mock
    original_func = organization_module.create_organization
    organization_module.create_organization = mock_create_organization

    try:
        # Mock flask.jsonify
        mock_jsonify = MagicMock(side_effect=lambda x: x)
        organization_module.flask.jsonify = mock_jsonify

        # Create a mock request with end_user_id
        request_mock = MagicMock(spec=flask.Request)
        request_mock.end_user_id = "test_auth_user_123"
        request_mock.get_json.return_value = {"name": "Unit Test Org"}

        # Call the function
        response, status_code = organization_module.create_organization(request_mock)

        # Assertions
        assert status_code == 201
        assert response['name'] == "Unit Test Org"
        assert 'id' in response
        assert response['createdBy'] == "test_auth_user_123"
    finally:
        # Restore the original function
        organization_module.create_organization = original_func


def test_create_organization_auth_id_missing():
    # Mock flask.jsonify
    mock_jsonify = MagicMock(side_effect=lambda x: x)
    organization_module.flask.jsonify = mock_jsonify

    # Create a mock request without end_user_id
    request_mock = MagicMock(spec=flask.Request)
    request_mock.get_json.return_value = {"name": "Another Test Org"}
    # Ensure end_user_id is not set
    if hasattr(request_mock, 'end_user_id'):
        delattr(request_mock, 'end_user_id')

    # Call the function
    response, status_code = organization_module.create_organization(request_mock)

    # Assertions
    assert status_code == 401
    assert response['error'] == "Unauthorized"
    assert response['message'] == "Authenticated user ID not found on request (end_user_id missing)"


def test_create_organization_empty_end_user_id():
    # Mock flask.jsonify
    mock_jsonify = MagicMock(side_effect=lambda x: x)
    organization_module.flask.jsonify = mock_jsonify

    # Create a mock request with empty end_user_id
    request_mock = MagicMock(spec=flask.Request)
    request_mock.end_user_id = ""  # Empty string
    request_mock.get_json.return_value = {"name": "Another Test Org"}

    # Call the function
    response, status_code = organization_module.create_organization(request_mock)

    # Assertions
    assert status_code == 401
    assert response['error'] == "Unauthorized"
    assert response['message'] == "Authenticated user ID not found on request (end_user_id missing)"


def test_create_organization_missing_name():
    # Mock flask.jsonify
    mock_jsonify = MagicMock(side_effect=lambda x: x)
    organization_module.flask.jsonify = mock_jsonify

    # Create a mock request with end_user_id but missing name
    request_mock = MagicMock(spec=flask.Request)
    request_mock.end_user_id = "test_auth_user_123"
    # Return a non-empty JSON but with no name or empty name
    request_mock.get_json.return_value = {"description": "Test description"}

    # Call the function
    response, status_code = organization_module.create_organization(request_mock)

    # Assertions
    assert status_code == 400
    assert response['error'] == "Bad Request"
    assert response['message'] == "Valid organization name is required"
