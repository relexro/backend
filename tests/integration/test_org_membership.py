#!/usr/bin/env python3
import json
import logging
import os
import sys
import requests
from flask import Request
from werkzeug.test import EnvironBuilder

# Add the functions/src directory to the Python path for proper imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../functions/src')))

from organization_membership import (
    add_organization_member,
    set_organization_member_role,
    list_organization_members,
    remove_organization_member,
    get_user_organization_role
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase authentication token
AUTH_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImZiOGNhNWE3OTlhYjBiODg4MmU5NDUwMjUyNjQwODNiZWYxMjg3NTciLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiR2VvcmdlIEFudG9uaXUiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jSmpPRExuajdQSUk0aGRXWlg3OHRmRWR6R0I3UFl3ZjBHckNJU0hWS1NFcWc9czk2LWMiLCJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vcmVsZXhybyIsImF1ZCI6InJlbGV4cm8iLCJhdXRoX3RpbWUiOjE3NDMwMTM3MTgsInVzZXJfaWQiOiJ6WFdvTjZGZTc0TVFXOGZpM2todXdFaE5iWXUxIiwic3ViIjoielh Xb042RmU3NE1RVzhmaTPraHV3RWhOYll1MSIsImlhdCI6MTc0MzAyODIxNSwiZXhwIjoxNzQzMDMxODE1LCJlbWFpbCI6Imdlb3JnZUBnZXRyZWxleC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJnb29nbGUuY29tIjpbIjEwOTY4MDI4OTc2OTEwNjcwNDYwOSJdLCJlbWFpbCI6WyJnZW9yZ2VAZ2V0cmVsZXguY29tIl19LCJzaWduX2luX3Byb3ZpZGVyIjoiZ29vZ2xlLmNvbSJ9fQ.BLFvhH-T3Tx-g63FyH7IhcQZLwPTpV_y-LFpJGXLNm9MRdmGg6jgx3z0hmn_6BMiqr6axw6EpS0wTsH17y_Ac3s3J_dDdIUNhblXJT98Tp3ZK8gaBDV5XSRfxnqvZgY-c8RkJZ87OBPscpnZ-vTqrS4R_gCSlHscQM-BI44TdQu5yIBHgqrYHH1n1PTRK2bRCZYK64W6QgdGZ7PiCbwb5rvjJvhyLOFPAOUgCgaA4VZdVAYKORGjSQj0xPWRJ9bMzXEfIKKcSzfQQ6Z1_l_LzL1_x7P32cIftjVQ0GsUQnNdXydZC-7PNj-P8WY2DFEF-O5hfZpXLxaESFMxp-I9Mg"

# Extract user_id from token
# In a real app, we'd decode the token more properly
USER_ID = "zXWoN6Fe74MQW8fi3khuwEhNbYu1"  # From the token

# Path to the test organization ID file
TEST_ORG_ID_FILE = os.path.join(os.path.dirname(__file__), '../test_data/test_org_id.txt')

# Try to get the organization ID from file if it exists
try:
    os.makedirs(os.path.dirname(TEST_ORG_ID_FILE), exist_ok=True)
    
    if os.path.exists(TEST_ORG_ID_FILE):
        with open(TEST_ORG_ID_FILE, "r") as f:
            TEST_ORG_ID = f.read().strip()
            logger.info(f"Using organization ID from file: {TEST_ORG_ID}")
    else:
        # Fallback to a default test ID
        TEST_ORG_ID = "test-org-123"
        logger.warning(f"Organization ID file not found, using default ID: {TEST_ORG_ID}")
except Exception as e:
    # Fallback to a default test ID
    TEST_ORG_ID = "test-org-123"
    logger.error(f"Error reading organization ID file: {str(e)}")
    logger.warning(f"Using default organization ID: {TEST_ORG_ID}")

def create_test_request(json_data=None, headers=None):
    """Create a test request for the functions."""
    if headers is None:
        headers = {'Authorization': f'Bearer {AUTH_TOKEN}'}
    
    builder = EnvironBuilder(
        method='POST',
        headers=headers,
        json=json_data
    )
    env = builder.get_environ()
    req = Request(env)
    
    # Manually attach the user_id to the request
    # This would normally be done by middleware
    req.user_id = USER_ID
    
    return req

def test_list_organization_members():
    """Test the list_organization_members function."""
    logger.info("Testing list_organization_members function")
    
    req = create_test_request(json_data={"organizationId": TEST_ORG_ID})
    response, status_code = list_organization_members(req)
    
    logger.info(f"Status code: {status_code}")
    logger.info(f"Response: {json.dumps(response, indent=2)}")
    
    return response, status_code

def test_add_organization_member():
    """Test the add_organization_member function."""
    logger.info("Testing add_organization_member function")
    
    # Use a test user ID - in production this would be a real Firebase Auth user ID
    test_user_id = "test-user-456"
    
    req = create_test_request(json_data={
        "organizationId": TEST_ORG_ID,
        "userId": test_user_id,
        "role": "staff"
    })
    
    response, status_code = add_organization_member(req)
    
    logger.info(f"Status code: {status_code}")
    logger.info(f"Response: {json.dumps(response, indent=2)}")
    
    return response, status_code

def test_set_organization_member_role():
    """Test the set_organization_member_role function."""
    logger.info("Testing set_organization_member_role function")
    
    # Use a test user ID - this should match a user that was previously added
    test_user_id = "test-user-456"
    
    req = create_test_request(json_data={
        "organizationId": TEST_ORG_ID,
        "userId": test_user_id,
        "newRole": "administrator"
    })
    
    response, status_code = set_organization_member_role(req)
    
    logger.info(f"Status code: {status_code}")
    logger.info(f"Response: {json.dumps(response, indent=2)}")
    
    return response, status_code

def test_remove_organization_member():
    """Test the remove_organization_member function."""
    logger.info("Testing remove_organization_member function")
    
    # Use a test user ID - this should match a user that was previously added
    test_user_id = "test-user-456"
    
    req = create_test_request(json_data={
        "organizationId": TEST_ORG_ID,
        "userId": test_user_id
    })
    
    response, status_code = remove_organization_member(req)
    
    logger.info(f"Status code: {status_code}")
    logger.info(f"Response: {json.dumps(response, indent=2)}")
    
    return response, status_code

def test_get_user_organization_role():
    """Test the get_user_organization_role function."""
    logger.info("Testing get_user_organization_role function")
    
    # Check our own role - we should be an administrator of the organization we created
    req = create_test_request(json_data={
        "organizationId": TEST_ORG_ID,
        "userId": USER_ID
    })
    
    response, status_code = get_user_organization_role(req)
    
    logger.info(f"Status code: {status_code}")
    logger.info(f"Response: {json.dumps(response, indent=2)}")
    
    return response, status_code

def main():
    """Run the tests."""
    logger.info("Starting organization membership tests")
    logger.info(f"Using organization ID: {TEST_ORG_ID}")
    logger.info(f"Using user ID: {USER_ID}")
    
    # Test listing members first to see if the organization exists and we're a member
    test_list_organization_members()
    
    # Test getting user role - this should tell us our role in the organization
    test_get_user_organization_role()
    
    # Run complete sequence of member management tests
    logger.info("\n--- Running member management test sequence ---")
    
    # Add a test user
    logger.info("\n1. Adding a test user")
    add_response, add_status = test_add_organization_member()
    
    if add_status == 200:
        # Update the user's role
        logger.info("\n2. Updating the test user's role")
        test_set_organization_member_role()
        
        # List members to confirm the user was added with the updated role
        logger.info("\n3. Listing members to confirm changes")
        test_list_organization_members()
        
        # Remove the test user
        logger.info("\n4. Removing the test user")
        test_remove_organization_member()
        
        # List members again to confirm the user was removed
        logger.info("\n5. Listing members to confirm removal")
        test_list_organization_members()
    else:
        logger.error(f"Failed to add test user, skipping remaining tests")

if __name__ == "__main__":
    main() 