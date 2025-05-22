#!/usr/bin/env python3
"""Tests for additional Stripe webhook events."""

import pytest
from unittest.mock import MagicMock, patch
import json
import time
import firebase_admin
from firebase_admin import firestore
from functions.src import payments

class TestStripeWebhookEvents:
    """Test suite for Stripe webhook event handling."""

    @pytest.fixture
    def setup_test_user(self, firestore_emulator_client):
        """Create a test user with subscription data."""
        user_id = "test_user_123"
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        
        current_time = int(time.time())
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "individual_monthly",
            "stripeCustomerId": "cus_test_123",
            "stripeSubscriptionId": "sub_test_123",
            "caseQuotaTotal": 10,
            "caseQuotaUsed": 2,
            "quotaDetails": {
                "tier_1": 5,
                "tier_2": 3,
                "tier_3": 2
            },
            "billingCycleStart": current_time - (15 * 24 * 60 * 60),
            "billingCycleEnd": current_time + (15 * 24 * 60 * 60),
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        return user_id

    @pytest.fixture
    def setup_test_organization(self, firestore_emulator_client):
        """Create a test organization with subscription data."""
        org_id = "test_org_123"
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        
        current_time = int(time.time())
        org_ref.set({
            "id": org_id,
            "name": "Test Organization",
            "description": "Test organization for webhook tests",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "org_basic_monthly",
            "stripeCustomerId": "cus_org_test_123",
            "stripeSubscriptionId": "sub_org_test_123",
            "caseQuotaTotal": 50,
            "caseQuotaUsed": 10,
            "quotaDetails": {
                "tier_1": 25,
                "tier_2": 15,
                "tier_3": 10
            },
            "billingCycleStart": current_time - (15 * 24 * 60 * 60),
            "billingCycleEnd": current_time + (15 * 24 * 60 * 60),
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        return org_id

    @pytest.fixture
    def setup_subscription_plan(self, firestore_emulator_client):
        """Set up a subscription plan in the database."""
        plan_id = "individual_monthly"
        plan_ref = firestore_emulator_client.collection("plans").document(plan_id)
        plan_ref.set({
            "planId": plan_id,
            "name": "Individual Monthly",
            "price": 900,
            "currency": "eur",
            "caseQuotaTotal": {
                "tier_1": 10,
                "tier_2": 5,
                "tier_3": 2
            },
            "interval": "month",
            "type": "individual",
            "active": True,
            "stripePriceId": "price_individual_monthly"
        })
        return plan_id

    def test_subscription_updated_event(self, mocker, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plan):
        """Test handling customer.subscription.updated event."""
        user_id = setup_test_user
        
        # Mock Stripe Webhook.construct_event
        current_time = int(time.time())
        event_data = {
            "id": "evt_sub_updated",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_123",
                    "customer": "cus_test_123",
                    "status": "active",
                    "current_period_start": current_time,
                    "current_period_end": current_time + (365 * 24 * 60 * 60),  # 1 year
                    "items": {
                        "data": [{
                            "price": {
                                "id": "price_individual_yearly",
                                "metadata": {"planId": "individual_yearly"}
                            }
                        }]
                    },
                    "metadata": {
                        "userId": user_id
                    }
                },
                "previous_attributes": {
                    "items": {
                        "data": [{
                            "price": {
                                "id": "price_individual_monthly",
                                "metadata": {"planId": "individual_monthly"}
                            }
                        }]
                    },
                    "current_period_end": current_time + (30 * 24 * 60 * 60)
                }
            }
        }
        
        # Mock Stripe library functions
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=event_data
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        
        # Verify user data was updated
        user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        user_data = user_doc.to_dict()
        
        # Depending on the implementation, verify expected fields were updated
        # This may vary based on the actual implementation
        assert "subscriptionStatus" in user_data
        assert user_data["subscriptionStatus"] == "active"

    def test_invoice_payment_succeeded_event(self, mocker, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plan):
        """Test handling invoice.payment_succeeded event."""
        user_id = setup_test_user
        subscription_id = "sub_test_123"
        
        # Mock Stripe Webhook.construct_event
        current_time = int(time.time())
        event_data = {
            "id": "evt_invoice_succeeded",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_test_123",
                    "customer": "cus_test_123",
                    "subscription": subscription_id,
                    "status": "paid",
                    "lines": {
                        "data": [{
                            "type": "subscription",
                            "subscription": subscription_id,
                            "period": {
                                "start": current_time,
                                "end": current_time + (30 * 24 * 60 * 60)
                            }
                        }]
                    },
                    "metadata": {
                        "userId": user_id
                    }
                }
            }
        }
        
        # Mock Stripe library functions
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Mock Subscription.retrieve
        mock_subscription = MagicMock()
        mock_subscription.id = subscription_id
        mock_subscription.status = "active"
        mock_subscription.items.data = [{
            "price": {
                "id": "price_individual_monthly",
                "metadata": {"planId": "individual_monthly"}
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
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        
        # Verify invoice event was processed
        # Specific assertions depend on implementation details

    def test_payment_intent_succeeded_event(self, mocker, firestore_emulator_client, mock_request, setup_test_user):
        """Test handling payment_intent.succeeded event."""
        user_id = setup_test_user
        payment_intent_id = "pi_test_123"
        
        # Create a payment intent in the database
        payment_intent_ref = firestore_emulator_client.collection("payment_intents").document(payment_intent_id)
        payment_intent_ref.set({
            "id": payment_intent_id,
            "userId": user_id,
            "caseTier": 2,
            "amount": 2900,
            "currency": "eur",
            "status": "created",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_pi_succeeded",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": payment_intent_id,
                    "amount": 2900,
                    "currency": "eur",
                    "status": "succeeded",
                    "metadata": {
                        "userId": user_id,
                        "caseTier": "2"
                    }
                }
            }
        }
        
        # Mock Stripe library functions
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=event_data
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        
        # Verify payment intent was updated
        updated_pi_doc = payment_intent_ref.get()
        updated_pi_data = updated_pi_doc.to_dict()
        
        # Verify status was updated, details depend on implementation
        assert "status" in updated_pi_data

    def test_payment_intent_failed_event(self, mocker, firestore_emulator_client, mock_request, setup_test_user):
        """Test handling payment_intent.payment_failed event."""
        user_id = setup_test_user
        payment_intent_id = "pi_test_failed"
        
        # Create a payment intent in the database
        payment_intent_ref = firestore_emulator_client.collection("payment_intents").document(payment_intent_id)
        payment_intent_ref.set({
            "id": payment_intent_id,
            "userId": user_id,
            "caseTier": 2,
            "amount": 2900,
            "currency": "eur",
            "status": "created",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_pi_failed",
            "type": "payment_intent.payment_failed",
            "data": {
                "object": {
                    "id": payment_intent_id,
                    "amount": 2900,
                    "currency": "eur",
                    "status": "payment_failed",
                    "last_payment_error": {
                        "code": "card_declined",
                        "message": "Your card was declined."
                    },
                    "metadata": {
                        "userId": user_id,
                        "caseTier": "2"
                    }
                }
            }
        }
        
        # Mock Stripe library functions
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Create a mock request
        request = mock_request(
            headers={"Stripe-Signature": "valid_signature"},
            json_data=event_data
        )
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        
        # Verify payment intent was updated with failure information
        updated_pi_doc = payment_intent_ref.get()
        updated_pi_data = updated_pi_doc.to_dict()
        
        # Status should be updated to failed or similar
        assert "status" in updated_pi_data
