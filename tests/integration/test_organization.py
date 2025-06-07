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

# Alias fixture to maintain backward compatibility with test instructions
@pytest.fixture
def individual_api_client(api_client):
    """Alias for `api_client` representing a user not belonging to the organization."""
    return api_client

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
            "name": TestOrganizationLifecycle.created_org_name,
            "type": "integration_test_type"  # Required field as per OpenAPI spec
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
            # Delete the organization with ID in the body and path
            payload = {"organizationId": TestOrganizationLifecycle.created_org_id}
            response = org_admin_api_client.delete(
                f"/organizations/{TestOrganizationLifecycle.created_org_id}",
                json=payload
            )

            # Verify the response
            if response.status_code == 200:
                logger.info(f"Successfully deleted organization with ID: {TestOrganizationLifecycle.created_org_id}")
            else:
                logger.warning(f"Failed to delete organization: {response.text}")

        except Exception as e:
            logger.error(f"Error deleting organization: {str(e)}")


class TestOrganizationUpdateDelete:
    """
    Tests for updating and deleting organizations, focusing on role-based access
    and adherence to API specifications.
    """

    # Class attribute to indicate that organization ID is required in the request body
    # This was determined through testing and is used in the conditional test
    _use_body_for_delete = True

    def _create_test_organization_for_test(self, api_client_creator, name_prefix="Test Org UD"):
        """
        Helper to create a unique organization using the provided API client.
        Returns the organization ID.
        """
        unique_name = f"{name_prefix} {uuid.uuid4()}"
        payload = {"name": unique_name, "type": "integration_test_type"}
        response = api_client_creator.post("/organizations", json=payload)
        assert response.status_code == 201, f"Failed to create org for test setup: {response.text}"
        # The API might return 'id' or 'organizationId'
        org_id = response.json().get("organizationId") or response.json().get("id")
        assert org_id is not None, "Organization ID not found in creation response."
        return org_id

    # --- Tests for PUT /organizations/{organizationId} ---

    def test_admin_can_update_organization(self, org_admin_api_client):
        org_id = None
        try:
            org_id = self._create_test_organization_for_test(org_admin_api_client, "AdminUpdate")

            update_payload = {
                "organizationId": org_id,  # Include the ID in the request body
                "name": f"Updated Name by Admin {uuid.uuid4()}",
                "description": "This organization was updated by an admin."
            }
            response = org_admin_api_client.put(f"/organizations/{org_id}", json=update_payload)

            assert response.status_code == 200, f"PUT /organizations/{org_id} Expected 200, got {response.status_code}. Response: {response.text}"
            data = response.json()
            assert data["name"] == update_payload["name"]
            assert data["description"] == update_payload["description"]
            assert "updatedAt" in data, "updatedAt field missing in response"
        finally:
            if org_id:
                # Include the ID in the request body for deletion
                cleanup_payload = {"organizationId": org_id}
                cleanup_response = org_admin_api_client.delete(f"/organizations/{org_id}", json=cleanup_payload)
                assert cleanup_response.status_code == 200 or cleanup_response.status_code == 404 # 404 if already gone for some reason

    def test_staff_cannot_update_organization(self, org_admin_api_client, org_user_api_client):
        # org_admin_api_client creates the org.
        # org_user_api_client (representing a staff member of a *different* org, or a user who is not an admin of *this* org) attempts the update.
        org_id = None
        try:
            org_id = self._create_test_organization_for_test(org_admin_api_client, "StaffUpdateAttempt")

            update_payload = {
                "organizationId": org_id,  # Include the ID in the request body
                "name": f"Attempted Update by Staff {uuid.uuid4()}"
            }
            response = org_user_api_client.put(f"/organizations/{org_id}", json=update_payload)

            assert response.status_code == 403, f"PUT /organizations/{org_id} Expected 403 (Forbidden), got {response.status_code}. Response: {response.text}"
        finally:
            if org_id:
                # Include the ID in the request body for deletion
                cleanup_payload = {"organizationId": org_id}
                cleanup_response = org_admin_api_client.delete(f"/organizations/{org_id}", json=cleanup_payload)
                assert cleanup_response.status_code == 200 or cleanup_response.status_code == 404

    def test_non_member_cannot_update_organization(self, org_admin_api_client, individual_api_client):
        # org_admin_api_client creates the org.
        # individual_api_client (representing a user not member of this org) attempts the update.
        org_id = None
        try:
            org_id = self._create_test_organization_for_test(org_admin_api_client, "NonMemberUpdateAttempt")

            update_payload = {
                "organizationId": org_id,  # Include the ID in the request body
                "name": f"Attempted Update by Non-Member {uuid.uuid4()}"
            }
            response = individual_api_client.put(f"/organizations/{org_id}", json=update_payload)

            # As per openapi_spec.yaml, this should be 403 or 404. Prioritize 403 if resource exists but user is forbidden.
            assert response.status_code == 403, f"PUT /organizations/{org_id} Expected 403 (Forbidden), got {response.status_code}. Response: {response.text}"
        finally:
            if org_id:
                # Include the ID in the request body for deletion
                cleanup_payload = {"organizationId": org_id}
                cleanup_response = org_admin_api_client.delete(f"/organizations/{org_id}", json=cleanup_payload)
                assert cleanup_response.status_code == 200 or cleanup_response.status_code == 404

    def test_update_non_existent_organization(self, org_admin_api_client):
        non_existent_org_id = str(uuid.uuid4())
        update_payload = {
            "organizationId": non_existent_org_id,  # Include the ID in the request body
            "name": "Update Non-Existent Org"
        }
        response = org_admin_api_client.put(f"/organizations/{non_existent_org_id}", json=update_payload)

        assert response.status_code == 404, f"PUT /organizations/{non_existent_org_id} Expected 404 (Not Found), got {response.status_code}. Response: {response.text}"

    # --- Tests for DELETE /organizations/{organizationId} ---

    def test_admin_can_delete_organization(self, org_admin_api_client):
        org_id = self._create_test_organization_for_test(org_admin_api_client, "AdminDelete")

        # Include the ID in the request body
        delete_payload = {"organizationId": org_id}
        delete_response = org_admin_api_client.delete(f"/organizations/{org_id}", json=delete_payload)
        assert delete_response.status_code == 200, f"DELETE /organizations/{org_id} Expected 200, got {delete_response.status_code}. Response: {delete_response.text}"
        delete_data = delete_response.json()

        # Check for success message in the response
        assert "message" in delete_data, "Response does not contain 'message' field"
        assert "successfully" in delete_data["message"].lower(), f"Expected success message, got: {delete_data['message']}"

        # Verify actual deletion by attempting a GET
        get_response = org_admin_api_client.get(f"/organizations/{org_id}")
        assert get_response.status_code == 404, f"GET /organizations/{org_id} Expected 404 (Not Found) after delete, got {get_response.status_code}. Response: {get_response.text}"

    def test_staff_cannot_delete_organization(self, org_admin_api_client, org_user_api_client):
        org_id = None
        try:
            org_id = self._create_test_organization_for_test(org_admin_api_client, "StaffDeleteAttempt")

            # Include the ID in the request body
            delete_payload = {"organizationId": org_id}
            response = org_user_api_client.delete(f"/organizations/{org_id}", json=delete_payload)
            assert response.status_code == 403, f"DELETE /organizations/{org_id} Expected 403 (Forbidden), got {response.status_code}. Response: {response.text}"
        finally:
            if org_id: # Staff failed to delete, admin must clean up
                cleanup_payload = {"organizationId": org_id}
                cleanup_response = org_admin_api_client.delete(f"/organizations/{org_id}", json=cleanup_payload)
                assert cleanup_response.status_code == 200 or cleanup_response.status_code == 404


    def test_non_member_cannot_delete_organization(self, org_admin_api_client, api_client):
        org_id = None
        try:
            org_id = self._create_test_organization_for_test(org_admin_api_client, "NonMemberDeleteAttempt")

            # Include the ID in the request body
            delete_payload = {"organizationId": org_id}
            response = api_client.delete(f"/organizations/{org_id}", json=delete_payload)
            assert response.status_code == 403, f"DELETE /organizations/{org_id} Expected 403 (Forbidden), got {response.status_code}. Response: {response.text}"
        finally:
            if org_id: # Non-member failed to delete, admin must clean up
                cleanup_payload = {"organizationId": org_id}
                cleanup_response = org_admin_api_client.delete(f"/organizations/{org_id}", json=cleanup_payload)
                assert cleanup_response.status_code == 200 or cleanup_response.status_code == 404

    def test_delete_non_existent_organization(self, org_admin_api_client):
        non_existent_org_id = str(uuid.uuid4())
        # Include the ID in the request body
        delete_payload = {"organizationId": non_existent_org_id}
        response = org_admin_api_client.delete(f"/organizations/{non_existent_org_id}", json=delete_payload)
        assert response.status_code == 404, f"DELETE /organizations/{non_existent_org_id} Expected 404 (Not Found), got {response.status_code}. Response: {response.text}"

    def test_admin_cannot_delete_organization_with_active_subscription(self, org_admin_api_client):
        """Test that an admin cannot delete an organization with an active subscription."""
        # Executor: Assess if simulating an "active subscription" state is feasible.
        # This may require direct Firestore manipulation if no API endpoint exists to set this test state.
        # If not feasible with current test infrastructure, this test should be skipped.
        org_id_to_test = None
        # Placeholder for actual subscription simulation status
        subscription_simulated_successfully = False
        try:
            org_id_to_test = self._create_test_organization_for_test(org_admin_api_client, "Subscribed Org Delete Test")

            # Check if FIRESTORE_EMULATOR_HOST is set, which would allow direct Firestore manipulation
            if os.environ.get("FIRESTORE_EMULATOR_HOST"):
                try:
                    # Get a Firestore client connected to the emulator
                    db = firestore.client()

                    # Update the organization document to simulate an active subscription
                    org_ref = db.collection('organizations').document(org_id_to_test)
                    org_ref.update({
                        'subscriptionStatus': 'active',
                        'stripeSubscriptionId': f'sub_test_{uuid.uuid4()}',
                        'stripeCustomerId': f'cus_test_{uuid.uuid4()}',
                        'subscriptionPlanId': 'plan_test_professional',
                        'caseQuotaTotal': 100,
                        'caseQuotaUsed': 10,
                        'billingCycleStart': firestore.SERVER_TIMESTAMP,
                        'billingCycleEnd': firestore.SERVER_TIMESTAMP
                    })

                    subscription_simulated_successfully = True
                    logger.info(f"Successfully simulated active subscription for organization {org_id_to_test}")
                except Exception as e:
                    logger.error(f"Failed to simulate active subscription: {str(e)}")
                    subscription_simulated_successfully = False

            # Skip the test if we couldn't simulate an active subscription
            if not subscription_simulated_successfully:
                pytest.skip("Skipping delete_organization_with_active_subscription: Cannot simulate active subscription without Firestore emulator access.")

            # Attempt to delete the organization with an active subscription
            delete_payload = {"organizationId": org_id_to_test}
            response = org_admin_api_client.delete(f"/organizations/{org_id_to_test}", json=delete_payload)

            # The API should return 400 Bad Request (not 403 Forbidden) as per the implementation
            assert response.status_code == 400, f"Expected 400 for org with active subscription, got {response.status_code}. Response: {response.text}"
            assert "active subscription" in response.json().get("message", "").lower(), f"Expected error message about active subscription, got: {response.text}"
        finally:
            if org_id_to_test and subscription_simulated_successfully:
                try:
                    # If we successfully simulated a subscription, we need to remove it before cleanup
                    db = firestore.client()
                    org_ref = db.collection('organizations').document(org_id_to_test)
                    org_ref.update({
                        'subscriptionStatus': None,
                        'stripeSubscriptionId': firestore.DELETE_FIELD,
                        'subscriptionPlanId': firestore.DELETE_FIELD
                    })
                    logger.info(f"Removed simulated subscription for organization {org_id_to_test}")

                    # Now try to delete the organization
                    delete_payload = {"organizationId": org_id_to_test}
                    cleanup_response = org_admin_api_client.delete(f"/organizations/{org_id_to_test}", json=delete_payload)
                    if cleanup_response.status_code == 200:
                        logger.info(f"Successfully cleaned up organization {org_id_to_test}")
                    else:
                        logger.warning(f"Failed to clean up organization {org_id_to_test}: {cleanup_response.text}")
                except Exception as e:
                    logger.error(f"Error during cleanup: {str(e)}")
            elif org_id_to_test:
                # If we didn't simulate a subscription, just try to delete the organization
                delete_payload = {"organizationId": org_id_to_test}
                org_admin_api_client.delete(f"/organizations/{org_id_to_test}", json=delete_payload)
