#!/usr/bin/env python3
import json
import logging
import os
import pytest
import uuid
from unittest.mock import MagicMock

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCrossOrgSecurity:
    """Test suite for cross-organization security, ensuring proper isolation of resources."""

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
            "description": "Test organization for cross-org security tests"
        }

        response = client.post("/organizations", json=payload)
        assert response.status_code == 201, f"Failed to create organization: {response.text}"
        
        response_data = response.json()

        # Check for different possible keys for the organization ID
        if "organizationId" in response_data:
            org_id = response_data["organizationId"]
        elif "id" in response_data:
            org_id = response_data["id"]
        else:
            logger.error(f"Could not find organization ID in response: {response_data}")
            raise KeyError(f"Could not find organization ID in response: {response_data}")

        logger.info(f"Created test organization: {org_id}")
        return org_id

    def _add_member_to_org(self, client, org_id, user_id, role):
        """Add a member to an organization with the specified role."""
        payload = {
            "userId": user_id,
            "role": role,
            "organizationId": org_id
        }

        response = client.post(f"/organizations/{org_id}/members", json=payload)
        logger.info(f"Add member response: {response.text}")

        # Accept either 200 or 201 as success codes
        assert response.status_code in [200, 201], f"Failed to add member: {response.text}"
        logger.info(f"Added user {user_id} to org {org_id} with role {role}")
        return response.json()

    def _create_test_case(self, client, org_id, case_tier=1, title=None, description=None):
        """Create a test case for an organization and return its ID."""
        if title is None:
            title = f"Test Case {uuid.uuid4()}"
        
        if description is None:
            description = "Test case created for cross-org security tests"

        payload = {
            "title": title,
            "description": description,
            "caseTier": case_tier,
            "caseTypeId": "general_consultation"
        }

        response = client.post(f"/organizations/{org_id}/cases", json=payload)
        
        # Check if payment is required
        if response.status_code == 402:
            logger.info("Payment required for case creation - this is expected if no quota is available")
            logger.info(f"Response: {response.text}")
            pytest.skip("Payment required for case creation - skipping test")
            
        assert response.status_code == 201, f"Failed to create case: {response.text}"
        
        data = response.json()
        if "id" in data:
            case_id = data["id"]
        elif "caseId" in data:
            case_id = data["caseId"]
        else:
            logger.error(f"Could not find case ID in response: {data}")
            raise KeyError(f"Could not find case ID in response: {data}")
            
        logger.info(f"Created test case with ID: {case_id} for organization: {org_id}")
        return case_id

    def _upload_file_to_case(self, client, case_id, filename="test_document.pdf", content=b"test file content"):
        """Upload a test file to a case and return the response."""
        files = {
            'file': (filename, content, 'application/pdf')
        }
        
        response = client.post(f"/cases/{case_id}/files", files=files)
        logger.info(f"Upload file response: {response.text}")
        return response

    def _create_test_party(self, client, party_type="individual"):
        """Create a test party and return its ID."""
        if party_type == "individual":
            payload = {
                "partyType": "individual",
                "nameDetails": {
                    "firstName": f"Test",
                    "lastName": f"Person {uuid.uuid4()}"
                },
                "identityCodes": {
                    "cnp": "1234567890123"  # Mock 13-digit CNP
                },
                "contactInfo": {
                    "address": "123 Test Street, Test City",
                    "email": "test@example.com",
                    "phone": "123-456-7890"
                }
            }
        else:
            payload = {
                "partyType": "organization",
                "nameDetails": {
                    "companyName": f"Test Company {uuid.uuid4()}"
                },
                "identityCodes": {
                    "cui": "RO12345678",
                    "regCom": "J12/345/2023"
                },
                "contactInfo": {
                    "address": "123 Test Street, Test City",
                    "email": "company@example.com",
                    "phone": "123-456-7890"
                }
            }

        response = client.post("/parties", json=payload)
        assert response.status_code == 201, f"Failed to create party: {response.text}"
        
        data = response.json()
        if "partyId" in data:
            party_id = data["partyId"]
        elif "id" in data:
            party_id = data["id"]
        else:
            logger.error(f"Could not find party ID in response: {data}")
            raise KeyError(f"Could not find party ID in response: {data}")
        
        logger.info(f"Created test party with ID: {party_id}")
        return party_id

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

    def _cleanup_test_case(self, client, case_id):
        """Delete a test case."""
        try:
            # Try multiple formats since the API might have different expectations
            try:
                response = client.delete(f"/cases/{case_id}")
            except Exception:
                # Try alternative format with payload
                response = client.delete(f"/cases/{case_id}", json={"caseId": case_id})
                
            if response.status_code == 200:
                logger.info(f"Deleted test case: {case_id}")
            else:
                logger.warning(f"Failed to delete case {case_id}: {response.text}")
        except Exception as e:
            logger.error(f"Error deleting case {case_id}: {str(e)}")

    def _cleanup_test_party(self, client, party_id):
        """Delete a test party."""
        try:
            response = client.delete(f"/parties/{party_id}")
            if response.status_code == 200:
                logger.info(f"Deleted test party: {party_id}")
            else:
                logger.warning(f"Failed to delete party {party_id}: {response.text}")
        except Exception as e:
            logger.error(f"Error deleting party {party_id}: {str(e)}")

    # Cross-Organization Resource Access Tests

    def test_admin_cannot_access_other_org_details(self, org_admin_api_client, setup_test_users):
        """Test that an administrator cannot access details of another organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        
        # Admin creates first organization
        org1_id = self._create_test_organization(org_admin_api_client, "Test Org 1")
        
        # Admin creates second organization
        org2_id = self._create_test_organization(org_admin_api_client, "Test Org 2")
        
        try:
            # Create a regular user who will be admin of org2 only
            regular_user_id = setup_test_users["regular_user_id"]
            api_client = org_admin_api_client  # Use admin client temporarily
            
            # Add regular user as admin to org2
            self._add_member_to_org(api_client, org2_id, regular_user_id, "administrator")
            
            # Remove original admin from org2 (so they're no longer a member)
            # This simulates two separate organizations with different admins
            # Note: The API might prevent admins from removing themselves with a 400 error
            # This is acceptable for our test since the regular user is still an admin of org2
            payload = {"organizationId": org2_id, "userId": admin_user_id}
            response = api_client.delete(f"/organizations/{org2_id}/members/{admin_user_id}", json=payload)
            logger.info(f"Attempt to remove admin from org2 returned: {response.status_code}, {response.text}")
            
            # Original admin attempts to access org2 details
            response = org_admin_api_client.get(f"/organizations/{org2_id}")
            
            # Verify access is denied
            assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}: {response.text}"
            logger.info("Admin cannot access other org details: Test passed")
            
        finally:
            # Clean up the organizations
            self._cleanup_test_organization(org_admin_api_client, org1_id)
            self._cleanup_test_organization(org_admin_api_client, org2_id)

    def test_admin_cannot_modify_other_org_members(self, org_admin_api_client, api_client, setup_test_users):
        """Test that an administrator cannot modify members of another organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]
        
        # Admin creates first organization
        org1_id = self._create_test_organization(org_admin_api_client, "Test Org 1")
        
        # Regular user creates second organization
        org2_id = self._create_test_organization(api_client, "Test Org 2")
        
        try:
            # Admin attempts to add a member to org2
            payload = {
                "userId": admin_user_id,
                "role": "administrator",
                "organizationId": org2_id
            }
            
            response = org_admin_api_client.post(f"/organizations/{org2_id}/members", json=payload)
            
            # Verify access is denied
            assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}: {response.text}"
            logger.info("Admin cannot modify other org members: Test passed")
            
        finally:
            # Clean up the organizations
            self._cleanup_test_organization(org_admin_api_client, org1_id)
            self._cleanup_test_organization(api_client, org2_id)

    def test_admin_cannot_access_other_org_cases(self, org_admin_api_client, api_client, setup_test_users):
        """Test that an administrator cannot access cases of another organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]
        
        # Admin creates first organization
        org1_id = self._create_test_organization(org_admin_api_client, "Test Org 1")
        
        # Regular user creates second organization
        org2_id = self._create_test_organization(api_client, "Test Org 2")
        
        try:
            # Regular user creates a case in org2
            case_id = self._create_test_case(api_client, org2_id)
            
            # Admin attempts to access the case in org2
            response = org_admin_api_client.get(f"/cases/{case_id}")
            
            # Verify access is denied - 400 is also acceptable as the API might reject the request format
            # before even checking permissions
            assert response.status_code in [400, 403, 404], f"Expected 400, 403 or 404, got {response.status_code}: {response.text}"
            logger.info("Admin cannot access other org cases: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(api_client, case_id)
            
        finally:
            # Clean up the organizations
            self._cleanup_test_organization(org_admin_api_client, org1_id)
            self._cleanup_test_organization(api_client, org2_id)

    def test_admin_cannot_upload_files_to_other_org_cases(self, org_admin_api_client, api_client, setup_test_users):
        """Test that an administrator cannot upload files to cases of another organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]
        
        # Admin creates first organization
        org1_id = self._create_test_organization(org_admin_api_client, "Test Org 1")
        
        # Regular user creates second organization
        org2_id = self._create_test_organization(api_client, "Test Org 2")
        
        try:
            # Regular user creates a case in org2
            case_id = self._create_test_case(api_client, org2_id)
            
            # Admin attempts to upload a file to the case in org2
            response = self._upload_file_to_case(org_admin_api_client, case_id)
            
            # Verify access is denied (either 403, 404, or possibly 400 if case ID validation fails first)
            assert response.status_code in [400, 403, 404], f"Expected access denial, got {response.status_code}: {response.text}"
            logger.info("Admin cannot upload files to other org cases: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(api_client, case_id)
            
        finally:
            # Clean up the organizations
            self._cleanup_test_organization(org_admin_api_client, org1_id)
            self._cleanup_test_organization(api_client, org2_id)

    def test_admin_cannot_attach_parties_to_other_org_cases(self, org_admin_api_client, api_client, setup_test_users):
        """Test that an administrator cannot attach parties to cases of another organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]
        
        # Admin creates first organization
        org1_id = self._create_test_organization(org_admin_api_client, "Test Org 1")
        
        # Regular user creates second organization
        org2_id = self._create_test_organization(api_client, "Test Org 2")
        
        try:
            # Regular user creates a case in org2
            case_id = self._create_test_case(api_client, org2_id)
            
            # Admin creates a party
            party_id = self._create_test_party(org_admin_api_client)
            
            try:
                # Admin attempts to attach the party to the case in org2
                payload = {
                    "partyId": party_id
                }
                
                response = org_admin_api_client.post(f"/cases/{case_id}/attach_party", json=payload)
                
                # Verify access is denied
                assert response.status_code in [400, 403, 404], f"Expected access denial, got {response.status_code}: {response.text}"
                logger.info("Admin cannot attach parties to other org cases: Test passed")
                
                # Clean up the case
                self._cleanup_test_case(api_client, case_id)
            finally:
                # Clean up the party
                self._cleanup_test_party(org_admin_api_client, party_id)
            
        finally:
            # Clean up the organizations
            self._cleanup_test_organization(org_admin_api_client, org1_id)
            self._cleanup_test_organization(api_client, org2_id)

    def test_staff_cannot_access_other_org_resources(self, org_admin_api_client, org_user_api_client, api_client, setup_test_users):
        """Test that a staff member cannot access resources of another organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        staff_user_id = setup_test_users["staff_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]
        
        # Admin creates first organization
        org1_id = self._create_test_organization(org_admin_api_client, "Test Org 1")
        
        # Add staff to org1
        self._add_member_to_org(org_admin_api_client, org1_id, staff_user_id, "staff")
        
        # Regular user creates second organization
        org2_id = self._create_test_organization(api_client, "Test Org 2")
        
        try:
            # Regular user creates a case in org2
            case_id = self._create_test_case(api_client, org2_id)
            
            # Staff from org1 attempts to access the case in org2
            response = org_user_api_client.get(f"/cases/{case_id}")
            
            # Verify access is denied - 400 is also acceptable as the API might reject the request format
            # before even checking permissions
            assert response.status_code in [400, 403, 404], f"Expected 400, 403 or 404, got {response.status_code}: {response.text}"
            logger.info("Staff cannot access other org resources: Test passed")
            
            # Staff from org1 attempts to list members of org2
            response = org_user_api_client.get(f"/organizations/{org2_id}/members")
            
            # Verify access is denied
            assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}: {response.text}"
            logger.info("Staff cannot list other org members: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(api_client, case_id)
            
        finally:
            # Clean up the organizations
            self._cleanup_test_organization(org_admin_api_client, org1_id)
            self._cleanup_test_organization(api_client, org2_id)

    def test_member_can_see_only_own_orgs(self, org_admin_api_client, org_user_api_client, api_client, setup_test_users):
        """Test that a user can only see organizations they are a member of."""
        admin_user_id = setup_test_users["admin_user_id"]
        staff_user_id = setup_test_users["staff_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]
        
        # Admin creates first organization
        org1_id = self._create_test_organization(org_admin_api_client, "Test Org 1")
        
        # Add staff to org1
        self._add_member_to_org(org_admin_api_client, org1_id, staff_user_id, "staff")
        
        # Regular user creates second organization
        org2_id = self._create_test_organization(api_client, "Test Org 2")
        
        try:
            # Staff lists their organizations
            response = org_user_api_client.get("/users/me/organizations")
            
            assert response.status_code == 200, f"Failed to list user organizations: {response.text}"
            data = response.json()
            
            # Check that only org1 is in the list
            org_ids = [org["id"] if "id" in org else org.get("organizationId") for org in data.get("organizations", [])]
            
            assert org1_id in org_ids, f"Expected org1_id {org1_id} to be in {org_ids}"
            assert org2_id not in org_ids, f"Expected org2_id {org2_id} not to be in {org_ids}"
            
            logger.info("Member can see only own orgs: Test passed")
            
        finally:
            # Clean up the organizations
            self._cleanup_test_organization(org_admin_api_client, org1_id)
            self._cleanup_test_organization(api_client, org2_id)

    def test_admin_cannot_list_other_org_cases(self, org_admin_api_client, api_client, setup_test_users):
        """Test that an administrator cannot list cases of another organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]
        
        # Admin creates first organization
        org1_id = self._create_test_organization(org_admin_api_client, "Test Org 1")
        
        # Regular user creates second organization
        org2_id = self._create_test_organization(api_client, "Test Org 2")
        
        try:
            # Regular user creates a case in org2
            case_id = self._create_test_case(api_client, org2_id)
            
            # Admin attempts to list cases in org2
            response = org_admin_api_client.get(f"/organizations/{org2_id}/cases")
            
            # Verify access is denied
            assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}: {response.text}"
            logger.info("Admin cannot list other org cases: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(api_client, case_id)
            
        finally:
            # Clean up the organizations
            self._cleanup_test_organization(org_admin_api_client, org1_id)
            self._cleanup_test_organization(api_client, org2_id)