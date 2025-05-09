#!/usr/bin/env python3
import json
import logging
import os
import pytest
import uuid
import time

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

    # Wait a moment for changes to propagate
    time.sleep(1)

    yield org_id

    # Teardown - Delete the test organization
    try:
        response = api_client.delete(f"/organizations/{org_id}")
        if response.status_code == 200:
            logger.info(f"Deleted test organization with ID: {org_id}")
        else:
            logger.warning(f"Failed to delete test organization: {response.text}")
    except Exception as e:
        logger.error(f"Error deleting test organization: {str(e)}")

    # Remove the ID file if it exists
    if os.path.exists(TEST_ORG_ID_FILE):
        os.remove(TEST_ORG_ID_FILE)
        logger.info(f"Removed organization ID file: {TEST_ORG_ID_FILE}")

class TestListUserOrganizations:
    """Test the list user organizations API endpoint."""

    def test_list_user_organizations_format(self, api_client):
        """Test that the list user organizations endpoint returns data in the expected format."""
        logger.info("Testing GET /users/me/organizations endpoint format")

        response = api_client.get("/users/me/organizations")

        assert response.status_code == 200, f"Failed to list user organizations: {response.text}"
        data = response.json()
        assert "organizations" in data, "Response does not contain 'organizations' field"
        assert isinstance(data["organizations"], list), "Organizations field is not a list"

        # Check the structure of each organization in the list
        if data["organizations"]:
            org = data["organizations"][0]
            assert "organizationId" in org, "Organization does not have organizationId field"
            assert "name" in org, "Organization does not have name field"
            assert "role" in org, "Organization does not have role field"

        logger.info(f"Successfully verified format of user organizations response with {len(data['organizations'])} organizations")
        return data

    def test_list_user_organizations_with_created_org(self, api_client, test_organization):
        """Test that a newly created organization appears in the user's organizations list."""
        logger.info("Testing GET /users/me/organizations endpoint with a newly created organization")

        response = api_client.get("/users/me/organizations")

        assert response.status_code == 200, f"Failed to list user organizations: {response.text}"
        data = response.json()
        assert "organizations" in data, "Response does not contain 'organizations' field"

        # Find the test organization in the list
        found_org = False
        for org in data["organizations"]:
            if org["organizationId"] == test_organization:
                found_org = True
                assert org["role"] == "administrator", "User should be an administrator of the created organization"
                break

        assert found_org, f"Test organization {test_organization} not found in user's organizations"
        logger.info(f"Successfully found test organization {test_organization} in user's organizations")
        return data

    def test_organization_role_in_response(self, api_client, test_organization):
        """Test that the organization role is correctly included in the response."""
        logger.info("Testing that organization role is correctly included in the response")

        response = api_client.get("/users/me/organizations")

        assert response.status_code == 200, f"Failed to list user organizations: {response.text}"
        data = response.json()

        # Find the test organization in the list
        for org in data["organizations"]:
            if org["organizationId"] == test_organization:
                assert "role" in org, "Organization does not have role field"
                assert org["role"] in ["administrator", "staff"], f"Invalid role value: {org['role']}"
                logger.info(f"Successfully verified role field for organization {test_organization}")
                return

        assert False, f"Test organization {test_organization} not found in user's organizations"