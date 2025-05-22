import pytest
from unittest.mock import MagicMock, patch
import json
import datetime
import time
import firebase_admin
from firebase_admin import firestore
from functions.src import payments, auth
import stripe

class TestStripeWebhook:
    """Test suite for Stripe webhook handler with Model B payment logic."""
    
    def test_handle_checkout_session_completed_subscription(self, mocker, firestore_emulator_client, mock_request):
        """Test handling checkout.session.completed event for a subscription."""
        # Create test user
        user_id = "test_user_123"
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "inactive",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create test plan
        plan_id = "personal_monthly"
        plan_ref = firestore_emulator_client.collection("plans").document(plan_id)
        plan_ref.set({
            "planId": plan_id,
            "name": "Personal Monthly",
            "price": 1999,
            "currency": "eur",
            "caseQuotaTotal": 10,
            "interval": "monthly",
            "type": "personal",
            "active": True,
            "stripePriceId": "price_test_123",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_test_123",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "mode": "subscription",
                    "client_reference_id": user_id,
                    "customer": "cus_test_123",
                    "subscription": "sub_test_123",
                    "metadata": {
                        "planId": plan_id
                    }
                }
            }
        }
        
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Mock Stripe Subscription.retrieve
        current_time = int(time.time())
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test_123"
        mock_subscription.customer = "cus_test_123"
        mock_subscription.status = "active"
        mock_subscription.current_period_start = current_time
        mock_subscription.current_period_end = current_time + (30 * 24 * 60 * 60)  # 30 days later
        mock_subscription.items.data = [{
            "price": {
                "id": "price_test_123",
                "metadata": {
                    "planId": plan_id
                }
            }
        }]
        
        stripe_sub_mock = mocker.patch('stripe.Subscription.retrieve')
        stripe_sub_mock.return_value = mock_subscription
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=event_data
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "checkout.session.completed" in response["message"]
        
        # Verify user subscription was updated
        updated_user_doc = user_ref.get()
        updated_user_data = updated_user_doc.to_dict()
        
        assert updated_user_data["subscriptionStatus"] == "active"
        assert updated_user_data["subscriptionPlanId"] == plan_id
        assert updated_user_data["stripeCustomerId"] == "cus_test_123"
        assert updated_user_data["stripeSubscriptionId"] == "sub_test_123"
        assert updated_user_data["caseQuotaTotal"] == 10
        assert updated_user_data["caseQuotaUsed"] == 0
        assert "billingCycleStart" in updated_user_data
        assert "billingCycleEnd" in updated_user_data
        
    def test_handle_checkout_session_completed_subscription_for_organization(self, mocker, firestore_emulator_client, mock_request):
        """Test handling checkout.session.completed event for an organization subscription."""
        # Create test user and organization
        user_id = "test_user_123"
        org_id = "test_org_123"
        
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        org_ref.set({
            "organizationId": org_id,
            "name": "Test Organization",
            "ownerId": user_id,
            "subscriptionStatus": "inactive",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create test plan
        plan_id = "business_pro_monthly"
        plan_ref = firestore_emulator_client.collection("plans").document(plan_id)
        plan_ref.set({
            "planId": plan_id,
            "name": "Business Pro Monthly",
            "price": 9999,
            "currency": "eur",
            "caseQuotaTotal": 50,
            "interval": "monthly",
            "type": "business",
            "active": True,
            "stripePriceId": "price_test_business_123",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_test_123",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "mode": "subscription",
                    "client_reference_id": user_id,
                    "customer": "cus_test_org_123",
                    "subscription": "sub_test_org_123",
                    "metadata": {
                        "planId": plan_id,
                        "organizationId": org_id
                    }
                }
            }
        }
        
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Mock Stripe Subscription.retrieve
        current_time = int(time.time())
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test_org_123"
        mock_subscription.customer = "cus_test_org_123"
        mock_subscription.status = "active"
        mock_subscription.current_period_start = current_time
        mock_subscription.current_period_end = current_time + (30 * 24 * 60 * 60)  # 30 days later
        mock_subscription.items.data = [{
            "price": {
                "id": "price_test_business_123",
                "metadata": {
                    "planId": plan_id
                }
            }
        }]
        
        stripe_sub_mock = mocker.patch('stripe.Subscription.retrieve')
        stripe_sub_mock.return_value = mock_subscription
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=event_data
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "checkout.session.completed" in response["message"]
        
        # Verify organization subscription was updated
        updated_org_doc = org_ref.get()
        updated_org_data = updated_org_doc.to_dict()
        
        assert updated_org_data["subscriptionStatus"] == "active"
        assert updated_org_data["subscriptionPlanId"] == plan_id
        assert updated_org_data["stripeCustomerId"] == "cus_test_org_123"
        assert updated_org_data["stripeSubscriptionId"] == "sub_test_org_123"
        assert updated_org_data["caseQuotaTotal"] == 50
        assert updated_org_data["caseQuotaUsed"] == 0
        assert "billingCycleStart" in updated_org_data
        assert "billingCycleEnd" in updated_org_data
    
    def test_handle_invoice_paid_event(self, mocker, firestore_emulator_client, mock_request):
        """Test handling invoice.paid event which should reset case quota."""
        # Create test user with active subscription
        user_id = "test_user_123"
        current_time = int(time.time())
        
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "personal_monthly",
            "stripeCustomerId": "cus_test_123",
            "stripeSubscriptionId": "sub_test_123",
            "caseQuotaTotal": 10,
            "caseQuotaUsed": 8,  # Used 8 out of 10 quota
            "billingCycleStart": datetime.datetime.fromtimestamp(current_time - (30 * 24 * 60 * 60)),  # 30 days ago
            "billingCycleEnd": datetime.datetime.fromtimestamp(current_time - (24 * 60 * 60)),  # 1 day ago (expired)
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create test plan
        plan_id = "personal_monthly"
        plan_ref = firestore_emulator_client.collection("plans").document(plan_id)
        plan_ref.set({
            "planId": plan_id,
            "name": "Personal Monthly",
            "price": 1999,
            "currency": "eur",
            "caseQuotaTotal": 10,
            "interval": "monthly",
            "type": "personal",
            "active": True,
            "stripePriceId": "price_test_123",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_test_invoice_123",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "id": "in_test_123",
                    "customer": "cus_test_123",
                    "subscription": "sub_test_123",
                    "billing_reason": "subscription_cycle",
                    "status": "paid",
                    "period_start": current_time,
                    "period_end": current_time + (30 * 24 * 60 * 60)  # 30 days later
                }
            }
        }
        
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Mock Stripe Subscription.retrieve
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test_123"
        mock_subscription.customer = "cus_test_123"
        mock_subscription.status = "active"
        mock_subscription.current_period_start = current_time
        mock_subscription.current_period_end = current_time + (30 * 24 * 60 * 60)  # 30 days later
        mock_subscription.items.data = [{
            "price": {
                "id": "price_test_123",
                "metadata": {
                    "planId": plan_id
                }
            }
        }]
        
        stripe_sub_mock = mocker.patch('stripe.Subscription.retrieve')
        stripe_sub_mock.return_value = mock_subscription
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=event_data
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "invoice.paid" in response["message"]
        
        # Verify user quota was reset for the new billing cycle
        updated_user_doc = user_ref.get()
        updated_user_data = updated_user_doc.to_dict()
        
        assert updated_user_data["subscriptionStatus"] == "active"
        assert updated_user_data["caseQuotaTotal"] == 10
        assert updated_user_data["caseQuotaUsed"] == 0  # Reset to 0
        
        # Verify billing cycle was updated
        if isinstance(updated_user_data["billingCycleStart"], datetime.datetime):
            start_timestamp = updated_user_data["billingCycleStart"].timestamp()
            end_timestamp = updated_user_data["billingCycleEnd"].timestamp()
        else:
            start_timestamp = updated_user_data["billingCycleStart"]
            end_timestamp = updated_user_data["billingCycleEnd"]
            
        assert abs(start_timestamp - current_time) < 10  # Within 10 seconds
        assert abs(end_timestamp - (current_time + (30 * 24 * 60 * 60))) < 10  # Within 10 seconds
    
    def test_handle_invoice_payment_failed_event(self, mocker, firestore_emulator_client, mock_request):
        """Test handling invoice.payment_failed event which should update subscription status."""
        # Create test user with active subscription
        user_id = "test_user_123"
        current_time = int(time.time())
        
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "personal_monthly",
            "stripeCustomerId": "cus_test_123",
            "stripeSubscriptionId": "sub_test_123",
            "caseQuotaTotal": 10,
            "caseQuotaUsed": 8,
            "billingCycleStart": datetime.datetime.fromtimestamp(current_time - (15 * 24 * 60 * 60)),  # 15 days ago
            "billingCycleEnd": datetime.datetime.fromtimestamp(current_time + (15 * 24 * 60 * 60)),  # 15 days from now
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_test_invoice_failed_123",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": "in_test_failed_123",
                    "customer": "cus_test_123",
                    "subscription": "sub_test_123",
                    "billing_reason": "subscription_cycle",
                    "status": "open",
                    "attempt_count": 3,
                    "next_payment_attempt": None  # No more retries
                }
            }
        }
        
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=event_data
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "invoice.payment_failed" in response["message"]
        
        # Verify user subscription status was updated
        updated_user_doc = user_ref.get()
        updated_user_data = updated_user_doc.to_dict()
        
        # Status should be set to inactive if payment failed and no more retries
        assert updated_user_data["subscriptionStatus"] == "inactive"
    
    def test_handle_customer_subscription_deleted_event(self, mocker, firestore_emulator_client, mock_request):
        """Test handling customer.subscription.deleted event which should mark subscription as inactive."""
        # Create test user with active subscription
        user_id = "test_user_123"
        current_time = int(time.time())
        
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "personal_monthly",
            "stripeCustomerId": "cus_test_123",
            "stripeSubscriptionId": "sub_test_123",
            "caseQuotaTotal": 10,
            "caseQuotaUsed": 5,
            "billingCycleStart": datetime.datetime.fromtimestamp(current_time - (15 * 24 * 60 * 60)),  # 15 days ago
            "billingCycleEnd": datetime.datetime.fromtimestamp(current_time + (15 * 24 * 60 * 60)),  # 15 days from now
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_test_sub_deleted_123",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test_123",
                    "customer": "cus_test_123",
                    "status": "canceled"
                }
            }
        }
        
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=event_data
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify the response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "customer.subscription.deleted" in response["message"]
        
        # Verify user subscription status was updated to inactive
        updated_user_doc = user_ref.get()
        updated_user_data = updated_user_doc.to_dict()
        
        assert updated_user_data["subscriptionStatus"] == "inactive"
    
    def test_handle_signature_verification_error(self, mocker, mock_request):
        """Test signature verification error in webhook handler."""
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
        assert status_code == 401
        assert "error" in response
        assert "Invalid signature" in response["message"]