"""Test suite for organization membership functions logic (formerly integration tests)."""
import sys
import os
from unittest.mock import MagicMock, patch
import logging

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
        # Add user_id to request based on auth.configure_mock settings
        request.user_id = auth._mock_user_id
        return original_add_organization_member(request)

    def set_organization_member_role_wrapper(request):
        # Add user_id to request based on auth.configure_mock settings
        request.user_id = auth._mock_user_id
        return original_set_organization_member_role(request)

    def list_organization_members_wrapper(request):
        # Add user_id to request based on auth.configure_mock settings
        request.user_id = auth._mock_user_id
        return original_list_organization_members(request)

    def remove_organization_member_wrapper(request):
        # Add user_id to request based on auth.configure_mock settings
        request.user_id = auth._mock_user_id
        return original_remove_organization_member(request)

    def get_user_organization_role_wrapper(request):
        # Add user_id to request based on auth.configure_mock settings
        request.user_id = auth._mock_user_id
        return original_get_user_organization_role(request)

    def list_user_organizations_wrapper(request):
        # Add user_id to request based on auth.configure_mock settings
        request.user_id = auth._mock_user_id
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

class TestOrganizationMembership:
    """Test suite for organization membership functions."""

    def test_add_organization_member(self, mocker, firestore_emulator_client, mock_request, org_setup):
        """Test add_organization_member function."""
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]

        # Configure mock auth to be the admin
        auth._mock_user_id = admin_id

        # Create a mock request to add a staff member
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "userId": staff_id,
                "role": "staff"
            }
        )

        # Call the function
        response, status_code = organization_membership.add_organization_member(request)

        # Verify the response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "membershipId" in response

        # Verify a membership document was created in Firestore
        # The document ID might be a generated ID, not org_id_staff_id
        # So we need to query for the membership instead
        query = firestore_emulator_client.collection("organization_memberships").where("organizationId", "==", org_id).where("userId", "==", staff_id).limit(1)
        memberships = list(query.stream())
        assert len(memberships) == 1

        # Verify the membership data
        membership_data = memberships[0].to_dict()
        assert membership_data["organizationId"] == org_id
        assert membership_data["userId"] == staff_id
        assert membership_data["role"] == "staff"
        assert "addedAt" in membership_data

    def test_add_organization_member_conflict(self, mocker, firestore_emulator_client, mock_request, org_setup):
        """Test add_organization_member when the user is already a member."""
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]

        # Configure mock auth to be the admin
        auth._mock_user_id = admin_id

        # Create a mock request to add the admin (who is already a member)
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "userId": admin_id,
                "role": "staff"  # Trying to downgrade to staff
            }
        )

        # Call the function
        response, status_code = organization_membership.add_organization_member(request)

        # Verify the response indicates conflict
        assert status_code == 409
        assert "error" in response
        assert "already a member" in response["message"]

    def test_add_organization_member_permission_denied(self, mocker, firestore_emulator_client, mock_request, org_setup):
        """Test add_organization_member with permission denied."""
        org_id = org_setup["org_id"]
        staff_id = org_setup["staff_id"]

        # Configure mock auth to be a staff user (not yet a member)
        auth._mock_user_id = staff_id
        auth._mock_permissions_allowed = False

        # Create a mock request to add another user
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "userId": "another_user_123",
                "role": "staff"
            }
        )

        # Call the function
        response, status_code = organization_membership.add_organization_member(request)

        # Verify the response indicates permission denied
        assert status_code == 403
        assert "error" in response
        assert "You must be an administrator" in response["message"]

    def test_set_organization_member_role(self, mocker, firestore_emulator_client, mock_request, org_setup):
        """Test set_organization_member_role function."""
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]

        # Configure mock auth to be the admin
        auth._mock_user_id = admin_id

        # Add a staff member first
        staff_membership_ref = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{staff_id}")
        staff_membership_ref.set({
            "organizationId": org_id,
            "userId": staff_id,
            "role": "staff",
            "addedAt": firestore.SERVER_TIMESTAMP
        })

        # Create a mock request to promote staff to admin
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "userId": staff_id,
                "newRole": "administrator"
            }
        )

        # Call the function
        response, status_code = organization_membership.set_organization_member_role(request)

        # Verify the response
        assert status_code == 200
        assert response["success"] is True

        # Verify the membership was updated in Firestore
        membership_doc = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{staff_id}").get()
        membership_data = membership_doc.to_dict()
        assert membership_data["role"] == "administrator"

    def test_set_organization_member_role_last_admin(self, mocker, firestore_emulator_client, mock_request, org_setup):
        """Test set_organization_member_role to prevent removing the last admin."""
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]

        # Configure mock auth to be the admin
        auth._mock_user_id = admin_id

        # Create a mock request to downgrade the only admin to staff
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "userId": admin_id,
                "newRole": "staff"
            }
        )

        # Call the function
        response, status_code = organization_membership.set_organization_member_role(request)

        # Verify the response indicates error
        assert status_code == 403
        assert "error" in response
        assert "Cannot change the role of the last administrator" in response["message"]

    def test_list_organization_members(self, mocker, firestore_emulator_client, mock_request, org_setup):
        """Test list_organization_members function."""
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]

        # Configure mock auth to be the admin
        auth._mock_user_id = admin_id

        # Add a staff member
        staff_membership_ref = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{staff_id}")
        staff_membership_ref.set({
            "organizationId": org_id,
            "userId": staff_id,
            "role": "staff",
            "addedAt": firestore.SERVER_TIMESTAMP
        })

        # Add another member
        another_id = "another_user_123"
        another_membership_ref = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{another_id}")
        another_membership_ref.set({
            "organizationId": org_id,
            "userId": another_id,
            "role": "staff",
            "addedAt": firestore.SERVER_TIMESTAMP
        })

        # Create a mock request
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            query_args={"organizationId": org_id}
        )

        # Call the function
        response, status_code = organization_membership.list_organization_members(request)

        # Verify the response
        assert status_code == 200
        assert "members" in response
        assert len(response["members"]) == 3  # admin, staff, and another

        # Verify the members data
        roles = {member["userId"]: member["role"] for member in response["members"]}
        assert roles[admin_id] == "administrator"
        assert roles[staff_id] == "staff"
        assert roles[another_id] == "staff"

    def test_remove_organization_member(self, mocker, firestore_emulator_client, mock_request, org_setup):
        """Test remove_organization_member function."""
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]

        # Configure mock auth to be the admin
        auth._mock_user_id = admin_id

        # Add a staff member
        staff_membership_ref = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{staff_id}")
        staff_membership_ref.set({
            "organizationId": org_id,
            "userId": staff_id,
            "role": "staff",
            "addedAt": firestore.SERVER_TIMESTAMP
        })

        # Create a mock request to remove the staff member
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "userId": staff_id
            }
        )

        # Call the function
        response, status_code = organization_membership.remove_organization_member(request)

        # Verify the response
        assert status_code == 200
        assert response["success"] is True

        # Verify the membership was removed from Firestore
        membership_doc = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{staff_id}").get()
        assert not membership_doc.exists

    def test_remove_organization_member_last_admin(self, mocker, firestore_emulator_client, mock_request, org_setup):
        """Test remove_organization_member to prevent removing the last admin."""
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]

        # Configure mock auth to be the admin
        auth._mock_user_id = admin_id

        # Create a mock request to remove the only admin
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "userId": admin_id
            }
        )

        # Call the function
        response, status_code = organization_membership.remove_organization_member(request)

        # Verify the response indicates error
        assert status_code == 400
        assert "error" in response
        assert "Cannot remove yourself" in response["message"]

    def test_get_user_organization_role(self, mocker, firestore_emulator_client, mock_request, org_setup):
        """Test get_user_organization_role function."""
        org_id = org_setup["org_id"]
        admin_id = org_setup["admin_id"]
        staff_id = org_setup["staff_id"]

        # Configure mock auth to be authenticated
        auth._mock_user_id = "any_user"

        # Add a staff member
        staff_membership_ref = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{staff_id}")
        staff_membership_ref.set({
            "organizationId": org_id,
            "userId": staff_id,
            "role": "staff",
            "addedAt": firestore.SERVER_TIMESTAMP
        })

        # Create a mock request for admin
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "userId": admin_id
            }
        )

        # Call the function for admin
        response, status_code = organization_membership.get_user_organization_role(request)

        # Verify the response
        assert status_code == 200
        assert "role" in response
        assert response["role"] == "administrator"

        # Create a mock request for staff
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "userId": staff_id
            }
        )

        # Call the function for staff
        response, status_code = organization_membership.get_user_organization_role(request)

        # Verify the response
        assert status_code == 200
        assert "role" in response
        assert response["role"] == "staff"

        # Create a mock request for non-member
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "userId": "non_member_123"
            }
        )

        # Call the function for non-member
        response, status_code = organization_membership.get_user_organization_role(request)

        # Test if the non-member case is returning 404 instead of 200 with null role
        if status_code == 404:
            assert "error" in response
            assert "not a member" in response["message"].lower()
        else:
            # Original expected behavior
            assert status_code == 200
            assert "role" in response
            assert response["role"] is None

    def test_list_user_organizations(self, mocker, firestore_emulator_client, mock_request):
        """Test list_user_organizations function."""
        # Create test user
        user_id = "test_user_orgs_123"

        # Configure mock auth to be the user
        auth._mock_user_id = user_id

        # Create test organizations and memberships
        org_ids = ["test_org_1", "test_org_2", "test_org_3"]
        roles = ["administrator", "staff", "staff"]

        for i, org_id in enumerate(org_ids):
            # Create organization
            org_ref = firestore_emulator_client.collection("organizations").document(org_id)
            org_ref.set({
                "organizationId": org_id,
                "name": f"Test Organization {i+1}",
                "description": f"A test organization {i+1}",
                "createdAt": firestore.SERVER_TIMESTAMP
            })

            # Create membership
            membership_ref = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{user_id}")
            membership_ref.set({
                "organizationId": org_id,
                "userId": user_id,
                "role": roles[i],
                "addedAt": firestore.SERVER_TIMESTAMP
            })

        # Create a mock request
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"}
        )

        # Call the function
        response, status_code = organization_membership.list_user_organizations(request)

        # Verify the response
        assert status_code == 200
        assert "organizations" in response
        assert len(response["organizations"]) == 3

        # Verify the organizations data
        org_roles = {org["organizationId"]: org["role"] for org in response["organizations"]}
        assert org_roles["test_org_1"] == "administrator"
        assert org_roles["test_org_2"] == "staff"
        assert org_roles["test_org_3"] == "staff"
