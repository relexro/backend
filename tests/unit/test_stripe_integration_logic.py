#!/usr/bin/env python3
"""
Comprehensive Stripe integration tests for the payment and subscription system.

These tests focus on:
1. Payment intents for different case tiers
2. Checkout sessions with promotions/coupons
3. Organization subscription handling
4. Quota management
5. Complete webhook event coverage
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
from functions.src.auth import TYPE_ORGANIZATION

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestStripeIntegration:
    """Comprehensive test suite for Stripe integration."""

    @pytest.fixture
    def setup_test_user(self, firestore_emulator_client):
        """Create a test user with initial subscription data."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "inactive",
            "caseQuotaTotal": 0,
            "caseQuotaUsed": 0,
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        return user_id

    @pytest.fixture
    def setup_test_organization(self, firestore_emulator_client):
        """Create a test organization with initial subscription data."""
        org_id = f"test_org_{uuid.uuid4().hex[:8]}"
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        org_ref.set({
            "id": org_id,
            "name": "Test Organization",
            "description": "Test organization for Stripe integration tests",
            "subscriptionStatus": "inactive",
            "caseQuotaTotal": 0,
            "caseQuotaUsed": 0,
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
                    "tier_3": 1
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
                    "tier_3": 12
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
                    "tier_3": 5
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
        
        # Set up case tier prices for one-time purchases
        case_tiers = {
            "1": {
                "price": 900,
                "currency": "eur",
                "stripePriceId": "price_case_tier1_onetime"
            },
            "2": {
                "price": 2900,
                "currency": "eur",
                "stripePriceId": "price_case_tier2_onetime"
            },
            "3": {
                "price": 9900,
                "currency": "eur",
                "stripePriceId": "price_case_tier3_onetime"
            }
        }
        
        for tier, tier_data in case_tiers.items():
            firestore_emulator_client.collection("case_tiers").document(tier).set(tier_data)
            
        return {"plans": plans, "case_tiers": case_tiers}

    # Payment Intent Tests

    def test_payment_intent_for_tier_1(self, mocker, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plans):
        """Test creating payment intent for case tier 1."""
        user_id = setup_test_user
        
        # Mock auth to be the test user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock Stripe PaymentIntent.create
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = "pi_test_tier1"
        mock_payment_intent.client_secret = "pi_test_secret_tier1"
        mock_payment_intent.amount = 900
        mock_payment_intent.currency = "eur"
        
        stripe_mock = mocker.patch('stripe.PaymentIntent.create')
        stripe_mock.return_value = mock_payment_intent
        
        # Create request for tier 1
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "caseTier": 1
            }
        )
        
        # Call the function
        response, status_code = payments.create_payment_intent(request)
        
        # Verify response
        assert status_code == 201
        assert "paymentIntentId" in response
        assert response["paymentIntentId"] == "pi_test_tier1"
        
        # Verify payment intent was stored
        payment_intent_doc = firestore_emulator_client.collection("payment_intents").document("pi_test_tier1").get()
        assert payment_intent_doc.exists
        payment_intent_data = payment_intent_doc.to_dict()
        assert payment_intent_data["amount"] == 900
        assert payment_intent_data["caseTier"] == 1

    def test_payment_intent_for_tier_3(self, mocker, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plans):
        """Test creating payment intent for case tier 3 (highest tier)."""
        user_id = setup_test_user
        
        # Mock auth to be the test user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock Stripe PaymentIntent.create
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = "pi_test_tier3"
        mock_payment_intent.client_secret = "pi_test_secret_tier3"
        mock_payment_intent.amount = 9900
        mock_payment_intent.currency = "eur"
        
        stripe_mock = mocker.patch('stripe.PaymentIntent.create')
        stripe_mock.return_value = mock_payment_intent
        
        # Create request for tier 3
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "caseTier": 3
            }
        )
        
        # Call the function
        response, status_code = payments.create_payment_intent(request)
        
        # Verify response
        assert status_code == 201
        assert "paymentIntentId" in response
        assert response["paymentIntentId"] == "pi_test_tier3"
        
        # Verify payment intent was stored
        payment_intent_doc = firestore_emulator_client.collection("payment_intents").document("pi_test_tier3").get()
        assert payment_intent_doc.exists
        payment_intent_data = payment_intent_doc.to_dict()
        assert payment_intent_data["amount"] == 9900
        assert payment_intent_data["caseTier"] == 3

    def test_payment_intent_with_promotion_code(self, mocker, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plans):
        """Test creating payment intent with a promotion code."""
        user_id = setup_test_user
        
        # Mock auth to be the test user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock Stripe PromotionCode retrieve
        mock_promotion_code = MagicMock()
        mock_promotion_code.id = "promo_test_123"
        mock_promotion_code.coupon.percent_off = 25
        mock_promotion_code.coupon.valid = True
        
        stripe_promo_mock = mocker.patch('stripe.PromotionCode.retrieve')
        stripe_promo_mock.return_value = mock_promotion_code
        
        # Mock Stripe PaymentIntent.create
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = "pi_test_promo"
        mock_payment_intent.client_secret = "pi_test_secret_promo"
        mock_payment_intent.amount = 675  # 900 - 25% = 675
        mock_payment_intent.currency = "eur"
        
        stripe_pi_mock = mocker.patch('stripe.PaymentIntent.create')
        stripe_pi_mock.return_value = mock_payment_intent
        
        # Create request with promotion code
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "caseTier": 1,
                "promotionCode": "RELEXTEST25"
            }
        )
        
        # Call the function
        response, status_code = payments.create_payment_intent(request)
        
        # Verify response
        assert status_code == 201
        assert "paymentIntentId" in response
        assert response["paymentIntentId"] == "pi_test_promo"
        assert "discountedAmount" in response
        assert response["discountedAmount"] == 675
        
        # Verify payment intent was stored with discount
        payment_intent_doc = firestore_emulator_client.collection("payment_intents").document("pi_test_promo").get()
        assert payment_intent_doc.exists
        payment_intent_data = payment_intent_doc.to_dict()
        assert payment_intent_data["amount"] == 675
        assert payment_intent_data["originalAmount"] == 900
        assert payment_intent_data["discountPercent"] == 25

    # Checkout Session Tests

    def test_checkout_session_individual_monthly(self, mocker, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plans):
        """Test creating checkout session for individual monthly subscription."""
        user_id = setup_test_user
        
        # Mock auth to be the test user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock Stripe Checkout Session create
        mock_session = MagicMock()
        mock_session.id = "cs_test_individual_monthly"
        mock_session.url = "https://checkout.stripe.com/test_individual_monthly"
        
        stripe_mock = mocker.patch('stripe.checkout.Session.create')
        stripe_mock.return_value = mock_session
        
        # Create request for individual monthly subscription
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "planId": "individual_monthly"
            }
        )
        
        # Call the function
        response, status_code = payments.create_checkout_session(request)
        
        # Verify response
        assert status_code == 201
        assert "sessionId" in response
        assert response["sessionId"] == "cs_test_individual_monthly"
        assert "url" in response
        
        # Verify checkout session was stored
        checkout_session_doc = firestore_emulator_client.collection("checkout_sessions").document("cs_test_individual_monthly").get()
        assert checkout_session_doc.exists
        checkout_session_data = checkout_session_doc.to_dict()
        assert checkout_session_data["userId"] == user_id
        assert checkout_session_data["planId"] == "individual_monthly"
        
        # Verify Stripe was called with right parameters
        stripe_mock.assert_called_once()
        call_args = stripe_mock.call_args[1]
        assert call_args["mode"] == "subscription"
        assert call_args["line_items"][0]["price"] == "price_individual_monthly"
        assert call_args["client_reference_id"] == user_id

    def test_checkout_session_organization_pro(self, mocker, firestore_emulator_client, mock_request, setup_test_organization, setup_subscription_plans):
        """Test creating checkout session for organization pro subscription."""
        org_id = setup_test_organization
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Mock auth to be the test user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock permission check to allow organization checkout
        permission_mock = mocker.patch('functions.src.auth.check_permissions')
        permission_mock.return_value = ({"allowed": True}, 200)
        
        # Mock Stripe Checkout Session create
        mock_session = MagicMock()
        mock_session.id = "cs_test_org_pro"
        mock_session.url = "https://checkout.stripe.com/test_org_pro"
        
        stripe_mock = mocker.patch('stripe.checkout.Session.create')
        stripe_mock.return_value = mock_session
        
        # Create request for org pro subscription
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "planId": "org_pro_monthly",
                "organizationId": org_id
            }
        )
        
        # Call the function
        response, status_code = payments.create_checkout_session(request)
        
        # Verify response
        assert status_code == 201
        assert "sessionId" in response
        assert response["sessionId"] == "cs_test_org_pro"
        
        # Verify checkout session was stored
        checkout_session_doc = firestore_emulator_client.collection("checkout_sessions").document("cs_test_org_pro").get()
        assert checkout_session_doc.exists
        checkout_session_data = checkout_session_doc.to_dict()
        assert checkout_session_data["userId"] == user_id
        assert checkout_session_data["planId"] == "org_pro_monthly"
        assert checkout_session_data["organizationId"] == org_id
        
        # Verify Stripe was called with right parameters
        stripe_mock.assert_called_once()
        call_args = stripe_mock.call_args[1]
        assert call_args["mode"] == "subscription"
        assert call_args["line_items"][0]["price"] == "price_org_pro_monthly"
        # Check that metadata includes organization ID
        assert call_args["metadata"]["organizationId"] == org_id

    def test_checkout_session_with_promotion_code(self, mocker, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plans):
        """Test creating checkout session with promotion code."""
        user_id = setup_test_user
        
        # Mock auth to be the test user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock Stripe PromotionCode retrieve
        mock_promotion_code = MagicMock()
        mock_promotion_code.id = "promo_test_123"
        mock_promotion_code.code = "RELEXTEST25"
        mock_promotion_code.active = True
        
        stripe_promo_mock = mocker.patch('stripe.PromotionCode.list')
        stripe_promo_mock.return_value = {"data": [mock_promotion_code]}
        
        # Mock Stripe Checkout Session create
        mock_session = MagicMock()
        mock_session.id = "cs_test_promo"
        mock_session.url = "https://checkout.stripe.com/test_promo"
        
        stripe_mock = mocker.patch('stripe.checkout.Session.create')
        stripe_mock.return_value = mock_session
        
        # Create request with promotion code
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "planId": "individual_monthly",
                "promotionCode": "RELEXTEST25"
            }
        )
        
        # Call the function
        response, status_code = payments.create_checkout_session(request)
        
        # Verify response
        assert status_code == 201
        assert "sessionId" in response
        assert response["sessionId"] == "cs_test_promo"
        
        # Verify checkout session was stored with promotion code
        checkout_session_doc = firestore_emulator_client.collection("checkout_sessions").document("cs_test_promo").get()
        assert checkout_session_doc.exists
        checkout_session_data = checkout_session_doc.to_dict()
        assert checkout_session_data["userId"] == user_id
        assert checkout_session_data["promotionCode"] == "RELEXTEST25"
        
        # Verify Stripe was called with promotion code
        stripe_mock.assert_called_once()
        call_args = stripe_mock.call_args[1]
        assert call_args["discounts"][0]["promotion_code"] == "promo_test_123"

    # Webhook Event Tests

    def test_webhook_customer_subscription_created(self, mocker, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plans):
        """Test handling customer.subscription.created event."""
        user_id = setup_test_user
        plan_id = "individual_monthly"
        quota_total = setup_subscription_plans["plans"][plan_id]["caseQuotaTotal"]
        
        # Mock Stripe Webhook.construct_event
        current_time = int(time.time())
        event_data = {
            "id": "evt_sub_created",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test_created",
                    "customer": "cus_test_created",
                    "status": "active",
                    "current_period_start": current_time,
                    "current_period_end": current_time + (30 * 24 * 60 * 60),
                    "items": {
                        "data": [{
                            "price": {
                                "id": "price_individual_monthly",
                                "metadata": {"planId": plan_id}
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
        
        # Verify user subscription data was updated
        updated_user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        updated_user_data = updated_user_doc.to_dict()
        
        assert updated_user_data["subscriptionStatus"] == "active"
        assert updated_user_data["subscriptionPlanId"] == plan_id
        assert updated_user_data["stripeCustomerId"] == "cus_test_created"
        assert updated_user_data["stripeSubscriptionId"] == "sub_test_created"
        
        # Verify quota was set correctly
        assert "caseQuotaTotal" in updated_user_data
        assert updated_user_data["caseQuotaTotal"] == sum(quota_total.values())
        assert "quotaDetails" in updated_user_data
        assert updated_user_data["quotaDetails"]["tier_1"] == quota_total["tier_1"]
        assert updated_user_data["quotaDetails"]["tier_2"] == quota_total["tier_2"]
        assert updated_user_data["quotaDetails"]["tier_3"] == quota_total["tier_3"]

    def test_webhook_subscription_created_for_organization(self, mocker, firestore_emulator_client, mock_request, setup_test_organization, setup_subscription_plans):
        """Test handling subscription created event for an organization."""
        org_id = setup_test_organization
        plan_id = "org_pro_monthly"
        quota_total = setup_subscription_plans["plans"][plan_id]["caseQuotaTotal"]
        
        # Mock Stripe Webhook.construct_event
        current_time = int(time.time())
        event_data = {
            "id": "evt_org_sub_created",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test_org_created",
                    "customer": "cus_test_org_created",
                    "status": "active",
                    "current_period_start": current_time,
                    "current_period_end": current_time + (30 * 24 * 60 * 60),
                    "items": {
                        "data": [{
                            "price": {
                                "id": "price_org_pro_monthly",
                                "metadata": {"planId": plan_id}
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
        
        # Verify organization subscription data was updated
        updated_org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        updated_org_data = updated_org_doc.to_dict()
        
        assert updated_org_data["subscriptionStatus"] == "active"
        assert updated_org_data["subscriptionPlanId"] == plan_id
        assert updated_org_data["stripeCustomerId"] == "cus_test_org_created"
        assert updated_org_data["stripeSubscriptionId"] == "sub_test_org_created"
        
        # Verify quota was set correctly
        assert "caseQuotaTotal" in updated_org_data
        assert updated_org_data["caseQuotaTotal"] == sum(quota_total.values())
        assert "quotaDetails" in updated_org_data
        assert updated_org_data["quotaDetails"]["tier_1"] == quota_total["tier_1"]
        assert updated_org_data["quotaDetails"]["tier_2"] == quota_total["tier_2"]
        assert updated_org_data["quotaDetails"]["tier_3"] == quota_total["tier_3"]

    def test_webhook_payment_intent_succeeded(self, mocker, firestore_emulator_client, mock_request, setup_test_user):
        """Test handling payment_intent.succeeded event."""
        user_id = setup_test_user
        case_tier = 2
        
        # Create a payment intent in the database
        payment_intent_id = "pi_test_succeeded"
        payment_intent_ref = firestore_emulator_client.collection("payment_intents").document(payment_intent_id)
        payment_intent_ref.set({
            "id": payment_intent_id,
            "userId": user_id,
            "caseTier": case_tier,
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
                        "caseTier": str(case_tier)
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
        
        # Set initial quota
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.update({
            "caseQuotaTotal": 0,
            "caseQuotaUsed": 0,
            "quotaDetails": {
                "tier_1": 0,
                "tier_2": 0,
                "tier_3": 0
            }
        })
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        
        # Verify payment intent was updated
        updated_pi_doc = payment_intent_ref.get()
        updated_pi_data = updated_pi_doc.to_dict()
        assert updated_pi_data["status"] == "succeeded"
        
        # Verify user quota was updated for the specific tier
        updated_user_doc = user_ref.get()
        updated_user_data = updated_user_doc.to_dict()
        
        assert updated_user_data["caseQuotaTotal"] == 1  # Added 1 quota for tier 2
        assert updated_user_data["quotaDetails"]["tier_2"] == 1
        
        # Other tiers should remain unchanged
        assert updated_user_data["quotaDetails"]["tier_1"] == 0
        assert updated_user_data["quotaDetails"]["tier_3"] == 0

    def test_webhook_payment_intent_succeeded_for_organization(self, mocker, firestore_emulator_client, mock_request, setup_test_organization):
        """Test handling payment_intent.succeeded event for organization."""
        org_id = setup_test_organization
        case_tier = 3
        
        # Create a payment intent in the database
        payment_intent_id = "pi_test_org_succeeded"
        payment_intent_ref = firestore_emulator_client.collection("payment_intents").document(payment_intent_id)
        payment_intent_ref.set({
            "id": payment_intent_id,
            "organizationId": org_id,
            "caseTier": case_tier,
            "amount": 9900,
            "currency": "eur",
            "status": "created",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_pi_org_succeeded",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": payment_intent_id,
                    "amount": 9900,
                    "currency": "eur",
                    "status": "succeeded",
                    "metadata": {
                        "organizationId": org_id,
                        "caseTier": str(case_tier)
                    }
                }
            }
        }
        
        stripe_webhook_mock = mocker.patch('stripe.Webhook.construct_event')
        stripe_webhook_mock.return_value = event_data
        
        # Set initial quota for organization
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        org_ref.update({
            "caseQuotaTotal": 0,
            "caseQuotaUsed": 0,
            "quotaDetails": {
                "tier_1": 0,
                "tier_2": 0,
                "tier_3": 0
            }
        })
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        
        # Verify payment intent was updated
        updated_pi_doc = payment_intent_ref.get()
        updated_pi_data = updated_pi_doc.to_dict()
        assert updated_pi_data["status"] == "succeeded"
        
        # Verify organization quota was updated for the specific tier
        updated_org_doc = org_ref.get()
        updated_org
