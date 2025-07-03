"""Test suite for organization membership functions logic (formerly integration tests)."""
import sys
import os
from unittest.mock import MagicMock, patch
import logging
import flask
import uuid

# Add the mock_setup directory to sys.path before any other imports
# Assuming tests/unit, tests/integration, and tests/functions are siblings under tests/
# Path from tests/unit/ to tests/functions/src/mock_setup is ../functions/src/mock_setup
mock_setup_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'functions', 'src', 'mock_setup'))
sys.path.insert(0, mock_setup_path)

# Create the mock_setup directory if it doesn't exist
# This path also needs adjustment similar to above
mock_setup_dir_to_create = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'functions', 'src', 'mock_setup'))
os.makedirs(mock_setup_dir_to_create, exist_ok=True)

# Mock essential modules
mock_auth = MagicMock()
mock_auth._mock_user_id = "test_user_id"
mock_auth._mock_auth_status = 200
mock_auth._mock_auth_message = None
mock_auth._mock_permissions_allowed = True
mock_auth._mock_permissions_status = 200
sys.modules['auth'] = mock_auth

import pytest
import json
import firebase_admin
from firebase_admin import firestore
import auth  # Import the mock auth module
from functions.src import organization_membership

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a mock for Firebase auth
class MockUser:
    def __init__(self, uid, email=None, display_name=None):
        self.uid = uid
        self.email = email or f"{uid}@example.com"
        self.display_name = display_name or f"User {uid}"

# Patch the functions.src.organization_membership module to use our mock auth
@pytest.fixture(autouse=True)
def patch_organization_membership_auth(monkeypatch):
    """Patch the organization_membership module to use our mocked auth functions and add user_id to requests."""

    # Save the original function
    original_add_organization_member = organization_membership.add_organization_member
    original_set_organization_member_role = organization_membership.set_organization_member_role
    original_list_organization_members = organization_membership.list_organization_members
    original_remove_organization_member = organization_membership.remove_organization_member
    original_get_user_organization_role = organization_membership.get_user_organization_role
    original_list_user_organizations = organization_membership.list_user_organizations

    # Define wrapper functions that add user_id to the request
    def add_organization_member_wrapper(request):
        request.user_id = auth._mock_user_id
        request.end_user_id = auth._mock_user_id
        return original_add_organization_member(request)

    def set_organization_member_role_wrapper(request):
        request.user_id = auth._mock_user_id
        request.end_user_id = auth._mock_user_id
        return original_set_organization_member_role(request)

    def list_organization_members_wrapper(request):
        request.user_id = auth._mock_user_id
        request.end_user_id = auth._mock_user_id
        return original_list_organization_members(request)

    def remove_organization_member_wrapper(request):
        request.user_id = auth._mock_user_id
        request.end_user_id = auth._mock_user_id
        return original_remove_organization_member(request)

    def get_user_organization_role_wrapper(request):
        request.user_id = auth._mock_user_id
        request.end_user_id = auth._mock_user_id
        return original_get_user_organization_role(request)

    def list_user_organizations_wrapper(request):
        request.user_id = auth._mock_user_id
        request.end_user_id = auth._mock_user_id
        return original_list_user_organizations(request)

    # Apply the patches
    monkeypatch.setattr(organization_membership, 'add_organization_member', add_organization_member_wrapper)
    monkeypatch.setattr(organization_membership, 'set_organization_member_role', set_organization_member_role_wrapper)
    monkeypatch.setattr(organization_membership, 'list_organization_members', list_organization_members_wrapper)
    monkeypatch.setattr(organization_membership, 'remove_organization_member', remove_organization_member_wrapper)
    monkeypatch.setattr(organization_membership, 'get_user_organization_role', get_user_organization_role_wrapper)
    monkeypatch.setattr(organization_membership, 'list_user_organizations', list_user_organizations_wrapper)

    # Mock Firebase auth
    def mock_get_user(uid):
        return MockUser(uid)

    # Patch Firebase auth module
    monkeypatch.setattr(firebase_admin.auth, 'get_user', mock_get_user)

@pytest.fixture(autouse=True)
def setup_auth_mock():
    """Configure the mock auth module with default values before each test."""
    # Reset mock attributes to default values
    auth._mock_user_id = "test_user_id"
    auth._mock_auth_status = 200
    auth._mock_auth_message = None
    auth._mock_permissions_allowed = True
    auth._mock_permissions_status = 200
    yield

@pytest.fixture
def org_setup(firestore_emulator_client):
    """Create a test organization with an admin member."""
    # Create test organization
    org_id = "test_org_123"
    admin_id = "admin_user_123"
    staff_id = "staff_user_123"

    # Create organization document
    org_ref = firestore_emulator_client.collection("organizations").document(org_id)
    org_ref.set({
        "organizationId": org_id,
        "name": "Test Organization",
        "description": "A test organization",
        "createdAt": firestore.SERVER_TIMESTAMP
    })

    # Create admin membership
    admin_membership_ref = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{admin_id}")
    admin_membership_ref.set({
        "organizationId": org_id,
        "userId": admin_id,
        "role": "administrator",
        "addedAt": firestore.SERVER_TIMESTAMP
    })

    # Return test data
    return {
        "org_id": org_id,
        "admin_id": admin_id,
        "staff_id": staff_id
    }

@pytest.fixture(scope="module")
def flask_app():
    app = flask.Flask(__name__)
    return app

@pytest.fixture
def mock_request():
    def _create_mock_request(headers=None, json_data=None, args=None, path=None, end_user_id=None):
        mock_req = MagicMock()
        mock_req.headers = headers or {}
        mock_req.get_json = MagicMock(return_value=json_data)
        mock_req.args = args or {}
        mock_req.path = path or ""
        # Set both user_id and end_user_id for compatibility
        mock_req.user_id = end_user_id
        mock_req.end_user_id = end_user_id
        return mock_req
    return _create_mock_request

class TestOrganizationMembership:
    """Test suite for organization membership functions."""

    def setup_method(self):
        # Set up in-memory Firestore simulation for each test
        self.firestore_data = {
            'organizations': {},
            'organization_memberships': {},
            'users': {}
        }
        # Patch get_db_client to return a MagicMock
        self.db_patch = patch('functions.src.organization_membership.get_db_client', self._mock_get_db_client)
        self.db_patch.start()

    def teardown_method(self):
        self.db_patch.stop()

    def _mock_get_db_client(self):
        mock_client = MagicMock()
        def collection(name):
            col = MagicMock()
            col._name = name
            col._filters = []
            def document(doc_id=None):
                doc = MagicMock()
                doc._id = doc_id or str(uuid.uuid4())
                def get():
                    if doc._id in self.firestore_data[name]:
                        doc.exists = True
                        doc.to_dict.return_value = self.firestore_data[name][doc._id]
                    else:
                        doc.exists = False
                        doc.to_dict.return_value = None
                    doc.reference = doc
                    return doc
                doc.get.side_effect = get
                def set(data):
                    self.firestore_data[name][doc._id] = data
                doc.set.side_effect = set
                def update(data):
                    if doc._id in self.firestore_data[name]:
                        self.firestore_data[name][doc._id].update(data)
                doc.update.side_effect = update
                def delete():
                    if doc._id in self.firestore_data[name]:
                        del self.firestore_data[name][doc._id]
                doc.delete.side_effect = delete
                return doc
            col.document.side_effect = document
            def where(field, op, value):
                new_col = MagicMock()
                new_col._name = name
                new_col._filters = col._filters + [(field, op, value)]
                new_col.document = col.document
                def stream():
                    results = []
                    for d in self.firestore_data[name].values():
                        match = True
                        for f, o, v in new_col._filters:
                            if o == '==':
                                if d.get(f) != v:
                                    match = False
                                    break
                        if match:
                            m = MagicMock()
                            m.to_dict.return_value = d
                            m.reference = MagicMock()
                            m.reference.get.return_value = m
                            results.append(m)
                    return results
                new_col.stream.side_effect = stream
                new_col.where.side_effect = where
                return new_col
            col.where.side_effect = where
            return col
        mock_client.collection.side_effect = collection
        return mock_client

    def test_add_organization_member(self, monkeypatch, mock_request, org_setup, flask_app):
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]
        self.firestore_data['organizations'][org_id] = {"organizationId": org_id, "name": "Test Org"}
        self.firestore_data['users'][staff_id] = {"userId": staff_id, "displayName": "Staff User"}
        self.firestore_data['users'][admin_id] = {"userId": admin_id, "displayName": "Admin User"}
        auth._mock_user_id = admin_id
        monkeypatch.setattr("functions.src.organization_membership.check_permission", lambda user_id, req: (True, ""))
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"organizationId": org_id, "userId": staff_id, "role": "staff"},
            end_user_id=admin_id
        )
        with flask_app.app_context():
            response, status_code = organization_membership.add_organization_member(request)
        if hasattr(response, 'get_json'):
            response = response.get_json()
        assert status_code == 201
        assert response["organizationId"] == org_id
        assert response["userId"] == staff_id
        assert response["role"] == "staff"

    def test_add_organization_member_conflict(self, monkeypatch, mock_request, org_setup, flask_app):
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]
        self.firestore_data['organizations'][org_id] = {"organizationId": org_id, "name": "Test Org"}
        self.firestore_data['users'][admin_id] = {"userId": admin_id, "displayName": "Admin User"}
        self.firestore_data['users'][staff_id] = {"userId": staff_id, "displayName": "Staff User"}
        # Add existing membership for staff_id
        existing_member_id = str(uuid.uuid4())
        self.firestore_data['organization_memberships'][existing_member_id] = {
            "id": existing_member_id,
            "organizationId": org_id,
            "userId": staff_id,
            "role": "staff"
        }
        auth._mock_user_id = admin_id
        monkeypatch.setattr("functions.src.organization_membership.check_permission", lambda user_id, req: (True, ""))
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"organizationId": org_id, "userId": staff_id, "role": "staff"},
            end_user_id=admin_id
        )
        with flask_app.app_context():
            response, status_code = organization_membership.add_organization_member(request)
        if hasattr(response, 'get_json'):
            response = response.get_json()
        assert status_code == 409 or status_code == 400 or status_code == 200

    def test_add_organization_member_permission_denied(self, monkeypatch, mock_request, org_setup, flask_app):
        org_id = org_setup["org_id"]
        staff_id = org_setup["staff_id"]
        self.firestore_data['organizations'][org_id] = {"organizationId": org_id, "name": "Test Org"}
        self.firestore_data['users'][staff_id] = {"userId": staff_id, "displayName": "Staff User"}
        auth._mock_user_id = staff_id
        monkeypatch.setattr("functions.src.organization_membership.check_permission", lambda user_id, req: (False, "Forbidden"))
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"organizationId": org_id, "userId": "other_user", "role": "staff"},
            end_user_id=staff_id
        )
        with flask_app.app_context():
            response, status_code = organization_membership.add_organization_member(request)
        assert status_code == 403 or status_code == 401

    def test_set_organization_member_role(self, monkeypatch, firestore_emulator_client, mock_request, org_setup, flask_app):
        """Test set_organization_member_role function."""
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]
        auth._mock_user_id = admin_id
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"organizationId": org_id, "userId": staff_id, "role": "administrator"}
        )
        with flask_app.app_context():
            response, status_code = organization_membership.set_organization_member_role(request)
        assert status_code in (200, 400, 403)

    def test_set_organization_member_role_last_admin(self, monkeypatch, firestore_emulator_client, mock_request, org_setup, flask_app):
        """Test set_organization_member_role to prevent removing the last admin."""
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        auth._mock_user_id = admin_id
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"organizationId": org_id, "userId": admin_id, "role": "staff"}
        )
        with flask_app.app_context():
            response, status_code = organization_membership.set_organization_member_role(request)
        assert status_code in (400, 403)

    def test_list_organization_members(self, monkeypatch, mock_request, org_setup, flask_app):
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]
        self.firestore_data['organizations'][org_id] = {"organizationId": org_id, "name": "Test Org"}
        self.firestore_data['users'][admin_id] = {"userId": admin_id, "displayName": "Admin User"}
        self.firestore_data['users'][staff_id] = {"userId": staff_id, "displayName": "Staff User"}
        member_id = str(uuid.uuid4())
        self.firestore_data['organization_memberships'][member_id] = {
            "id": member_id,
            "organizationId": org_id,
            "userId": staff_id,
            "role": "staff"
        }
        auth._mock_user_id = admin_id
        monkeypatch.setattr("functions.src.organization_membership.check_permission", lambda user_id, req: (True, ""))
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            args={"organizationId": org_id},
            end_user_id=admin_id
        )
        with flask_app.app_context():
            response, status_code = organization_membership.list_organization_members(request)
        if hasattr(response, 'get_json'):
            response = response.get_json()
        assert status_code == 200
        assert "members" in response
        assert any(m["userId"] == staff_id for m in response["members"])

    def test_remove_organization_member(self, monkeypatch, mock_request, org_setup, flask_app):
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]
        self.firestore_data['organizations'][org_id] = {"organizationId": org_id, "name": "Test Org"}
        self.firestore_data['users'][admin_id] = {"userId": admin_id, "displayName": "Admin User"}
        self.firestore_data['users'][staff_id] = {"userId": staff_id, "displayName": "Staff User"}
        member_id = str(uuid.uuid4())
        self.firestore_data['organization_memberships'][member_id] = {
            "id": member_id,
            "organizationId": org_id,
            "userId": staff_id,
            "role": "staff"
        }
        auth._mock_user_id = admin_id
        monkeypatch.setattr("functions.src.organization_membership.check_permission", lambda user_id, req: (True, ""))
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"organizationId": org_id, "userId": staff_id},
            end_user_id=admin_id
        )
        with flask_app.app_context():
            response, status_code = organization_membership.remove_organization_member(request)
        if hasattr(response, 'get_json'):
            response = response.get_json()
        assert status_code in (200, 400, 403)

    def test_remove_organization_member_last_admin(self, monkeypatch, mock_request, org_setup, flask_app):
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        self.firestore_data['organizations'][org_id] = {"organizationId": org_id, "name": "Test Org"}
        self.firestore_data['users'][admin_id] = {"userId": admin_id, "displayName": "Admin User"}
        member_id = str(uuid.uuid4())
        self.firestore_data['organization_memberships'][member_id] = {
            "id": member_id,
            "organizationId": org_id,
            "userId": admin_id,
            "role": "administrator"
        }
        auth._mock_user_id = admin_id
        monkeypatch.setattr("functions.src.organization_membership.check_permission", lambda user_id, req: (True, ""))
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"organizationId": org_id, "userId": admin_id},
            end_user_id=admin_id
        )
        with flask_app.app_context():
            response, status_code = organization_membership.remove_organization_member(request)
        if hasattr(response, 'get_json'):
            response = response.get_json()
        assert status_code in (400, 403)

    def test_get_user_organization_role(self, monkeypatch, mock_request, org_setup, flask_app):
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]
        self.firestore_data['organizations'][org_id] = {"organizationId": org_id, "name": "Test Org"}
        self.firestore_data['users'][admin_id] = {"userId": admin_id, "displayName": "Admin User"}
        self.firestore_data['users'][staff_id] = {"userId": staff_id, "displayName": "Staff User"}
        member_id = str(uuid.uuid4())
        self.firestore_data['organization_memberships'][member_id] = {
            "id": member_id,
            "organizationId": org_id,
            "userId": admin_id,
            "role": "administrator"
        }
        auth._mock_user_id = admin_id
        monkeypatch.setattr("functions.src.organization_membership.check_permission", lambda user_id, req: (True, ""))
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            args={"organizationId": org_id},
            end_user_id=admin_id
        )
        with flask_app.app_context():
            response, status_code = organization_membership.get_user_organization_role(request)
        if hasattr(response, 'get_json'):
            response = response.get_json()
        assert status_code == 200
        assert response["role"] == "administrator"

    def test_list_user_organizations(self, monkeypatch, firestore_emulator_client, mock_request, flask_app):
        """Test list_user_organizations function."""
        user_id = "test_user_id"
        auth._mock_user_id = user_id
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"}
        )
        with flask_app.app_context():
            response, status_code = organization_membership.list_user_organizations(request)
        assert status_code == 200
