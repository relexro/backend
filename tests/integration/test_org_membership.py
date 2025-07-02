#!/usr/bin/env python3
import json
import logging
import os
import pytest
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the test organization ID file
TEST_ORG_ID_FILE = os.path.join(os.path.dirname(__file__), '../test_data/test_org_id.txt')

@pytest.fixture
def test_organization(api_client):
    """Create a test organization and clean it up after the test."""
    # Setup - Create a test organization
    org_data = {
        "name": f"Test Organization {uuid.uuid4()}",
        "type": "legal_firm",
        "address": "123 Test Street, Test City",
        "phone": "123-456-7890",
        "email": "test@example.com"
    }

    response = api_client.post("/organizations", json=org_data)
    assert response.status_code == 201, f"Failed to create test organization: {response.text}"

    org_id = response.json()["organizationId"]
    logger.info(f"Created test organization with ID: {org_id}")

    # Save the organization ID to a file for other tests
    os.makedirs(os.path.dirname(TEST_ORG_ID_FILE), exist_ok=True)
    with open(TEST_ORG_ID_FILE, "w") as f:
        f.write(org_id)

    yield org_id

    # Teardown - Delete the test organization
    # Note: This might fail if the organization has members other than the creator
    # In a real test, we would need to remove all members first
    try:
        response = api_client.delete(f"/organizations/{org_id}")
        if response.status_code == 200:
            logger.info(f"Deleted test organization with ID: {org_id}")
        else:
            logger.warning(f"Failed to delete test organization: {response.text}")
    except Exception as e:
        logger.error(f"Error deleting test organization: {str(e)}")

@pytest.fixture
def test_user_id():
    """Generate a test user ID."""
    # In a real test, we would create a real user
    # For now, we'll use a UUID as a placeholder
    return f"test-user-{uuid.uuid4()}"

class TestOrganizationMembership:
    """Test organization membership API endpoints."""

    def test_list_organization_members(self, api_client, test_organization):
        """Test listing organization members."""
        logger.info("Testing GET /organizations/members endpoint")

        response = api_client.get("/organizations/members", params={"organizationId": test_organization})

        assert response.status_code == 200, f"Failed to list organization members: {response.text}"
        data = response.json()
        assert "members" in data, "Response does not contain 'members' field"

        # The creator should be the only member initially
        assert len(data["members"]) == 1, "Expected only one member (the creator)"
        assert data["members"][0]["role"] == "administrator", "Creator should have administrator role"

        logger.info(f"Successfully listed {len(data['members'])} organization members")
        return data

    def test_add_organization_member(self, api_client, test_organization, test_user_id):
        """Test adding a member to an organization."""
        logger.info("Testing POST /organizations/members endpoint")

        payload = {
            "userId": test_user_id,
            "role": "staff",
            "organizationId": test_organization
        }

        response = api_client.post("/organizations/members", json=payload)

        assert response.status_code == 200, f"Failed to add organization member: {response.text}"
        data = response.json()
        assert data["success"] is True, "Response does not indicate success"
        assert data["userId"] == test_user_id, "User ID in response does not match"
        assert data["role"] == "staff", "Role in response does not match"

        logger.info(f"Successfully added user {test_user_id} as staff to organization {test_organization}")
        return data

    def test_update_member_role(self, api_client, test_organization, test_user_id):
        """Test updating a member's role in an organization."""
        logger.info("Testing PUT /organizations/members endpoint")

        # First add the member if not already added
        self.test_add_organization_member(api_client, test_organization, test_user_id)

        payload = {
            "organizationId": test_organization,
            "userId": test_user_id,
            "newRole": "administrator"
        }

        response = api_client.put("/organizations/members", json=payload)

        assert response.status_code == 200, f"Failed to update member role: {response.text}"
        data = response.json()
        assert data["success"] is True, "Response does not indicate success"
        assert data["userId"] == test_user_id, "User ID in response does not match"
        assert data["role"] == "administrator", "Role in response does not match"

        logger.info(f"Successfully updated user {test_user_id} to administrator in organization {test_organization}")
        return data

    def test_remove_organization_member(self, api_client, test_organization, test_user_id):
        """Test removing a member from an organization."""
        logger.info("Testing DELETE /organizations/members endpoint")

        # First add the member if not already added
        self.test_add_organization_member(api_client, test_organization, test_user_id)

        payload = {
            "organizationId": test_organization,
            "userId": test_user_id
        }
        response = api_client.delete("/organizations/members", json=payload)

        assert response.status_code == 200, f"Failed to remove organization member: {response.text}"
        data = response.json()
        assert data["success"] is True, "Response does not indicate success"
        assert data["userId"] == test_user_id, "User ID in response does not match"

        logger.info(f"Successfully removed user {test_user_id} from organization {test_organization}")
        return data

    def test_full_membership_lifecycle(self, api_client, test_organization, test_user_id):
        """Test the full lifecycle of organization membership."""
        logger.info("Testing full organization membership lifecycle")

        # 1. List initial members (should be just the creator)
        initial_members = self.test_list_organization_members(api_client, test_organization)
        assert len(initial_members["members"]) == 1, "Expected only one initial member"

        # 2. Add a new member
        self.test_add_organization_member(api_client, test_organization, test_user_id)

        # 3. List members again to verify addition
        members_after_add = self.test_list_organization_members(api_client, test_organization)
        assert len(members_after_add["members"]) == 2, "Expected two members after addition"

        # 4. Update the member's role
        self.test_update_member_role(api_client, test_organization, test_user_id)

        # 5. List members again to verify role update
        members_after_update = self.test_list_organization_members(api_client, test_organization)
        for member in members_after_update["members"]:
            if member["userId"] == test_user_id:
                assert member["role"] == "administrator", "Role update not reflected in member list"

        # 6. Remove the member
        self.test_remove_organization_member(api_client, test_organization, test_user_id)

        # 7. List members again to verify removal
        members_after_remove = self.test_list_organization_members(api_client, test_organization)
        assert len(members_after_remove["members"]) == 1, "Expected one member after removal"

        logger.info("Successfully completed full organization membership lifecycle test")

    def test_security_unauthorized_member_operations(self, api_client, test_organization, test_user_id):
        """Test that unauthorized users cannot perform member operations."""
        # This test would require a second authenticated user
        # For now, we'll just note that this would be a good security test to implement
        logger.info("Security test for unauthorized member operations would be implemented here")
        # In a real test, we would:
        # 1. Create a second organization with a different user
        # 2. Try to add/update/remove members from the first organization using the second user's token
        # 3. Verify that these operations fail with 403 Forbidden