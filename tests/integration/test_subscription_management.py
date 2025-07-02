#!/usr/bin/env python3
"""
Tests for subscription management and quota operations:
- Viewing subscription status
- Updating subscription (upgrading/downgrading)
- Organization-specific subscription management
- Quota consumption and management
- Quota sharing among organization members
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
from functions.src import cases
from functions.src.auth import TYPE_ORGANIZATION

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestSubscriptionManagement:
    """Test suite for subscription management and quota operations."""

    @pytest.fixture
    def setup_test_user(self, firestore_emulator_client):
        """Create a test user with active subscription."""
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
            "caseQuotaTotal": 17,
            "caseQuotaUsed": 3,
            "quotaDetails": {
                "tier_1": 10,
                "tier_2": 5,
                "tier_3": 2
            },
            "billingCycleStart": current_time - (15 * 24 * 60 * 60),  # 15 days ago
            "billingCycleEnd": current_time + (15 * 24 * 60 * 60),    # 15 days in future
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        return user_id

    @pytest.fixture
    def setup_test_organization(self, firestore_emulator_client):
        """Create a test organization with active subscription."""
        org_id = f"test_org_{uuid.uuid4().hex[:8]}"
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        
        current_time = int(time.time())
        org_ref.set({
            "id": org_id,
            "name": "Test Organization",
            "description": "Test organization for subscription tests",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "org_basic_monthly",
            "stripeCustomerId": "cus_org_test_123",
            "stripeSubscriptionId": "sub_org_test_123",
            "caseQuotaTotal": 85,
            "caseQuotaUsed": 10,
            "quotaDetails": {
                "tier_1": 50,
                "tier_2": 25,
                "tier_3": 10
            },
            "billingCycleStart": current_time - (15 * 24 * 60 * 60),
            "billingCycleEnd": current_time + (15 * 24 * 60 * 60),
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        return org_id

    @pytest.fixture
    def setup_organization_members(self, firestore_emulator_client, setup_test_organization):
        """Add members to the test organization."""
        org_id = setup_test_organization
        
        # Create admin user
        admin_id = f"admin_user_{uuid.uuid4().hex[:8]}"
        firestore_emulator_client.collection("users").document(admin_id).set({
            "userId": admin_id,
            "email": "admin@example.com",
            "displayName": "Admin User",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create staff user
        staff_id = f"staff_user_{uuid.uuid4().hex[:8]}"
        firestore_emulator_client.collection("users").document(staff_id).set({
            "userId": staff_id,
            "email": "staff@example.com",
            "displayName": "Staff User",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Add membership records
        firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{admin_id}").set({
            "userId": admin_id,
            "organizationId": org_id,
            "role": "administrator",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        firestore_emulator_client.collection("organization_memberships").document(f"{org_id}_{staff_id}").set({
            "userId": staff_id,
            "organizationId": org_id,
            "role": "staff",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        return {
            "org_id": org_id,
            "admin_id": admin_id,
            "staff_id": staff_id
        }

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

    # Subscription Status Tests

    def test_view_user_subscription_status(self, firestore_emulator_client, mock_request, setup_test_user):
        """Test viewing subscription status for a user."""
        user_id = setup_test_user
        
        # Create a mock request
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Call the function
        response, status_code = payments.get_user_subscription(request)
        
        # Verify response
        assert status_code == 200
        assert "status" in response
        assert response["status"] == "active"
        assert "planId" in response
        assert response["planId"] == "individual_monthly"
        assert "currentPeriodEnd" in response
        assert "caseQuotaTotal" in response
        assert response["caseQuotaTotal"] == 17
        assert "caseQuotaUsed" in response
        assert response["caseQuotaUsed"] == 3
        assert "quotaDetails" in response
        assert response["quotaDetails"]["tier_1"] == 10
        assert response["quotaDetails"]["tier_2"] == 5
        assert response["quotaDetails"]["tier_3"] == 2

    def test_view_organization_subscription_status(self, firestore_emulator_client, mock_request, setup_organization_members):
        """Test viewing subscription status for an organization."""
        org_id = setup_organization_members["org_id"]
        admin_id = setup_organization_members["admin_id"]
        
        # Create a mock request
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"organizationId": org_id},
            path=f"/organizations/{org_id}/subscription"
        )
        
        # Call the function
        response, status_code = payments.get_organization_subscription(request)
        
        # Verify response
        assert status_code == 200
        assert "status" in response
        assert response["status"] == "active"
        assert "planId" in response
        assert response["planId"] == "org_basic_monthly"
        assert "currentPeriodEnd" in response
        assert "caseQuotaTotal" in response
        assert response["caseQuotaTotal"] == 85
        assert "caseQuotaUsed" in response
        assert response["caseQuotaUsed"] == 10
        assert "quotaDetails" in response
        assert response["quotaDetails"]["tier_1"] == 50
        assert response["quotaDetails"]["tier_2"] == 25
        assert response["quotaDetails"]["tier_3"] == 10

    def test_non_member_cannot_view_organization_subscription(self, firestore_emulator_client, mock_request, setup_organization_members):
        """Test that non-members cannot view an organization's subscription."""
        org_id = setup_organization_members["org_id"]
        non_member_id = f"non_member_{uuid.uuid4().hex[:8]}"
        
        # Create a mock request
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"organizationId": org_id},
            path=f"/organizations/{org_id}/subscription"
        )
        
        # Call the function
        response, status_code = payments.get_organization_subscription(request)
        
        # Verify access is denied
        assert status_code == 403
        assert "error" in response

    # Subscription Update Tests

    def test_update_user_subscription(self, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plans):
        """Test updating a user's subscription (plan upgrade)."""
        user_id = setup_test_user
        old_plan_id = "individual_monthly"
        new_plan_id = "individual_yearly"
        
        # Create a mock request
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"planId": new_plan_id}
        )
        
        # Call the function
        response, status_code = payments.update_subscription(request)
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "subscriptionId" in response
        assert response["subscriptionId"] == "sub_test_123"
        
        # Verify database was updated
        user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        user_data = user_doc.to_dict()
        assert user_data["subscriptionPlanId"] == new_plan_id

    def test_update_organization_subscription(self, firestore_emulator_client, mock_request, setup_organization_members, setup_subscription_plans):
        """Test updating an organization's subscription (plan upgrade)."""
        org_id = setup_organization_members["org_id"]
        admin_id = setup_organization_members["admin_id"]
        old_plan_id = "org_basic_monthly"
        new_plan_id = "org_pro_monthly"
        
        # Create a mock request
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={"planId": new_plan_id, "organizationId": org_id},
            path=f"/organizations/{org_id}/subscription/update"
        )
        
        # Call the function
        response, status_code = payments.update_organization_subscription(request)
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        assert "subscriptionId" in response
        assert response["subscriptionId"] == "sub_org_test_123"
        
        # Verify database was updated
        org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        org_data = org_doc.to_dict()
        assert org_data["subscriptionPlanId"] == new_plan_id

    # Quota Tests

    def test_quota_consumption_for_case_creation(self, firestore_emulator_client, mock_request, setup_test_user):
        """Test quota consumption when creating a new case."""
        user_id = setup_test_user
        
        # Get initial quota values
        user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        user_data = user_doc.to_dict()
        initial_quota_used = user_data["caseQuotaUsed"]
        initial_tier1_quota = user_data["quotaDetails"]["tier_1"]
        
        # Create a mock request for a tier 1 case
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Case",
                "description": "Test case for quota consumption",
                "caseTier": 1,
                "caseTypeId": "general_consultation"
            }
        )
        
        # Call the function
        response, status_code = cases.create_case(request)
        
        # Verify case was created
        assert status_code == 201
        assert "caseId" in response
        
        # Verify quota was consumed
        updated_user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        updated_user_data = updated_user_doc.to_dict()
        assert updated_user_data["caseQuotaUsed"] == initial_quota_used + 1
        assert updated_user_data["quotaDetails"]["tier_1"] == initial_tier1_quota - 1

    def test_organization_quota_consumption(self, firestore_emulator_client, mock_request, setup_organization_members):
        """Test quota consumption for an organization when creating a case."""
        org_id = setup_organization_members["org_id"]
        admin_id = setup_organization_members["admin_id"]
        staff_id = setup_organization_members["staff_id"]
        
        # Get initial quota values
        org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        org_data = org_doc.to_dict()
        initial_quota_used = org_data["caseQuotaUsed"]
        initial_tier2_quota = org_data["quotaDetails"]["tier_2"]
        
        # Create a mock request for a tier 2 case
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Org Case",
                "description": "Test organization case for quota consumption",
                "caseTier": 2,
                "caseTypeId": "general_consultation",
                "organizationId": org_id
            },
            path=f"/organizations/{org_id}/cases"
        )
        
        # Call the function
        response, status_code = cases.create_organization_case(request)
        
        # Verify case was created
        assert status_code == 201
        assert "id" in response
        
        # Verify organization quota was consumed
        updated_org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        updated_org_data = updated_org_doc.to_dict()
        assert updated_org_data["caseQuotaUsed"] == initial_quota_used + 1
        assert updated_org_data["quotaDetails"]["tier_2"] == initial_tier2_quota - 1

    def test_quota_insufficient_requires_payment(self, firestore_emulator_client, mock_request, setup_test_user):
        """Test that insufficient quota requires payment."""
        user_id = setup_test_user
        
        # Set quota to zero
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.update({
            "quotaDetails.tier_3": 0
        })
        
        # Create a mock request for a tier 3 case
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Premium Case",
                "description": "Test case requiring payment due to insufficient quota",
                "caseTier": 3,
                "caseTypeId": "complex_litigation"
            }
        )
        
        # Call the function
        response, status_code = cases.create_case(request)
        
        # Verify payment required response
        assert status_code == 402
        assert "error" in response
        assert "paymentRequired" in response
        assert response["paymentRequired"] is True
        assert "caseTier" in response
        assert response["caseTier"] == 3

    def test_quota_reset_on_billing_cycle_renewal(self, firestore_emulator_client, mock_request, setup_test_user, setup_subscription_plans):
        """Test quota reset when billing cycle renews."""
        user_id = setup_test_user
        subscription_id = "sub_test_123"
        plan_id = "individual_monthly"
        plan_quota = setup_subscription_plans["plans"][plan_id]["caseQuotaTotal"]
        
        # Set some consumed quota
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.update({
            "caseQuotaUsed": 5,
            "quotaDetails.tier_1": 5,  # Half consumed
            "quotaDetails.tier_2": 2,  # Partially consumed
            "quotaDetails.tier_3": 0   # Fully consumed
        })
        
        # Mock Stripe Webhook.construct_event
        current_time = int(time.time())
        event_data = {
            "id": "evt_invoice_renewal",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_renewal_123",
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
                "metadata": {"planId": plan_id}
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
        
        # Verify quota was reset to full
        updated_user_doc = user_ref.get()
        updated_user_data = updated_user_doc.to_dict()
        assert updated_user_data["caseQuotaUsed"] == 0
        assert updated_user_data["quotaDetails"]["tier_1"] == plan_quota["tier_1"]
        assert updated_user_data["quotaDetails"]["tier_2"] == plan_quota["tier_2"]
        assert updated_user_data["quotaDetails"]["tier_3"] == plan_quota["tier_3"]
        assert updated_user_data["caseQuotaTotal"] == sum(plan_quota.values())

    def test_one_time_purchase_quota_addition(self, firestore_emulator_client, mock_request, setup_test_user):
        """Test quota addition after one-time case purchase."""
        user_id = setup_test_user
        case_tier = 3
        
        # Get initial quota values
        user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        user_data = user_doc.to_dict()
        initial_tier3_quota = user_data["quotaDetails"]["tier_3"]
        
        # Create a payment intent in the database
        payment_intent_id = "pi_test_onetime_quota"
        payment_intent_ref = firestore_emulator_client.collection("payment_intents").document(payment_intent_id)
        payment_intent_ref.set({
            "id": payment_intent_id,
            "userId": user_id,
            "caseTier": case_tier,
            "amount": 9900,
            "currency": "eur",
            "status": "created",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Mock Stripe Webhook.construct_event
        event_data = {
            "id": "evt_pi_onetime",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": payment_intent_id,
                    "amount": 9900,
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
        
        # Call the function
        response, status_code = payments.handle_stripe_webhook(request)
        
        # Verify response
        assert status_code == 200
        assert "success" in response
        assert response["success"] is True
        
        # Verify tier-specific quota was increased
        updated_user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        updated_user_data = updated_user_doc.to_dict()
        assert updated_user_data["quotaDetails"]["tier_3"] == initial_tier3_quota + 1

    def test_organization_quota_sharing(self, firestore_emulator_client, mock_request, setup_organization_members):
        """Test that organization members share the same quota pool."""
        org_id = setup_organization_members["org_id"]
        admin_id = setup_organization_members["admin_id"]
        staff_id = setup_organization_members["staff_id"]
        
        # Get initial quota values
        org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        org_data = org_doc.to_dict()
        initial_quota_used = org_data["caseQuotaUsed"]
        
        # First create a case as admin
        # Mock auth to be the admin user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": admin_id}, 200, None)
        
        # Mock permission check to allow admin to create a case
        permission_mock = mocker.patch('functions.src.auth.check_permissions')
        permission_mock.return_value = ({"allowed": True}, 200)
        
        # Mock quota check to return success
        quota_check_mock = mocker.patch('functions.src.cases.check_quota')
        quota_check_mock.return_value = (True, "Sufficient quota available")
        
        # Create a mock request for a tier 2 case
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Org Case",
                "description": "Test organization case for quota consumption",
                "caseTier": 2,
                "caseTypeId": "general_consultation",
                "organizationId": org_id
            },
            path=f"/organizations/{org_id}/cases"
        )
        
        # Call the function
        response, status_code = cases.create_organization_case(request)
        
        # Verify case was created
        assert status_code == 201
        assert "id" in response
        
        # Verify organization quota was consumed
        updated_org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        updated_org_data = updated_org_doc.to_dict()
        assert updated_org_data["caseQuotaUsed"] == initial_quota_used + 1
        assert updated_org_data["quotaDetails"]["tier_2"] == 24