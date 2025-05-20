#!/usr/bin/env python3
import json
import logging
import os
import pytest
import uuid
import time
from pytest_dependency import depends

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Skip all tests in this module if the org admin token is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("RELEX_ORG_ADMIN_TEST_JWT") is None,
    reason="RELEX_ORG_ADMIN_TEST_JWT environment variable is not set"
)

class TestOrganizationLifecycle:
    """Test the organization lifecycle API endpoints.

    This test class verifies the following flow:
    1. Create a new organization using POST /organizations
    2. Retrieve the organization using GET /organizations/{organizationId}
    3. Verify the organization appears in the user's list of organizations
    """

    # Class variables to store state between tests
    created_org_id = None
    created_org_name = None

    @pytest.mark.dependency()
    def test_create_organization_with_admin(self, org_admin_api_client):
        """Test creating a new organization with an admin user."""
        logger.info("Testing POST /organizations endpoint with admin user")

        # Generate a unique organization name
        unique_suffix = str(uuid.uuid4()).split('-')[0]
        TestOrganizationLifecycle.created_org_name = f"Test Org By Admin - {unique_suffix}"

        # Prepare the payload
        payload = {
            "name": TestOrganizationLifecycle.created_org_name
            # Note: 'type' might be in the OpenAPI spec but not strictly required by the code
        }

        # Send the request
        response = org_admin_api_client.post("/organizations", json=payload)

        # Verify the response
        assert response.status_code == 201, f"Expected 201, got {response.status_code}. Response: {response.text}"
        data = response.json()

        # Verify the response data
        # The API might return 'id' or 'organizationId' based on the implementation
        org_id = data.get("id") or data.get("organizationId")
        assert org_id is not None, "Response does not contain 'id' or 'organizationId' field"
        TestOrganizationLifecycle.created_org_id = org_id

        assert "name" in data, "Response does not contain 'name' field"
        assert data["name"] == TestOrganizationLifecycle.created_org_name, "Organization name does not match"

        assert "createdBy" in data, "Response does not contain 'createdBy' field"
        assert data["createdBy"] is not None, "createdBy is None"

        logger.info(f"Successfully created organization with ID: {TestOrganizationLifecycle.created_org_id}")

        # Add a small delay to ensure the API has time to process the request
        time.sleep(1)

    @pytest.mark.dependency(depends=["TestOrganizationLifecycle::test_create_organization_with_admin"])
    def test_get_organization_by_id_with_admin(self, org_admin_api_client):
        """Test retrieving an organization by ID with an admin user."""
        logger.info("Testing GET /organizations/{organizationId} endpoint with admin user")

        # Ensure the organization ID is set from the previous test
        assert TestOrganizationLifecycle.created_org_id is not None, "Organization ID not set from create test"

        # Send the request using the path parameter format as per API specification
        response = org_admin_api_client.get(f"/organizations/{TestOrganizationLifecycle.created_org_id}")

        # Verify the response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        data = response.json()

        # Verify the response data
        # The API might return 'id' or 'organizationId' based on the implementation
        org_id = data.get("id") or data.get("organizationId")
        assert org_id is not None, "Response does not contain 'id' or 'organizationId' field"
        assert org_id == TestOrganizationLifecycle.created_org_id, "Organization ID does not match"

        assert "name" in data, "Response does not contain 'name' field"
        assert data["name"] == TestOrganizationLifecycle.created_org_name, "Organization name does not match"

        logger.info(f"Successfully retrieved organization with ID: {TestOrganizationLifecycle.created_org_id}")

        # Add a small delay to ensure the API has time to process the request
        time.sleep(1)

    @pytest.mark.dependency(depends=["TestOrganizationLifecycle::test_create_organization_with_admin"])
    def test_list_user_organizations_contains_new_org_for_admin(self, org_admin_api_client):
        """Test that a newly created organization appears in the admin user's organizations list."""
        logger.info("Testing GET /users/me/organizations endpoint with admin user")

        # Ensure the organization ID is set from the previous test
        assert TestOrganizationLifecycle.created_org_id is not None, "Organization ID not set from create test"

        # Send the request
        response = org_admin_api_client.get("/users/me/organizations")

        # Verify the response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        data = response.json()

        # Verify the response data
        assert "organizations" in data, "Response does not contain 'organizations' field"
        assert isinstance(data["organizations"], list), "Organizations field is not a list"

        # Find the newly created organization in the list
        found_new_org = False
        for org in data["organizations"]:
            if org.get("organizationId") == TestOrganizationLifecycle.created_org_id:
                found_new_org = True
                assert org.get("name") == TestOrganizationLifecycle.created_org_name, "Organization name does not match"
                assert org.get("role") == "administrator", f"Expected admin user's role to be 'administrator' in org {TestOrganizationLifecycle.created_org_id}, got {org.get('role')}"
                break

        assert found_new_org, f"Newly created organization with ID {TestOrganizationLifecycle.created_org_id} not found in admin user's organizations list"
        logger.info(f"Successfully found newly created organization in admin user's organizations list")

        # Add a small delay to ensure the API has time to process the request
        time.sleep(1)

    @pytest.mark.dependency(depends=["TestOrganizationLifecycle::test_list_user_organizations_contains_new_org_for_admin"])
    def test_cleanup_created_organization(self, org_admin_api_client):
        """Clean up the created organization after tests."""
        logger.info("Cleaning up created organization")

        # Ensure the organization ID is set from the previous tests
        if TestOrganizationLifecycle.created_org_id is None:
            logger.warning("No organization ID to clean up")
            return

        try:
            # Delete the organization
            # The API might expect a DELETE request with the ID in the path
            # or a DELETE request with the ID in the body
            try:
                # First try with ID in the path
                response = org_admin_api_client.delete(f"/organizations/{TestOrganizationLifecycle.created_org_id}")

                # Verify the response
                if response.status_code == 200:
                    logger.info(f"Successfully deleted organization with ID: {TestOrganizationLifecycle.created_org_id}")
                    return
                else:
                    logger.warning(f"Failed to delete organization with ID in path: {response.text}")
            except Exception as path_error:
                logger.warning(f"Error deleting organization with ID in path: {str(path_error)}")

            # If that fails, try with ID in the body
            payload = {"organizationId": TestOrganizationLifecycle.created_org_id}
            response = org_admin_api_client.delete("/organizations", json=payload)

            # Verify the response
            if response.status_code == 200:
                logger.info(f"Successfully deleted organization with ID: {TestOrganizationLifecycle.created_org_id}")
            else:
                logger.warning(f"Failed to delete organization with ID in body: {response.text}")

        except Exception as e:
            logger.error(f"Error deleting organization: {str(e)}")
