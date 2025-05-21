#!/usr/bin/env python3
"""
Unit Tests for Party Module

This module contains unit tests for the functions in the party.py module.
"""

import pytest
import sys
import os
import re
from unittest.mock import MagicMock, patch
import flask
from datetime import datetime
import uuid

# Add the functions/src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../functions/src'))

# Create a mock auth module with the necessary components
auth_mock = MagicMock()
auth_mock.check_permission = MagicMock(return_value=(True, ""))
auth_mock.PermissionCheckRequest = MagicMock()
auth_mock.TYPE_PARTY = "party"
auth_mock.ACTION_READ = "read"
auth_mock.ACTION_UPDATE = "update"
auth_mock.ACTION_DELETE = "delete"

# Mock the auth module before importing party
sys.modules['auth'] = auth_mock

# Now import the party module
import party as party_module

# Make auth accessible via party_module.auth
party_module.auth = auth_mock
party_module.RESOURCE_TYPE_PARTY = "party"


@pytest.fixture
def mock_db_client():
    """Create a mock Firestore client."""
    mock_client = MagicMock()

    # Mock the SERVER_TIMESTAMP
    mock_server_timestamp = "SERVER_TIMESTAMP_PLACEHOLDER"
    party_module.firestore.SERVER_TIMESTAMP = mock_server_timestamp

    # Replace the db in the party module with our mock
    original_db = party_module.db
    party_module.db = mock_client

    yield mock_client

    # Restore the original db
    party_module.db = original_db


@pytest.fixture
def mock_request():
    """Create a mock Flask request."""
    def _create_mock_request(end_user_id=None, json_data=None, args=None, path=None):
        mock_req = MagicMock(spec=flask.Request)
        mock_req.end_user_id = end_user_id
        mock_req.get_json = MagicMock(return_value=json_data)
        mock_req.args = args or {}
        mock_req.path = path or ""
        return mock_req

    return _create_mock_request


class TestCreateParty:
    """Tests for the create_party function."""

    def test_create_individual_party_success(self, mock_db_client, mock_request, monkeypatch):
        """Test successful creation of an individual party."""
        # Mock uuid.uuid4 to return a predictable value
        mock_uuid = MagicMock()
        mock_uuid.return_value = "test-party-uuid"
        monkeypatch.setattr(uuid, 'uuid4', mock_uuid)

        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "nameDetails": {
                "firstName": "John",
                "lastName": "Doe"
            },
            "identityCodes": {
                "cnp": "1234567890123"
            },
            "contactInfo": {
                "address": "123 Test St",
                "email": "john@example.com",
                "phone": "123456789"
            },
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot
        mock_doc_ref.id = "test-party-uuid"

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Create a mock request with valid data for an individual party
        request_data = {
            "partyType": "individual",
            "nameDetails": {
                "firstName": "John",
                "lastName": "Doe"
            },
            "identityCodes": {
                "cnp": "1234567890123"
            },
            "contactInfo": {
                "address": "123 Test St",
                "email": "john@example.com",
                "phone": "123456789"
            }
        }
        request_mock = mock_request(end_user_id="test-user-123", json_data=request_data)

        # Call the function
        result, status_code = party_module.create_party(request_mock)

        # Assertions
        assert status_code == 201  # HTTP 201 Created
        assert result["partyId"] == "test-party-uuid"
        assert result["partyType"] == "individual"
        assert result["nameDetails"]["firstName"] == "John"
        assert result["nameDetails"]["lastName"] == "Doe"
        assert result["identityCodes"]["cnp"] == "1234567890123"
        assert result["contactInfo"]["address"] == "123 Test St"
        assert result["contactInfo"]["email"] == "john@example.com"
        assert result["contactInfo"]["phone"] == "123456789"
        assert result["userId"] == "test-user-123"

        # Verify the document was created with the correct data
        mock_db_client.collection.assert_called_once_with("parties")
        mock_db_client.collection().document.assert_called_once()
        mock_doc_ref.set.assert_called_once()

        # Verify the data passed to set
        set_data = mock_doc_ref.set.call_args[0][0]
        assert set_data["partyType"] == "individual"
        assert set_data["nameDetails"]["firstName"] == "John"
        assert set_data["nameDetails"]["lastName"] == "Doe"
        assert set_data["identityCodes"]["cnp"] == "1234567890123"
        assert set_data["contactInfo"]["address"] == "123 Test St"
        assert set_data["userId"] == "test-user-123"
        assert set_data["createdAt"] == party_module.firestore.SERVER_TIMESTAMP
        assert set_data["updatedAt"] == party_module.firestore.SERVER_TIMESTAMP

    def test_create_organization_party_success(self, mock_db_client, mock_request, monkeypatch):
        """Test successful creation of an organization party."""
        # Mock uuid.uuid4 to return a predictable value
        mock_uuid = MagicMock()
        mock_uuid.return_value = "test-org-party-uuid"
        monkeypatch.setattr(uuid, 'uuid4', mock_uuid)

        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "organization",
            "nameDetails": {
                "companyName": "Test Company"
            },
            "identityCodes": {
                "cui": "RO12345678",
                "regCom": "J12/345/2023"
            },
            "contactInfo": {
                "address": "456 Company St",
                "email": "contact@company.com",
                "phone": "987654321"
            },
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot
        mock_doc_ref.id = "test-org-party-uuid"

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Create a mock request with valid data for an organization party
        request_data = {
            "partyType": "organization",
            "nameDetails": {
                "companyName": "Test Company"
            },
            "identityCodes": {
                "cui": "RO12345678",
                "regCom": "J12/345/2023"
            },
            "contactInfo": {
                "address": "456 Company St",
                "email": "contact@company.com",
                "phone": "987654321"
            }
        }
        request_mock = mock_request(end_user_id="test-user-123", json_data=request_data)

        # Call the function
        result, status_code = party_module.create_party(request_mock)

        # Assertions
        assert status_code == 201  # HTTP 201 Created
        assert result["partyId"] == "test-org-party-uuid"
        assert result["partyType"] == "organization"
        assert result["nameDetails"]["companyName"] == "Test Company"
        assert result["identityCodes"]["cui"] == "RO12345678"
        assert result["identityCodes"]["regCom"] == "J12/345/2023"
        assert result["contactInfo"]["address"] == "456 Company St"
        assert result["contactInfo"]["email"] == "contact@company.com"
        assert result["contactInfo"]["phone"] == "987654321"
        assert result["userId"] == "test-user-123"

        # Verify the document was created with the correct data
        mock_db_client.collection.assert_called_once_with("parties")
        mock_db_client.collection().document.assert_called_once()
        mock_doc_ref.set.assert_called_once()

        # Verify the data passed to set
        set_data = mock_doc_ref.set.call_args[0][0]
        assert set_data["partyType"] == "organization"
        assert set_data["nameDetails"]["companyName"] == "Test Company"
        assert set_data["identityCodes"]["cui"] == "RO12345678"
        assert set_data["identityCodes"]["regCom"] == "J12/345/2023"
        assert set_data["contactInfo"]["address"] == "456 Company St"
        assert set_data["userId"] == "test-user-123"
        assert set_data["createdAt"] == party_module.firestore.SERVER_TIMESTAMP
        assert set_data["updatedAt"] == party_module.firestore.SERVER_TIMESTAMP

    def test_create_party_missing_auth(self, mock_request):
        """Test create_party with missing authentication."""
        request_mock = mock_request(end_user_id=None, json_data={"partyType": "individual"})

        result, status_code = party_module.create_party(request_mock)

        assert status_code == 401
        assert "error" in result
        assert result["error"] == "Unauthorized"
        assert "message" in result
        assert "end_user_id missing" in result["message"]

    def test_create_party_missing_json(self, mock_request):
        """Test create_party with missing JSON data."""
        request_mock = mock_request(end_user_id="test-user-123", json_data=None)

        result, status_code = party_module.create_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "Request body required" in result["message"]

    def test_create_party_invalid_type(self, mock_request):
        """Test create_party with invalid party type."""
        request_data = {
            "partyType": "invalid_type",
            "nameDetails": {"firstName": "John", "lastName": "Doe"}
        }
        request_mock = mock_request(end_user_id="test-user-123", json_data=request_data)

        result, status_code = party_module.create_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "partyType must be" in result["message"]

    def test_create_individual_missing_name(self, mock_request):
        """Test create_party for individual with missing name details."""
        request_data = {
            "partyType": "individual",
            "nameDetails": {"firstName": "John"},  # Missing lastName
            "identityCodes": {"cnp": "1234567890123"},
            "contactInfo": {"address": "123 Test St"}
        }
        request_mock = mock_request(end_user_id="test-user-123", json_data=request_data)

        result, status_code = party_module.create_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "firstName and lastName required" in result["message"]

    def test_create_organization_missing_name(self, mock_request):
        """Test create_party for organization with missing company name."""
        request_data = {
            "partyType": "organization",
            "nameDetails": {},  # Missing companyName
            "identityCodes": {"cui": "RO12345678", "regCom": "J12/345/2023"},
            "contactInfo": {"address": "456 Company St"}
        }
        request_mock = mock_request(end_user_id="test-user-123", json_data=request_data)

        result, status_code = party_module.create_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "companyName required" in result["message"]

    def test_create_individual_invalid_cnp(self, mock_request):
        """Test create_party for individual with invalid CNP."""
        request_data = {
            "partyType": "individual",
            "nameDetails": {"firstName": "John", "lastName": "Doe"},
            "identityCodes": {"cnp": "123456"},  # Invalid CNP (too short)
            "contactInfo": {"address": "123 Test St"}
        }
        request_mock = mock_request(end_user_id="test-user-123", json_data=request_data)

        result, status_code = party_module.create_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "CNP must be 13 digits" in result["message"]

    def test_create_organization_missing_codes(self, mock_request):
        """Test create_party for organization with missing identity codes."""
        request_data = {
            "partyType": "organization",
            "nameDetails": {"companyName": "Test Company"},
            "identityCodes": {"cui": "RO12345678"},  # Missing regCom
            "contactInfo": {"address": "456 Company St"}
        }
        request_mock = mock_request(end_user_id="test-user-123", json_data=request_data)

        result, status_code = party_module.create_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "CUI and RegCom required" in result["message"]

    def test_create_party_missing_address(self, mock_request):
        """Test create_party with missing address in contactInfo."""
        request_data = {
            "partyType": "individual",
            "nameDetails": {"firstName": "John", "lastName": "Doe"},
            "identityCodes": {"cnp": "1234567890123"},
            "contactInfo": {"email": "john@example.com"}  # Missing address
        }
        request_mock = mock_request(end_user_id="test-user-123", json_data=request_data)

        result, status_code = party_module.create_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "address required" in result["message"]


class TestGetParty:
    """Tests for the get_party function."""

    def test_get_party_success(self, mock_db_client, mock_request):
        """Test successful retrieval of a party."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "nameDetails": {
                "firstName": "John",
                "lastName": "Doe"
            },
            "identityCodes": {
                "cnp": "1234567890123"
            },
            "contactInfo": {
                "address": "123 Test St",
                "email": "john@example.com",
                "phone": "123456789"
            },
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return success
        auth_mock.check_permission.return_value = (True, "")

        # Create a mock request with a party ID
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={"partyId": "test-party-id"}
        )

        # Call the function
        result, status_code = party_module.get_party(request_mock)

        # Assertions
        assert status_code == 200
        assert result["partyType"] == "individual"
        assert result["nameDetails"]["firstName"] == "John"
        assert result["nameDetails"]["lastName"] == "Doe"
        assert result["identityCodes"]["cnp"] == "1234567890123"
        assert result["contactInfo"]["address"] == "123 Test St"
        assert result["contactInfo"]["email"] == "john@example.com"
        assert result["contactInfo"]["phone"] == "123456789"
        assert result["userId"] == "test-user-123"
        assert result["partyId"] == "test-party-id"

        # Verify the document was retrieved correctly
        mock_db_client.collection.assert_called_once_with("parties")
        mock_db_client.collection().document.assert_called_once_with("test-party-id")
        mock_doc_ref.get.assert_called_once()

        # Verify permission check was called correctly
        auth_mock.check_permission.assert_called_once()
        args = auth_mock.check_permission.call_args[0]
        assert args[0] == "test-user-123"  # user_id

        # Verify PermissionCheckRequest was created correctly
        auth_mock.PermissionCheckRequest.assert_called_once_with(
            resourceType="party",
            resourceId="test-party-id",
            action="read"
        )

    def test_get_party_from_path(self, mock_db_client, mock_request):
        """Test retrieving a party with ID from path."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return success
        auth_mock.check_permission.return_value = (True, "")

        # Create a mock request with a party ID in the path
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={},  # No query args
            path="/parties/test-party-id"  # ID in path
        )

        # Call the function
        result, status_code = party_module.get_party(request_mock)

        # Assertions
        assert status_code == 200
        assert result["partyId"] == "test-party-id"

        # Verify the document was retrieved correctly
        mock_db_client.collection.assert_called_once_with("parties")
        mock_db_client.collection().document.assert_called_once_with("test-party-id")

    def test_get_party_missing_auth(self, mock_request):
        """Test get_party with missing authentication."""
        request_mock = mock_request(
            end_user_id=None,
            args={"partyId": "test-party-id"}
        )

        result, status_code = party_module.get_party(request_mock)

        assert status_code == 401
        assert "error" in result
        assert result["error"] == "Unauthorized"
        assert "message" in result
        assert "end_user_id missing" in result["message"]

    def test_get_party_missing_id(self, mock_request):
        """Test get_party with missing party ID."""
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={},  # No partyId
            path="/some/other/path"  # No ID in path
        )

        result, status_code = party_module.get_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "partyId is required" in result["message"]

    def test_get_party_not_found(self, mock_db_client, mock_request):
        """Test get_party with non-existent party ID."""
        # Create a mock document reference with non-existent snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = False  # Party doesn't exist
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Create a mock request with a non-existent party ID
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={"partyId": "non-existent-party"}
        )

        # Call the function
        result, status_code = party_module.get_party(request_mock)

        # Assertions
        assert status_code == 404
        assert "error" in result
        assert result["error"] == "Not Found"
        assert "message" in result
        assert "Party not found" in result["message"]

    def test_get_party_permission_denied(self, mock_db_client, mock_request):
        """Test get_party with permission denied."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "userId": "other-user-id",  # Different user
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return failure
        auth_mock.check_permission.return_value = (False, "Permission denied")

        # Create a mock request
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={"partyId": "test-party-id"}
        )

        # Call the function
        result, status_code = party_module.get_party(request_mock)

        # Assertions
        assert status_code == 403
        assert "error" in result
        assert result["error"] == "Permission denied"


class TestUpdateParty:
    """Tests for the update_party function."""

    def test_update_individual_party_success(self, mock_db_client, mock_request):
        """Test successful update of an individual party."""
        # Create a mock document reference and snapshots
        mock_doc_ref = MagicMock()

        # Original party data
        mock_original_snapshot = MagicMock()
        mock_original_snapshot.exists = True
        mock_original_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "nameDetails": {
                "firstName": "John",
                "lastName": "Doe"
            },
            "identityCodes": {
                "cnp": "1234567890123"
            },
            "contactInfo": {
                "address": "123 Test St",
                "email": "john@example.com"
            },
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }

        # Updated party data
        mock_updated_snapshot = MagicMock()
        mock_updated_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "nameDetails": {
                "firstName": "John",
                "lastName": "Smith"  # Changed last name
            },
            "identityCodes": {
                "cnp": "1234567890123"
            },
            "contactInfo": {
                "address": "456 New St",  # Changed address
                "email": "john@example.com"
            },
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 2, 12, 0, 0)  # Updated timestamp
        }

        # Configure the mock document reference to return different snapshots on consecutive calls
        mock_doc_ref.get = MagicMock(side_effect=[mock_original_snapshot, mock_updated_snapshot])

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return success
        auth_mock.check_permission.return_value = (True, "")

        # Create a mock request with update data
        request_data = {
            "partyId": "test-party-id",
            "nameDetails": {
                "lastName": "Smith"  # Update last name
            },
            "contactInfo": {
                "address": "456 New St"  # Update address
            }
        }
        request_mock = mock_request(end_user_id="test-user-123", json_data=request_data)

        # Call the function
        result, status_code = party_module.update_party(request_mock)

        # Assertions
        assert status_code == 200
        assert result["partyId"] == "test-party-id"
        assert result["nameDetails"]["firstName"] == "John"
        assert result["nameDetails"]["lastName"] == "Smith"  # Updated
        assert result["contactInfo"]["address"] == "456 New St"  # Updated
        assert result["contactInfo"]["email"] == "john@example.com"  # Unchanged

        # Verify the document was updated correctly
        mock_db_client.collection.assert_called_with("parties")
        mock_db_client.collection().document.assert_called_with("test-party-id")
        mock_doc_ref.update.assert_called_once()

        # Verify the update data
        update_data = mock_doc_ref.update.call_args[0][0]
        assert "nameDetails" in update_data
        assert update_data["nameDetails"]["lastName"] == "Smith"
        assert "contactInfo" in update_data
        assert update_data["contactInfo"]["address"] == "456 New St"
        assert "updatedAt" in update_data

        # Verify permission check was called
        # Note: We don't use assert_called_once() because the mock might be called by other tests
        assert auth_mock.check_permission.call_count >= 1

        # Verify that PermissionCheckRequest was called with the right parameters
        auth_mock.PermissionCheckRequest.assert_any_call(
            resourceType="party",
            resourceId="test-party-id",
            action="update"
        )

    def test_update_organization_party_success(self, mock_db_client, mock_request):
        """Test successful update of an organization party."""
        # Create a mock document reference and snapshots
        mock_doc_ref = MagicMock()

        # Original party data
        mock_original_snapshot = MagicMock()
        mock_original_snapshot.exists = True
        mock_original_snapshot.to_dict.return_value = {
            "partyType": "organization",
            "nameDetails": {
                "companyName": "Old Company Name"
            },
            "identityCodes": {
                "cui": "RO12345678",
                "regCom": "J12/345/2023"
            },
            "contactInfo": {
                "address": "123 Company St",
                "email": "contact@company.com"
            },
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }

        # Updated party data
        mock_updated_snapshot = MagicMock()
        mock_updated_snapshot.to_dict.return_value = {
            "partyType": "organization",
            "nameDetails": {
                "companyName": "New Company Name"  # Changed name
            },
            "identityCodes": {
                "cui": "RO87654321",  # Changed CUI
                "regCom": "J12/345/2023"
            },
            "contactInfo": {
                "address": "123 Company St",
                "email": "contact@company.com"
            },
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 2, 12, 0, 0)  # Updated timestamp
        }

        # Configure the mock document reference to return different snapshots on consecutive calls
        mock_doc_ref.get = MagicMock(side_effect=[mock_original_snapshot, mock_updated_snapshot])

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return success
        auth_mock.check_permission.return_value = (True, "")

        # Create a mock request with update data
        request_data = {
            "partyId": "test-org-party-id",
            "nameDetails": {
                "companyName": "New Company Name"  # Update company name
            },
            "identityCodes": {
                "cui": "RO87654321"  # Update CUI
            }
        }
        request_mock = mock_request(end_user_id="test-user-123", json_data=request_data)

        # Call the function
        result, status_code = party_module.update_party(request_mock)

        # Assertions
        assert status_code == 200
        assert result["partyId"] == "test-org-party-id"
        assert result["nameDetails"]["companyName"] == "New Company Name"  # Updated
        assert result["identityCodes"]["cui"] == "RO87654321"  # Updated
        assert result["identityCodes"]["regCom"] == "J12/345/2023"  # Unchanged

        # Verify the document was updated correctly
        mock_db_client.collection.assert_called_with("parties")
        mock_db_client.collection().document.assert_called_with("test-org-party-id")
        mock_doc_ref.update.assert_called_once()

        # Verify the update data
        update_data = mock_doc_ref.update.call_args[0][0]
        assert "nameDetails" in update_data
        assert update_data["nameDetails"]["companyName"] == "New Company Name"
        assert "identityCodes" in update_data
        assert update_data["identityCodes"]["cui"] == "RO87654321"

    def test_update_party_missing_auth(self, mock_request):
        """Test update_party with missing authentication."""
        request_mock = mock_request(
            end_user_id=None,
            json_data={"partyId": "test-party-id"}
        )

        result, status_code = party_module.update_party(request_mock)

        assert status_code == 401
        assert "error" in result
        assert result["error"] == "Unauthorized"
        assert "message" in result
        assert "end_user_id missing" in result["message"]

    def test_update_party_missing_json(self, mock_request):
        """Test update_party with missing JSON data."""
        request_mock = mock_request(
            end_user_id="test-user-123",
            json_data=None
        )

        result, status_code = party_module.update_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "Request body required" in result["message"]

    def test_update_party_missing_id(self, mock_request):
        """Test update_party with missing party ID."""
        request_mock = mock_request(
            end_user_id="test-user-123",
            json_data={"nameDetails": {"firstName": "John"}}  # No partyId
        )

        result, status_code = party_module.update_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "partyId is required" in result["message"]

    def test_update_party_not_found(self, mock_db_client, mock_request):
        """Test update_party with non-existent party ID."""
        # Create a mock document reference with non-existent snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = False  # Party doesn't exist
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Create a mock request with a non-existent party ID
        request_mock = mock_request(
            end_user_id="test-user-123",
            json_data={"partyId": "non-existent-party", "nameDetails": {"firstName": "John"}}
        )

        # Call the function
        result, status_code = party_module.update_party(request_mock)

        # Assertions
        assert status_code == 404
        assert "error" in result
        assert result["error"] == "Not Found"
        assert "message" in result
        assert "Party not found" in result["message"]

    def test_update_party_permission_denied(self, mock_db_client, mock_request):
        """Test update_party with permission denied."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "userId": "other-user-id",  # Different user
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return failure
        auth_mock.check_permission.return_value = (False, "Permission denied")

        # Create a mock request
        request_mock = mock_request(
            end_user_id="test-user-123",
            json_data={"partyId": "test-party-id", "nameDetails": {"firstName": "John"}}
        )

        # Call the function
        result, status_code = party_module.update_party(request_mock)

        # Assertions
        assert status_code == 403
        assert "error" in result
        assert result["error"] == "Permission denied"

    def test_update_party_invalid_type_mix(self, mock_db_client, mock_request):
        """Test update_party with invalid type mixing (individual with company fields)."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",  # Individual party
            "nameDetails": {"firstName": "John", "lastName": "Doe"},
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return success
        auth_mock.check_permission.return_value = (True, "")

        # Create a mock request with invalid data (company name for individual)
        request_mock = mock_request(
            end_user_id="test-user-123",
            json_data={
                "partyId": "test-party-id",
                "nameDetails": {"companyName": "Company Name"}  # Invalid for individual
            }
        )

        # Call the function
        result, status_code = party_module.update_party(request_mock)

        # Assertions
        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "companyName invalid for individual" in result["message"]

    def test_update_party_invalid_cnp(self, mock_db_client, mock_request):
        """Test update_party with invalid CNP for individual."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "nameDetails": {"firstName": "John", "lastName": "Doe"},
            "identityCodes": {"cnp": "1234567890123"},
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return success
        auth_mock.check_permission.return_value = (True, "")

        # Create a mock request with invalid CNP
        request_mock = mock_request(
            end_user_id="test-user-123",
            json_data={
                "partyId": "test-party-id",
                "identityCodes": {"cnp": "123456"}  # Invalid CNP (too short)
            }
        )

        # Call the function
        result, status_code = party_module.update_party(request_mock)

        # Assertions
        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "Valid CNP required" in result["message"]

    def test_update_party_no_valid_fields(self, mock_db_client, mock_request):
        """Test update_party with no valid fields to update."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "nameDetails": {"firstName": "John", "lastName": "Doe"},
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return success
        auth_mock.check_permission.return_value = (True, "")

        # Create a mock request with only partyId (no fields to update)
        request_mock = mock_request(
            end_user_id="test-user-123",
            json_data={"partyId": "test-party-id"}  # No fields to update
        )

        # Call the function
        result, status_code = party_module.update_party(request_mock)

        # Assertions
        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "No valid fields provided for update" in result["message"]


class TestDeleteParty:
    """Tests for the delete_party function."""

    def test_delete_party_success(self, mock_db_client, mock_request):
        """Test successful deletion of a party."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "nameDetails": {"firstName": "John", "lastName": "Doe"},
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Mock the cases query to return empty list (no attached cases)
        mock_cases_query = MagicMock()
        mock_cases_query.stream.return_value = []

        # First, mock the 'cases' collection query
        mock_db_client.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_cases_query

        # Reset the mock to prepare for the 'parties' collection call
        mock_db_client.collection.reset_mock()

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return success
        auth_mock.check_permission.return_value = (True, "")

        # Create a mock request with a party ID
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={"partyId": "test-party-id"}
        )

        # Call the function
        result, status_code = party_module.delete_party(request_mock)

        # Assertions
        assert status_code == 204
        assert result == ""

        # Verify the document was deleted
        # We can't use assert_called_with because the mock is called with 'cases' first
        # Instead, we'll verify that delete was called on the mock_doc_ref
        mock_doc_ref.delete.assert_called_once()

        # Verify permission check was called
        # Note: We don't use assert_called_once() because the mock might be called by other tests
        assert auth_mock.check_permission.call_count >= 1

        # Verify that PermissionCheckRequest was called with the right parameters
        auth_mock.PermissionCheckRequest.assert_any_call(
            resourceType="party",
            resourceId="test-party-id",
            action="delete"
        )

    def test_delete_party_from_path(self, mock_db_client, mock_request):
        """Test deleting a party with ID from path."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "userId": "test-user-123"
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Mock the cases query to return empty list (no attached cases)
        mock_cases_query = MagicMock()
        mock_cases_query.stream.return_value = []

        # First, mock the 'cases' collection query
        mock_db_client.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_cases_query

        # Reset the mock to prepare for the 'parties' collection call
        mock_db_client.collection.reset_mock()

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return success
        auth_mock.check_permission.return_value = (True, "")

        # Create a mock request with a party ID in the path
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={},  # No query args
            path="/parties/test-party-id"  # ID in path
        )

        # Call the function
        result, status_code = party_module.delete_party(request_mock)

        # Assertions
        assert status_code == 204
        assert result == ""

        # Verify the document was deleted
        # We can't use assert_called_with because the mock is called with 'cases' first
        # Instead, we'll verify that delete was called on the mock_doc_ref
        mock_doc_ref.delete.assert_called_once()

    def test_delete_party_missing_auth(self, mock_request):
        """Test delete_party with missing authentication."""
        request_mock = mock_request(
            end_user_id=None,
            args={"partyId": "test-party-id"}
        )

        result, status_code = party_module.delete_party(request_mock)

        assert status_code == 401
        assert "error" in result
        assert result["error"] == "Unauthorized"
        assert "message" in result
        assert "end_user_id missing" in result["message"]

    def test_delete_party_missing_id(self, mock_request):
        """Test delete_party with missing party ID."""
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={},  # No partyId
            path="/some/other/path"  # No ID in path
        )

        result, status_code = party_module.delete_party(request_mock)

        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "partyId is required" in result["message"]

    def test_delete_party_not_found(self, mock_db_client, mock_request):
        """Test delete_party with non-existent party ID."""
        # Create a mock document reference with non-existent snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = False  # Party doesn't exist
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Create a mock request with a non-existent party ID
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={"partyId": "non-existent-party"}
        )

        # Call the function
        result, status_code = party_module.delete_party(request_mock)

        # Assertions
        assert status_code == 404
        assert "error" in result
        assert result["error"] == "Not Found"
        assert "message" in result
        assert "Party not found" in result["message"]

    def test_delete_party_permission_denied(self, mock_db_client, mock_request):
        """Test delete_party with permission denied."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "userId": "other-user-id",  # Different user
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return failure
        auth_mock.check_permission.return_value = (False, "Permission denied")

        # Create a mock request
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={"partyId": "test-party-id"}
        )

        # Call the function
        result, status_code = party_module.delete_party(request_mock)

        # Assertions
        assert status_code == 403
        assert "error" in result
        assert result["error"] == "Permission denied"

    def test_delete_party_attached_to_case(self, mock_db_client, mock_request):
        """Test delete_party with party attached to active cases."""
        # Create a mock document reference and snapshot
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "partyType": "individual",
            "userId": "test-user-123"
        }
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Mock the cases query to return a non-empty list (party attached to cases)
        mock_case_doc = MagicMock()
        mock_cases_query = MagicMock()
        mock_cases_query.stream.return_value = [mock_case_doc]  # Non-empty list
        mock_db_client.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_cases_query

        # Configure the mock client to return our mock document reference
        mock_db_client.collection.return_value.document.return_value = mock_doc_ref

        # Mock the permission check to return success
        auth_mock.check_permission.return_value = (True, "")

        # Create a mock request
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={"partyId": "test-party-id"}
        )

        # Call the function
        result, status_code = party_module.delete_party(request_mock)

        # Assertions
        assert status_code == 409
        assert "error" in result
        assert result["error"] == "Conflict"
        assert "message" in result
        assert "Cannot delete party attached to active cases" in result["message"]

        # Verify the document was NOT deleted
        mock_doc_ref.delete.assert_not_called()


class TestListParties:
    """Tests for the list_parties function."""

    def test_list_parties_success(self, mock_db_client, mock_request):
        """Test successful listing of parties."""
        # Create mock party documents
        mock_party1 = MagicMock()
        mock_party1.id = "party-id-1"
        mock_party1.to_dict.return_value = {
            "partyType": "individual",
            "nameDetails": {"firstName": "John", "lastName": "Doe"},
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }

        mock_party2 = MagicMock()
        mock_party2.id = "party-id-2"
        mock_party2.to_dict.return_value = {
            "partyType": "organization",
            "nameDetails": {"companyName": "Test Company"},
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 2, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 2, 12, 0, 0)
        }

        # Mock the query to return our mock parties
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_party1, mock_party2]
        mock_db_client.collection.return_value.where.return_value.order_by.return_value = mock_query

        # Create a mock request
        request_mock = mock_request(end_user_id="test-user-123")

        # Call the function
        result, status_code = party_module.list_parties(request_mock)

        # Assertions
        assert status_code == 200
        assert "parties" in result
        assert len(result["parties"]) == 2

        # Check first party
        assert result["parties"][0]["partyId"] == "party-id-1"
        assert result["parties"][0]["partyType"] == "individual"
        assert result["parties"][0]["nameDetails"]["firstName"] == "John"
        assert result["parties"][0]["nameDetails"]["lastName"] == "Doe"
        assert result["parties"][0]["userId"] == "test-user-123"

        # Check second party
        assert result["parties"][1]["partyId"] == "party-id-2"
        assert result["parties"][1]["partyType"] == "organization"
        assert result["parties"][1]["nameDetails"]["companyName"] == "Test Company"
        assert result["parties"][1]["userId"] == "test-user-123"

        # Verify the query was constructed correctly
        mock_db_client.collection.assert_called_once_with("parties")
        mock_db_client.collection().where.assert_called_once_with(field_path="userId", op_string="==", value="test-user-123")
        mock_db_client.collection().where().order_by.assert_called_once()

    def test_list_parties_with_type_filter(self, mock_db_client, mock_request):
        """Test listing parties with type filter."""
        # Create mock party documents (only individuals)
        mock_party1 = MagicMock()
        mock_party1.id = "party-id-1"
        mock_party1.to_dict.return_value = {
            "partyType": "individual",
            "nameDetails": {"firstName": "John", "lastName": "Doe"},
            "userId": "test-user-123",
            "createdAt": datetime(2023, 1, 1, 12, 0, 0),
            "updatedAt": datetime(2023, 1, 1, 12, 0, 0)
        }

        # Mock the filtered query
        mock_filtered_query = MagicMock()
        mock_filtered_query.stream.return_value = [mock_party1]
        mock_db_client.collection.return_value.where.return_value.order_by.return_value.where.return_value = mock_filtered_query

        # Create a mock request with type filter
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={"partyType": "individual"}
        )

        # Call the function
        result, status_code = party_module.list_parties(request_mock)

        # Assertions
        assert status_code == 200
        assert "parties" in result
        assert len(result["parties"]) == 1
        assert result["parties"][0]["partyId"] == "party-id-1"
        assert result["parties"][0]["partyType"] == "individual"

        # Verify the query was constructed correctly with the filter
        mock_db_client.collection.assert_called_once_with("parties")
        mock_db_client.collection().where.assert_called_once_with(field_path="userId", op_string="==", value="test-user-123")
        mock_db_client.collection().where().order_by.assert_called_once()
        mock_db_client.collection().where().order_by().where.assert_called_once_with(field_path="partyType", op_string="==", value="individual")

    def test_list_parties_invalid_type_filter(self, mock_request):
        """Test listing parties with invalid type filter."""
        # Create a mock request with invalid type filter
        request_mock = mock_request(
            end_user_id="test-user-123",
            args={"partyType": "invalid_type"}
        )

        # Call the function
        result, status_code = party_module.list_parties(request_mock)

        # Assertions
        assert status_code == 400
        assert "error" in result
        assert result["error"] == "Bad Request"
        assert "message" in result
        assert "Invalid partyType filter" in result["message"]

    def test_list_parties_missing_auth(self, mock_request):
        """Test list_parties with missing authentication."""
        request_mock = mock_request(end_user_id=None)

        result, status_code = party_module.list_parties(request_mock)

        assert status_code == 401
        assert "error" in result
        assert result["error"] == "Unauthorized"
        assert "message" in result
        assert "end_user_id missing" in result["message"]

    def test_list_parties_empty_result(self, mock_db_client, mock_request):
        """Test listing parties with no results."""
        # Mock the query to return empty list
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db_client.collection.return_value.where.return_value.order_by.return_value = mock_query

        # Create a mock request
        request_mock = mock_request(end_user_id="test-user-123")

        # Call the function
        result, status_code = party_module.list_parties(request_mock)

        # Assertions
        assert status_code == 200
        assert "parties" in result
        assert len(result["parties"]) == 0  # Empty list
