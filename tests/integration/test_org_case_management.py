#!/usr/bin/env python3
import json
import logging
import os
import pytest
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestOrgCaseManagement:
    """Test suite for organization case management, focusing on RBAC."""

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
            "description": "Test organization for case management tests"
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
            description = "Test case created for case management tests"

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

    def _assign_case(self, client, case_id, user_id):
        """Assign a case to a user."""
        payload = {
            "userId": user_id
        }

        response = client.post(f"/cases/{case_id}/assign", json=payload)
        logger.info(f"Assign case response: {response.text}")
        
        return response

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
            response = client.delete(f"/cases/{case_id}")
            if response.status_code == 200:
                logger.info(f"Deleted test case: {case_id}")
            else:
                logger.warning(f"Failed to delete case {case_id}: {response.text}")
        except Exception as e:
            logger.error(f"Error deleting case {case_id}: {str(e)}")

    # Create Case Tests

    def test_admin_can_create_case(self, org_admin_api_client, setup_test_users):
        """Test that an administrator can create a case in an organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        
        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)
        
        try:
            # Admin creates a case
            case_id = self._create_test_case(org_admin_api_client, org_id)
            
            # Verify the case exists by getting it
            response = org_admin_api_client.get(f"/cases/{case_id}")
            assert response.status_code == 200, f"Failed to get case: {response.text}"
            
            # Clean up the case
            self._cleanup_test_case(org_admin_api_client, case_id)
            
        finally:
            # Clean up the organization
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_staff_can_create_case(self, org_admin_api_client, org_user_api_client, setup_test_users):
        """Test that a staff member can create a case in an organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        staff_user_id = setup_test_users["staff_user_id"]
        
        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)
        
        try:
            # Admin adds staff to the organization
            self._add_member_to_org(org_admin_api_client, org_id, staff_user_id, "staff")
            
            # Staff creates a case
            case_id = self._create_test_case(org_user_api_client, org_id)
            
            # Verify the case exists by getting it
            response = org_user_api_client.get(f"/cases/{case_id}")
            assert response.status_code == 200, f"Failed to get case: {response.text}"
            
            # Clean up the case
            self._cleanup_test_case(org_admin_api_client, case_id)
            
        finally:
            # Clean up the organization
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_non_member_cannot_create_case(self, org_admin_api_client, api_client, setup_test_users):
        """Test that a non-member cannot create a case in an organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]
        
        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)
        
        try:
            # Regular user (non-member) attempts to create a case
            payload = {
                "title": f"Test Case {uuid.uuid4()}",
                "description": "Test case that should fail",
                "caseTier": 1,
                "caseTypeId": "general_consultation"
            }
            
            response = api_client.post(f"/organizations/{org_id}/cases", json=payload)
            
            # Verify access is denied
            assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}: {response.text}"
            logger.info("Non-member cannot create case: Test passed")
            
        finally:
            # Clean up the organization
            self._cleanup_test_organization(org_admin_api_client, org_id)

    # List Cases Tests

    def test_admin_can_list_cases(self, org_admin_api_client, setup_test_users):
        """Test that an administrator can list cases in an organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        
        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)
        
        try:
            # Admin creates a case
            case_id = self._create_test_case(org_admin_api_client, org_id)
            
            # Admin lists cases
            response = org_admin_api_client.get(f"/organizations/{org_id}/cases")
            assert response.status_code == 200, f"Failed to list cases: {response.text}"
            
            data = response.json()
            assert "cases" in data, "Response does not contain cases field"
            assert isinstance(data["cases"], list), "Cases field is not a list"
            
            # Verify the case is in the list
            found = False
            for case in data["cases"]:
                if case.get("id") == case_id or case.get("caseId") == case_id:
                    found = True
                    break
                    
            assert found, f"Created case {case_id} not found in organization's cases"
            logger.info("Admin can list cases: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(org_admin_api_client, case_id)
            
        finally:
            # Clean up the organization
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_staff_can_list_cases(self, org_admin_api_client, org_user_api_client, setup_test_users):
        """Test that a staff member can list cases in an organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        staff_user_id = setup_test_users["staff_user_id"]
        
        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)
        
        try:
            # Admin adds staff to the organization
            self._add_member_to_org(org_admin_api_client, org_id, staff_user_id, "staff")
            
            # Admin creates a case
            case_id = self._create_test_case(org_admin_api_client, org_id)
            
            # Staff lists cases
            response = org_user_api_client.get(f"/organizations/{org_id}/cases")
            assert response.status_code == 200, f"Failed to list cases: {response.text}"
            
            data = response.json()
            assert "cases" in data, "Response does not contain cases field"
            assert isinstance(data["cases"], list), "Cases field is not a list"
            
            # Verify the case is in the list
            found = False
            for case in data["cases"]:
                if case.get("id") == case_id or case.get("caseId") == case_id:
                    found = True
                    break
                    
            assert found, f"Created case {case_id} not found in organization's cases"
            logger.info("Staff can list cases: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(org_admin_api_client, case_id)
            
        finally:
            # Clean up the organization
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_non_member_cannot_list_cases(self, org_admin_api_client, api_client, setup_test_users):
        """Test that a non-member cannot list cases in an organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        
        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)
        
        try:
            # Admin creates a case
            case_id = self._create_test_case(org_admin_api_client, org_id)
            
            # Non-member attempts to list cases
            response = api_client.get(f"/organizations/{org_id}/cases")
            
            # Verify access is denied
            assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}: {response.text}"
            logger.info("Non-member cannot list cases: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(org_admin_api_client, case_id)
            
        finally:
            # Clean up the organization
            self._cleanup_test_organization(org_admin_api_client, org_id)

    # Assign Case Tests

    def test_admin_can_assign_case(self, org_admin_api_client, setup_test_users):
        """Test that an administrator can assign a case in an organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        
        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)
        
        try:
            # Admin creates a case
            case_id = self._create_test_case(org_admin_api_client, org_id)
            
            # Admin assigns the case to themselves
            response = self._assign_case(org_admin_api_client, case_id, admin_user_id)
            assert response.status_code == 200, f"Failed to assign case: {response.text}"
            
            # Verify the assignment by getting the case
            get_response = org_admin_api_client.get(f"/cases/{case_id}")
            assert get_response.status_code == 200, f"Failed to get case: {get_response.text}"
            
            case_data = get_response.json()
            assert "assignedTo" in case_data, "Response does not contain assignedTo field"
            assert case_data["assignedTo"] == admin_user_id, f"Case not assigned to expected user"
            
            logger.info("Admin can assign case: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(org_admin_api_client, case_id)
            
        finally:
            # Clean up the organization
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_staff_cannot_assign_case(self, org_admin_api_client, org_user_api_client, setup_test_users):
        """Test that a staff member cannot assign a case in an organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        staff_user_id = setup_test_users["staff_user_id"]
        
        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)
        
        try:
            # Admin adds staff to the organization
            self._add_member_to_org(org_admin_api_client, org_id, staff_user_id, "staff")
            
            # Admin creates a case
            case_id = self._create_test_case(org_admin_api_client, org_id)
            
            # Staff attempts to assign the case
            response = self._assign_case(org_user_api_client, case_id, staff_user_id)
            
            # Verify access is denied
            assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
            logger.info("Staff cannot assign case: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(org_admin_api_client, case_id)
            
        finally:
            # Clean up the organization
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_non_member_cannot_assign_case(self, org_admin_api_client, api_client, setup_test_users):
        """Test that a non-member cannot assign a case in an organization."""
        admin_user_id = setup_test_users["admin_user_id"]
        regular_user_id = setup_test_users["regular_user_id"]
        
        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)
        
        try:
            # Admin creates a case
            case_id = self._create_test_case(org_admin_api_client, org_id)
            
            # Non-member attempts to assign the case
            response = self._assign_case(api_client, case_id, regular_user_id)
            
            # Verify access is denied
            assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}: {response.text}"
            logger.info("Non-member cannot assign case: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(org_admin_api_client, case_id)
            
        finally:
            # Clean up the organization
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_invalid_assignment(self, org_admin_api_client, setup_test_users):
        """Test that assigning a case to an invalid user fails."""
        admin_user_id = setup_test_users["admin_user_id"]
        
        # Admin creates an organization
        org_id = self._create_test_organization(org_admin_api_client)
        
        try:
            # Admin creates a case
            case_id = self._create_test_case(org_admin_api_client, org_id)
            
            # Admin attempts to assign the case to a non-existent user
            invalid_user_id = f"nonexistent-user-{uuid.uuid4()}"
            response = self._assign_case(org_admin_api_client, case_id, invalid_user_id)
            
            # Verify the assignment fails
            assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}: {response.text}"
            logger.info("Invalid assignment fails: Test passed")
            
            # Clean up the case
            self._cleanup_test_case(org_admin_api_client, case_id)
            
        finally:
            # Clean up the organization
            self._cleanup_test_organization(org_admin_api_client, org_id)

    def test_case_not_found_assignment(self, org_admin_api_client, setup_test_users):
        """Test that assigning a non-existent case fails."""
        admin_user_id = setup_test_users["admin_user_id"]
        
        # Generate a random case ID that doesn't exist
        nonexistent_case_id = f"nonexistent-case-{uuid.uuid4()}"
        
        # Admin attempts to assign the non-existent case
        response = self._assign_case(org_admin_api_client, nonexistent_case_id, admin_user_id)
        
        # Verify the assignment fails
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        logger.info("Case not found assignment fails: Test passed")