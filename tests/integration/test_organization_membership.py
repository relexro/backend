"""Test setup file that modifies Python path and imports for testing."""
import sys
import os
from unittest.mock import MagicMock, patch
import uuid
import logging

import pytest
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
