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

from organization import create_organization

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase authentication token
AUTH_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImZiOGNhNWE3OTlhYjBiODg4MmU5NDUwMjUyNjQwODNiZWYxMjg3NTciLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiR2VvcmdlIEFudG9uaXUiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jSmpPRExuajdQSUk0aGRXWlg3OHRmRWR6R0I3UFl3ZjBHckNJU0hWS1NFcWc9czk2LWMiLCJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vcmVsZXhybyIsImF1ZCI6InJlbGV4cm8iLCJhdXRoX3RpbWUiOjE3NDMwMTM3MTgsInVzZXJfaWQiOiJ6WFdvTjZGZTc0TVFXOGZpM2todXdFaE5iWXUxIiwic3ViIjoielh Xb042RmU3NE1RVzhmaTPraHV3RWhOYll1MSIsImlhdCI6MTc0MzAyODIxNSwiZXhwIjoxNzQzMDMxODE1LCJlbWFpbCI6Imdlb3JnZUBnZXRyZWxleC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJnb29nbGUuY29tIjpbIjEwOTY4MDI4OTc2OTEwNjcwNDYwOSJdLCJlbWFpbCI6WyJnZW9yZ2VAZ2V0cmVsZXguY29tIl19LCJzaWduX2luX3Byb3ZpZGVyIjoiZ29vZ2xlLmNvbSJ9fQ.BLFvhH-T3Tx-g63FyH7IhcQZLwPTpV_y-LFpJGXLNm9MRdmGg6jgx3z0hmn_6BMiqr6axw6EpS0wTsH17y_Ac3s3J_dDdIUNhblXJT98Tp3ZK8gaBDV5XSRfxnqvZgY-c8RkJZ87OBPscpnZ-vTqrS4R_gCSlHscQM-BI44TdQu5yIBHgqrYHH1n1PTRK2bRCZYK64W6QgdGZ7PiCbwb5rvjJvhyLOFPAOUgCgaA4VZdVAYKORGjSQj0xPWRJ9bMzXEfIKKcSzfQQ6Z1_l_LzL1_x7P32cIftjVQ0GsUQnNdXydZC-7PNj-P8WY2DFEF-O5hfZpXLxaESFMxp-I9Mg"

# Path to the test organization ID file
TEST_ORG_ID_FILE = os.path.join(os.path.dirname(__file__), '../test_data/test_org_id.txt')

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
    
    return req

def test_create_organization():
    """Test creating an organization."""
    logger.info("Testing create_organization function")
    
    # Create a test organization
    org_data = {
        "name": "Test Organization",
        "type": "legal_firm",
        "address": "123 Test Street, Test City",
        "phone": "123-456-7890",
        "email": "test@example.com"
    }
    
    req = create_test_request(json_data=org_data)
    response, status_code = create_organization(req)
    
    logger.info(f"Status code: {status_code}")
    logger.info(f"Response: {json.dumps(response, indent=2)}")
    
    # If successful, save the organization ID to a file for future tests
    if status_code == 200 and 'id' in response:
        org_id = response['id']
        logger.info(f"Created organization with ID: {org_id}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(TEST_ORG_ID_FILE), exist_ok=True)
        
        # Save organization ID to file
        with open(TEST_ORG_ID_FILE, "w") as f:
            f.write(org_id)
        
        logger.info(f"Saved organization ID to {TEST_ORG_ID_FILE}")
    
    return response, status_code

if __name__ == "__main__":
    test_create_organization() 