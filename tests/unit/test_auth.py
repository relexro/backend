"""
Unit Tests for Authentication Module

This module contains unit tests for the auth.py module, focusing on token validation,
user extraction, and core authentication logic.
"""
import pytest
from unittest.mock import MagicMock, patch, mock_open
import base64
import json
import os
import datetime
from flask import Request, jsonify
from pydantic import ValidationError

# Import the module/functions to be tested
from functions.src import auth as auth_module
from functions.src.auth import AuthContext

@pytest.fixture(autouse=True)
def mock_firebase_admin_sdk(mocker):
    """Mocks firebase_admin initialization and auth modules."""
    mocker.patch('firebase_admin.initialize_app', return_value=None)
    mocker.patch('firebase_admin.get_app', return_value=MagicMock())

    # Mock firebase_auth_admin (the alias for firebase_admin.auth)
    mock_firebase_auth = MagicMock()
    mocker.patch('functions.src.auth.firebase_auth_admin', new=mock_firebase_auth)


@pytest.fixture
def mock_google_id_token_verify(mocker):
    """Mocks google.oauth2.id_token.verify_firebase_token and verify_oauth2_token."""
    mock_verify_firebase = mocker.patch('google.oauth2.id_token.verify_firebase_token')
    mock_verify_oauth2 = mocker.patch('google.oauth2.id_token.verify_oauth2_token')
    return mock_verify_firebase, mock_verify_oauth2

@pytest.fixture
def mock_google_auth_requests(mocker):
    """Mocks google.auth.transport.requests.Request."""
    return mocker.patch('google.auth.transport.requests.Request')

@pytest.fixture
def mock_firestore_client(mocker):
    """Mocks the Firestore client and its methods."""
    # Create a basic mock Firestore client
    mock_db = MagicMock(spec=auth_module.firestore.Client)
    mock_doc_ref = MagicMock()
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = False
    mock_doc_snapshot.to_dict.return_value = {}
    mock_doc_ref.get.return_value = mock_doc_snapshot
    mock_doc_ref.set.return_value = None

    mock_collection_ref = MagicMock()
    mock_collection_ref.document.return_value = mock_doc_ref
    mock_collection_ref.where.return_value.where.return_value.limit.return_value.stream.return_value = []

    mock_db.collection.return_value = mock_collection_ref

    # Mock the Client constructor instead of client function
    mocker.patch('functions.src.auth.firestore.Client', return_value=mock_db)
    mocker.patch('functions.src.auth._get_firestore_client', return_value=mock_db)

    # Create more sophisticated mocks for get_document_data and get_membership_data
    # that can be configured per test

    # Default implementation for get_document_data
    def default_get_document_data(db, collection, doc_id):
        return None  # Default to document not found

    # Default implementation for get_membership_data
    def default_get_membership_data(db, user_id, org_id):
        return None  # Default to no membership

    # Create the mocks with default implementations
    mock_get_document_data = mocker.patch('functions.src.auth.get_document_data',
                                         side_effect=default_get_document_data)
    mock_get_membership_data = mocker.patch('functions.src.auth.get_membership_data',
                                           side_effect=default_get_membership_data)

    # Add the mocks to the mock_db object for easy access in tests
    mock_db.mock_get_document_data = mock_get_document_data
    mock_db.mock_get_membership_data = mock_get_membership_data

    return mock_db

@pytest.fixture
def configure_mock_document_data():
    """Helper fixture to configure document data responses for specific collection/doc_id combinations."""
    def _configure(document_data_map):
        """
        Configure mock responses for get_document_data.

        Args:
            document_data_map: A dictionary mapping (collection, doc_id) tuples to document data.
                Example: {('cases', 'case1'): {'userId': 'user1', 'organizationId': 'org1'}}
        """
        def mock_get_document_data(db, collection, doc_id):
            key = (collection, doc_id)
            return document_data_map.get(key)

        # Replace the side_effect of the mock
        auth_module.get_document_data = MagicMock(side_effect=mock_get_document_data)

    return _configure

@pytest.fixture
def configure_mock_membership_data():
    """Helper fixture to configure membership data responses for specific user_id/org_id combinations."""
    def _configure(membership_data_map):
        """
        Configure mock responses for get_membership_data.

        Args:
            membership_data_map: A dictionary mapping (user_id, org_id) tuples to membership data.
                Example: {('user1', 'org1'): {'role': 'administrator', 'userId': 'user1', 'organizationId': 'org1'}}
        """
        def mock_get_membership_data(db, user_id, org_id):
            key = (user_id, org_id)
            return membership_data_map.get(key)

        # Replace the side_effect of the mock
        auth_module.get_membership_data = MagicMock(side_effect=mock_get_membership_data)

    return _configure

@pytest.fixture
def mock_request_builder(mocker):
    """Factory to create mock Flask request objects."""
    def _builder(headers=None, method='POST', json_data=None, health_check=False):
        req = MagicMock(spec=Request)
        req.headers = headers or {}
        if health_check:
            req.headers = {auth_module.EXPECTED_HEALTH_CHECK_HEADER: 'true', **(headers or {})}

        req.method = method
        req.get_json = MagicMock(return_value=json_data if json_data is not None else {})
        return req
    return _builder


class TestValidateFirebaseIdToken:
    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    def test_valid_token(self, mock_google_id_token_verify, mock_google_auth_requests):
        mock_verify_firebase, _ = mock_google_id_token_verify
        expected_claims = {"sub": "test_user_id", "email": "test@example.com", "iss": "https://securetoken.google.com/test-project"}
        mock_verify_firebase.return_value = expected_claims

        token = "valid_firebase_token"
        claims = auth_module.validate_firebase_id_token(token)

        assert claims == expected_claims
        # Just check that it was called once with the right token and audience
        assert mock_verify_firebase.call_count == 1
        args, kwargs = mock_verify_firebase.call_args
        assert args[0] == token
        assert kwargs.get('audience') == "test-project"

    def test_invalid_token_verification_fails(self, mock_google_id_token_verify, mock_google_auth_requests):
        mock_verify_firebase, _ = mock_google_id_token_verify
        mock_verify_firebase.side_effect = ValueError("Invalid token")

        with pytest.raises(ValueError, match="Invalid token"):
            auth_module.validate_firebase_id_token("invalid_token")

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    def test_invalid_issuer(self, mock_google_id_token_verify, mock_google_auth_requests):
        mock_verify_firebase, _ = mock_google_id_token_verify
        mock_verify_firebase.return_value = {"sub": "test_user_id", "iss": "https://wrong.issuer.com/test-project"}

        with pytest.raises(ValueError, match="Invalid token issuer"):
            auth_module.validate_firebase_id_token("token_with_wrong_issuer")

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    def test_missing_sub_in_claims(self, mock_google_id_token_verify, mock_google_auth_requests):
        mock_verify_firebase, _ = mock_google_id_token_verify
        mock_verify_firebase.return_value = {"email": "test@example.com", "iss": "https://securetoken.google.com/test-project"}

        claims = auth_module.validate_firebase_id_token("token_missing_sub")
        assert "sub" not in claims


class TestValidateGatewaySaToken:
    def test_valid_token(self, mock_google_id_token_verify, mock_google_auth_requests):
        _, mock_verify_oauth2 = mock_google_id_token_verify

        # Prepare a mock token that can be base64 decoded for audience extraction
        audience = "test_audience_url"
        mock_payload_dict = {"aud": audience, "sub": "sa_subject_id", "email": "sa@example.com"}
        mock_payload_json = json.dumps(mock_payload_dict)
        mock_payload_b64 = base64.urlsafe_b64encode(mock_payload_json.encode('utf-8')).decode('utf-8').rstrip("=")
        mock_jwt = f"header.{mock_payload_b64}.signature"

        expected_claims = mock_payload_dict
        mock_verify_oauth2.return_value = expected_claims

        claims = auth_module.validate_gateway_sa_token(mock_jwt)

        assert claims == expected_claims
        # Just check that it was called once with the right token and audience
        assert mock_verify_oauth2.call_count == 1
        args, kwargs = mock_verify_oauth2.call_args
        assert args[0] == mock_jwt
        assert kwargs.get('audience') == audience

    def test_malformed_jwt(self, mock_google_id_token_verify):
        with pytest.raises(ValueError, match="Malformed JWT token"):
            auth_module.validate_gateway_sa_token("malformed.token")

    def test_token_missing_aud_claim(self, mock_google_id_token_verify):
        _, mock_verify_oauth2 = mock_google_id_token_verify
        mock_payload_dict = {"sub": "sa_subject_id"} # No 'aud'
        mock_payload_json = json.dumps(mock_payload_dict)
        mock_payload_b64 = base64.urlsafe_b64encode(mock_payload_json.encode('utf-8')).decode('utf-8').rstrip("=")
        mock_jwt = f"header.{mock_payload_b64}.signature"

        with pytest.raises(ValueError, match="Token missing 'aud' claim"):
            auth_module.validate_gateway_sa_token(mock_jwt)

    def test_invalid_token_verification_fails(self, mock_google_id_token_verify, mock_google_auth_requests):
        _, mock_verify_oauth2 = mock_google_id_token_verify
        mock_verify_oauth2.side_effect = ValueError("Invalid OAuth2 token")

        mock_payload_dict = {"aud": "some_audience", "sub": "sa_subject_id"}
        mock_payload_json = json.dumps(mock_payload_dict)
        mock_payload_b64 = base64.urlsafe_b64encode(mock_payload_json.encode('utf-8')).decode('utf-8').rstrip("=")
        mock_jwt = f"header.{mock_payload_b64}.signature"

        with pytest.raises(ValueError, match="Invalid OAuth2 token"):
            auth_module.validate_gateway_sa_token(mock_jwt)


class TestGetAuthenticatedUser:
    def test_health_check(self, mock_request_builder):
        request = mock_request_builder(health_check=True)
        auth_context, status_code, error_message = auth_module.get_authenticated_user(request)
        assert status_code == 200
        assert error_message == "Health check request"
        assert auth_context is None

    def test_api_gateway_valid_userinfo(self, mock_request_builder):
        user_info = {"sub": "firebase_uid_123", "email": "user@example.com", "locale": "ro-RO"}
        user_info_b64 = base64.b64encode(json.dumps(user_info).encode('utf-8')).decode('utf-8')
        headers = {"X-Endpoint-API-Userinfo": user_info_b64}
        request = mock_request_builder(headers=headers)

        auth_context, status_code, error_message = auth_module.get_authenticated_user(request)

        assert status_code == 200
        assert error_message is None
        assert auth_context is not None
        assert auth_context.is_authenticated_call_from_gateway is True
        assert auth_context.firebase_user_id == "firebase_uid_123"
        assert auth_context.firebase_user_email == "user@example.com"
        assert auth_context.firebase_user_locale == "ro-RO"

    def test_api_gateway_userinfo_missing_sub(self, mock_request_builder):
        user_info = {"email": "user@example.com"} # Missing "sub"
        user_info_b64 = base64.b64encode(json.dumps(user_info).encode('utf-8')).decode('utf-8')
        headers = {"X-Endpoint-API-Userinfo": user_info_b64}
        request = mock_request_builder(headers=headers)

        auth_context, status_code, error_message = auth_module.get_authenticated_user(request)

        assert status_code == 401
        assert "Missing subject (user ID) in userinfo header" in error_message
        assert auth_context is None

    def test_direct_firebase_token_valid(self, mock_request_builder, mock_google_id_token_verify, mock_google_auth_requests):
        mock_verify_firebase, _ = mock_google_id_token_verify
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            expected_claims = {"sub": "direct_fb_uid", "email": "direct@example.com", "locale": "en-US", "iss": "https://securetoken.google.com/test-project"}
            mock_verify_firebase.return_value = expected_claims

            headers = {"Authorization": "Bearer valid_direct_firebase_token"}
            request = mock_request_builder(headers=headers)

            auth_context, status_code, error_message = auth_module.get_authenticated_user(request)

            assert status_code == 200
            assert error_message is None
            assert auth_context is not None
            assert auth_context.is_authenticated_call_from_gateway is False
            assert auth_context.firebase_user_id == "direct_fb_uid"
            assert auth_context.firebase_user_email == "direct@example.com"
            assert auth_context.firebase_user_locale == "en-US"

    def test_no_auth_header(self, mock_request_builder):
        request = mock_request_builder(headers={})
        auth_context, status_code, error_message = auth_module.get_authenticated_user(request)
        assert status_code == 401
        assert "Missing or invalid Authorization header" in error_message
        assert auth_context is None

    def test_invalid_base64_userinfo(self, mock_request_builder):
        headers = {"X-Endpoint-API-Userinfo": "invalid_base64"}
        request = mock_request_builder(headers=headers)

        auth_context, status_code, error_message = auth_module.get_authenticated_user(request)

        assert status_code == 500
        assert "Error processing authentication information" in error_message
        assert auth_context is None

    def test_invalid_json_userinfo(self, mock_request_builder):
        # Valid base64 but invalid JSON when decoded
        invalid_json_b64 = base64.b64encode(b"not valid json").decode('utf-8')
        headers = {"X-Endpoint-API-Userinfo": invalid_json_b64}
        request = mock_request_builder(headers=headers)

        auth_context, status_code, error_message = auth_module.get_authenticated_user(request)

        assert status_code == 500
        assert "Error processing authentication information" in error_message
        assert auth_context is None

    def test_direct_firebase_token_validation_failure(self, mock_request_builder, mock_google_id_token_verify):
        mock_verify_firebase, mock_verify_oauth2 = mock_google_id_token_verify
        mock_verify_firebase.side_effect = ValueError("Invalid Firebase token")
        mock_verify_oauth2.side_effect = ValueError("Invalid OAuth2 token")

        headers = {"Authorization": "Bearer invalid_token"}
        request = mock_request_builder(headers=headers)

        auth_context, status_code, error_message = auth_module.get_authenticated_user(request)

        assert status_code == 401
        assert "Invalid authentication token" in error_message
        assert auth_context is None


class TestRequiresAuthDecorator:
    def test_successful_auth(self, mock_request_builder, mocker):
        # Mock the get_authenticated_user function to return a successful auth
        auth_context = AuthContext(
            is_authenticated_call_from_gateway=True,
            firebase_user_id="test_user_id",
            firebase_user_email="test@example.com",
            firebase_user_locale="en-US"
        )
        mocker.patch('functions.src.auth.get_authenticated_user', return_value=(auth_context, 200, None))

        # Create a mock function to decorate
        mock_func = mocker.Mock(return_value=("Success", 200))

        # Apply the decorator
        decorated_func = auth_module.requires_auth(mock_func)

        # Call the decorated function
        request = mock_request_builder()
        result = decorated_func(request)

        # Verify the original function was called with the auth_context
        mock_func.assert_called_once_with(request, auth_context)
        assert result == ("Success", 200)

    def test_options_request(self, mock_request_builder, mocker):
        # Create a mock function to decorate
        mock_func = mocker.Mock()

        # Apply the decorator
        decorated_func = auth_module.requires_auth(mock_func)

        # Call the decorated function with OPTIONS method
        request = mock_request_builder(method='OPTIONS')
        result, status_code = decorated_func(request)

        # Verify the original function was not called and we got a 204 response
        mock_func.assert_not_called()
        assert status_code == 204
        assert result == ''

    def test_auth_failure(self, mock_request_builder, mocker):
        # Create a Flask app for the test context
        from flask import Flask, Response
        app = Flask(__name__)

        # Mock the get_authenticated_user function to return an auth failure
        mocker.patch('functions.src.auth.get_authenticated_user',
                    return_value=(None, 401, "Authentication failed"))

        # Create a mock response for jsonify
        expected_json = {"error": "Unauthorized", "message": "Authentication failed"}
        mock_response = Response(json.dumps(expected_json), mimetype='application/json')
        mocker.patch('flask.jsonify', return_value=mock_response)

        # Create a mock function to decorate
        mock_func = mocker.Mock()

        # Apply the decorator
        decorated_func = auth_module.requires_auth(mock_func)

        # Call the decorated function within app context
        with app.app_context():
            request = mock_request_builder()
            result, status_code = decorated_func(request)

        # Verify the original function was not called and we got a 401 response
        mock_func.assert_not_called()
        assert status_code == 401
        # Just verify it's a Response object
        assert isinstance(result, Response)


class TestPermissionCheckRequestModel:
    def test_valid_request(self):
        data = {"resourceId": "id1", "action": "read", "resourceType": "case"}
        req = auth_module.PermissionCheckRequest(**data)  # Using ** for Pydantic v2 compatibility
        assert req.resourceType == "case"
        assert req.resourceId == "id1"
        assert req.action == "read"
        assert req.organizationId is None

    def test_valid_request_with_organization(self):
        data = {"resourceId": "id1", "action": "read", "resourceType": "case", "organizationId": "org1"}
        req = auth_module.PermissionCheckRequest(**data)
        assert req.resourceType == "case"
        assert req.organizationId == "org1"

    def test_invalid_resource_type(self):
        data = {"resourceId": "id1", "action": "read", "resourceType": "invalid_type"}
        with pytest.raises(ValueError, match="Invalid resourceType"):
            auth_module.PermissionCheckRequest(**data)

    def test_optional_resource_id(self):
        # For creation/listing actions, resourceId can be None
        data = {"action": "create", "resourceType": "case", "organizationId": "org1"}
        req = auth_module.PermissionCheckRequest(**data)
        assert req.resourceId is None
        assert req.action == "create"


class TestPermissionChecking:
    def test_is_action_allowed(self):
        # Test with a valid role and action
        permissions_map = {
            "admin": {"read", "write", "delete"},
            "user": {"read"}
        }

        # Admin should be allowed to read
        assert auth_module._is_action_allowed(permissions_map, "admin", "read") is True

        # Admin should be allowed to write
        assert auth_module._is_action_allowed(permissions_map, "admin", "write") is True

        # User should be allowed to read
        assert auth_module._is_action_allowed(permissions_map, "user", "read") is True

        # User should not be allowed to write
        assert auth_module._is_action_allowed(permissions_map, "user", "write") is False

        # Non-existent role should not be allowed any action
        assert auth_module._is_action_allowed(permissions_map, "guest", "read") is False

        # Non-existent action should not be allowed for any role
        assert auth_module._is_action_allowed(permissions_map, "admin", "execute") is False

    def test_check_permission_with_invalid_resource_type(self, mock_firestore_client):
        # Create a request with an invalid resource type
        req = MagicMock()
        req.resourceType = "invalid_type"  # Not in permission_check_functions

        # Call check_permission
        allowed, message = auth_module.check_permission("test_user", req)

        # Should return False with an error message
        assert allowed is False
        assert "No permission checker configured for resource type" in message

    def test_check_permission_with_exception(self, mock_firestore_client, mocker):
        # Mock _check_case_permissions to raise an exception
        mocker.patch('functions.src.auth._check_case_permissions', side_effect=Exception("Test exception"))

        # Create a request with a valid resource type
        req = MagicMock()
        req.resourceType = auth_module.TYPE_CASE

        # Call check_permission
        allowed, message = auth_module.check_permission("test_user", req)

        # Should return False with an error message
        assert allowed is False
        assert "An internal error occurred during permission check" in message


class TestCheckOrganizationPermissions:
    def test_admin_all_org_permissions(self, mock_firestore_client, configure_mock_membership_data):
        """Test that admin users have all permissions defined in PERMISSIONS map."""
        user_id = "admin_user"
        org_id = "org_1"

        # Configure membership data for this test
        membership_data = {
            (user_id, org_id): {"role": auth_module.ROLE_ADMIN, "userId": user_id, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        # Test all actions defined for admin in PERMISSIONS map
        actions_to_test = auth_module.PERMISSIONS[auth_module.TYPE_ORGANIZATION][auth_module.ROLE_ADMIN]
        for action in actions_to_test:
            req = auth_module.PermissionCheckRequest(
                resourceId=org_id,
                action=action,
                resourceType=auth_module.TYPE_ORGANIZATION,
                organizationId=org_id
            )
            allowed, msg = auth_module._check_organization_permissions(mock_firestore_client, user_id, req)
            assert allowed is True, f"Admin should be allowed action '{action}', msg: {msg}"

    def test_staff_allowed_org_permissions(self, mock_firestore_client, configure_mock_membership_data):
        """Test that staff users have the correct subset of permissions."""
        user_id = "staff_user"
        org_id = "org_1"

        # Configure membership data for this test
        membership_data = {
            (user_id, org_id): {"role": auth_module.ROLE_STAFF, "userId": user_id, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        # Explicitly list staff allowed actions from PERMISSIONS map
        staff_allowed_actions = ["read", "create_case", "list_cases", "listMembers"]

        for action in staff_allowed_actions:
            req = auth_module.PermissionCheckRequest(
                resourceId=org_id,
                action=action,
                resourceType=auth_module.TYPE_ORGANIZATION,
                organizationId=org_id
            )
            allowed, msg = auth_module._check_organization_permissions(mock_firestore_client, user_id, req)
            assert allowed is True, f"Staff should be allowed action '{action}', msg: {msg}"

    def test_staff_disallowed_org_permissions(self, mock_firestore_client, configure_mock_membership_data):
        """Test that staff users are denied permissions not in their role."""
        user_id = "staff_user"
        org_id = "org_1"

        # Configure membership data for this test
        membership_data = {
            (user_id, org_id): {"role": auth_module.ROLE_STAFF, "userId": user_id, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        # Actions that staff should not be allowed to perform
        disallowed_actions = ["update", "delete", "assign_case", "addMember", "setMemberRole", "removeMember"]

        for action in disallowed_actions:
            req = auth_module.PermissionCheckRequest(
                resourceId=org_id,
                action=action,
                resourceType=auth_module.TYPE_ORGANIZATION,
                organizationId=org_id
            )
            allowed, msg = auth_module._check_organization_permissions(mock_firestore_client, user_id, req)
            assert allowed is False, f"Staff should NOT be allowed action '{action}', msg: {msg}"

    def test_non_member_org_permissions(self, mock_firestore_client, configure_mock_membership_data):
        """Test that non-members are denied all permissions."""
        user_id = "non_member_user"
        org_id = "org_1"

        # Configure empty membership data map (get_membership_data will return None)
        configure_mock_membership_data({})

        # Test a representative set of actions
        actions_to_test = ["read", "update", "manage_members"]

        for action in actions_to_test:
            req = auth_module.PermissionCheckRequest(
                resourceId=org_id,
                action=action,
                resourceType=auth_module.TYPE_ORGANIZATION,
                organizationId=org_id
            )
            allowed, msg = auth_module._check_organization_permissions(mock_firestore_client, user_id, req)
            assert allowed is False, f"Non-member should NOT be allowed action '{action}', msg: {msg}"
            assert f"User {user_id} is not a member of organization {org_id}" in msg

    def test_no_org_id_provided(self, mock_firestore_client):
        """Test that requests without an organization ID are rejected."""
        user_id = "any_user"

        # Test with resourceId=None and organizationId=None
        req = auth_module.PermissionCheckRequest(
            action="read",
            resourceType=auth_module.TYPE_ORGANIZATION
        )
        allowed, msg = auth_module._check_organization_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert "organizationId is required" in msg

    def test_user_in_org_no_role(self, mock_firestore_client, configure_mock_membership_data):
        """Test that users with membership but no role are denied permissions."""
        user_id = "user_no_role"
        org_id = "org_1"

        # Configure membership data with no role
        membership_data = {
            (user_id, org_id): {"role": None, "userId": user_id, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        req = auth_module.PermissionCheckRequest(
            resourceId=org_id,
            action="read",
            resourceType=auth_module.TYPE_ORGANIZATION,
            organizationId=org_id
        )
        allowed, msg = auth_module._check_organization_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert f"User {user_id} has no role assigned" in msg

    def test_admin_manage_members_sub_actions(self, mock_firestore_client, configure_mock_membership_data):
        """Test that admin users can perform all member management sub-actions."""
        user_id = "admin_user_manage"
        org_id = "org_manage"

        # Configure membership data for admin
        membership_data = {
            (user_id, org_id): {"role": auth_module.ROLE_ADMIN, "userId": user_id, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        # These actions should be allowed if "manage_members" is allowed for admin
        sub_actions = ["addMember", "setMemberRole", "removeMember", "listMembers"]

        for action in sub_actions:
            req = auth_module.PermissionCheckRequest(
                resourceId=org_id,
                action=action,
                resourceType=auth_module.TYPE_ORGANIZATION,
                organizationId=org_id
            )
            allowed, msg = auth_module._check_organization_permissions(mock_firestore_client, user_id, req)
            assert allowed is True, f"Admin should be allowed sub-action '{action}' via manage_members, msg: {msg}"

    def test_cross_org_access_denied_for_org_resource(self, mock_firestore_client, configure_mock_membership_data):
        """Test that users cannot access organization resources from a different organization."""
        user_id = "user_from_org_A"
        org_A_id = "org_A"
        org_B_id = "org_B"  # Target resource is in Org B

        # Configure membership data: User is a member (admin) of Org A
        membership_data = {
            (user_id, org_A_id): {"role": auth_module.ROLE_ADMIN, "userId": user_id, "organizationId": org_A_id}
            # User is NOT a member of Org B (no entry for this combination)
        }
        configure_mock_membership_data(membership_data)

        # User from Org A attempts to read Org B's details
        req = auth_module.PermissionCheckRequest(
            resourceId=org_B_id,  # Attempting to access Org B
            action="read",
            resourceType=auth_module.TYPE_ORGANIZATION,
            organizationId=org_B_id  # Context is Org B
        )

        allowed, msg = auth_module._check_organization_permissions(mock_firestore_client, user_id, req)

        assert allowed is False, f"User {user_id} from {org_A_id} should not access {org_B_id}, msg: {msg}"
        assert f"User {user_id} is not a member of organization {org_B_id}" in msg


class TestCheckPartyPermissions:
    """Tests for the _check_party_permissions function."""

    @pytest.mark.parametrize("action", ["create", "list"])
    def test_party_create_list_actions_allowed(self, mock_firestore_client, action):
        """Test that 'create' and 'list' actions are always allowed for parties."""
        user_id = "test_user_party_create_list"
        req = auth_module.PermissionCheckRequest(
            action=action,
            resourceType=auth_module.TYPE_PARTY
        )

        allowed, msg = auth_module._check_party_permissions(mock_firestore_client, user_id, req)

        assert allowed is True, f"User should be allowed action '{action}' for parties, msg: {msg}"
        assert msg == ""

    def test_party_owner_allowed_actions(self, mock_firestore_client):
        """Test that party owners can perform all owner-allowed actions."""
        user_id = "party_owner"
        party_id = "party_123"

        # Mock the party data to show this user as owner
        auth_module.get_document_data = MagicMock(return_value={"userId": user_id})

        # Test all actions defined for party owners
        owner_allowed_actions = auth_module.PERMISSIONS[auth_module.TYPE_PARTY][auth_module.ROLE_OWNER]
        for action in owner_allowed_actions:
            if action not in ["create", "list"]:  # These are tested separately
                req = auth_module.PermissionCheckRequest(
                    resourceId=party_id,
                    action=action,
                    resourceType=auth_module.TYPE_PARTY
                )
                allowed, msg = auth_module._check_party_permissions(mock_firestore_client, user_id, req)
                assert allowed is True, f"Owner should be allowed action '{action}' on their party, msg: {msg}"

    def test_party_owner_invalid_action_for_resource(self, mock_firestore_client):
        """Test that even party owners cannot perform invalid actions."""
        user_id = "party_owner_invalid_action"
        party_id = "party_124"

        # Mock the party data to show this user as owner
        auth_module.get_document_data = MagicMock(return_value={"userId": user_id})

        # Example of an action not defined for TYPE_PARTY in PERMISSIONS
        invalid_action = "archive"
        req = auth_module.PermissionCheckRequest(
            resourceId=party_id,
            action=invalid_action,
            resourceType=auth_module.TYPE_PARTY
        )
        allowed, msg = auth_module._check_party_permissions(mock_firestore_client, user_id, req)
        assert allowed is False, f"Owner should NOT be allowed invalid action '{invalid_action}', msg: {msg}"
        assert f"Action '{invalid_action}' is invalid for resource type '{auth_module.TYPE_PARTY}'" in msg

    def test_party_non_owner_denied(self, mock_firestore_client):
        """Test that non-owners are denied access to parties."""
        actual_owner_id = "actual_party_owner"
        user_id = "non_owner_user_party"  # Current user trying to access
        party_id = "party_456"

        # Mock the party data to show a different user as owner
        auth_module.get_document_data = MagicMock(return_value={"userId": actual_owner_id})

        # Test a representative set of actions
        actions_to_test = ["read", "update", "delete"]
        for action in actions_to_test:
            req = auth_module.PermissionCheckRequest(
                resourceId=party_id,
                action=action,
                resourceType=auth_module.TYPE_PARTY
            )
            allowed, msg = auth_module._check_party_permissions(mock_firestore_client, user_id, req)
            assert allowed is False, f"Non-owner should NOT be allowed action '{action}', msg: {msg}"
            assert f"User {user_id} is not the owner of party {party_id}" in msg

    def test_party_not_found(self, mock_firestore_client):
        """Test that non-existent parties return appropriate error."""
        user_id = "any_user_party_not_found"
        party_id = "non_existent_party"

        # Mock get_document_data to return None (party not found)
        auth_module.get_document_data = MagicMock(return_value=None)

        req = auth_module.PermissionCheckRequest(
            resourceId=party_id,
            action="read",
            resourceType=auth_module.TYPE_PARTY
        )
        allowed, msg = auth_module._check_party_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert f"Party {party_id} not found" in msg

    def test_party_missing_resourceid_for_read(self, mock_firestore_client):
        """Test that read actions require a resourceId."""
        user_id = "any_user_party_missing_id"

        # No resourceId provided
        req = auth_module.PermissionCheckRequest(
            action="read",
            resourceType=auth_module.TYPE_PARTY
        )
        allowed, msg = auth_module._check_party_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert "resourceId is required" in msg


class TestCheckCasePermissions:
    # === Individual Case Scenarios ===
    def test_individual_case_owner_allowed_actions(self, mock_firestore_client, configure_mock_document_data):
        """Test that case owners can perform all owner-allowed actions on individual cases."""
        user_id = "owner_user_case"
        case_id = "individual_case_1"

        # Configure document data for this test
        document_data = {
            ('cases', case_id): {"userId": user_id, "organizationId": None}  # Individual case owned by user_id
        }
        configure_mock_document_data(document_data)

        # Test a representative set of owner-allowed actions for cases
        owner_allowed_actions = auth_module.PERMISSIONS[auth_module.TYPE_CASE][auth_module.ROLE_OWNER]
        for action in owner_allowed_actions:
            req = auth_module.PermissionCheckRequest(
                resourceId=case_id,
                action=action,
                resourceType=auth_module.TYPE_CASE
            )
            allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
            assert allowed is True, f"Owner should be allowed action '{action}' on individual case, msg: {msg}"

    def test_individual_case_non_owner_denied(self, mock_firestore_client, configure_mock_document_data):
        """Test that non-owners are denied access to individual cases."""
        owner_id = "actual_owner_id"
        user_id = "non_owner_user"  # Current user
        case_id = "individual_case_2"

        # Configure document data for this test
        document_data = {
            ('cases', case_id): {"userId": owner_id, "organizationId": None}
        }
        configure_mock_document_data(document_data)

        req = auth_module.PermissionCheckRequest(
            resourceId=case_id,
            action="read",
            resourceType=auth_module.TYPE_CASE
        )
        allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
        assert allowed is False, f"Non-owner should NOT be allowed action 'read', msg: {msg}"
        assert f"User {user_id} is not the owner" in msg

    def test_individual_case_creation_listing_allowed(self, mock_firestore_client):
        """Test that any user can create or list individual cases."""
        user_id = "any_user_creating_case"

        # For 'create' and 'list', resourceId is None
        for action in ["create", "list"]:
            req = auth_module.PermissionCheckRequest(
                action=action,
                resourceType=auth_module.TYPE_CASE,
                organizationId=None  # No orgId for individual
            )
            allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
            assert allowed is True, f"User should be allowed '{action}' for individual cases, msg: {msg}"

    # === Organization Case Scenarios ===
    def test_org_case_admin_member_allowed(self, mock_firestore_client, configure_mock_document_data, configure_mock_membership_data):
        """Test that org admins can perform all admin-allowed actions on org cases."""
        user_id = "org_admin_user_case"
        org_id = "org_for_case_1"
        case_id = "org_case_1"

        # Configure document and membership data for this test
        document_data = {
            ('cases', case_id): {"userId": "creator_user", "organizationId": org_id}  # Case belongs to org_id
        }
        configure_mock_document_data(document_data)

        membership_data = {
            (user_id, org_id): {"role": auth_module.ROLE_ADMIN, "userId": user_id, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        # Admin should be allowed all actions defined for ROLE_ADMIN in PERMISSIONS[TYPE_CASE]
        admin_case_actions = auth_module.PERMISSIONS[auth_module.TYPE_CASE][auth_module.ROLE_ADMIN]
        for action in admin_case_actions:
            req = auth_module.PermissionCheckRequest(
                resourceId=case_id,
                action=action,
                resourceType=auth_module.TYPE_CASE,
                organizationId=org_id
            )
            allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
            assert allowed is True, f"Org admin should be allowed action '{action}' on org case, msg: {msg}"

    def test_org_case_staff_member_assigned_allowed(self, mock_firestore_client, configure_mock_document_data, configure_mock_membership_data):
        """Test that assigned staff members can perform update actions on org cases."""
        user_id = "org_staff_user_case_assigned"
        org_id = "org_for_case_2"
        case_id = "org_case_2"

        # Configure document and membership data for this test
        document_data = {
            ('cases', case_id): {"userId": "creator_user", "organizationId": org_id, "assignedUserId": user_id}
        }
        configure_mock_document_data(document_data)

        membership_data = {
            (user_id, org_id): {"role": auth_module.ROLE_STAFF, "userId": user_id, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        # Staff assigned can typically update, attach_party etc.
        staff_assigned_actions = ["update", "upload_file", "attach_party"]
        for action in staff_assigned_actions:
            req = auth_module.PermissionCheckRequest(
                resourceId=case_id,
                action=action,
                resourceType=auth_module.TYPE_CASE,
                organizationId=org_id
            )
            allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
            assert allowed is True, f"Assigned staff should be allowed action '{action}', msg: {msg}"

    def test_org_case_staff_member_assigned_read_list_create(self, mock_firestore_client, configure_mock_document_data, configure_mock_membership_data):
        """Test that staff members can read, list, and create cases in their org."""
        user_id = "org_staff_user_case_assigned"
        org_id = "org_for_case_2a"
        case_id = "org_case_2a"

        # Configure document and membership data for this test
        document_data = {
            ('cases', case_id): {"userId": "creator_user", "organizationId": org_id, "assignedUserId": user_id}
        }
        configure_mock_document_data(document_data)

        membership_data = {
            (user_id, org_id): {"role": auth_module.ROLE_STAFF, "userId": user_id, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        read_list_create_actions = ["read", "list", "create"]  # List/Create here implies context of the org.
        for action in read_list_create_actions:
            if action in ["list", "create"]:  # resourceId will be None
                req = auth_module.PermissionCheckRequest(
                    action=action,
                    resourceType=auth_module.TYPE_CASE,
                    organizationId=org_id
                )
            else:  # "read" requires resourceId
                req = auth_module.PermissionCheckRequest(
                    resourceId=case_id,
                    action=action,
                    resourceType=auth_module.TYPE_CASE,
                    organizationId=org_id
                )
            allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
            assert allowed is True, f"Assigned staff should be allowed action '{action}', msg: {msg}"

    def test_org_case_staff_member_unassigned_denied_modify(self, mock_firestore_client, configure_mock_document_data, configure_mock_membership_data):
        """Test that unassigned staff members cannot modify cases."""
        user_id = "org_staff_user_case_unassigned"
        org_id = "org_for_case_3"
        case_id = "org_case_3"

        # Configure document and membership data for this test
        document_data = {
            ('cases', case_id): {"userId": "creator_user", "organizationId": org_id, "assignedUserId": "another_staff_user"}
        }
        configure_mock_document_data(document_data)

        membership_data = {
            (user_id, org_id): {"role": auth_module.ROLE_STAFF, "userId": user_id, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        modifying_actions = ["update", "delete", "archive", "attach_party"]
        for action in modifying_actions:
            req = auth_module.PermissionCheckRequest(
                resourceId=case_id,
                action=action,
                resourceType=auth_module.TYPE_CASE,
                organizationId=org_id
            )
            allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
            assert allowed is False, f"Unassigned staff should NOT be allowed action '{action}', msg: {msg}"

    def test_org_case_staff_member_unassigned_allowed_read(self, mock_firestore_client, configure_mock_document_data, configure_mock_membership_data):
        """Test that unassigned staff members can still read cases in their org."""
        user_id = "org_staff_user_case_unassigned_read"
        org_id = "org_for_case_3a"
        case_id = "org_case_3a"

        # Configure document and membership data for this test
        document_data = {
            ('cases', case_id): {"userId": "creator_user", "organizationId": org_id, "assignedUserId": "another_staff_user"}
        }
        configure_mock_document_data(document_data)

        membership_data = {
            (user_id, org_id): {"role": auth_module.ROLE_STAFF, "userId": user_id, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        req = auth_module.PermissionCheckRequest(
            resourceId=case_id,
            action="read",
            resourceType=auth_module.TYPE_CASE,
            organizationId=org_id
        )
        allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
        assert allowed is True, f"Unassigned staff should be allowed to 'read' cases in their org, msg: {msg}"

    def test_org_case_non_member_denied(self, mock_firestore_client, configure_mock_document_data, configure_mock_membership_data):
        """Test that non-members cannot access org cases."""
        user_id = "non_org_member_case"
        org_id = "org_for_case_4"
        case_id = "org_case_4"

        # Configure document data and ensure membership data returns None
        document_data = {
            ('cases', case_id): {"userId": "creator_user", "organizationId": org_id}
        }
        configure_mock_document_data(document_data)

        # Empty membership_data map means get_membership_data will return None
        configure_mock_membership_data({})

        req = auth_module.PermissionCheckRequest(
            resourceId=case_id,
            action="read",
            resourceType=auth_module.TYPE_CASE,
            organizationId=org_id
        )
        allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert "not owner or member of org" in msg

    def test_org_case_owner_privileges(self, mock_firestore_client, configure_mock_document_data, configure_mock_membership_data):
        """Test that case creators have owner privileges even if they're staff."""
        user_id_creator = "case_creator_in_org"
        org_id = "org_for_case_5"
        case_id = "org_case_5"

        # Configure document and membership data for this test
        document_data = {
            ('cases', case_id): {"userId": user_id_creator, "organizationId": org_id, "assignedUserId": "another_staff"}
        }
        configure_mock_document_data(document_data)

        membership_data = {
            (user_id_creator, org_id): {"role": auth_module.ROLE_STAFF, "userId": user_id_creator, "organizationId": org_id}
        }
        configure_mock_membership_data(membership_data)

        # Even if staff and unassigned, owner permissions should apply for owner-specific actions
        owner_specific_actions = ["delete", "archive"]  # Actions typically granted to owner
        for action in owner_specific_actions:
            if action in auth_module.PERMISSIONS[auth_module.TYPE_CASE][auth_module.ROLE_OWNER]:
                req = auth_module.PermissionCheckRequest(
                    resourceId=case_id,
                    action=action,
                    resourceType=auth_module.TYPE_CASE,
                    organizationId=org_id
                )
                allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id_creator, req)
                assert allowed is True, f"Org case creator (owner) should be allowed owner-specific action '{action}', msg: {msg}"

    def test_case_not_found(self, mock_firestore_client, configure_mock_document_data):
        """Test that non-existent cases return appropriate error."""
        user_id = "any_user_case_not_found"
        case_id = "non_existent_case"

        # Configure document data to return None for this case
        configure_mock_document_data({})  # Empty map means get_document_data will return None

        req = auth_module.PermissionCheckRequest(
            resourceId=case_id,
            action="read",
            resourceType=auth_module.TYPE_CASE
        )
        allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert f"Case {case_id} not found" in msg

    def test_case_missing_resourceid_for_read(self, mock_firestore_client):
        """Test that read actions require a resourceId."""
        user_id = "any_user_missing_id"

        req = auth_module.PermissionCheckRequest(
            action="read",
            resourceType=auth_module.TYPE_CASE
        )  # No resourceId
        allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert "resourceId is required" in msg

    def test_cross_org_access_denied_for_org_case(self, mock_firestore_client, configure_mock_document_data, configure_mock_membership_data):
        """Test that users cannot access cases from a different organization."""
        user_id_org_A_member = "user_in_org_A_only"
        org_A_id = "org_A_cases"
        org_B_id = "org_B_cases"
        case_in_org_B_id = "case_belonging_to_org_B"

        # Configure membership data: User is member of Org A but not Org B
        membership_data = {
            (user_id_org_A_member, org_A_id): {"role": auth_module.ROLE_STAFF, "userId": user_id_org_A_member, "organizationId": org_A_id}
            # User is NOT member of Org B (no entry for this combination)
        }
        configure_mock_membership_data(membership_data)

        # Configure document data: Case belongs to Org B
        document_data = {
            ('cases', case_in_org_B_id): {"userId": "creator_in_org_b", "organizationId": org_B_id}
        }
        configure_mock_document_data(document_data)

        # User from Org A attempts to read a case in Org B
        req = auth_module.PermissionCheckRequest(
            resourceId=case_in_org_B_id,
            action="read",
            resourceType=auth_module.TYPE_CASE,
            organizationId=org_B_id  # Context is the case's actual organization
        )

        allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id_org_A_member, req)

        assert allowed is False, f"User from {org_A_id} should not read case from {org_B_id}, msg: {msg}"
        assert f"User {user_id_org_A_member} is not owner or member of org {org_B_id}" in msg

    def test_org_case_creation_attempt_in_unauthorized_org(self, mock_firestore_client, configure_mock_membership_data):
        """Test that users cannot create cases in organizations they don't belong to."""
        user_id = "user_trying_cross_create"
        user_actual_org_id = "user_home_org"
        target_org_id_for_case_creation = "foreign_org"  # User wants to create a case here

        # Configure membership data: User is member of their own org but not the target org
        membership_data = {
            (user_id, user_actual_org_id): {"role": auth_module.ROLE_STAFF, "userId": user_id, "organizationId": user_actual_org_id}
            # User is NOT a member of the target org (no entry for this combination)
        }
        configure_mock_membership_data(membership_data)

        # Attempt to 'create' a case under 'foreign_org'
        req = auth_module.PermissionCheckRequest(
            action="create",
            resourceType=auth_module.TYPE_CASE,
            organizationId=target_org_id_for_case_creation  # Crucial: specifying the org for creation
        )

        allowed, msg = auth_module._check_case_permissions(mock_firestore_client, user_id, req)

        assert allowed is False, f"User {user_id} should not be allowed to create a case in {target_org_id_for_case_creation}, msg: {msg}"
        assert f"User {user_id} is not a member of organization {target_org_id_for_case_creation}" in msg


class TestCheckDocumentPermissions:
    """Tests for the _check_document_permissions function."""

    @patch('functions.src.auth._check_case_permissions')
    def test_doc_permission_granted_via_case_permission(self, mock_check_case_perms, mock_firestore_client):
        """Test that document permissions are granted when parent case permissions are granted."""
        user_id = "user_with_case_perms"
        doc_id = "doc_1"
        case_id = "case_for_doc_1"

        # Mock document data with a caseId
        def side_effect_get_doc_data(db, collection, doc_id_param):
            if collection == "documents" and doc_id_param == doc_id:
                return {"caseId": case_id}
            if collection == "cases" and doc_id_param == case_id:
                return {"organizationId": "some_org_id"}  # Minimal case data
            return None
        auth_module.get_document_data = MagicMock(side_effect=side_effect_get_doc_data)

        # Mock the case document reference and snapshot
        mock_case_doc = MagicMock()
        mock_case_doc.exists = True
        mock_case_doc.to_dict.return_value = {"organizationId": "some_org_id"}

        mock_case_ref = MagicMock()
        mock_case_ref.get.return_value = mock_case_doc

        mock_firestore_client.collection.return_value.document.return_value = mock_case_ref

        # Mock _check_case_permissions to return success
        mock_check_case_perms.return_value = (True, "Permissions granted on parent case")

        # Test document read permission
        req = auth_module.PermissionCheckRequest(
            resourceId=doc_id,
            action="read",
            resourceType=auth_module.TYPE_DOCUMENT
        )
        allowed, msg = auth_module._check_document_permissions(mock_firestore_client, user_id, req)

        assert allowed is True
        assert msg == "Permissions granted on parent case"

        # Verify _check_case_permissions was called with correct parameters
        mock_check_case_perms.assert_called_once()
        call_args = mock_check_case_perms.call_args[0]
        assert call_args[1] == user_id  # user_id
        assert call_args[2].resourceId == case_id  # case_id
        assert call_args[2].action == "read"  # Mapped action
        assert call_args[2].resourceType == auth_module.TYPE_CASE  # resource type

    @patch('functions.src.auth._check_case_permissions')
    def test_doc_permission_denied_via_case_permission(self, mock_check_case_perms, mock_firestore_client):
        """Test that document permissions are denied when parent case permissions are denied."""
        user_id = "user_without_case_perms"
        doc_id = "doc_2"
        case_id = "case_for_doc_2"

        # Mock document data with a caseId
        def side_effect_get_doc_data(db, collection, doc_id_param):
            if collection == "documents" and doc_id_param == doc_id:
                return {"caseId": case_id}
            if collection == "cases" and doc_id_param == case_id:
                return {"organizationId": "some_org_id"}
            return None
        auth_module.get_document_data = MagicMock(side_effect=side_effect_get_doc_data)

        # Mock the case document reference and snapshot
        mock_case_doc = MagicMock()
        mock_case_doc.exists = True
        mock_case_doc.to_dict.return_value = {"organizationId": "some_org_id"}

        mock_case_ref = MagicMock()
        mock_case_ref.get.return_value = mock_case_doc

        mock_firestore_client.collection.return_value.document.return_value = mock_case_ref

        # Mock _check_case_permissions to return failure
        mock_check_case_perms.return_value = (False, "Permissions denied on parent case")

        # Test document delete permission
        req = auth_module.PermissionCheckRequest(
            resourceId=doc_id,
            action="delete",
            resourceType=auth_module.TYPE_DOCUMENT
        )
        allowed, msg = auth_module._check_document_permissions(mock_firestore_client, user_id, req)

        assert allowed is False
        assert msg == "Permissions denied on parent case"

        # Verify _check_case_permissions was called with correct parameters
        mock_check_case_perms.assert_called_once()
        call_args = mock_check_case_perms.call_args[0]
        assert call_args[2].action == "delete"  # Mapped action for document delete

    def test_doc_permission_doc_not_found(self, mock_firestore_client):
        """Test that permissions are denied for non-existent documents."""
        user_id = "any_user_doc_not_found"
        doc_id = "non_existent_doc"

        # Mock get_document_data to return None (document not found)
        auth_module.get_document_data = MagicMock(return_value=None)

        req = auth_module.PermissionCheckRequest(
            resourceId=doc_id,
            action="read",
            resourceType=auth_module.TYPE_DOCUMENT
        )
        allowed, msg = auth_module._check_document_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert f"Document {doc_id} not found" in msg

    def test_doc_permission_doc_no_caseid(self, mock_firestore_client):
        """Test that permissions are denied for documents without a caseId."""
        user_id = "any_user_doc_no_caseid"
        doc_id = "doc_no_case_ref"

        # Mock document data without a caseId
        auth_module.get_document_data = MagicMock(return_value={"some_other_field": "value"})

        req = auth_module.PermissionCheckRequest(
            resourceId=doc_id,
            action="read",
            resourceType=auth_module.TYPE_DOCUMENT
        )
        allowed, msg = auth_module._check_document_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert "Document has no associated case ID" in msg

    @patch('functions.src.auth._check_case_permissions')
    def test_doc_permission_parent_case_not_found(self, mock_check_case_perms, mock_firestore_client):
        """Test that permissions are denied when the parent case doesn't exist."""
        user_id = "any_user_parent_case_not_found"
        doc_id = "doc_3"
        case_id = "non_existent_case_for_doc_3"

        # Mock document data with a caseId
        auth_module.get_document_data = MagicMock(return_value={"caseId": case_id})

        # Mock the case document reference and snapshot to indicate case not found
        mock_case_doc = MagicMock()
        mock_case_doc.exists = False

        mock_case_ref = MagicMock()
        mock_case_ref.get.return_value = mock_case_doc

        mock_firestore_client.collection.return_value.document.return_value = mock_case_ref

        req = auth_module.PermissionCheckRequest(
            resourceId=doc_id,
            action="read",
            resourceType=auth_module.TYPE_DOCUMENT
        )
        allowed, msg = auth_module._check_document_permissions(mock_firestore_client, user_id, req)

        assert allowed is False
        assert f"Parent case {case_id} for document {doc_id} not found" in msg

        # Verify _check_case_permissions was not called
        mock_check_case_perms.assert_not_called()

    def test_doc_permission_invalid_action_mapping(self, mock_firestore_client):
        """Test that permissions are denied for actions not mapped to case actions."""
        user_id = "any_user_invalid_doc_action"
        doc_id = "doc_4"
        case_id = "case_for_doc_4"

        # Mock document data with a caseId
        auth_module.get_document_data = MagicMock(return_value={"caseId": case_id})

        # Use an action that's not mapped in _check_document_permissions
        invalid_action = "publish"
        req = auth_module.PermissionCheckRequest(
            resourceId=doc_id,
            action=invalid_action,
            resourceType=auth_module.TYPE_DOCUMENT
        )
        allowed, msg = auth_module._check_document_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert f"Action '{invalid_action}' on document type is not mapped" in msg

    def test_doc_permission_missing_resourceid(self, mock_firestore_client):
        """Test that permissions are denied when resourceId is missing."""
        user_id = "any_user_doc_missing_id"

        # No resourceId provided
        req = auth_module.PermissionCheckRequest(
            action="read",
            resourceType=auth_module.TYPE_DOCUMENT
        )
        allowed, msg = auth_module._check_document_permissions(mock_firestore_client, user_id, req)
        assert allowed is False
        assert "resourceId is required" in msg


# class TestValidateUserEndpoint:
#     """Tests for the validate_user HTTP endpoint function."""
#
#     @patch('functions.src.auth.get_authenticated_user')
#     @patch('functions.src.auth.datetime')
#     def test_validate_user_new_user_creation(self, mock_datetime, mock_get_auth_user, mock_request_builder, mock_firestore_client):
#         """Test that a new user is created when they don't exist in the database."""
#         # Mock the current time
#         mock_now = datetime.datetime(2024, 1, 1, 12, 0, 0)
#         mock_datetime.datetime.now.return_value = mock_now
#
#         # Mock the authentication result
#         user_id = "new_validate_user"
#         user_email = "new_validate@example.com"
#         mock_auth_context = AuthContext(
#             is_authenticated_call_from_gateway=True,
#             firebase_user_id=user_id,
#             firebase_user_email=user_email,
#             firebase_user_locale="en"
#         )
#         mock_get_auth_user.return_value = (mock_auth_context, 200, None)
#
#         # Mock the Firestore document snapshot to indicate user doesn't exist
#         mock_doc_snapshot = mock_firestore_client.collection.return_value.document.return_value.get.return_value
#         mock_doc_snapshot.exists = False  # Simulate new user
#
#         # Create a mock request
#         request = mock_request_builder(method='POST')
#
#         # Call the function under test
#         response_tuple = auth_module.validate_user(request)
#         response_data = json.loads(response_tuple[0].get_data(as_text=True))
#         status_code = response_tuple[1]
#
#         # Verify the response
#         assert status_code == 200
#         assert response_data['user_id'] == user_id
#         assert response_data['is_authenticated'] is True
#
#         # Verify that a new user document was created in Firestore
#         mock_firestore_client.collection.assert_called_with('users')
#         mock_firestore_client.collection.return_value.document.assert_called_with(user_id)
#         mock_firestore_client.collection.return_value.document.return_value.set.assert_called_once_with({
#             'user_id': user_id,
#             'email': user_email,
#             'created_at': mock_now,
#             'updated_at': mock_now
#         })
#
#     @patch('functions.src.auth.get_authenticated_user')
#     @patch('functions.src.auth.datetime')
#     def test_validate_user_existing_user_update(self, mock_datetime, mock_get_auth_user, mock_request_builder, mock_firestore_client):
#         """Test that an existing user is updated when they already exist in the database."""
#         # Mock the current time
#         mock_now = datetime.datetime(2024, 1, 1, 13, 0, 0)
#         mock_datetime.datetime.now.return_value = mock_now
#
#         # Mock the authentication result
#         user_id = "existing_validate_user"
#         user_email = "existing_validate@example.com"
#         mock_auth_context = AuthContext(
#             is_authenticated_call_from_gateway=True,
#             firebase_user_id=user_id,
#             firebase_user_email=user_email
#         )
#         mock_get_auth_user.return_value = (mock_auth_context, 200, None)
#
#         # Mock the Firestore document snapshot to indicate user exists
#         mock_doc_snapshot = mock_firestore_client.collection.return_value.document.return_value.get.return_value
#         mock_doc_snapshot.exists = True
#         # Mock the existing email to be different from the new one
#         mock_doc_snapshot.get.return_value = "old_email@example.com"
#
#         # Create a mock request
#         request = mock_request_builder(method='POST')
#
#         # Call the function under test
#         response_tuple = auth_module.validate_user(request)
#         response_data = json.loads(response_tuple[0].get_data(as_text=True))
#         status_code = response_tuple[1]
#
#         # Verify the response
#         assert status_code == 200
#         assert response_data['user_id'] == user_id
#         assert response_data['is_authenticated'] is True
#
#         # Verify that the user document was updated in Firestore
#         mock_firestore_client.collection.assert_called_with('users')
#         mock_firestore_client.collection.return_value.document.assert_called_with(user_id)
#         mock_firestore_client.collection.return_value.document.return_value.update.assert_called_once_with({
#             'updated_at': mock_now,
#             'email': user_email  # Email should be updated since it's different
#         })
#
#     @patch('functions.src.auth.get_authenticated_user')
#     def test_validate_user_auth_fails(self, mock_get_auth_user, mock_request_builder):
#         """Test that authentication failures are properly handled."""
#         # Mock authentication failure
#         mock_get_auth_user.return_value = (None, 401, "Auth error message")
#
#         # Create a mock request
#         request = mock_request_builder(method='POST')
#
#         # Call the function under test
#         response_tuple = auth_module.validate_user(request)
#         response_data = json.loads(response_tuple[0].get_data(as_text=True))
#         status_code = response_tuple[1]
#
#         # Verify the response
#         assert status_code == 401
#         assert response_data['error'] == "Unauthorized"
#         assert response_data['message'] == "Auth error message"
#
#     def test_validate_user_options_request(self, mock_request_builder):
#         """Test that OPTIONS requests are handled correctly for CORS."""
#         # Create a mock OPTIONS request
#         request = mock_request_builder(method='OPTIONS')
#
#         # Call the function under test
#         response_body, status_code, headers = auth_module.validate_user(request)
#
#         # Verify the response
#         assert status_code == 204  # Standard for OPTIONS preflight
#         assert response_body == ""
#         # CORS headers are added by add_cors_headers decorator


# class TestAuthGetUserProfileEndpoint:
#     """Tests for the get_user_profile HTTP endpoint function in auth.py."""
#
#     @patch('functions.src.auth.get_authenticated_user')
#     def test_get_user_profile_success(self, mock_get_auth_user, mock_request_builder, mock_firestore_client):
#         """Test successful retrieval of a user profile."""
#         # Mock the authentication result
#         user_id = "auth_profile_user"
#         user_email = "auth_profile@example.com"
#         mock_auth_context = AuthContext(
#             is_authenticated_call_from_gateway=True,
#             firebase_user_id=user_id,
#             firebase_user_email=user_email
#         )
#         mock_get_auth_user.return_value = (mock_auth_context, 200, None)
#
#         # Mock the Firestore document snapshot to return user data
#         user_data_from_db = {"userId": user_id, "email": user_email, "displayName": "Auth Profile User"}
#         mock_doc_snapshot = mock_firestore_client.collection.return_value.document.return_value.get.return_value
#         mock_doc_snapshot.exists = True
#         mock_doc_snapshot.to_dict.return_value = user_data_from_db
#
#         # Create a mock request
#         request = mock_request_builder(method='GET')
#
#         # Call the function under test
#         response_tuple = auth_module.get_user_profile(request)
#         response_data = json.loads(response_tuple[0].get_data(as_text=True))
#         status_code = response_tuple[1]
#
#         # Verify the response
#         assert status_code == 200
#         assert response_data == user_data_from_db
#
#         # Verify Firestore interactions
#         mock_firestore_client.collection.assert_called_with('users')
#         mock_firestore_client.collection.return_value.document.assert_called_with(user_id)
#
#     @patch('functions.src.auth.get_authenticated_user')
#     def test_get_user_profile_not_found(self, mock_get_auth_user, mock_request_builder, mock_firestore_client):
#         """Test handling of a user profile that doesn't exist."""
#         # Mock the authentication result
#         user_id = "auth_profile_notfound"
#         mock_auth_context = AuthContext(
#             is_authenticated_call_from_gateway=True,
#             firebase_user_id=user_id,
#             firebase_user_email="notfound@example.com"
#         )
#         mock_get_auth_user.return_value = (mock_auth_context, 200, None)
#
#         # Mock the Firestore document snapshot to indicate user doesn't exist
#         mock_doc_snapshot = mock_firestore_client.collection.return_value.document.return_value.get.return_value
#         mock_doc_snapshot.exists = False  # User not found in DB
#
#         # Create a mock request
#         request = mock_request_builder(method='GET')
#
#         # Call the function under test
#         response_tuple = auth_module.get_user_profile(request)
#         response_data = json.loads(response_tuple[0].get_data(as_text=True))
#         status_code = response_tuple[1]
#
#         # Verify the response
#         assert status_code == 404
#         assert response_data['error'] == "Not Found"
#         assert response_data['message'] == "User profile not found"
#
#         # Verify Firestore interactions
#         mock_firestore_client.collection.assert_called_with('users')
#         mock_firestore_client.collection.return_value.document.assert_called_with(user_id)
#
#     @patch('functions.src.auth.get_authenticated_user')
#     def test_get_user_profile_auth_fails(self, mock_get_auth_user, mock_request_builder):
#         """Test handling of authentication failures."""
#         # Mock authentication failure
#         mock_get_auth_user.return_value = (None, 403, "Forbidden access")
#
#         # Create a mock request
#         request = mock_request_builder(method='GET')
#
#         # Call the function under test
#         response_tuple = auth_module.get_user_profile(request)
#         response_data = json.loads(response_tuple[0].get_data(as_text=True))
#         status_code = response_tuple[1]
#
#         # Verify the response
#         assert status_code == 403  # Should match the status code from get_authenticated_user
#         assert response_data['error'] == "Unauthorized"  # The endpoint wraps the error
#         assert response_data['message'] == "Forbidden access"
#
#     def test_get_user_profile_options_request(self, mock_request_builder):
#         """Test that OPTIONS requests are handled correctly for CORS."""
#         # Create a mock OPTIONS request
#         request = mock_request_builder(method='OPTIONS')
#
#         # Call the function under test
#         response_body, status_code, headers = auth_module.get_user_profile(request)
#
#         # Verify the response
#         assert status_code == 204
#         assert response_body == ""
#         # CORS headers are added by add_cors_headers decorator


# class TestGetUserRoleLogic:
#     """Tests for the get_user_role logic function."""
#
#     @patch('functions.src.auth.get_authenticated_user')
#     def test_get_user_role_success(self, mock_get_auth_user, mock_request_builder, mock_firestore_client):
#         """Test successful retrieval of a user's role in an organization."""
#         # Mock the authentication result
#         requesting_user_id = "requester_admin"
#         target_user_id = "target_user_for_role"
#         org_id = "org_for_role_check"
#
#         mock_auth_context = AuthContext(
#             is_authenticated_call_from_gateway=True,
#             firebase_user_id=requesting_user_id,
#             firebase_user_email="req@example.com"
#         )
#         mock_get_auth_user.return_value = (mock_auth_context, 200, None)
#
#         # Mock the permission check (implicitly by not patching check_permission)
#         # For this test, we'll assume the requester has permission to view roles
#
#         # Mock the membership data for the target user
#         auth_module.get_membership_data = MagicMock(return_value={"role": "staff", "userId": target_user_id})
#
#         # Create a mock request with JSON data
#         request = mock_request_builder(json_data={"userId": target_user_id, "organizationId": org_id})
#
#         # Call the function under test
#         response_flask, status_code = auth_module.get_user_role(request)
#         response_data = json.loads(response_flask.get_data(as_text=True))
#
#         # Verify the response
#         assert status_code == 200
#         assert response_data['role'] == "staff"
#
#         # Verify that get_membership_data was called with the correct parameters
#         auth_module.get_membership_data.assert_called_once_with(mock_firestore_client, target_user_id, org_id)
#
#     @patch('functions.src.auth.get_authenticated_user')
#     @patch('functions.src.auth.check_permission')  # Mock internal permission check
#     def test_get_user_role_requester_lacks_permission(self, mock_check_perm, mock_get_auth_user, mock_request_builder):
#         """Test handling when the requester lacks permission to view roles."""
#         # Mock the authentication result
#         requesting_user_id = "requester_no_perms"
#         target_user_id = "target_user_other"
#         org_id = "org_for_role_check_no_perms"
#
#         mock_auth_context = AuthContext(
#             is_authenticated_call_from_gateway=True,
#             firebase_user_id=requesting_user_id,
#             firebase_user_email="req_no@example.com"
#         )
#         mock_get_auth_user.return_value = (mock_auth_context, 200, None)
#
#         # Mock the permission check to deny access
#         mock_check_perm.return_value = (False, "Permission denied to view roles")
#
#         # Create a mock request with JSON data
#         request = mock_request_builder(json_data={"userId": target_user_id, "organizationId": org_id})
#
#         # Call the function under test
#         response_flask, status_code = auth_module.get_user_role(request)
#         response_data = json.loads(response_flask.get_data(as_text=True))
#
#         # Verify the response
#         assert status_code == 403
#         assert response_data['error'] == "Forbidden"
#         assert "Permission denied" in response_data['message']
#
#         # Verify that check_permission was called
#         mock_check_perm.assert_called_once()
#         # Verify the permission check was for the correct action
#         call_args = mock_check_perm.call_args[0]
#         assert call_args[0] == requesting_user_id  # user_id
#         assert call_args[1].action == "listMembers"  # action
#         assert call_args[1].resourceType == auth_module.TYPE_ORGANIZATION  # resource type
#
#     @patch('functions.src.auth.get_authenticated_user')
#     def test_get_user_role_self_check_allowed(self, mock_get_auth_user, mock_request_builder, mock_firestore_client):
#         """Test that users can always check their own role without permission checks."""
#         # Mock the authentication result - same user for requester and target
#         user_id = "self_check_user"
#         org_id = "org_for_self_check"
#
#         mock_auth_context = AuthContext(
#             is_authenticated_call_from_gateway=True,
#             firebase_user_id=user_id,
#             firebase_user_email="self@example.com"
#         )
#         mock_get_auth_user.return_value = (mock_auth_context, 200, None)
#
#         # Mock the membership data
#         auth_module.get_membership_data = MagicMock(return_value={"role": "staff", "userId": user_id})
#
#         # Create a mock request with JSON data - same userId as the authenticated user
#         request = mock_request_builder(json_data={"userId": user_id, "organizationId": org_id})
#
#         # Call the function under test
#         response_flask, status_code = auth_module.get_user_role(request)
#         response_data = json.loads(response_flask.get_data(as_text=True))
#
#         # Verify the response
#         assert status_code == 200
#         assert response_data['role'] == "staff"
#
#         # Verify that get_membership_data was called with the correct parameters
#         auth_module.get_membership_data.assert_called_once_with(mock_firestore_client, user_id, org_id)
#
#     def test_get_user_role_missing_params(self, mock_request_builder):
#         """Test handling of missing required parameters."""
#         # Test missing userId
#         request_no_userid = mock_request_builder(json_data={"organizationId": "org1"})
#         response_flask, status_code = auth_module.get_user_role(request_no_userid)
#         response_data = json.loads(response_flask.get_data(as_text=True))
#
#         assert status_code == 400
#         assert response_data['error'] == "Bad Request"
#         assert "userId is required" in response_data['message']
#
#         # Test missing organizationId
#         request_no_orgid = mock_request_builder(json_data={"userId": "user1"})
#         response_flask, status_code = auth_module.get_user_role(request_no_orgid)
#         response_data = json.loads(response_flask.get_data(as_text=True))
#
#         assert status_code == 400
#         assert response_data['error'] == "Bad Request"
#         assert "organizationId is required" in response_data['message']
#
#     @patch('functions.src.auth.get_authenticated_user')
#     def test_get_user_role_auth_fails(self, mock_get_auth_user, mock_request_builder):
#         """Test handling of authentication failures."""
#         # Mock authentication failure
#         mock_get_auth_user.return_value = (None, 401, "Authentication failed")
#
#         # Create a mock request with valid JSON data
#         request = mock_request_builder(json_data={"userId": "user1", "organizationId": "org1"})
#
#         # Call the function under test
#         response_flask, status_code = auth_module.get_user_role(request)
#         response_data = json.loads(response_flask.get_data(as_text=True))
#
#         # Verify the response
#         assert status_code == 401
#         assert response_data['error'] == "Unauthorized"
#         assert response_data['message'] == "Authentication failed"
#
#     @patch('functions.src.auth.get_authenticated_user')
#     def test_get_user_role_user_not_member(self, mock_get_auth_user, mock_request_builder, mock_firestore_client):
#         """Test handling when the target user is not a member of the organization."""
#         # Mock the authentication result
#         requesting_user_id = "requester_admin_for_nonmember"
#         target_user_id = "target_nonmember"
#         org_id = "org_for_nonmember_check"
#
#         mock_auth_context = AuthContext(
#             is_authenticated_call_from_gateway=True,
#             firebase_user_id=requesting_user_id,
#             firebase_user_email="admin@example.com"
#         )
#         mock_get_auth_user.return_value = (mock_auth_context, 200, None)
#
#         # Mock get_membership_data to return None (user is not a member)
#         auth_module.get_membership_data = MagicMock(return_value=None)
#
#         # Create a mock request with JSON data
#         request = mock_request_builder(json_data={"userId": target_user_id, "organizationId": org_id})
#
#         # Call the function under test
#         response_flask, status_code = auth_module.get_user_role(request)
#         response_data = json.loads(response_flask.get_data(as_text=True))
#
#         # Verify the response
#         assert status_code == 200
#         assert response_data['role'] is None  # Role should be None for non-members


class TestCheckPermissionDispatcher:
    """Tests for the check_permission dispatcher function."""

    @patch('functions.src.auth._check_case_permissions')
    def test_check_permission_dispatches_to_case(self, mock_case_checker, mock_firestore_client):
        """Test that check_permission correctly dispatches to the case checker function."""
        user_id = "test_user_dispatch_case"
        req_data = auth_module.PermissionCheckRequest(
            resourceId="case1",
            action="read",
            resourceType=auth_module.TYPE_CASE,
            organizationId="org1"
        )

        # Mock the case checker to return success
        mock_case_checker.return_value = (True, "Case allowed")

        # Call the function under test
        allowed, msg = auth_module.check_permission(user_id, req_data)

        # Verify the result
        assert allowed is True
        assert msg == "Case allowed"

        # Verify that the case checker was called with the correct parameters
        mock_case_checker.assert_called_once_with(db=mock_firestore_client, user_id=user_id, req=req_data)

    @patch('functions.src.auth._check_organization_permissions')
    def test_check_permission_dispatches_to_org(self, mock_org_checker, mock_firestore_client):
        """Test that check_permission correctly dispatches to the organization checker function."""
        user_id = "test_user_dispatch_org"
        req_data = auth_module.PermissionCheckRequest(
            resourceId="org1",
            action="update",
            resourceType=auth_module.TYPE_ORGANIZATION,
            organizationId="org1"
        )

        # Mock the organization checker to return failure
        mock_org_checker.return_value = (False, "Org denied")

        # Call the function under test
        allowed, msg = auth_module.check_permission(user_id, req_data)

        # Verify the result
        assert allowed is False
        assert msg == "Org denied"

        # Verify that the organization checker was called with the correct parameters
        mock_org_checker.assert_called_once_with(db=mock_firestore_client, user_id=user_id, req=req_data)

    @patch('functions.src.auth._check_party_permissions')
    def test_check_permission_dispatches_to_party(self, mock_party_checker, mock_firestore_client):
        """Test that check_permission correctly dispatches to the party checker function."""
        user_id = "test_user_dispatch_party"
        req_data = auth_module.PermissionCheckRequest(
            resourceId="party1",
            action="read",
            resourceType=auth_module.TYPE_PARTY
        )

        # Mock the party checker to return success
        mock_party_checker.return_value = (True, "Party allowed")

        # Call the function under test
        allowed, msg = auth_module.check_permission(user_id, req_data)

        # Verify the result
        assert allowed is True
        assert msg == "Party allowed"

        # Verify that the party checker was called with the correct parameters
        mock_party_checker.assert_called_once_with(db=mock_firestore_client, user_id=user_id, req=req_data)

    @patch('functions.src.auth._check_document_permissions')
    def test_check_permission_dispatches_to_document(self, mock_doc_checker, mock_firestore_client):
        """Test that check_permission correctly dispatches to the document checker function."""
        user_id = "test_user_dispatch_doc"
        req_data = auth_module.PermissionCheckRequest(
            resourceId="doc1",
            action="read",
            resourceType=auth_module.TYPE_DOCUMENT
        )

        # Mock the document checker to return success
        mock_doc_checker.return_value = (True, "Document allowed")

        # Call the function under test
        allowed, msg = auth_module.check_permission(user_id, req_data)

        # Verify the result
        assert allowed is True
        assert msg == "Document allowed"

        # Verify that the document checker was called with the correct parameters
        mock_doc_checker.assert_called_once_with(db=mock_firestore_client, user_id=user_id, req=req_data)

    def test_check_permission_invalid_resource_type(self, mock_firestore_client):
        """Test handling of an invalid resource type."""
        user_id = "test_user_invalid_type"

        # Create a request with an invalid resource type
        # Note: We can't use PermissionCheckRequest constructor directly with an invalid type
        # because the validator would catch it, so we mock a request object
        req_data = MagicMock()
        req_data.resourceType = "unknown_type"  # Invalid resource type
        req_data.action = "read"
        req_data.resourceId = "id1"

        # Call the function under test
        allowed, msg = auth_module.check_permission(user_id, req_data)

        # Verify the result
        assert allowed is False
        assert "No permission checker configured for resource type" in msg

    @patch('functions.src.auth._check_case_permissions')
    def test_check_permission_general_exception(self, mock_case_checker, mock_firestore_client):
        """Test handling of a general exception during permission checking."""
        user_id = "test_user_exception"
        req_data = auth_module.PermissionCheckRequest(
            resourceId="case1",
            action="read",
            resourceType=auth_module.TYPE_CASE
        )

        # Mock the case checker to raise an exception
        mock_case_checker.side_effect = Exception("Firestore unavailable")

        # Call the function under test
        allowed, msg = auth_module.check_permission(user_id, req_data)

        # Verify the result
        assert allowed is False
        assert "An internal error occurred during permission check" in msg


def test_add_cors_headers_decorator():
    """Test that the add_cors_headers decorator correctly adds CORS headers to a response tuple."""
    # 1. Define a mock Flask view function that returns a simple response
    mock_view_function_data = {"message": "test"}
    mock_view_function_status = 200

    def mock_view():
        # Simulate a Flask view returning (data, status_code)
        return jsonify(mock_view_function_data), mock_view_function_status

    # 2. Apply the decorator to the mock view function
    decorated_view = auth_module.add_cors_headers(mock_view)

    # 3. Create a Flask app for the test context
    from flask import Flask
    app = Flask(__name__)

    # 4. Call the decorated function within app context
    with app.app_context():
        response_data_flask, status_code, headers = decorated_view()

    # 5. Assertions
    assert status_code == mock_view_function_status
    # response_data_flask is a Flask Response object due to jsonify
    assert json.loads(response_data_flask.get_data(as_text=True)) == mock_view_function_data

    expected_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
    for key, value in expected_headers.items():
        assert key in headers
        assert headers[key] == value


def test_add_cors_headers_decorator_with_options_request():
    """Test that the add_cors_headers decorator handles OPTIONS requests correctly."""
    # 1. Define a mock Flask view function that handles OPTIONS requests
    def mock_view_with_options():
        # Simulate a Flask view that handles OPTIONS requests
        return "", 204

    # 2. Apply the decorator to the mock view function
    decorated_view = auth_module.add_cors_headers(mock_view_with_options)

    # 3. Create a Flask app for the test context
    from flask import Flask
    app = Flask(__name__)

    # 4. Call the decorated function within app context
    with app.app_context():
        response_data, status_code, headers = decorated_view()

    # 5. Assertions
    assert status_code == 204
    assert response_data == ""

    expected_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
    for key, value in expected_headers.items():
        assert key in headers
        assert headers[key] == value


def test_add_cors_headers_decorator_with_non_tuple_response():
    """Test that the add_cors_headers decorator handles non-tuple responses correctly."""
    # 1. Define a mock Flask view function that returns a non-tuple response
    mock_data = {"message": "data only"}

    def mock_data_only_view():
        # Return a Flask Response object directly (not a tuple)
        return jsonify(mock_data)

    # 2. Apply the decorator to the mock view function
    decorated_view = auth_module.add_cors_headers(mock_data_only_view)

    # 3. Create a Flask app for the test context
    from flask import Flask
    app = Flask(__name__)

    # 4. Call the decorated function within app context
    with app.app_context():
        response = decorated_view()

    # 5. Assertions
    # The decorator should return the original response unchanged if it's not a tuple
    assert json.loads(response.get_data(as_text=True)) == mock_data

    # Check that CORS headers were NOT added because the return type wasn't (data, status_code)
    # This is the current behavior of the add_cors_headers decorator
    assert 'Access-Control-Allow-Origin' not in response.headers
