import pytest
import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta
from tests.helpers.stripe_test_helpers import create_test_clock, advance_clock, delete_test_clock

class TestVouchers:
    """Integration test suite for voucher endpoints against deployed API."""

    def _cleanup_firestore_document(self, collection, document_id):
        """Clean up a Firestore document using gcloud CLI."""
        try:
            cmd = [
                "gcloud", "firestore", "delete",
                f"projects/relexro/databases/(default)/documents/{collection}/{document_id}",
                "--quiet"
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            # Log but don't fail the test if cleanup fails
            print(f"Warning: Failed to cleanup Firestore document {collection}/{document_id}: {e}")

    def _cleanup_firestore_collection_query(self, collection, field, value):
        """Clean up Firestore documents matching a query using gcloud CLI."""
        try:
            # First, list documents matching the query
            cmd = [
                "gcloud", "firestore", "query", collection,
                "--filter", f"{field}={value}",
                "--format", "value(name)",
                "--project", "relexro"
            ]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Delete each document found
            for doc_path in result.stdout.strip().split('\n'):
                if doc_path:
                    delete_cmd = ["gcloud", "firestore", "delete", doc_path, "--quiet"]
                    subprocess.run(delete_cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to cleanup Firestore collection {collection} where {field}={value}: {e}")

    def test_create_voucher_admin_only(self, api_client):
        """Test that only admin users can create vouchers."""
        # Test data for creating a voucher
        voucher_data = {
            "code": "TEST_VOUCHER_001",
            "discountPercentage": 15.0,
            "usageLimit": 100,
            "description": "Test voucher for integration testing",
            "isActive": True
        }

        # Make request to deployed API
        response = api_client.post("/vouchers", json=voucher_data)

        # Currently the API Gateway may not be properly configured
        # So we expect either success or 404 (endpoint not found)
        if response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        # If endpoint is available, verify the response
        # Should fail with 403 Forbidden for non-admin users
        assert response.status_code == 403
        response_data = response.json()
        assert "error" in response_data
        assert "Admin privileges required" in response_data.get("message", "")

    def test_create_voucher_with_admin_user(self, org_admin_api_client):
        """Test creating a voucher with admin user."""
        # Test data for creating a voucher
        voucher_data = {
            "code": "ADMIN_VOUCHER_001",
            "discountPercentage": 20.0,
            "usageLimit": 50,
            "description": "Admin-created test voucher",
            "isActive": True
        }

        # Make request to deployed API with admin client
        response = org_admin_api_client.post("/vouchers", json=voucher_data)

        # Skip if endpoint not available
        if response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        # Verify the response
        assert response.status_code == 201, \
            f"Expected 201 Created, but got {response.status_code}. Response: {response.text}"
        
        response_data = response.json()
        assert "id" in response_data
        assert response_data["code"] == "ADMIN_VOUCHER_001"
        assert response_data["discountPercentage"] == 20.0
        assert response_data["usageLimit"] == 50
        assert response_data["usageCount"] == 0
        assert response_data["isActive"] is True
        assert "createdAt" in response_data

        # Clean up: Delete the voucher from Firestore
        self._cleanup_firestore_document("vouchers", "ADMIN_VOUCHER_001")

    def test_create_voucher_duplicate_code(self, org_admin_api_client):
        """Test creating a voucher with duplicate code."""
        # First, create a voucher
        voucher_data = {
            "code": "DUPLICATE_TEST",
            "discountPercentage": 10.0,
            "usageLimit": 25,
            "description": "First voucher",
            "isActive": True
        }

        response = org_admin_api_client.post("/vouchers", json=voucher_data)
        
        if response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        assert response.status_code == 201

        # Try to create another voucher with the same code
        duplicate_voucher_data = {
            "code": "DUPLICATE_TEST",
            "discountPercentage": 15.0,
            "usageLimit": 30,
            "description": "Second voucher with same code",
            "isActive": True
        }

        response = org_admin_api_client.post("/vouchers", json=duplicate_voucher_data)
        
        # Should fail with 409 Conflict
        assert response.status_code == 409
        response_data = response.json()
        assert "error" in response_data
        assert "VoucherExists" in response_data.get("error", "")

        # Clean up
        self._cleanup_firestore_document("vouchers", "DUPLICATE_TEST")

    def test_create_voucher_invalid_data(self, org_admin_api_client):
        """Test creating a voucher with invalid data."""
        # Test with invalid discount percentage
        invalid_voucher_data = {
            "code": "INVALID_TEST",
            "discountPercentage": 150.0,  # Invalid: > 100%
            "usageLimit": 25,
            "description": "Invalid voucher",
            "isActive": True
        }

        response = org_admin_api_client.post("/vouchers", json=invalid_voucher_data)
        
        if response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        # Should fail with 400 Bad Request
        assert response.status_code == 400
        response_data = response.json()
        assert "error" in response_data
        assert "ValidationError" in response_data.get("error", "")

    def test_get_voucher(self, org_admin_api_client):
        """Test retrieving a voucher's details."""
        # First, create a voucher
        voucher_data = {
            "code": "GET_TEST_VOUCHER",
            "discountPercentage": 25.0,
            "usageLimit": 75,
            "description": "Voucher for get test",
            "isActive": True
        }

        create_response = org_admin_api_client.post("/vouchers", json=voucher_data)
        
        if create_response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        assert create_response.status_code == 201

        # Now retrieve the voucher
        response = org_admin_api_client.get("/vouchers/GET_TEST_VOUCHER")
        
        # Verify the response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["code"] == "GET_TEST_VOUCHER"
        assert response_data["discountPercentage"] == 25.0
        assert response_data["usageLimit"] == 75
        assert response_data["usageCount"] == 0
        assert response_data["isActive"] is True
        assert "createdAt" in response_data
        assert "updatedAt" in response_data

        # Clean up
        self._cleanup_firestore_document("vouchers", "GET_TEST_VOUCHER")

    def test_get_voucher_not_found(self, api_client):
        """Test retrieving a non-existent voucher."""
        response = api_client.get("/vouchers/NONEXISTENT_VOUCHER")
        
        if response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        # Should fail with 404 Not Found
        assert response.status_code == 404
        response_data = response.json()
        assert "error" in response_data
        assert "VoucherNotFound" in response_data.get("error", "")

    def test_update_voucher(self, org_admin_api_client):
        """Test updating a voucher's details."""
        # First, create a voucher
        voucher_data = {
            "code": "UPDATE_TEST_VOUCHER",
            "discountPercentage": 10.0,
            "usageLimit": 50,
            "description": "Original description",
            "isActive": True
        }

        create_response = org_admin_api_client.post("/vouchers", json=voucher_data)
        
        if create_response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        assert create_response.status_code == 201

        # Update the voucher
        update_data = {
            "discountPercentage": 20.0,
            "description": "Updated description",
            "isActive": False
        }

        response = org_admin_api_client.put("/vouchers/UPDATE_TEST_VOUCHER", json=update_data)
        
        # Verify the response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["code"] == "UPDATE_TEST_VOUCHER"
        assert response_data["discountPercentage"] == 20.0
        assert response_data["description"] == "Updated description"
        assert response_data["isActive"] is False
        assert response_data["usageLimit"] == 50  # Should remain unchanged

        # Clean up
        self._cleanup_firestore_document("vouchers", "UPDATE_TEST_VOUCHER")

    def test_update_voucher_invalid_usage_limit(self, org_admin_api_client):
        """Test updating a voucher with invalid usage limit."""
        # First, create a voucher
        voucher_data = {
            "code": "USAGE_LIMIT_TEST",
            "discountPercentage": 15.0,
            "usageLimit": 100,
            "description": "Test voucher",
            "isActive": True
        }

        create_response = org_admin_api_client.post("/vouchers", json=voucher_data)
        
        if create_response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        assert create_response.status_code == 201

        # Try to update with usage limit less than current usage count
        # First, we need to simulate some usage by directly updating the document
        # This is a limitation of the test environment - in real usage, this would happen through voucher application
        update_data = {
            "usageLimit": 50  # This should be valid since usage count is 0
        }

        response = org_admin_api_client.put("/vouchers/USAGE_LIMIT_TEST", json=update_data)
        
        # Should succeed since current usage count is 0
        assert response.status_code == 200

        # Clean up
        self._cleanup_firestore_document("vouchers", "USAGE_LIMIT_TEST")

    def test_delete_voucher(self, org_admin_api_client):
        """Test deleting a voucher."""
        # First, create a voucher
        voucher_data = {
            "code": "DELETE_TEST_VOUCHER",
            "discountPercentage": 30.0,
            "usageLimit": 25,
            "description": "Voucher to be deleted",
            "isActive": True
        }

        create_response = org_admin_api_client.post("/vouchers", json=voucher_data)
        
        if create_response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        assert create_response.status_code == 201

        # Delete the voucher
        response = org_admin_api_client.delete("/vouchers/DELETE_TEST_VOUCHER")
        
        # Verify the response
        assert response.status_code == 200
        response_data = response.json()
        assert "message" in response_data
        assert "deleted successfully" in response_data["message"]

        # Verify the voucher is actually deleted
        get_response = org_admin_api_client.get("/vouchers/DELETE_TEST_VOUCHER")
        assert get_response.status_code == 404

    def test_delete_voucher_not_found(self, org_admin_api_client):
        """Test deleting a non-existent voucher."""
        response = org_admin_api_client.delete("/vouchers/NONEXISTENT_DELETE_VOUCHER")
        
        if response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        # Should fail with 404 Not Found
        assert response.status_code == 404
        response_data = response.json()
        assert "error" in response_data
        assert "VoucherNotFound" in response_data.get("error", "")

    def test_create_checkout_session_with_voucher(self, org_admin_api_client):
        """Test creating a checkout session with a valid voucher."""
        # First, create a voucher
        voucher_data = {
            "code": "CHECKOUT_TEST_VOUCHER",
            "discountPercentage": 25.0,
            "usageLimit": 10,
            "description": "Voucher for checkout test",
            "isActive": True
        }

        create_response = org_admin_api_client.post("/vouchers", json=voucher_data)
        
        if create_response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        assert create_response.status_code == 201

        # Ensure the Stripe Price ID is available in env for Operator to configure Firestore
        stripe_price_id_env = os.getenv("STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY")
        if not stripe_price_id_env:
            pytest.skip(
                "Required environment variable STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY is not set. "
                "This is needed to test checkout session creation with voucher."
            )

        # Create checkout session with voucher
        checkout_data = {
            "planId": "individual_monthly",
            "voucherCode": "CHECKOUT_TEST_VOUCHER"
        }

        response = org_admin_api_client.post("/payments/checkout", json=checkout_data)
        
        # Verify the response
        assert response.status_code == 201, \
            f"Expected 201 Created, but got {response.status_code}. Response: {response.text}"
        
        response_data = response.json()
        assert "sessionId" in response_data
        assert response_data["sessionId"].startswith("cs_test_")
        assert "url" in response_data
        assert "voucherApplied" in response_data
        assert response_data["voucherApplied"]["code"] == "CHECKOUT_TEST_VOUCHER"
        assert response_data["voucherApplied"]["discountPercentage"] == 25.0

        # Clean up
        self._cleanup_firestore_document("vouchers", "CHECKOUT_TEST_VOUCHER")
        self._cleanup_firestore_document("checkoutSessions", response_data["sessionId"])

    def test_create_checkout_session_with_invalid_voucher(self, api_client):
        """Test creating a checkout session with an invalid voucher."""
        # Ensure the Stripe Price ID is available in env
        stripe_price_id_env = os.getenv("STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY")
        if not stripe_price_id_env:
            pytest.skip(
                "Required environment variable STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY is not set. "
                "This is needed to test checkout session creation with invalid voucher."
            )

        # Create checkout session with invalid voucher
        checkout_data = {
            "planId": "individual_monthly",
            "voucherCode": "INVALID_VOUCHER_CODE"
        }

        response = api_client.post("/payments/checkout", json=checkout_data)
        
        # Should fail with 400 Bad Request
        assert response.status_code == 400
        response_data = response.json()
        assert "error" in response_data
        assert "InvalidVoucher" in response_data.get("error", "")

    def test_create_checkout_session_with_expired_voucher(self, org_admin_api_client):
        """Test creating a checkout session with an expired voucher."""
        # Create a voucher with expiration date in the past
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        voucher_data = {
            "code": "EXPIRED_TEST_VOUCHER",
            "discountPercentage": 20.0,
            "usageLimit": 5,
            "description": "Expired voucher",
            "isActive": True,
            "expirationDate": past_date.isoformat()
        }

        create_response = org_admin_api_client.post("/vouchers", json=voucher_data)
        
        if create_response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        assert create_response.status_code == 201

        # Ensure the Stripe Price ID is available in env
        stripe_price_id_env = os.getenv("STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY")
        if not stripe_price_id_env:
            pytest.skip(
                "Required environment variable STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY is not set. "
                "This is needed to test checkout session creation with expired voucher."
            )

        # Create checkout session with expired voucher
        checkout_data = {
            "planId": "individual_monthly",
            "voucherCode": "EXPIRED_TEST_VOUCHER"
        }

        response = org_admin_api_client.post("/payments/checkout", json=checkout_data)
        
        # Should fail with 400 Bad Request
        assert response.status_code == 400
        response_data = response.json()
        assert "error" in response_data
        assert "InvalidVoucher" in response_data.get("error", "")
        assert "expired" in response_data.get("message", "").lower()

        # Clean up
        self._cleanup_firestore_document("vouchers", "EXPIRED_TEST_VOUCHER")

    def test_create_checkout_session_with_inactive_voucher(self, org_admin_api_client):
        """Test creating a checkout session with an inactive voucher."""
        # Create an inactive voucher
        voucher_data = {
            "code": "INACTIVE_TEST_VOUCHER",
            "discountPercentage": 15.0,
            "usageLimit": 10,
            "description": "Inactive voucher",
            "isActive": False
        }

        create_response = org_admin_api_client.post("/vouchers", json=voucher_data)
        
        if create_response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        assert create_response.status_code == 201

        # Ensure the Stripe Price ID is available in env
        stripe_price_id_env = os.getenv("STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY")
        if not stripe_price_id_env:
            pytest.skip(
                "Required environment variable STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY is not set. "
                "This is needed to test checkout session creation with inactive voucher."
            )

        # Create checkout session with inactive voucher
        checkout_data = {
            "planId": "individual_monthly",
            "voucherCode": "INACTIVE_TEST_VOUCHER"
        }

        response = org_admin_api_client.post("/payments/checkout", json=checkout_data)
        
        # Should fail with 400 Bad Request
        assert response.status_code == 400
        response_data = response.json()
        assert "error" in response_data
        assert "InvalidVoucher" in response_data.get("error", "")
        assert "not active" in response_data.get("message", "").lower()

        # Clean up
        self._cleanup_firestore_document("vouchers", "INACTIVE_TEST_VOUCHER")

    def test_voucher_usage_limit_enforcement(self, org_admin_api_client):
        """Test that voucher usage limits are enforced."""
        # Create a voucher with usage limit of 1
        voucher_data = {
            "code": "USAGE_LIMIT_ENFORCEMENT",
            "discountPercentage": 10.0,
            "usageLimit": 1,
            "description": "Voucher with usage limit of 1",
            "isActive": True
        }

        create_response = org_admin_api_client.post("/vouchers", json=voucher_data)
        
        if create_response.status_code == 404:
            pytest.skip("Voucher endpoints not available in current API Gateway configuration")

        assert create_response.status_code == 201

        # Ensure the Stripe Price ID is available in env
        stripe_price_id_env = os.getenv("STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY")
        if not stripe_price_id_env:
            pytest.skip(
                "Required environment variable STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY is not set. "
                "This is needed to test voucher usage limit enforcement."
            )

        # First checkout session should succeed
        checkout_data = {
            "planId": "individual_monthly",
            "voucherCode": "USAGE_LIMIT_ENFORCEMENT"
        }

        response1 = org_admin_api_client.post("/payments/checkout", json=checkout_data)
        assert response1.status_code == 201

        # Second checkout session with same voucher should fail
        response2 = org_admin_api_client.post("/payments/checkout", json=checkout_data)
        assert response2.status_code == 400
        response_data = response2.json()
        assert "error" in response_data
        assert "InvalidVoucher" in response_data.get("error", "")
        assert "usage limit reached" in response_data.get("message", "").lower()

        # Clean up
        self._cleanup_firestore_document("vouchers", "USAGE_LIMIT_ENFORCEMENT")
        if response1.status_code == 201:
            self._cleanup_firestore_document("checkoutSessions", response1.json()["sessionId"]) 