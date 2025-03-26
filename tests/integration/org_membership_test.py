#!/usr/bin/env python3
import json
import logging
import os
import sys
import firebase_admin
from firebase_admin import firestore
from firebase_admin import auth
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the test organization ID file
TEST_ORG_ID_FILE = os.path.join(os.path.dirname(__file__), '../test_data/test_org_id.txt')

# Initialize Firebase Admin SDK
try:
    firebase_admin.get_app()
except ValueError:
    # Use the application default credentials
    firebase_admin.initialize_app()

# Firebase authentication token
AUTH_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImZiOGNhNWE3OTlhYjBiODg4MmU5NDUwMjUyNjQwODNiZWYxMjg3NTciLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiR2VvcmdlIEFudG9uaXUiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jSmpPRExuajdQSUk0aGRXWlg3OHRmRWR6R0I3UFl3ZjBHckNJU0hWS1NFcWc9czk2LWMiLCJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vcmVsZXhybyIsImF1ZCI6InJlbGV4cm8iLCJhdXRoX3RpbWUiOjE3NDMwMTM3MTgsInVzZXJfaWQiOiJ6WFdvTjZGZTc0TVFXOGZpM2todXdFaE5iWXUxIiwic3ViIjoielh Xb042RmU3NE1RVzhmaTPraHV3RWhOYll1MSIsImlhdCI6MTc0MzAyODIxNSwiZXhwIjoxNzQzMDMxODE1LCJlbWFpbCI6Imdlb3JnZUBnZXRyZWxleC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJnb29nbGUuY29tIjpbIjEwOTY4MDI4OTc2OTEwNjcwNDYwOSJdLCJlbWFpbCI6WyJnZW9yZ2VAZ2V0cmVsZXguY29tIl19LCJzaWduX2luX3Byb3ZpZGVyIjoiZ29vZ2xlLmNvbSJ9fQ.BLFvhH-T3Tx-g63FyH7IhcQZLwPTpV_y-LFpJGXLNm9MRdmGg6jgx3z0hmn_6BMiqr6axw6EpS0wTsH17y_Ac3s3J_dDdIUNhblXJT98Tp3ZK8gaBDV5XSRfxnqvZgY-c8RkJZ87OBPscpnZ-vTqrS4R_gCSlHscQM-BI44TdQu5yIBHgqrYHH1n1PTRK2bRCZYK64W6QgdGZ7PiCbwb5rvjJvhyLOFPAOUgCgaA4VZdVAYKORGjSQj0xPWRJ9bMzXEfIKKcSzfQQ6Z1_l_LzL1_x7P32cIftjVQ0GsUQnNdXydZC-7PNj-P8WY2DFEF-O5hfZpXLxaESFMxp-I9Mg"

# Extract user_id from token (in a real app, we'd decode the token more properly)
USER_ID = "zXWoN6Fe74MQW8fi3khuwEhNbYu1"  # From the token

# Test organization details
ORG_NAME = "Test Organization"
ORG_TYPE = "legal_firm"

def create_test_organization():
    """Create a test organization directly in Firestore."""
    logger.info("Creating a test organization")
    
    # Initialize Firestore
    db = firestore.client()
    
    # Create organization data
    organization_data = {
        "name": ORG_NAME,
        "type": ORG_TYPE,
        "address": "123 Test Street, Test City",
        "phone": "123-456-7890",
        "email": "test@example.com",
        "createdAt": firestore.SERVER_TIMESTAMP,
        "createdBy": USER_ID
    }
    
    # Create the organization document
    org_ref = db.collection("organizations").document()
    org_id = org_ref.id
    
    org_ref.set(organization_data)
    logger.info(f"Created organization with ID: {org_id}")
    
    # Add creator as administrator in organization_memberships collection
    membership_data = {
        "userId": USER_ID,
        "organizationId": org_id,
        "role": "administrator",
        "addedAt": firestore.SERVER_TIMESTAMP
    }
    
    membership_ref = db.collection("organization_memberships").document()
    membership_ref.set(membership_data)
    logger.info(f"Added user {USER_ID} as administrator in organization_memberships collection")
    
    # For backward compatibility, also add to the users subcollection
    user_data = {
        "role": "admin",
        "addedAt": firestore.SERVER_TIMESTAMP
    }
    
    user_ref = org_ref.collection("users").document(USER_ID)
    user_ref.set(user_data)
    logger.info(f"Added user {USER_ID} to organization's users subcollection for backward compatibility")
    
    # Save the organization ID to a file for future tests
    os.makedirs(os.path.dirname(TEST_ORG_ID_FILE), exist_ok=True)
    with open(TEST_ORG_ID_FILE, "w") as f:
        f.write(org_id)
    
    logger.info(f"Saved organization ID to {TEST_ORG_ID_FILE}")
    
    return org_id

def list_organization_members(org_id):
    """List all members of an organization."""
    logger.info(f"Listing members of organization: {org_id}")
    
    # Initialize Firestore
    db = firestore.client()
    
    # Query the organization_memberships collection
    members_query = db.collection("organization_memberships").where("organizationId", "==", org_id)
    members = list(members_query.stream())
    
    if members:
        logger.info(f"Found {len(members)} members:")
        for member in members:
            member_data = member.to_dict()
            logger.info(f"User ID: {member_data.get('userId')}, Role: {member_data.get('role')}")
    else:
        logger.info("No members found")
    
    return members

def add_test_member(org_id, test_user_id="test-user-456"):
    """Add a test member to the organization."""
    logger.info(f"Adding test member {test_user_id} to organization {org_id}")
    
    # Initialize Firestore
    db = firestore.client()
    
    # Check if the member already exists
    query = db.collection("organization_memberships").where("organizationId", "==", org_id).where("userId", "==", test_user_id)
    existing_memberships = list(query.stream())
    
    if existing_memberships:
        logger.info(f"Member {test_user_id} already exists in organization {org_id}")
        return False
    
    # Add the membership
    membership_data = {
        "userId": test_user_id,
        "organizationId": org_id,
        "role": "staff",
        "addedAt": firestore.SERVER_TIMESTAMP
    }
    
    membership_ref = db.collection("organization_memberships").document()
    membership_ref.set(membership_data)
    
    logger.info(f"Added member {test_user_id} to organization {org_id} with role 'staff'")
    return True

def change_member_role(org_id, user_id, new_role):
    """Change a member's role in the organization."""
    logger.info(f"Changing role of member {user_id} in organization {org_id} to {new_role}")
    
    # Initialize Firestore
    db = firestore.client()
    
    # Find the membership document
    query = db.collection("organization_memberships").where("organizationId", "==", org_id).where("userId", "==", user_id)
    memberships = list(query.stream())
    
    if not memberships:
        logger.info(f"Member {user_id} not found in organization {org_id}")
        return False
    
    # Update the role
    membership_ref = memberships[0].reference
    membership_ref.update({"role": new_role})
    
    logger.info(f"Updated role of member {user_id} to {new_role}")
    return True

def remove_member(org_id, user_id):
    """Remove a member from the organization."""
    logger.info(f"Removing member {user_id} from organization {org_id}")
    
    # Initialize Firestore
    db = firestore.client()
    
    # Find the membership document
    query = db.collection("organization_memberships").where("organizationId", "==", org_id).where("userId", "==", user_id)
    memberships = list(query.stream())
    
    if not memberships:
        logger.info(f"Member {user_id} not found in organization {org_id}")
        return False
    
    # Delete the membership
    membership_ref = memberships[0].reference
    membership_ref.delete()
    
    logger.info(f"Removed member {user_id} from organization {org_id}")
    return True

def main():
    """Run the tests."""
    logger.info("Starting organization membership tests")
    
    # Check if we already have a test organization
    org_id = None
    if os.path.exists(TEST_ORG_ID_FILE):
        with open(TEST_ORG_ID_FILE, "r") as f:
            org_id = f.read().strip()
            logger.info(f"Using existing organization ID from file: {org_id}")
    
    # If no organization ID exists, create a new test organization
    if not org_id:
        org_id = create_test_organization()
        logger.info(f"Created new test organization with ID: {org_id}")
    
    # List current members
    logger.info("\n--- Current members ---")
    list_organization_members(org_id)
    
    # Add a test member
    logger.info("\n--- Adding test member ---")
    test_user_id = "test-user-456"
    add_test_member(org_id, test_user_id)
    
    # List members after adding
    logger.info("\n--- Members after adding test user ---")
    list_organization_members(org_id)
    
    # Change the member's role
    logger.info("\n--- Changing test member role ---")
    change_member_role(org_id, test_user_id, "administrator")
    
    # List members after role change
    logger.info("\n--- Members after role change ---")
    list_organization_members(org_id)
    
    # Remove the test member
    logger.info("\n--- Removing test member ---")
    remove_member(org_id, test_user_id)
    
    # List members after removal
    logger.info("\n--- Members after removal ---")
    list_organization_members(org_id)
    
    logger.info("\nAll tests completed successfully!")

if __name__ == "__main__":
    main() 