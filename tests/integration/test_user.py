"""Test setup file that modifies Python path and imports for testing."""
import sys
import os
from unittest.mock import MagicMock, patch

# Add the mock_setup directory to sys.path before any other imports
mock_setup_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'functions', 'src', 'mock_setup'))
sys.path.insert(0, mock_setup_path)

# Mock essential modules
sys.modules['auth'] = __import__('auth')

import pytest
import json
import requests
import firebase_admin
from firebase_admin import firestore
import auth  # Import the mock auth module
from functions.src import user

@pytest.fixture(autouse=True)
def patch_user_auth(monkeypatch):
    """Patch the user module to use our mocked auth functions and add user_id to requests."""

    # Save the original function
    original_get_user_profile = user.get_user_profile
    original_update_user_profile = user.update_user_profile

    # Define wrapper functions that add user_id to the request
    def get_user_profile_wrapper(request):
        # Add user_id to request based on auth.configure_mock settings
        request.user_id = auth._mock_user_id
        return original_get_user_profile(request)

    def update_user_profile_wrapper(request):
        # Add user_id to request based on auth.configure_mock settings
        request.user_id = auth._mock_user_id
        return original_update_user_profile(request)

    # Apply the patches
    monkeypatch.setattr(user, 'get_user_profile', get_user_profile_wrapper)
    monkeypatch.setattr(user, 'update_user_profile', update_user_profile_wrapper)

@pytest.fixture(autouse=True)
def setup_auth_mock():
    """Configure the mock auth module with default values before each test."""
    auth.configure_mock(
        user_id="test_user_id",
        auth_status=200,
        auth_message=None,
        permissions_allowed=True,
        permissions_status=200
    )
    yield

class TestUserProfile:
    """Test suite for user profile functions."""

    def test_create_user_profile(self, firestore_emulator_client):
        """Test create_user_profile creates a user document in Firestore."""
        # Create a mock user record
        class MockUserRecord:
            uid = "test_user_123"
            email = "test@example.com"
            display_name = "Test User"
            photo_url = "https://example.com/photo.jpg"

        # Call the function
        user.create_user_profile(MockUserRecord())

        # Verify a document was created in Firestore
        user_doc = firestore_emulator_client.collection("users").document("test_user_123").get()
        assert user_doc.exists

        # Verify the document data
        user_data = user_doc.to_dict()
        assert user_data["userId"] == "test_user_123"
        assert user_data["email"] == "test@example.com"
        assert user_data["displayName"] == "Test User"
        assert user_data["photoURL"] == "https://example.com/photo.jpg"
        assert user_data["role"] == "user"
        assert user_data["languagePreference"] == "en"
        assert user_data["subscriptionStatus"] is None
        assert "createdAt" in user_data

    def test_get_user_profile_success(self, mocker, firestore_emulator_client, mock_request):
        """Test get_user_profile successfully retrieves user profile."""
        # Setup test data
        test_uid = "test_user_456"
        test_email = "test2@example.com"

        # Configure mock auth module to return our test user
        auth.configure_mock(user_id=test_uid)

        # Create a user document in Firestore
        user_ref = firestore_emulator_client.collection("users").document(test_uid)
        user_ref.set({
            "userId": test_uid,
            "email": test_email,
            "displayName": "Test User 2",
            "photoURL": "https://example.com/photo2.jpg",
            "role": "user",
            "languagePreference": "en",
            "subscriptionStatus": None,
            "createdAt": firestore.SERVER_TIMESTAMP
        })

        # Create a mock request
        request = mock_request(headers={"Authorization": "Bearer fake_token"})

        # Call the function
        response, status_code = user.get_user_profile(request)

        # Verify the response
        assert status_code == 200
        assert response["userId"] == test_uid
        assert response["email"] == test_email
        assert response["displayName"] == "Test User 2"

    def test_get_user_profile_not_found(self, mocker, firestore_emulator_client, mock_request):
        """Test get_user_profile when user document doesn't exist."""
        # Configure mock auth to return a user that doesn't exist in Firestore
        test_uid = "nonexistent_user"
        auth.configure_mock(user_id=test_uid)

        # Create a mock request
        request = mock_request(headers={"Authorization": "Bearer fake_token"})

        # Call the function
        response, status_code = user.get_user_profile(request)

        # Verify the response
        assert status_code == 404
        assert "error" in response
        assert response["error"] == "Not Found"

    def test_get_user_profile_unauthorized(self, mock_request):
        """Test get_user_profile with an unauthorized request."""
        # Configure mock auth to return unauthorized
        auth.configure_mock(auth_status=401, auth_message="Invalid token")

        # Create a mock request
        request = mock_request(headers={"Authorization": "Bearer invalid_token"})

        # Call the function
        response, status_code = user.get_user_profile(request)

        # Verify the response
        assert status_code == 401
        assert "error" in response
        assert response["error"] == "Unauthorized"

    def test_update_user_profile_success(self, firestore_emulator_client, mock_request):
        """Test update_user_profile successfully updates user profile."""
        # Setup test data
        test_uid = "test_user_789"
        test_email = "test3@example.com"

        # Configure mock auth to return our test user
        auth.configure_mock(user_id=test_uid)

        # Create a user document in Firestore
        user_ref = firestore_emulator_client.collection("users").document(test_uid)
        user_ref.set({
            "userId": test_uid,
            "email": test_email,
            "displayName": "Original Name",
            "photoURL": "https://example.com/original.jpg",
            "role": "user",
            "languagePreference": "en",
            "subscriptionStatus": None,
            "createdAt": firestore.SERVER_TIMESTAMP
        })

        # Create a mock request with update data
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "displayName": "Updated Name",
                "languagePreference": "ro"
            }
        )

        # Call the function
        response, status_code = user.update_user_profile(request)

        # Verify the response
        assert status_code == 200
        assert response["displayName"] == "Updated Name"
        assert response["languagePreference"] == "ro"

        # Verify the document was updated in Firestore
        updated_doc = firestore_emulator_client.collection("users").document(test_uid).get()
        updated_data = updated_doc.to_dict()
        assert updated_data["displayName"] == "Updated Name"
        assert updated_data["languagePreference"] == "ro"
        assert "updatedAt" in updated_data

    def test_update_user_profile_invalid_input(self, firestore_emulator_client, mock_request):
        """Test update_user_profile with invalid input."""
        # Setup test data
        test_uid = "test_user_101"
        test_email = "test4@example.com"

        # Configure mock auth to return our test user
        auth.configure_mock(user_id=test_uid)

        # Create a user document in Firestore
        user_ref = firestore_emulator_client.collection("users").document(test_uid)
        user_ref.set({
            "userId": test_uid,
            "email": test_email,
            "displayName": "Original Name",
            "photoURL": "https://example.com/original.jpg",
            "role": "user",
            "languagePreference": "en",
            "subscriptionStatus": None,
            "createdAt": firestore.SERVER_TIMESTAMP
        })

        # Test with invalid language preference
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"languagePreference": "invalid_language"}
        )

        response, status_code = user.update_user_profile(request)
        assert status_code == 400
        assert "error" in response
        assert "Language preference" in response["message"]

        # Verify the document was not updated in Firestore
        doc = firestore_emulator_client.collection("users").document(test_uid).get()
        data = doc.to_dict()
        assert data["languagePreference"] == "en"  # Still the original value

    def test_update_user_profile_restricted_fields(self, firestore_emulator_client, mock_request):
        """Test update_user_profile ignores attempts to update restricted fields."""
        # Setup test data
        test_uid = "test_user_102"
        test_email = "test5@example.com"

        # Configure mock auth to return our test user
        auth.configure_mock(user_id=test_uid)

        # Create a user document in Firestore
        user_ref = firestore_emulator_client.collection("users").document(test_uid)
        user_ref.set({
            "userId": test_uid,
            "email": test_email,
            "displayName": "Original Name",
            "photoURL": "https://example.com/original.jpg",
            "role": "user",
            "languagePreference": "en",
            "subscriptionStatus": None,
            "createdAt": firestore.SERVER_TIMESTAMP
        })

        # Try to update restricted fields
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "displayName": "Valid Update",
                "role": "admin",  # Restricted field
                "email": "hacked@example.com",  # Not in updatable fields
                "subscriptionStatus": "premium"  # Not in updatable fields
            }
        )

        response, status_code = user.update_user_profile(request)

        # Verify the response
        assert status_code == 200
        assert response["displayName"] == "Valid Update"  # This field should be updated

        # Verify the document was updated, but restricted fields were not changed
        updated_doc = firestore_emulator_client.collection("users").document(test_uid).get()
        updated_data = updated_doc.to_dict()
        assert updated_data["displayName"] == "Valid Update"  # This should be updated
        assert updated_data["role"] == "user"  # This should still be the original value
        assert updated_data["email"] == test_email  # This should still be the original value
        assert updated_data["subscriptionStatus"] is None  # This should still be the original value