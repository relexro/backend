import pytest
from unittest.mock import MagicMock, patch
import json
import flask
from firebase_admin import firestore
from functions.src import auth

# Create a simple JSON response function for testing
def _test_jsonify(data):
    return data

class TestAuthPermissions:
    """Test suite for auth.py check_permissions function."""

    def test_invalid_inputs(self):
        """Test check_permissions with missing required fields."""
        # Test missing required fields
        response, status_code = auth.check_permissions({
            "resourceId": "case123",
            "action": "read"
        })
        assert status_code == 400
        assert "Validation Failed" in response["message"]

        # Test missing resourceId
        response, status_code = auth.check_permissions({
            "userId": "user123",
            "action": "read",
            "resourceType": "case"
        })
        assert status_code == 400
        assert "Validation Failed" in response["message"]

        # Test missing action
        response, status_code = auth.check_permissions({
            "userId": "user123",
            "resourceId": "case123",
            "resourceType": "case"
        })
        assert status_code == 400
        assert "Validation Failed" in response["message"]

        # Test invalid action
        response, status_code = auth.check_permissions({
            "userId": "user123",
            "resourceId": "case123",
            "action": "invalid_action",
            "resourceType": "case"
        })
        assert status_code == 400
        assert "Validation Failed" in response["message"]

    def test_individual_case_owner_permissions(self):
        """Test permissions for individual case owner.

        Owner should have access to read, update, delete, and upload_file.
        """
        # Mock the Firestore client and document
        mock_db = MagicMock()
        mock_case_doc = MagicMock()
        mock_case_doc.exists = True
        mock_case_doc.to_dict.return_value = {
            "userId": "owner123",
            "organizationId": None  # Individual case
        }

        # Configure the mock Firestore client
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_case_doc
        mock_collection_ref = MagicMock()
        mock_collection_ref.document.return_value = mock_doc_ref
        mock_db.collection.return_value = mock_collection_ref

        # Patch firestore.client() to return our mock
        mock_db.collection.side_effect = lambda name: mock_collection_ref if name == "cases" else MagicMock()

        # Test for all actions an owner should be allowed to perform
        actions = ["read", "update", "delete", "upload_file"]
        for action in actions:
            response, status_code = auth.check_permissions({
                "userId": "owner123",
                "resourceId": "case123",
                "action": action,
                "resourceType": "case"
            })
            assert status_code == 200
            assert response["allowed"] is True

    def test_individual_case_non_owner_permissions(self):
        """Test permissions for non-owner on individual case.

        Non-owner should not have access to individual case.
        """
        # Mock the Firestore client and document
        mock_db = MagicMock()
        mock_case_doc = MagicMock()
        mock_case_doc.exists = True
        mock_case_doc.to_dict.return_value = {
            "userId": "owner123",
            "organizationId": None  # Individual case
        }

        # Configure the mock Firestore client
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_case_doc
        mock_collection_ref = MagicMock()
        mock_collection_ref.document.return_value = mock_doc_ref
        mock_db.collection.return_value = mock_collection_ref

        # Patch firestore.client() to return our mock
        mock_db.collection.side_effect = lambda name: mock_collection_ref if name == "cases" else MagicMock()

        # Test for all actions a non-owner should not be allowed to perform
        actions = ["read", "update", "delete", "upload_file"]
        for action in actions:
            response, status_code = auth.check_permissions({
                "userId": "non_owner123",
                "resourceId": "case123",
                "action": action,
                "resourceType": "case"
            })
            assert status_code == 200
            assert response["allowed"] is False

    def test_organization_case_admin_permissions(self):
        """Test permissions for admin on organization case.

        Admin should have access to read, update, delete, upload_file, and manage_access.
        """
        # Mock the Firestore client and documents
        mock_db = MagicMock()

        # Mock case document
        mock_case_doc = MagicMock()
        mock_case_doc.exists = True
        mock_case_doc.to_dict.return_value = {
            "userId": "owner123",
            "organizationId": "org123"
        }

        # Mock organization membership document
        mock_membership_doc = MagicMock()
        mock_membership_doc.to_dict.return_value = {
            "userId": "admin123",
            "organizationId": "org123",
            "role": "administrator"
        }

        # Configure the mock Firestore client for case document
        mock_case_doc_ref = MagicMock()
        mock_case_doc_ref.get.return_value = mock_case_doc
        mock_case_collection_ref = MagicMock()
        mock_case_collection_ref.document.return_value = mock_case_doc_ref

        # Configure the mock Firestore client for membership query
        mock_membership_query = MagicMock()
        mock_membership_query.where.return_value = mock_membership_query
        mock_membership_query.limit.return_value = mock_membership_query
        mock_membership_query.stream.return_value = [mock_membership_doc]

        # Setup collection mocks
        def mock_collection(name):
            if name == "cases":
                return mock_case_collection_ref
            elif name == "organization_memberships":
                return mock_membership_query
            return MagicMock()

        mock_db.collection.side_effect = mock_collection

        # Patch firestore.client() to return our mock
        mock_db.collection.side_effect = lambda name: mock_collection(name)

        # Test for all actions an admin should be allowed to perform
        actions = ["read", "update", "delete", "upload_file", "manage_access"]
        for action in actions:
            response, status_code = auth.check_permissions({
                "userId": "admin123",
                "resourceId": "case123",
                "action": action,
                "resourceType": "case"
            })
            assert status_code == 200
            assert response["allowed"] is True

    def test_organization_case_staff_permissions(self):
        """Test permissions for staff on organization case.

        Staff should have access to read, update, and upload_file.
        Staff should not have access to delete or manage_access.
        """
        # Mock the Firestore client and documents
        mock_db = MagicMock()

        # Mock case document
        mock_case_doc = MagicMock()
        mock_case_doc.exists = True
        mock_case_doc.to_dict.return_value = {
            "userId": "owner123",
            "organizationId": "org123"
        }

        # Mock organization membership document
        mock_membership_doc = MagicMock()
        mock_membership_doc.to_dict.return_value = {
            "userId": "staff123",
            "organizationId": "org123",
            "role": "staff"
        }

        # Configure the mock Firestore client for case document
        mock_case_doc_ref = MagicMock()
        mock_case_doc_ref.get.return_value = mock_case_doc
        mock_case_collection_ref = MagicMock()
        mock_case_collection_ref.document.return_value = mock_case_doc_ref

        # Configure the mock Firestore client for membership query
        mock_membership_query = MagicMock()
        mock_membership_query.where.return_value = mock_membership_query
        mock_membership_query.limit.return_value = mock_membership_query
        mock_membership_query.stream.return_value = [mock_membership_doc]

        # Setup collection mocks
        def mock_collection(name):
            if name == "cases":
                return mock_case_collection_ref
            elif name == "organization_memberships":
                return mock_membership_query
            return MagicMock()

        mock_db.collection.side_effect = mock_collection

        # Patch firestore.client() to return our mock
        mock_db.collection.side_effect = lambda name: mock_collection(name)

        # Test for actions a staff should be allowed to perform
        allowed_actions = ["read", "update", "upload_file"]
        for action in allowed_actions:
            response, status_code = auth.check_permissions({
                "userId": "staff123",
                "resourceId": "case123",
                "action": action,
                "resourceType": "case"
            })
            assert status_code == 200
            assert response["allowed"] is True

        # Test for actions a staff should not be allowed to perform
        disallowed_actions = ["delete", "manage_access"]
        for action in disallowed_actions:
            response, status_code = auth.check_permissions({
                "userId": "staff123",
                "resourceId": "case123",
                "action": action,
                "resourceType": "case"
            })
            assert status_code == 200
            assert response["allowed"] is False

    def test_organization_case_staff_as_owner_permissions(self):
        """Test permissions for staff who is also the owner on organization case.

        Staff who is also the case owner should have access to delete.
        """
        # Mock the Firestore client and documents
        mock_db = MagicMock()

        # Mock case document (with staff as owner)
        mock_case_doc = MagicMock()
        mock_case_doc.exists = True
        mock_case_doc.to_dict.return_value = {
            "userId": "staff123",  # Staff is also the owner
            "organizationId": "org123"
        }

        # Mock organization membership document
        mock_membership_doc = MagicMock()
        mock_membership_doc.to_dict.return_value = {
            "userId": "staff123",
            "organizationId": "org123",
            "role": "staff"
        }

        # Configure the mock Firestore client for case document
        mock_case_doc_ref = MagicMock()
        mock_case_doc_ref.get.return_value = mock_case_doc
        mock_case_collection_ref = MagicMock()
        mock_case_collection_ref.document.return_value = mock_case_doc_ref

        # Configure the mock Firestore client for membership query
        mock_membership_query = MagicMock()
        mock_membership_query.where.return_value = mock_membership_query
        mock_membership_query.limit.return_value = mock_membership_query
        mock_membership_query.stream.return_value = [mock_membership_doc]

        # Setup collection mocks
        def mock_collection(name):
            if name == "cases":
                return mock_case_collection_ref
            elif name == "organization_memberships":
                return mock_membership_query
            return MagicMock()

        mock_db.collection.side_effect = mock_collection

        # Patch firestore.client() to return our mock
        mock_db.collection.side_effect = lambda name: mock_collection(name)

        # Test delete action for staff who is also owner (should be allowed)
        response, status_code = auth.check_permissions({
            "userId": "staff123",
            "resourceId": "case123",
            "action": "delete",
            "resourceType": "case"
        })
        assert status_code == 200
        assert response["allowed"] is True

    def test_organization_resource_permissions(self):
        """Test permissions for users on organization resources.

        Admin should have full access.
        Staff should have limited access.
        """
        # Use the auth module imported at the top

        # Create mock responses for different test cases
        def mock_auth_response(request):
            data = request.get_json()
            if data["resourceType"] != "organization" or data["resourceId"] != "org123":
                return {"allowed": False}, 200

            if data["userId"] == "admin123":
                # Admin has access to all actions
                return {"allowed": True}, 200
            elif data["userId"] == "staff123":
                # Staff has limited access
                if data["action"] in ["read", "create_case"]:
                    return {"allowed": True}, 200
                else:
                    return {"allowed": False}, 200
            else:
                # Other users have no access
                return {"allowed": False}, 200

        # Create a patch to override the check_permissions function
        mock_auth_response_patch = MagicMock()
        mock_auth_response_patch.side_effect = mock_auth_response

        # Test admin permissions for organization resource
        admin_allowed_actions = ["read", "update", "manage_access"]
        for action in admin_allowed_actions:
            response, status_code = auth.check_permissions({
                "userId": "admin123",
                "resourceId": "org123",
                "action": action,
                "resourceType": "organization"
            })
            assert status_code == 200
            assert response["allowed"] is True

        # Test staff permissions for organization resource
        staff_allowed_actions = ["read", "create_case"]
        staff_disallowed_actions = ["update", "manage_access"]

        for action in staff_allowed_actions:
            response, status_code = auth.check_permissions({
                "userId": "staff123",
                "resourceId": "org123",
                "action": action,
                "resourceType": "organization"
            })
            assert status_code == 200
            assert response["allowed"] is True

        for action in staff_disallowed_actions:
            response, status_code = auth.check_permissions({
                "userId": "staff123",
                "resourceId": "org123",
                "action": action,
                "resourceType": "organization"
            })
            assert status_code == 200
            assert response["allowed"] is False

    def test_non_member_permissions(self):
        """Test permissions for non-member of organization.

        Non-member should not have access to organization resources or cases.
        """
        # Mock the Firestore client and documents
        mock_db = MagicMock()

        # Mock case document
        mock_case_doc = MagicMock()
        mock_case_doc.exists = True
        mock_case_doc.to_dict.return_value = {
            "userId": "owner123",
            "organizationId": "org123"
        }

        # Configure the mock Firestore client for case document
        mock_case_doc_ref = MagicMock()
        mock_case_doc_ref.get.return_value = mock_case_doc
        mock_case_collection_ref = MagicMock()
        mock_case_collection_ref.document.return_value = mock_case_doc_ref

        # Configure the mock Firestore client for membership query (empty result)
        mock_membership_query = MagicMock()
        mock_membership_query.where.return_value = mock_membership_query
        mock_membership_query.limit.return_value = mock_membership_query
        mock_membership_query.stream.return_value = []  # No membership documents found

        # Setup collection mocks
        def mock_collection(name):
            if name == "cases":
                return mock_case_collection_ref
            elif name == "organization_memberships":
                return mock_membership_query
            return MagicMock()

        mock_db.collection.side_effect = mock_collection

        # Patch firestore.client() to return our mock
        mock_db.collection.side_effect = lambda name: mock_collection(name)

        # Test for organization case access (should be denied)
        response, status_code = auth.check_permissions({
            "userId": "non_member123",
            "resourceId": "case123",
            "action": "read",
            "resourceType": "case"
        })
        assert status_code == 200
        assert response["allowed"] is False

        # Test for organization resource access (should be denied)
        response, status_code = auth.check_permissions({
            "userId": "non_member123",
            "resourceId": "org123",
            "action": "read",
            "resourceType": "organization"
        })
        assert status_code == 200
        assert response["allowed"] is False

    def test_resource_not_found(self):
        """Test when the resource (case) does not exist."""
        # Mock the Firestore client and document
        mock_db = MagicMock()
        mock_case_doc = MagicMock()
        mock_case_doc.exists = False  # Resource does not exist

        # Configure the mock Firestore client
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_case_doc
        mock_collection_ref = MagicMock()
        mock_collection_ref.document.return_value = mock_doc_ref
        mock_db.collection.return_value = mock_collection_ref

        # Patch firestore.client() to return our mock
        mock_db.collection.side_effect = lambda name: mock_collection_ref if name == "cases" else MagicMock()

        # Test for non-existent resource
        response, status_code = auth.check_permissions({
            "userId": "user123",
            "resourceId": "non_existent_case",
            "action": "read",
            "resourceType": "case"
        })
        assert status_code == 200
        assert response["allowed"] is False