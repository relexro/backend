#!/usr/bin/env python3
"""
Tests for additional Stripe webhook events:
- customer.subscription.updated
- invoice.payment_succeeded
- invoice.paid
- payment_intent.payment_failed
- payment_intent.canceled
"""

import json
import logging
import os
import pytest
import uuid
import time
from unittest.mock import MagicMock, patch
import firebase_admin
from firebase_admin import firestore

from functions.src import payments

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestStripeAdditionalWebhooks:
    """Test suite for additional Stripe webhook event handling."""

    @pytest.fixture
    def setup_test_user(self, firestore_emulator_client):
        """Create a test user with subscription data."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
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
            "billingCycleStart": current_time - (15 * 24 * 60 * 60),  # 15 days ago
            "billingCycleEnd": current_time + (15 * 24 * 60 * 60),    # 15 days in future
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        return user_id

    @pytest.fixture
    def setup_test_organization(self, firestore_emulator_client):
        """Create a test organization with subscription data."""
        org_id = f"test_org_{uuid.uuid4().hex[:8]}"
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
    def setup_subscription_plans(self, firestore_emulator_client):
        """Set up subscription plans in the database."""
        plans = {
            "individual_monthly": {
                "planId": "individual_monthly",
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
            },
            "individual_yearly": {
                "planId": "individual_yearly",
                "name": "Individual Yearly",
                "price": 8640,
                "currency": "eur",
                "caseQuotaTotal": {
                    "tier_1": 120,
                    "tier_2": 60,
                    "tier_3": 24
                },
                "interval": "year",
                "type": "individual",
                "active": True,
                "stripePriceId": "price_individual_yearly"
            },
            "org_basic_monthly": {
                "planId": "org_basic_monthly",
                "name": "Organization Basic Monthly",
                "price": 20000,
                "currency": "eur",
                "caseQuotaTotal": {
                    "tier_1": 50,
                    "tier_2": 25,
                    "tier_3": 10
                },
                "interval": "month",
                "type": "organization",
                "active": True,
                "stripePriceId": "price_org_basic_monthly",
                "maxMembers": 5
            },
            "org_pro_monthly": {
                "planId": "org_pro_monthly",
                "name": "Organization Pro Monthly",
                "price": 50000,
                "currency": "eur",
                "caseQuotaTotal": {
                    "tier_1": 150,
                    "tier_2": 75,
                    "tier_3": 25
                },
                "interval": "month",
                "type": "organization",
                "active": True,
                "stripePriceId": "price_org_pro_monthly",
                "maxMembers": 20
            }
        }
        
        for plan_id, plan_data in plans.items():
            firestore_emulator_client.collection("plans").document(plan_id).set(plan_data)
            
        return plans

    def test_subscription_updated_event(self, mocker, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plans):
        """Test handling customer.subscription.updated event (plan upgrade)."""
        user_id = setup_test_user
        old_plan_id = "individual_monthly"
        new_plan_id = "individual_yearly"
        
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
                                "metadata": {"planId": new_plan_id}
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
                                "metadata": {"planId": old_plan_id}
                            }
                        }]
                    },
                    "current_period_end": current_time + (30 * 24 * 60 * 60)  # previous was monthly
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
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "subscription updated" in response["message"].lower()
        
        # Verify user subscription was updated
        user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        user_data = user_doc.to_dict()
        
        assert user_data["subscriptionStatus"] == "active"
        assert user_data["subscriptionPlanId"] == new_plan_id
        
        # Verify quota was updated to yearly plan quota
        yearly_quota = setup_subscription_plans[new_plan_id]["caseQuotaTotal"]
        assert user_data["quotaDetails"]["tier_1"] == yearly_quota["tier_1"]
        assert user_data["quotaDetails"]["tier_2"] == yearly_quota["tier_2"]
        assert user_data["quotaDetails"]["tier_3"] == yearly_quota["tier_3"]
        assert user_data["caseQuotaTotal"] == sum(yearly_quota.values())
        
        # Billing cycle should be updated to yearly
        assert user_data["billingCycleEnd"] > current_time + (30 * 24 * 60 * 60)

    def test_subscription_updated_event_for_organization(self, mocker, firestore_emulator_client, mock_request, setup_test_organization, setup_subscription_plans):
        """Test handling customer.subscription.updated event for an organization (plan upgrade)."""
        org_id = setup_test_organization
        old_plan_id = "org_basic_monthly"
        new_plan_id = "org_pro_monthly"
        
        # Mock Stripe Webhook.construct_event
        current_time = int(time.time())
        event_data = {
            "id": "evt_org_sub_updated",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_org_test_123",
                    "customer": "cus_org_test_123",
                    "status": "active",
                    "current_period_start": current_time,
                    "current_period_end": current_time + (30 * 24 * 60 * 60),
                    "items": {
                        "data": [{
                            "price": {
                                "id": "price_org_pro_monthly",
                                "metadata": {"planId": new_plan_id}
                            }
                        }]
                    },
                    "metadata": {
                        "organizationId": org_id
                    }
                },
                "previous_attributes": {
                    "items": {
                        "data": [{
                            "price": {
                                "id": "price_org_basic_monthly",
                                "metadata": {"planId": old_plan_id}
                            }
                        }]
                    }
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
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "subscription updated" in response["message"].lower()
        
        # Verify organization subscription was updated
        org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        org_data = org_doc.to_dict()
        
        assert org_data["subscriptionStatus"] == "active"
        assert org_data["subscriptionPlanId"] == new_plan_id
        
        # Verify quota was updated to pro plan quota
        pro_quota = setup_subscription_plans[new_plan_id]["caseQuotaTotal"]
        assert org_data["quotaDetails"]["tier_1"] == pro_quota["tier_1"]
        assert org_data["quotaDetails"]["tier_2"] == pro_quota["tier_2"]
        assert org_data["quotaDetails"]["tier_3"] == pro_quota["tier_3"]
        assert org_data["caseQuotaTotal"] == sum(pro_quota.values())

    def test_invoice_payment_succeeded_event(self, mocker, firestore_emulator_client, mock_request, setup_test_user):
        """Test handling invoice.payment_succeeded event (subscription renewal)."""
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
        
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Mock Stripe Subscription.retrieve to return plan info
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
        
        # Get the user's current quota usage
        user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        original_quota_used = user_doc.to_dict()["caseQuotaUsed"]
        
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
        assert "invoice payment succeeded" in response["message"].lower()
        
        # Verify billing cycle was updated
        updated_user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        updated_user_data = updated_user_doc.to_dict()
        
        assert updated_user_data["billingCycleStart"] == current_time
        assert updated_user_data["billingCycleEnd"] == current_time + (30 * 24 * 60 * 60)
        
        # Quota should be reset on renewal
        plan_quota = {
            "tier_1": 10,
            "tier_2": 5,
            "tier_3": 2
        }
        assert updated_user_data["quotaDetails"]["tier_1"] == plan_quota["tier_1"]
        assert updated_user_data["quotaDetails"]["tier_2"] == plan_quota["tier_2"]
        assert updated_user_data["quotaDetails"]["tier_3"] == plan_quota["tier_3"]
        assert updated_user_data["caseQuotaTotal"] == sum(plan_quota.values())
        assert updated_user_data["caseQuotaUsed"] == 0  # Should be reset

    def test_invoice_paid_event(self, mocker, firestore_emulator_client, mock_request, setup_test_organization):
        """Test handling invoice.paid event for an organization."""
        org_id = setup_test_organization
        subscription_id = "sub_org_test_123"
        
        # Mock Stripe Webhook.construct_event
        current_time = int(time.time())
        event_data = {
            "id": "evt_invoice_paid",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "id": "in_org_test_123",
                    "customer": "cus_org_test_123",
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
                        "organizationId": org_id
                    }
                }
            }
        }
        
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Mock Stripe Subscription.retrieve to return plan info
        mock_subscription = MagicMock()
        mock_subscription.id = subscription_id
        mock_subscription.status = "active"
        mock_subscription.items.data = [{
            "price": {
                "id": "price_org_basic_monthly",
                "metadata": {"planId": "org_basic_monthly"}
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
        assert "invoice paid" in response["message"].lower()
        
        # Verify billing cycle was updated for organization
        updated_org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        updated_org_data = updated_org_doc.to_dict()
        
        assert updated_org_data["billingCycleStart"] == current_time
        assert updated_org_data["billingCycleEnd"] == current_time + (30 * 24 * 60 * 60)
        
        # Quota should be reset on renewal
        plan_quota = {
            "tier_1": 50,
            "tier_2": 25,
            "tier_3": 10
        }
        assert updated_org_data["quotaDetails"]["tier_1"] == plan_quota["tier_1"]
        assert updated_org_data["quotaDetails"]["tier_2"] == plan_quota["tier_2"]
        assert updated_org_data["quotaDetails"]["tier_3"] == plan_quota["tier_3"]
        assert updated_org_data["caseQuotaTotal"] == sum(plan_quota.values())
        assert updated_org_data["caseQuotaUsed"] == 0  # Should be reset

    def test_payment_intent_payment_failed(self, mocker, firestore_emulator_client, mock_request, setup_test_user):
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
        assert "payment failed" in response["message"].lower()
        
        # Verify payment intent was updated
        updated_pi_doc = payment_intent_ref.get()
        updated_pi_data = updated_pi_doc.to_dict()
        assert updated_pi_data["status"] == "payment_failed"
        assert "errorCode" in updated_pi_data
        assert updated_pi_data["errorCode"] == "card_declined"
        assert "errorMessage" in updated_pi_data
        assert "card was declined" in updated_pi_data["errorMessage"]

    def test_payment_intent_canceled(self, mocker, firestore_emulator_client, mock_request, setup_test_user):
        """Test handling payment_intent.canceled event."""
        user_id = setup_test_user
        payment_intent_id = "pi_test_canceled"
        
        # Create a payment intent in the database
        payment_intent_ref = firestore_emulator_client.collection("payment_intents").document(payment_intent_id)
        payment_intent_ref.set({
            "id": payment_intent_id,
            "userId": user_id,
            "caseTier": 1,
            "amount": 900,
            "currency": "eur",
            "status": "created",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_pi_canceled",
            "type": "payment_intent.canceled",
            "data": {
                "object": {
                    "id": payment_intent_id,
                    "amount": 900,
                    "currency": "eur",
                    "status": "canceled",
                    "cancellation_reason": "requested_by_customer",
                    "metadata": {
                        "userId": user_id,
                        "caseTier": "1"
                    }
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
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "payment intent canceled" in response["message"].lower()
        
        # Verify payment intent was updated
        updated_pi_doc = payment_intent_ref.get()
        updated_pi_data = updated_pi_doc.to_dict()
        assert updated_pi_data["status"] == "canceled"
        assert "cancellationReason" in updated_pi_data
        assert updated_pi_data["cancellationReason"] == "requested_by_customer"

    def test_payment_intent_canceled_for_organization(self, mocker, firestore_emulator_client, mock_request, setup_test_organization):
        """Test handling payment_intent.canceled event for an organization."""
        org_id = setup_test_organization
        payment_intent_id = "pi_org_test_canceled"
        
        # Create a payment intent in the database
        payment_intent_ref = firestore_emulator_client.collection("payment_intents").document(payment_intent_id)
        payment_intent_ref.set({
            "id": payment_intent_id,
            "organizationId": org_id,
            "caseTier": 3,
            "amount": 9900,
            "currency": "eur",
            "status": "created",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_pi_org_canceled",
            "type": "payment_intent.canceled",
            "data": {
                "object": {
                    "id": payment_intent_id,
                    "amount": 9900,
                    "currency": "eur",
                    "status": "canceled",
                    "cancellation_reason": "abandoned",
                    "metadata": {
                        "organizationId": org_id,
                        "caseTier": "3"
                    }
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
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "payment intent canceled" in response["message"].lower()
        
        # Verify payment intent was updated
        updated_pi_doc = payment_intent_ref.get()
        updated_pi_data = updated_pi_doc.to_dict()
        assert updated_pi_data["status"] == "canceled"
        assert "cancellationReason" in updated_pi_data
        assert updated_pi_data["cancellationReason"] == "abandoned"