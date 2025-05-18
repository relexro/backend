#!/usr/bin/env python3
import json
import logging
import os
import sys
import uuid
import pytest
import requests
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the test organization ID file
TEST_ORG_ID_FILE = os.path.join(os.path.dirname(__file__), '../test_data/test_org_id.txt')

class APIClient:
    """Simple API client for creating test organizations."""

    def __init__(self, base_url, auth_token=None):
        """Initialize the API client with base URL and optional auth token."""
        self.base_url = base_url
        self.session = requests.Session()
        if auth_token:
            self.session.headers.update({"Authorization": f"Bearer {auth_token}"})

    def post(self, endpoint, json=None, **kwargs):
        """Make a POST request to the API."""
        url = f"{self.base_url}{endpoint}"
        return self.session.post(url, json=json, **kwargs)

    def delete(self, endpoint, **kwargs):
        """Make a DELETE request to the API."""
        url = f"{self.base_url}{endpoint}"
        return self.session.delete(url, **kwargs)

def create_test_organization(base_url, auth_token):
    """Create a test organization using the API."""
    logger.info("Creating a test organization")

    # Initialize API client
    api_client = APIClient(base_url, auth_token)

    # Create a test organization
    org_data = {
        "name": f"Test Organization {uuid.uuid4()}",
        "type": "legal_firm",
        "address": "123 Test Street, Test City",
        "phone": "123-456-7890",
        "email": "test@example.com"
    }

    response = api_client.post("/organizations", json=org_data)

    logger.info(f"Response status code: {response.status_code}")

    # If successful, save the organization ID to a file for future tests
    if response.status_code == 201:
        data = response.json()
        org_id = data.get("organizationId")
        if org_id:
            logger.info(f"Created organization with ID: {org_id}")

            # Ensure directory exists
            os.makedirs(os.path.dirname(TEST_ORG_ID_FILE), exist_ok=True)

            # Save organization ID to file
            with open(TEST_ORG_ID_FILE, "w") as f:
                f.write(org_id)

            logger.info(f"Saved organization ID to {TEST_ORG_ID_FILE}")
            return org_id
        else:
            logger.error("Organization ID not found in response")
            return None
    else:
        logger.error(f"Failed to create organization: {response.text}")
        return None

def delete_test_organization(base_url, auth_token, org_id):
    """Delete a test organization using the API."""
    logger.info(f"Deleting test organization: {org_id}")

    # Initialize API client
    api_client = APIClient(base_url, auth_token)

    # Delete the organization
    response = api_client.delete(f"/organizations/{org_id}")

    if response.status_code == 200:
        logger.info(f"Successfully deleted organization: {org_id}")

        # Remove the ID file if it exists
        if os.path.exists(TEST_ORG_ID_FILE):
            os.remove(TEST_ORG_ID_FILE)
            logger.info(f"Removed organization ID file: {TEST_ORG_ID_FILE}")

        return True
    else:
        logger.error(f"Failed to delete organization: {response.text}")
        return False

def main():
    """Main function to create or delete a test organization."""
    parser = argparse.ArgumentParser(description="Create or delete a test organization")
    parser.add_argument("--action", choices=["create", "delete"], default="create", help="Action to perform")
    parser.add_argument("--base-url", default="https://api-dev.relex.ro", help="Base URL for the API")
    parser.add_argument("--token", help="Auth token (if not provided, will use RELEX_ORG_ADMIN_TEST_JWT environment variable)")
    parser.add_argument("--org-id", help="Organization ID to delete (only needed for delete action)")

    args = parser.parse_args()

    # Get auth token from environment variable or command line argument
    auth_token = args.token or os.environ.get("RELEX_ORG_ADMIN_TEST_JWT")
    if not auth_token:
        logger.error("Auth token not provided and RELEX_ORG_ADMIN_TEST_JWT environment variable not set")
        logger.error("Please set the RELEX_ORG_ADMIN_TEST_JWT environment variable or provide a token with --token")
        return 1

    if args.action == "create":
        org_id = create_test_organization(args.base_url, auth_token)
        if org_id:
            logger.info(f"Successfully created test organization: {org_id}")
            return 0
        else:
            logger.error("Failed to create test organization")
            return 1
    elif args.action == "delete":
        org_id = args.org_id
        if not org_id:
            # Try to get org_id from file
            try:
                with open(TEST_ORG_ID_FILE, "r") as f:
                    org_id = f.read().strip()
            except FileNotFoundError:
                logger.error(f"Organization ID file not found: {TEST_ORG_ID_FILE}")
                logger.error("Please specify an organization ID with --org-id")
                return 1

        success = delete_test_organization(args.base_url, auth_token, org_id)
        if success:
            logger.info(f"Successfully deleted test organization: {org_id}")
            return 0
        else:
            logger.error(f"Failed to delete test organization: {org_id}")
            return 1

if __name__ == "__main__":
    sys.exit(main())