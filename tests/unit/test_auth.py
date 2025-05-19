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
