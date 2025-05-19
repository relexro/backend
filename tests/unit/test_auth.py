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
    return mock_db

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
