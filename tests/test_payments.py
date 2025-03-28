import pytest
from unittest.mock import MagicMock, patch
import json
import firebase_admin
from firebase_admin import firestore
from functions.src import payments, auth

class TestPayments:
    """Test suite for payment functions."""
    
    def test_create_payment_intent(self, mocker, firestore_emulator_client, mock_request):
        """Test create_payment_intent function."""
        user_id = "test_user_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock Stripe PaymentIntent.create
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = "pi_test_123"
        mock_payment_intent.client_secret = "pi_test_secret_123"
        mock_payment_intent.amount = 900  # $9.00
        mock_payment_intent.currency = "usd"
        
        stripe_mock = mocker.patch('stripe.PaymentIntent.create')
        stripe_mock.return_value = mock_payment_intent
        
        # Create a mock request for caseTier 1
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "caseTier": 1
            }
        )
        
        # Call the function
        response, status_code = payments.create_payment_intent(request)
        
        # Verify the response
        assert status_code == 201
        assert "paymentIntentId" in response
        assert response["paymentIntentId"] == "pi_test_123"
        assert "clientSecret" in response
        assert response["clientSecret"] == "pi_test_secret_123"
        
        # Verify the payment intent was created in Firestore
        payment_intent_doc = firestore_emulator_client.collection("payment_intents").document("pi_test_123").get()
        assert payment_intent_doc.exists
        
        payment_intent_data = payment_intent_doc.to_dict()
        assert payment_intent_data["userId"] == user_id
        assert payment_intent_data["amount"] == 900
        assert payment_intent_data["currency"] == "usd"
        assert payment_intent_data["status"] == "created"
        assert "createdAt" in payment_intent_data
        
        # Verify Stripe was called with the right parameters
        stripe_mock.assert_called_once()
        call_args = stripe_mock.call_args[1]  # Get keyword arguments
        assert call_args["amount"] == 900  # $9.00
        assert call_args["currency"] == "usd"
        assert call_args["metadata"]["userId"] == user_id
        assert call_args["metadata"]["caseTier"] == "1"
    
    def test_create_payment_intent_invalid_tier(self, mocker, mock_request):
        """Test create_payment_intent with invalid case tier."""
        user_id = "test_user_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Create a mock request with invalid tier
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "caseTier": 99  # Invalid tier
            }
        )
        
        # Call the function
        response, status_code = payments.create_payment_intent(request)
        
        # Verify the response indicates invalid tier
        assert status_code == 400
        assert "error" in response
        assert "Invalid case tier" in response["message"]
    
    def test_create_checkout_session(self, mocker, firestore_emulator_client, mock_request):
        """Test create_checkout_session function."""
        user_id = "test_user_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock Stripe Checkout Session create
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/test_session"
        
        stripe_mock = mocker.patch('stripe.checkout.Session.create')
        stripe_mock.return_value = mock_session
        
        # Create a mock request for personal monthly subscription
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "planId": "personal_monthly"
            }
        )
        
        # Call the function
        response, status_code = payments.create_checkout_session(request)
        
        # Verify the response
        assert status_code == 201
        assert "sessionId" in response
        assert response["sessionId"] == "cs_test_123"
        assert "url" in response
        assert response["url"] == "https://checkout.stripe.com/test_session"
        
        # Verify the checkout session was created in Firestore
        checkout_session_doc = firestore_emulator_client.collection("checkout_sessions").document("cs_test_123").get()
        assert checkout_session_doc.exists
        
        checkout_session_data = checkout_session_doc.to_dict()
        assert checkout_session_data["userId"] == user_id
        assert checkout_session_data["planId"] == "personal_monthly"
        assert checkout_session_data["status"] == "created"
        assert "createdAt" in checkout_session_data
        
        # Verify Stripe was called with the right parameters
        stripe_mock.assert_called_once()
        call_args = stripe_mock.call_args[1]  # Get keyword arguments
        assert call_args["mode"] == "subscription"
        assert call_args["success_url"] is not None
        assert call_args["cancel_url"] is not None
        assert "client_reference_id" in call_args
        assert call_args["client_reference_id"] == user_id
    
    def test_create_checkout_session_invalid_plan(self, mocker, mock_request):
        """Test create_checkout_session with invalid plan ID."""
        user_id = "test_user_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Create a mock request with invalid plan
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "planId": "invalid_plan"  # Invalid plan
            }
        )
        
        # Call the function
        response, status_code = payments.create_checkout_session(request)
        
        # Verify the response indicates invalid plan
        assert status_code == 400
        assert "error" in response
        assert "Invalid plan ID" in response["message"]
    
    def test_handle_stripe_webhook_signature_verification_error(self, mocker, mock_request):
        """Test handle_stripe_webhook with signature verification error."""
        # Mock Stripe Webhook.construct_event to raise SignatureVerificationError
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.side_effect = stripe.error.SignatureVerificationError("Invalid signature", "sig_123")
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "invalid_signature"},
            json_data={"type": "checkout.session.completed"}
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response indicates signature verification error
        assert status_code == 400
        assert "error" in response
        assert "Invalid signature" in response["message"]
    
    def test_handle_stripe_webhook_checkout_session_completed_subscription(self, mocker, firestore_emulator_client, mock_request):
        """Test handle_stripe_webhook with checkout.session.completed event for subscription."""
        # Create test organization
        org_id = "test_org_123"
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        org_ref.set({
            "organizationId": org_id,
            "name": "Test Organization",
            "description": "A test organization",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create a mock webhook event for checkout.session.completed
        checkout_session = {
            "id": "cs_test_123",
            "client_reference_id": org_id,
            "metadata": {
                "organizationId": org_id,
                "planId": "business_monthly"
            },
            "subscription": "sub_test_123",
            "mode": "subscription"
        }
        
        webhook_event = {
            "id": "evt_test_123",
            "type": "checkout.session.completed",
            "data": {
                "object": checkout_session
            }
        }
        
        # Mock Stripe Webhook.construct_event to return our mock event
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = webhook_event
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=webhook_event
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response
        assert status_code == 200
        assert "received" in response
        assert response["received"] is True
        
        # Verify the organization was updated in Firestore
        org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        org_data = org_doc.to_dict()
        assert org_data["subscriptionStatus"] == "active"
        assert org_data["stripeSubscriptionId"] == "sub_test_123"
        assert org_data["stripePlanId"] == "business_monthly"
    
    def test_handle_stripe_webhook_checkout_session_completed_payment(self, mocker, firestore_emulator_client, mock_request):
        """Test handle_stripe_webhook with checkout.session.completed event for one-time payment."""
        # Create test case
        case_id = "test_case_123"
        case_ref = firestore_emulator_client.collection("cases").document(case_id)
        case_ref.set({
            "caseId": case_id,
            "userId": "test_user_123",
            "title": "Test Case",
            "description": "A test case",
            "status": "open",
            "paymentStatus": "pending",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create a mock webhook event for checkout.session.completed
        checkout_session = {
            "id": "cs_test_123",
            "client_reference_id": "test_user_123",
            "metadata": {
                "caseId": case_id,
                "caseTier": "1"
            },
            "mode": "payment"
        }
        
        webhook_event = {
            "id": "evt_test_123",
            "type": "checkout.session.completed",
            "data": {
                "object": checkout_session
            }
        }
        
        # Mock Stripe Webhook.construct_event to return our mock event
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = webhook_event
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=webhook_event
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response
        assert status_code == 200
        assert "received" in response
        assert response["received"] is True
        
        # Verify the case was updated in Firestore
        case_doc = firestore_emulator_client.collection("cases").document(case_id).get()
        case_data = case_doc.to_dict()
        assert case_data["paymentStatus"] == "paid"
    
    def test_handle_stripe_webhook_invoice_payment_failed(self, mocker, firestore_emulator_client, mock_request):
        """Test handle_stripe_webhook with invoice.payment_failed event."""
        # Create test organization with subscription
        org_id = "test_org_456"
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        org_ref.set({
            "organizationId": org_id,
            "name": "Test Organization",
            "description": "A test organization",
            "subscriptionStatus": "active",
            "stripeSubscriptionId": "sub_test_456",
            "stripePlanId": "business_monthly",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create a mock webhook event for invoice.payment_failed
        invoice = {
            "id": "in_test_123",
            "subscription": "sub_test_456",
            "customer": "cus_test_123"
        }
        
        webhook_event = {
            "id": "evt_test_456",
            "type": "invoice.payment_failed",
            "data": {
                "object": invoice
            }
        }
        
        # Mock Stripe Webhook.construct_event to return our mock event
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = webhook_event
        
        # Mock Stripe Subscription.retrieve to return subscription with organization metadata
        mock_subscription = MagicMock()
        mock_subscription.metadata = {"organizationId": org_id}
        
        stripe_subscription_mock = mocker.patch('stripe.Subscription.retrieve')
        stripe_subscription_mock.return_value = mock_subscription
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=webhook_event
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response
        assert status_code == 200
        assert "received" in response
        assert response["received"] is True
        
        # Verify the organization was updated in Firestore
        org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        org_data = org_doc.to_dict()
        assert org_data["subscriptionStatus"] == "past_due"
    
    def test_handle_stripe_webhook_customer_subscription_deleted(self, mocker, firestore_emulator_client, mock_request):
        """Test handle_stripe_webhook with customer.subscription.deleted event."""
        # Create test organization with subscription
        org_id = "test_org_789"
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        org_ref.set({
            "organizationId": org_id,
            "name": "Test Organization",
            "description": "A test organization",
            "subscriptionStatus": "active",
            "stripeSubscriptionId": "sub_test_789",
            "stripePlanId": "business_monthly",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create a mock webhook event for customer.subscription.deleted
        subscription = {
            "id": "sub_test_789",
            "metadata": {
                "organizationId": org_id
            },
            "status": "canceled"
        }
        
        webhook_event = {
            "id": "evt_test_789",
            "type": "customer.subscription.deleted",
            "data": {
                "object": subscription
            }
        }
        
        # Mock Stripe Webhook.construct_event to return our mock event
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = webhook_event
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=webhook_event
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response
        assert status_code == 200
        assert "received" in response
        assert response["received"] is True
        
        # Verify the organization was updated in Firestore
        org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        org_data = org_doc.to_dict()
        assert org_data["subscriptionStatus"] == "canceled"
    
    def test_handle_stripe_webhook_unhandled_event(self, mocker, mock_request):
        """Test handle_stripe_webhook with unhandled event type."""
        # Create a mock webhook event for an unhandled event type
        webhook_event = {
            "id": "evt_test_unhandled",
            "type": "unhandled.event.type",
            "data": {
                "object": {}
            }
        }
        
        # Mock Stripe Webhook.construct_event to return our mock event
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = webhook_event
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=webhook_event
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response is still 200 (as per Stripe best practice)
        assert status_code == 200
        assert "received" in response
        assert response["received"] is True
    
    def test_cancel_subscription(self, mocker, firestore_emulator_client, mock_request):
        """Test cancel_subscription function."""
        # Create test organization with subscription
        org_id = "test_org_cancel"
        user_id = "admin_user_123"
        
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        org_ref.set({
            "organizationId": org_id,
            "name": "Test Organization",
            "description": "A test organization",
            "subscriptionStatus": "active",
            "stripeSubscriptionId": "sub_test_cancel",
            "stripePlanId": "business_monthly",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create admin membership
        admin_membership_ref = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{user_id}")
        admin_membership_ref.set({
            "organizationId": org_id,
            "userId": user_id,
            "role": "administrator",
            "addedAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock auth to be the admin
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock check_permissions to return allowed=True for admin
        permissions_mock = mocker.patch('functions.src.auth.check_permissions')
        permissions_mock.return_value = ({"allowed": True}, 200)
        
        # Mock Stripe Subscription.delete
        stripe_mock = mocker.patch('stripe.Subscription.delete')
        
        # Create a mock request
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "subscriptionId": "sub_test_cancel"
            }
        )
        
        # Call the function
        response, status_code = payments.cancel_subscription(request)
        
        # Verify the response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        
        # Verify Stripe was called to delete the subscription
        stripe_mock.assert_called_once_with("sub_test_cancel")
    
    def test_cancel_subscription_permission_denied(self, mocker, firestore_emulator_client, mock_request):
        """Test cancel_subscription with permission denied."""
        # Create test organization with subscription
        org_id = "test_org_deny"
        user_id = "staff_user_123"
        
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        org_ref.set({
            "organizationId": org_id,
            "name": "Test Organization",
            "description": "A test organization",
            "subscriptionStatus": "active",
            "stripeSubscriptionId": "sub_test_deny",
            "stripePlanId": "business_monthly",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create staff membership
        staff_membership_ref = firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{user_id}")
        staff_membership_ref.set({
            "organizationId": org_id,
            "userId": user_id,
            "role": "staff",  # Not an admin
            "addedAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock auth to be the staff
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock check_permissions to return allowed=False for staff
        permissions_mock = mocker.patch('functions.src.auth.check_permissions')
        permissions_mock.return_value = ({"allowed": False}, 200)
        
        # Create a mock request
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "organizationId": org_id,
                "subscriptionId": "sub_test_deny"
            }
        )
        
        # Call the function
        response, status_code = payments.cancel_subscription(request)
        
        # Verify the response indicates permission denied
        assert status_code == 403
        assert "error" in response
        assert "Permission denied" in response["message"] 