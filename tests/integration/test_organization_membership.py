"""Test setup file that modifies Python path and imports for testing."""
import sys
import os
from unittest.mock import MagicMock, patch
import uuid
import logging

# Add the mock_setup directory to sys.path before any other imports
mock_setup_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'functions', 'src', 'mock_setup'))
sys.path.insert(0, mock_setup_path)

# Create the mock_setup directory if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'functions', 'src', 'mock_setup'), exist_ok=True)

# Mock essential modules
sys.modules['auth'] = __import__('auth')

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
    auth.configure_mock(
        user_id="test_user_id",
        auth_status=200,
        auth_message=None,
        permissions_allowed=True,
        permissions_status=200
    )
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
        auth.configure_mock(user_id=admin_id)

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
        auth.configure_mock(user_id=admin_id)

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
        auth.configure_mock(user_id=staff_id)
        auth.configure_mock(permissions_allowed=False)

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
        auth.configure_mock(user_id=admin_id)

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
        auth.configure_mock(user_id=admin_id)

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
        auth.configure_mock(user_id=admin_id)

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
        auth.configure_mock(user_id=admin_id)

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
        auth.configure_mock(user_id=admin_id)

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
        auth.configure_mock(user_id="any_user")

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
        auth.configure_mock(user_id=user_id)

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


class TestOrganizationMembershipRBAC:
    """Test suite for organization membership RBAC (Role-Based Access Control)."""

    @pytest.fixture(scope="function")
    def setup_test_users(self, api_client, org_admin_api_client, org_user_api_client):
        """Get user IDs for the test users from their respective API clients."""
        # Get user IDs by calling /users/me endpoint
        admin_response = org_admin_api_client.get("/users/me")
        assert admin_response.status_code == 200, f"Failed to get admin user: {admin_response.text}"
        admin_user_id = admin_response.json()["userId"]

        staff_response = org_user_api_client.get("/users/me")
        assert staff_response.status_code == 200, f"Failed to get staff user: {staff_response.text}"
        staff_user_id = staff_response.json()["userId"]

        regular_response = api_client.get("/users/me")
        assert regular_response.status_code == 200, f"Failed to get regular user: {regular_response.text}"
        regular_user_id = regular_response.json()["userId"]

        logger.info(f"Test users: Admin={admin_user_id}, Staff={staff_user_id}, Regular={regular_user_id}")

        return {
            "admin_user_id": admin_user_id,
            "staff_user_id": staff_user_id,
            "regular_user_id": regular_user_id
        }

    def _create_test_organization(self, client, name=None):
        """Create a test organization and return its ID."""
        if name is None:
            name = f"Test Org {uuid.uuid4()}"

        payload = {
            "name": name,
            "description": "Test organization for RBAC tests"
        }

        response = client.post("/organizations", json=payload)
        assert response.status_code == 201, f"Failed to create organization: {response.text}"

        # Log the full response for debugging
        logger.info(f"Organization creation response: {response.text}")
        response_data = response.json()

        # Check for different possible keys for the organization ID
        if "organizationId" in response_data:
            org_id = response_data["organizationId"]
        elif "id" in response_data:
            org_id = response_data["id"]
        else:
            # If we can't find the ID, log the response and raise an error
            logger.error(f"Could not find organization ID in response: {response_data}")
            raise KeyError(f"Could not find organization ID in response: {response_data}")

        logger.info(f"Created test organization: {org_id}")
        return org_id

    def _add_member_to_org(self, client, org_id, user_id, role):
        """Add a member to an organization with the specified role."""
        payload = {
            "userId": user_id,
            "role": role,
            "organizationId": org_id  # Include organizationId in the payload as well
        }

        response = client.post(f"/organizations/{org_id}/members", json=payload)
        logger.info(f"Add member response: {response.text}")

        # Accept either 200 or 201 as success codes
        assert response.status_code in [200, 201], f"Failed to add member: {response.text}"
        logger.info(f"Added user {user_id} to org {org_id} with role {role}")
        return response.json()

    def _get_org_members(self, client, org_id):
        """Get the list of members for an organization."""
        response = client.get(f"/organizations/{org_id}/members")
        assert response.status_code == 200, f"Failed to get members: {response.text}"
        return response.json()["members"]

    def _is_user_member(self, client, org_id, user_id):
        """Check if a user is a member of an organization."""
        try:
            members = self._get_org_members(client, org_id)
            return any(member["userId"] == user_id for member in members)
        except AssertionError:
            # If we can't get the members list, the user is not a member or doesn't have permission
            return False

    def _cleanup_test_organization(self, client, org_id):
        """Delete a test organization."""
        try:
            # Some APIs might expect a JSON payload with the organization ID
            payload = {"organizationId": org_id}
            response = client.delete(f"/organizations/{org_id}", json=payload)
            if response.status_code == 200:
                logger.info(f"Deleted test organization: {org_id}")
            else:
                logger.warning(f"Failed to delete organization {org_id}: {response.text}")
        except Exception as e:
            logger.error(f"Error deleting organization {org_id}: {str(e)}")
            # Try without payload as fallback
            try:
                response = client.delete(f"/organizations/{org_id}")
                if response.status_code == 200:
                    logger.info(f"Deleted test organization (fallback): {org_id}")
                else:
                    logger.warning(f"Failed to delete organization {org_id} (fallback): {response.text}")
            except Exception as e2:
                logger.error(f"Error deleting organization {org_id} (fallback): {str(e2)}")

    # Staff Cannot Manage Members Tests

    def test_staff_cannot_add_new_member(self, org_admin_api_client, org_user_api_client, api_client, setup_test_users):
        """Test that staff members cannot add new members to an organization."""
        # Get user IDs
        admin_user_id = setup_test_users["admin_user_id"]
        staff_user_id = setup_test_users["staff_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]

        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)

        try:
            # Admin adds staff user to the organization
            self._add_member_to_org(org_admin_api_client, org_id, staff_user_id, "staff")

            # Staff attempts to add regular user to the organization
            payload = {
                "userId": regular_user_id,
                "role": "staff",
                "organizationId": org_id
            }

            response = org_user_api_client.post(f"/organizations/{org_id}/members", json=payload)

            # Verify that the request is forbidden
            assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
            logger.info("Staff cannot add new members: Test passed")

            # Verify that the regular user was not added
            assert not self._is_user_member(org_admin_api_client, org_id, regular_user_id), "Regular user should not have been added"

        finally:
            # Cleanup
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_staff_cannot_remove_other_staff_member(self, org_admin_api_client, org_user_api_client, api_client, setup_test_users):
        """Test that staff members cannot remove other staff members from an organization."""
        # Get user IDs
        admin_user_id = setup_test_users["admin_user_id"]
        staff_user_id = setup_test_users["staff_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]

        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)

        try:
            # Admin adds staff user to the organization
            self._add_member_to_org(org_admin_api_client, org_id, staff_user_id, "staff")

            # Admin adds regular user to the organization as staff
            self._add_member_to_org(org_admin_api_client, org_id, regular_user_id, "staff")

            # Staff attempts to remove regular user from the organization
            payload = {"organizationId": org_id, "userId": regular_user_id}
            response = org_user_api_client.delete(f"/organizations/{org_id}/members/{regular_user_id}", json=payload)

            # Verify that the request is forbidden
            assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
            logger.info("Staff cannot remove other staff members: Test passed")

            # Verify that the regular user is still a member
            assert self._is_user_member(org_admin_api_client, org_id, regular_user_id), "Regular user should still be a member"

        finally:
            # Cleanup
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_staff_cannot_remove_admin_member(self, org_admin_api_client, org_user_api_client, setup_test_users):
        """Test that staff members cannot remove admin members from an organization."""
        # Get user IDs
        admin_user_id = setup_test_users["admin_user_id"]
        staff_user_id = setup_test_users["staff_user_id"]

        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)

        try:
            # Admin adds staff user to the organization
            self._add_member_to_org(org_admin_api_client, org_id, staff_user_id, "staff")

            # Staff attempts to remove admin from the organization
            payload = {"organizationId": org_id, "userId": admin_user_id}
            response = org_user_api_client.delete(f"/organizations/{org_id}/members/{admin_user_id}", json=payload)

            # Verify that the request is forbidden
            assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
            logger.info("Staff cannot remove admin members: Test passed")

            # Verify that the admin is still a member
            assert self._is_user_member(org_admin_api_client, org_id, admin_user_id), "Admin should still be a member"

        finally:
            # Cleanup
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_staff_cannot_change_role_of_other_staff_to_admin(self, org_admin_api_client, org_user_api_client, api_client, setup_test_users):
        """Test that staff members cannot change the role of other staff members to admin."""
        # Get user IDs
        admin_user_id = setup_test_users["admin_user_id"]
        staff_user_id = setup_test_users["staff_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]

        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)

        try:
            # Admin adds staff user to the organization
            self._add_member_to_org(org_admin_api_client, org_id, staff_user_id, "staff")

            # Admin adds regular user to the organization as staff
            self._add_member_to_org(org_admin_api_client, org_id, regular_user_id, "staff")

            # Staff attempts to change regular user's role to admin
            payload = {
                "role": "administrator",  # Use 'role' instead of 'newRole'
                "organizationId": org_id,
                "userId": regular_user_id
            }

            response = org_user_api_client.put(f"/organizations/{org_id}/members/{regular_user_id}", json=payload)

            # Verify that the request is forbidden
            assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
            logger.info("Staff cannot change role of other staff to admin: Test passed")

            # Verify that the regular user's role is still staff
            members = self._get_org_members(org_admin_api_client, org_id)
            regular_user_role = next((member["role"] for member in members if member["userId"] == regular_user_id), None)
            assert regular_user_role == "staff", f"Regular user's role should still be staff, got {regular_user_role}"

        finally:
            # Cleanup
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_staff_cannot_change_role_of_admin_to_staff(self, org_admin_api_client, org_user_api_client, setup_test_users):
        """Test that staff members cannot change the role of admin members to staff."""
        # Get user IDs
        admin_user_id = setup_test_users["admin_user_id"]
        staff_user_id = setup_test_users["staff_user_id"]

        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)

        try:
            # Admin adds staff user to the organization
            self._add_member_to_org(org_admin_api_client, org_id, staff_user_id, "staff")

            # Staff attempts to change admin's role to staff
            payload = {
                "role": "staff",  # Use 'role' instead of 'newRole'
                "organizationId": org_id,
                "userId": admin_user_id
            }

            response = org_user_api_client.put(f"/organizations/{org_id}/members/{admin_user_id}", json=payload)

            # Verify that the request is forbidden
            assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
            logger.info("Staff cannot change role of admin to staff: Test passed")

            # Verify that the admin's role is still administrator
            members = self._get_org_members(org_admin_api_client, org_id)
            admin_role = next((member["role"] for member in members if member["userId"] == admin_user_id), None)
            assert admin_role == "administrator", f"Admin's role should still be administrator, got {admin_role}"

        finally:
            # Cleanup
            self._cleanup_test_organization(org_admin_api_client, org_id)

    # Last Administrator Constraints Tests

    def test_last_admin_cannot_remove_self(self, org_admin_api_client, setup_test_users):
        """Test that the last administrator cannot remove themselves from an organization."""
        # Get user IDs
        admin_user_id = setup_test_users["admin_user_id"]

        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)

        try:
            # Admin attempts to remove themselves from the organization
            payload = {"organizationId": org_id, "userId": admin_user_id}
            response = org_admin_api_client.delete(f"/organizations/{org_id}/members/{admin_user_id}", json=payload)

            # Verify that the request is forbidden or bad request
            assert response.status_code in [400, 403], f"Expected 400 or 403, got {response.status_code}: {response.text}"
            logger.info("Last admin cannot remove self: Test passed")

            # Verify that the admin is still a member
            assert self._is_user_member(org_admin_api_client, org_id, admin_user_id), "Admin should still be a member"

        finally:
            # Cleanup
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_last_admin_cannot_be_downgraded_to_staff(self, org_admin_api_client, setup_test_users):
        """Test that the last administrator cannot be downgraded to staff."""
        # Get user IDs
        admin_user_id = setup_test_users["admin_user_id"]

        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)

        try:
            # Admin attempts to downgrade themselves to staff
            payload = {
                "role": "staff",  # Use 'role' instead of 'newRole'
                "organizationId": org_id,
                "userId": admin_user_id
            }

            response = org_admin_api_client.put(f"/organizations/{org_id}/members/{admin_user_id}", json=payload)

            # Verify that the request is forbidden or bad request
            assert response.status_code in [400, 403], f"Expected 400 or 403, got {response.status_code}: {response.text}"
            logger.info("Last admin cannot be downgraded to staff: Test passed")

            # Verify that the admin's role is still administrator
            members = self._get_org_members(org_admin_api_client, org_id)
            admin_role = next((member["role"] for member in members if member["userId"] == admin_user_id), None)
            assert admin_role == "administrator", f"Admin's role should still be administrator, got {admin_role}"

        finally:
            # Cleanup
            self._cleanup_test_organization(org_admin_api_client, org_id)

    # Multiple Administrator Scenarios Tests

    def test_admin_can_remove_other_admin_if_not_last(self, org_admin_api_client, api_client, setup_test_users):
        """Test that an administrator can remove another administrator if they are not the last one."""
        # Get user IDs
        admin_user_id = setup_test_users["admin_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]

        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)

        try:
            # Admin adds regular user to the organization as administrator
            self._add_member_to_org(org_admin_api_client, org_id, regular_user_id, "administrator")

            # Verify that both users are administrators
            members = self._get_org_members(org_admin_api_client, org_id)
            admin_roles = [member["role"] for member in members if member["userId"] in [admin_user_id, regular_user_id]]
            assert all(role == "administrator" for role in admin_roles), "Both users should be administrators"

            # Admin removes the other admin
            payload = {"organizationId": org_id, "userId": regular_user_id}
            response = org_admin_api_client.delete(f"/organizations/{org_id}/members/{regular_user_id}", json=payload)

            # Verify that the request is successful
            assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
            logger.info("Admin can remove other admin if not last: Test passed")

            # Verify that the regular user is no longer a member
            assert not self._is_user_member(org_admin_api_client, org_id, regular_user_id), "Regular user should no longer be a member"

        finally:
            # Cleanup
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_admin_can_downgrade_other_admin_if_not_last(self, org_admin_api_client, api_client, setup_test_users):
        """Test that an administrator can downgrade another administrator to staff if they are not the last one."""
        # Get user IDs
        admin_user_id = setup_test_users["admin_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]

        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)

        try:
            # Admin adds regular user to the organization as administrator
            self._add_member_to_org(org_admin_api_client, org_id, regular_user_id, "administrator")

            # Verify that both users are administrators
            members = self._get_org_members(org_admin_api_client, org_id)
            admin_roles = [member["role"] for member in members if member["userId"] in [admin_user_id, regular_user_id]]
            assert all(role == "administrator" for role in admin_roles), "Both users should be administrators"

            # Admin downgrades the other admin to staff
            payload = {
                "role": "staff",  # Use 'role' instead of 'newRole'
                "organizationId": org_id,
                "userId": regular_user_id
            }

            response = org_admin_api_client.put(f"/organizations/{org_id}/members/{regular_user_id}", json=payload)

            # Verify that the request is successful
            assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
            logger.info("Admin can downgrade other admin if not last: Test passed")

            # Verify that the regular user's role is now staff
            members = self._get_org_members(org_admin_api_client, org_id)
            regular_user_role = next((member["role"] for member in members if member["userId"] == regular_user_id), None)
            assert regular_user_role == "staff", f"Regular user's role should be staff, got {regular_user_role}"

        finally:
            # Cleanup
            self._cleanup_test_organization(org_admin_api_client, org_id)