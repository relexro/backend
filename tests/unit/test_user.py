import pytest
from unittest.mock import MagicMock, patch
import functions_framework  # Required for Request type hint if used in mocks
from flask import Request
import datetime
from datetime import timezone
import json
import sys

# Import the functions to be tested from user.py
# Assuming user.py is in functions/src and tests are run from project root,
# or PYTHONPATH is set up correctly.
# Adjust the import path if necessary based on the testing environment structure.
from functions.src import user as user_module

# Global mock for Firestore client
@pytest.fixture(autouse=True)
def mock_firestore_client(monkeypatch):
    mock_db_client = MagicMock(spec=user_module.firestore.Client)

    # Generic mock for document interaction
    mock_doc_ref = MagicMock()
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = False  # Default to not existing
    mock_doc_snapshot.to_dict.return_value = {}

    mock_doc_ref.get.return_value = mock_doc_snapshot
    mock_doc_ref.set.return_value = None
    mock_doc_ref.update.return_value = None

    mock_collection_ref = MagicMock()
    mock_collection_ref.document.return_value = mock_doc_ref

    mock_db_client.collection.return_value = mock_collection_ref

    monkeypatch.setattr('functions.src.user.db', mock_db_client)  # Patch user_module.db
    monkeypatch.setattr('functions.src.user.firestore.Client', lambda: mock_db_client)  # If Client is called inside functions
    monkeypatch.setattr('functions.src.user.firestore.SERVER_TIMESTAMP', 'SERVER_TIMESTAMP_MOCK')

    return mock_db_client

@pytest.fixture
def mock_request():
    mock_req = MagicMock(spec=Request)
    mock_req.get_json.return_value = {}
    # Allow attributes to be set directly for end_user_ values
    mock_req.end_user_email = None
    mock_req.end_user_display_name = None
    mock_req.end_user_locale = None
    return mock_req

# Mock flask.jsonify to return a dict-like object with a json property
@pytest.fixture(autouse=True)
def mock_flask_jsonify(monkeypatch):
    def mock_jsonify(data):
        mock_response = MagicMock()
        mock_response.json = data
        return mock_response
    monkeypatch.setattr('functions.src.user.flask.jsonify', mock_jsonify)
    return mock_jsonify

class TestGetUserProfile:
    def test_get_user_profile_new_user_no_locale(self, mock_firestore_client, mock_request):
        mock_doc_snapshot = mock_firestore_client.collection('users').document().get()
        mock_doc_snapshot.exists = False  # Simulate user not existing

        mock_request.end_user_email = "test@example.com"
        mock_request.end_user_display_name = "Test User"
        mock_request.end_user_locale = None

        response, status_code = user_module.get_user_profile(mock_request, "new_user_id_1")

        assert status_code == 200
        assert response.json['userId'] == "new_user_id_1"
        assert response.json['languagePreference'] == "en"
        mock_firestore_client.collection('users').document("new_user_id_1").set.assert_called_once()
        called_data = mock_firestore_client.collection('users').document("new_user_id_1").set.call_args[0][0]
        assert called_data['languagePreference'] == "en"

    def test_get_user_profile_new_user_locale_ro(self, mock_firestore_client, mock_request):
        mock_doc_snapshot = mock_firestore_client.collection('users').document().get()
        mock_doc_snapshot.exists = False
        mock_request.end_user_locale = "ro-RO"

        response, status_code = user_module.get_user_profile(mock_request, "new_user_id_2")

        assert status_code == 200
        assert response.json['languagePreference'] == "ro"
        mock_firestore_client.collection('users').document("new_user_id_2").set.assert_called_once()
        called_data = mock_firestore_client.collection('users').document("new_user_id_2").set.call_args[0][0]
        assert called_data['languagePreference'] == "ro"

    def test_get_user_profile_new_user_locale_other(self, mock_firestore_client, mock_request):
        mock_doc_snapshot = mock_firestore_client.collection('users').document().get()
        mock_doc_snapshot.exists = False
        mock_request.end_user_locale = "fr-FR"

        response, status_code = user_module.get_user_profile(mock_request, "new_user_id_3")

        assert status_code == 200
        assert response.json['languagePreference'] == "en"
        mock_firestore_client.collection('users').document("new_user_id_3").set.assert_called_once()
        called_data = mock_firestore_client.collection('users').document("new_user_id_3").set.call_args[0][0]
        assert called_data['languagePreference'] == "en"

    def test_get_user_profile_existing_user(self, mock_firestore_client, mock_request):
        existing_user_id = "existing_user_1"
        # Use timezone-aware datetime objects
        now = datetime.datetime.now(timezone.utc)
        existing_data = {
            "userId": existing_user_id,
            "email": "exist@example.com",
            "displayName": "Existing User",
            "languagePreference": "ro",
            "role": "user",
            "subscriptionStatus": None,
            "createdAt": now,
            "updatedAt": now
        }
        mock_doc_snapshot = mock_firestore_client.collection('users').document(existing_user_id).get()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = existing_data

        response, status_code = user_module.get_user_profile(mock_request, existing_user_id)

        assert status_code == 200
        assert response.json['userId'] == existing_user_id
        assert response.json['languagePreference'] == "ro"
        mock_firestore_client.collection('users').document(existing_user_id).set.assert_not_called()

    def test_get_user_profile_auth_missing(self, mock_request):
        # Simulate get_authenticated_user returning an error or no user_id_for_profile passed
        response, status_code = user_module.get_user_profile(mock_request, None)  # Pass None for user_id_for_profile
        assert status_code == 401
        assert response.json['error'] == "Unauthorized"


class TestUpdateUserProfile:
    def test_update_user_profile_language_preference_en(self, mock_firestore_client, mock_request):
        user_id = "user_to_update_1"
        mock_request.get_json.return_value = {"languagePreference": "en"}

        # Simulate user existing
        mock_doc_snapshot = mock_firestore_client.collection('users').document(user_id).get()
        mock_doc_snapshot.exists = True
        # Simulate return after update
        updated_data_mock = {"userId": user_id, "languagePreference": "en", "updatedAt": "SERVER_TIMESTAMP_MOCK"}
        mock_doc_snapshot.to_dict.return_value = updated_data_mock


        response, status_code = user_module.update_user_profile(mock_request, user_id)

        assert status_code == 200
        assert response['languagePreference'] == "en"
        mock_firestore_client.collection('users').document(user_id).update.assert_called_once_with(
            {"languagePreference": "en", "updatedAt": "SERVER_TIMESTAMP_MOCK"}
        )

    def test_update_user_profile_language_preference_ro(self, mock_firestore_client, mock_request):
        user_id = "user_to_update_2"
        mock_request.get_json.return_value = {"languagePreference": "ro"}
        mock_doc_snapshot = mock_firestore_client.collection('users').document(user_id).get()
        mock_doc_snapshot.exists = True
        updated_data_mock = {"userId": user_id, "languagePreference": "ro", "updatedAt": "SERVER_TIMESTAMP_MOCK"}
        mock_doc_snapshot.to_dict.return_value = updated_data_mock

        response, status_code = user_module.update_user_profile(mock_request, user_id)

        assert status_code == 200
        assert response['languagePreference'] == "ro"
        mock_firestore_client.collection('users').document(user_id).update.assert_called_once_with(
            {"languagePreference": "ro", "updatedAt": "SERVER_TIMESTAMP_MOCK"}
        )

    def test_update_user_profile_language_preference_invalid(self, mock_firestore_client, mock_request):
        user_id = "user_to_update_3"
        mock_request.get_json.return_value = {"languagePreference": "de"}  # Invalid language
        mock_doc_snapshot = mock_firestore_client.collection('users').document(user_id).get()  # Not strictly necessary for this path, but good practice
        mock_doc_snapshot.exists = True


        response, status_code = user_module.update_user_profile(mock_request, user_id)

        assert status_code == 400
        assert "Language preference must be one of: en, ro" in response['message']
        mock_firestore_client.collection('users').document(user_id).update.assert_not_called()

    def test_update_user_profile_no_valid_fields(self, mock_firestore_client, mock_request):
        user_id = "user_to_update_4"
        mock_request.get_json.return_value = {"unknownField": "someValue"}
        mock_doc_snapshot = mock_firestore_client.collection('users').document(user_id).get()
        mock_doc_snapshot.exists = True


        response, status_code = user_module.update_user_profile(mock_request, user_id)

        assert status_code == 400
        assert response['message'] == "No valid fields provided for update"
        mock_firestore_client.collection('users').document(user_id).update.assert_not_called()

    def test_update_user_profile_user_not_found(self, mock_firestore_client, mock_request):
        user_id = "user_not_found_1"
        mock_request.get_json.return_value = {"languagePreference": "en"}
        mock_doc_snapshot = mock_firestore_client.collection('users').document(user_id).get()
        mock_doc_snapshot.exists = False  # Simulate user not found

        response, status_code = user_module.update_user_profile(mock_request, user_id)

        assert status_code == 404
        assert response['message'] == "User profile not found"
        mock_firestore_client.collection('users').document(user_id).update.assert_not_called()

    def test_update_user_profile_no_userid_provided(self, mock_request):
        # Test the check for user_id_for_profile at the beginning of update_user_profile
        mock_request.get_json.return_value = {"languagePreference": "en"}
        response, status_code = user_module.update_user_profile(mock_request, None)  # Pass None for user_id_for_profile

        assert status_code == 400
        assert response['message'] == "User ID for profile update is missing"

    def test_update_user_profile_no_json_data(self, mock_request):
        user_id = "user_to_update_5"
        mock_request.get_json.return_value = None  # Simulate no JSON data

        response, status_code = user_module.update_user_profile(mock_request, user_id)
        assert status_code == 400
        assert response['message'] == "No JSON data provided"
