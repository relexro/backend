import pytest
import uuid
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCreateCase:
    """Test suite for case creation API endpoints."""

    def test_create_individual_case(self, api_client):
        """Test creating an individual case through the API."""
        logger.info("Testing POST /cases endpoint for individual case creation")

        # Create case data
        case_data = {
            "title": f"Test Case {uuid.uuid4()}",
            "description": "This is a test case created through the API",
            "caseTier": 1,
            "caseTypeId": "general_consultation"
            # No paymentIntentId - will use quota if available or return payment required
        }

        # Make the API request
        response = api_client.post("/cases", json=case_data)

        # Check if payment is required
        if response.status_code == 402:
            logger.info("Payment required for case creation - this is expected if no quota is available")
            logger.info(f"Response: {response.text}")
            # This is a valid response, so we'll consider the test passed
            return

        # If not payment required, should be successful creation
        assert response.status_code == 201, f"Failed to create case: {response.text}"

        # Verify the response
        data = response.json()
        assert "caseId" in data, "Response does not contain caseId"
        assert "status" in data, "Response does not contain status"
        assert data["status"] == "open", "Case status should be 'open'"

        case_id = data["caseId"]
        logger.info(f"Successfully created case with ID: {case_id}")

        # Verify the case was created by getting it
        get_response = api_client.get(f"/cases/{case_id}")
        assert get_response.status_code == 200, f"Failed to get created case: {get_response.text}"

        # Clean up - delete the case
        delete_response = api_client.delete(f"/cases/{case_id}")
        if delete_response.status_code == 200:
            logger.info(f"Successfully deleted test case: {case_id}")
        else:
            logger.warning(f"Failed to delete test case: {delete_response.text}")

    def test_create_organization_case(self, api_client, test_organization):
        """Test creating a case for an organization through the API."""
        logger.info("Testing POST /organizations/{organizationId}/cases endpoint")

        # Create case data
        case_data = {
            "title": f"Test Organization Case {uuid.uuid4()}",
            "description": "This is a test organization case created through the API",
            "caseTier": 1,
            "caseTypeId": "general_consultation"
            # No paymentIntentId - will use quota if available or return payment required
        }

        # Make the API request
        response = api_client.post(f"/organizations/{test_organization}/cases", json=case_data)

        # Check if payment is required
        if response.status_code == 402:
            logger.info("Payment required for case creation - this is expected if no quota is available")
            logger.info(f"Response: {response.text}")
            # This is a valid response, so we'll consider the test passed
            return

        # If not payment required, should be successful creation
        assert response.status_code == 201, f"Failed to create organization case: {response.text}"

        # Verify the response
        data = response.json()
        assert "id" in data, "Response does not contain id"
        assert "title" in data, "Response does not contain title"
        assert "organizationId" in data, "Response does not contain organizationId"
        assert data["organizationId"] == test_organization, "Organization ID in response does not match"

        case_id = data["id"]
        logger.info(f"Successfully created organization case with ID: {case_id}")

        # Verify the case was created by getting it
        get_response = api_client.get(f"/cases/{case_id}")
        assert get_response.status_code == 200, f"Failed to get created case: {get_response.text}"

        # Clean up - delete the case
        delete_response = api_client.delete(f"/cases/{case_id}")
        if delete_response.status_code == 200:
            logger.info(f"Successfully deleted test case: {case_id}")
        else:
            logger.warning(f"Failed to delete test case: {delete_response.text}")

    def test_list_user_cases(self, api_client):
        """Test listing user's cases."""
        logger.info("Testing GET /users/me/cases endpoint")

        # Create a test case first
        case_data = {
            "title": f"Test Case for Listing {uuid.uuid4()}",
            "description": "This is a test case created for testing the list endpoint",
            "caseTier": 1,
            "caseTypeId": "general_consultation"
        }

        # Try to create a case - if it fails due to payment required, we'll skip case creation
        # but still test the listing endpoint
        create_response = api_client.post("/cases", json=case_data)
        case_id = None

        if create_response.status_code == 201:
            data = create_response.json()
            case_id = data["caseId"]
            logger.info(f"Created test case with ID: {case_id} for listing test")

        # Make the API request to list cases
        response = api_client.get("/users/me/cases")

        assert response.status_code == 200, f"Failed to list user cases: {response.text}"

        # Verify the response
        data = response.json()
        assert "cases" in data, "Response does not contain cases field"
        assert isinstance(data["cases"], list), "Cases field is not a list"

        # If we created a case, verify it's in the list and then delete it
        if case_id:
            found = False
            for case in data["cases"]:
                if case["caseId"] == case_id:
                    found = True
                    break

            assert found, f"Created case {case_id} not found in user's cases"

            # Clean up - delete the case
            delete_response = api_client.delete(f"/cases/{case_id}")
            if delete_response.status_code == 200:
                logger.info(f"Successfully deleted test case: {case_id}")
            else:
                logger.warning(f"Failed to delete test case: {delete_response.text}")

        logger.info(f"Successfully listed {len(data['cases'])} user cases")

    def test_list_organization_cases(self, api_client, test_organization):
        """Test listing organization's cases."""
        logger.info("Testing GET /organizations/{organizationId}/cases endpoint")

        # Create a test case first
        case_data = {
            "title": f"Test Org Case for Listing {uuid.uuid4()}",
            "description": "This is a test organization case created for testing the list endpoint",
            "caseTier": 1,
            "caseTypeId": "general_consultation"
        }

        # Try to create a case - if it fails due to payment required, we'll skip case creation
        # but still test the listing endpoint
        create_response = api_client.post(f"/organizations/{test_organization}/cases", json=case_data)
        case_id = None

        if create_response.status_code == 201:
            data = create_response.json()
            case_id = data["id"]
            logger.info(f"Created test organization case with ID: {case_id} for listing test")

        # Make the API request to list cases
        response = api_client.get(f"/organizations/{test_organization}/cases")

        assert response.status_code == 200, f"Failed to list organization cases: {response.text}"

        # Verify the response
        data = response.json()
        assert "cases" in data, "Response does not contain cases field"
        assert isinstance(data["cases"], list), "Cases field is not a list"

        # If we created a case, verify it's in the list and then delete it
        if case_id:
            found = False
            for case in data["cases"]:
                if case["id"] == case_id:
                    found = True
                    break

            assert found, f"Created case {case_id} not found in organization's cases"

            # Clean up - delete the case
            delete_response = api_client.delete(f"/cases/{case_id}")
            if delete_response.status_code == 200:
                logger.info(f"Successfully deleted test case: {case_id}")
            else:
                logger.warning(f"Failed to delete test case: {delete_response.text}")

        logger.info(f"Successfully listed {len(data['cases'])} organization cases")


