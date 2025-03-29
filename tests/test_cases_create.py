import pytest
from unittest.mock import MagicMock, patch
import datetime
import firebase_admin
from firebase_admin import firestore
from functions.src import cases, auth

class TestCreateCase:
    """Test suite for create_case function with Model B payment logic."""
    
    def test_create_case_with_subscription_quota_available_user(self, mocker, firestore_emulator_client, mock_request):
        """Test creating a case for a user with an active subscription and available quota."""
        user_id = "test_user_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Create user with active subscription in Firestore
        current_time = datetime.datetime.now()
        billing_start = current_time - datetime.timedelta(days=10)
        billing_end = current_time + datetime.timedelta(days=20)
        
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "personal_monthly",
            "billingCycleStart": billing_start,
            "billingCycleEnd": billing_end,
            "caseQuotaTotal": 10,
            "caseQuotaUsed": 5,
            "stripeCustomerId": "cus_test_123",
            "stripeSubscriptionId": "sub_test_123",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create plan in Firestore
        plan_ref = firestore_emulator_client.collection("plans").document("personal_monthly")
        plan_ref.set({
            "planId": "personal_monthly",
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
        
        # Create a mock request for case creation
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Case",
                "description": "This is a test case",
                "caseTier": 1
                # No paymentIntentId needed - should use quota
            }
        )
        
        # Call the function
        response, status_code = cases.create_case(request)
        
        # Verify the response
        assert status_code == 201
        assert "caseId" in response
        assert response["userId"] == user_id
        assert response["caseTier"] == 1
        assert response["casePrice"] == 900
        assert response["paymentStatus"] == "covered_by_quota"
        assert "paymentIntentId" not in response
        
        # Verify case was created in Firestore
        case_id = response["caseId"]
        case_doc = firestore_emulator_client.collection("cases").document(case_id).get()
        assert case_doc.exists
        
        case_data = case_doc.to_dict()
        assert case_data["userId"] == user_id
        assert case_data["title"] == "Test Case"
        assert case_data["description"] == "This is a test case"
        assert case_data["caseTier"] == 1
        assert case_data["casePrice"] == 900
        assert case_data["paymentStatus"] == "covered_by_quota"
        assert "paymentIntentId" not in case_data
        
        # Verify user quota was incremented
        updated_user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        updated_user_data = updated_user_doc.to_dict()
        assert updated_user_data["caseQuotaUsed"] == 6  # Increased by 1

    def test_create_case_with_subscription_quota_available_organization(self, mocker, firestore_emulator_client, mock_request):
        """Test creating a case for an organization with an active subscription and available quota."""
        user_id = "test_user_123"
        org_id = "test_org_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock permission check
        permission_mock = mocker.patch('functions.src.cases.check_permissions_func')
        permission_mock.return_value = ({"allowed": True}, 200)
        
        # Create organization with active subscription in Firestore
        current_time = datetime.datetime.now()
        billing_start = current_time - datetime.timedelta(days=10)
        billing_end = current_time + datetime.timedelta(days=20)
        
        org_ref = firestore_emulator_client.collection("organizations").document(org_id)
        org_ref.set({
            "organizationId": org_id,
            "name": "Test Organization",
            "ownerId": user_id,
            "subscriptionStatus": "active",
            "subscriptionPlanId": "business_pro_monthly",
            "billingCycleStart": billing_start,
            "billingCycleEnd": billing_end,
            "caseQuotaTotal": 50,
            "caseQuotaUsed": 25,
            "stripeCustomerId": "cus_test_org_123",
            "stripeSubscriptionId": "sub_test_org_123",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create plan in Firestore
        plan_ref = firestore_emulator_client.collection("plans").document("business_pro_monthly")
        plan_ref.set({
            "planId": "business_pro_monthly",
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
        
        # Create a mock request for organization case creation
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Organization Case",
                "description": "This is a test organization case",
                "organizationId": org_id,
                "caseTier": 2
                # No paymentIntentId needed - should use quota
            }
        )
        
        # Call the function
        response, status_code = cases.create_case(request)
        
        # Verify the response
        assert status_code == 201
        assert "caseId" in response
        assert response["userId"] == user_id
        assert response["organizationId"] == org_id
        assert response["caseTier"] == 2
        assert response["casePrice"] == 2900
        assert response["paymentStatus"] == "covered_by_quota"
        assert "paymentIntentId" not in response
        
        # Verify case was created in Firestore
        case_id = response["caseId"]
        case_doc = firestore_emulator_client.collection("cases").document(case_id).get()
        assert case_doc.exists
        
        case_data = case_doc.to_dict()
        assert case_data["userId"] == user_id
        assert case_data["organizationId"] == org_id
        assert case_data["title"] == "Test Organization Case"
        assert case_data["description"] == "This is a test organization case"
        assert case_data["caseTier"] == 2
        assert case_data["casePrice"] == 2900
        assert case_data["paymentStatus"] == "covered_by_quota"
        assert "paymentIntentId" not in case_data
        
        # Verify organization quota was incremented
        updated_org_doc = firestore_emulator_client.collection("organizations").document(org_id).get()
        updated_org_data = updated_org_doc.to_dict()
        assert updated_org_data["caseQuotaUsed"] == 26  # Increased by 1
        
    def test_create_case_with_quota_exhausted_no_payment(self, mocker, firestore_emulator_client, mock_request):
        """Test creating a case when quota is exhausted and no payment intent is provided."""
        user_id = "test_user_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Create user with active subscription but exhausted quota in Firestore
        current_time = datetime.datetime.now()
        billing_start = current_time - datetime.timedelta(days=10)
        billing_end = current_time + datetime.timedelta(days=20)
        
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "personal_monthly",
            "billingCycleStart": billing_start,
            "billingCycleEnd": billing_end,
            "caseQuotaTotal": 10,
            "caseQuotaUsed": 10,  # Quota is fully used
            "stripeCustomerId": "cus_test_123",
            "stripeSubscriptionId": "sub_test_123",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create plan in Firestore
        plan_ref = firestore_emulator_client.collection("plans").document("personal_monthly")
        plan_ref.set({
            "planId": "personal_monthly",
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
        
        # Create a mock request for case creation without payment intent
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Case",
                "description": "This is a test case",
                "caseTier": 1
                # No paymentIntentId provided
            }
        )
        
        # Call the function
        response, status_code = cases.create_case(request)
        
        # Verify the response indicates quota exhausted and payment required
        assert status_code == 402  # Payment Required
        assert "error" in response
        assert "Your subscription quota is exhausted" in response["message"]
        
        # Verify no new case was created
        cases_query = firestore_emulator_client.collection("cases").where("title", "==", "Test Case").get()
        assert len(list(cases_query)) == 0

    def test_create_case_with_quota_exhausted_with_payment(self, mocker, firestore_emulator_client, mock_request):
        """Test creating a case when quota is exhausted but payment intent is provided."""
        user_id = "test_user_123"
        payment_intent_id = "pi_test_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock Stripe PaymentIntent.retrieve
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = payment_intent_id
        mock_payment_intent.status = 'succeeded'
        mock_payment_intent.amount = 900  # $9.00
        
        stripe_mock = mocker.patch('stripe.PaymentIntent.retrieve')
        stripe_mock.return_value = mock_payment_intent
        
        # Create user with active subscription but exhausted quota in Firestore
        current_time = datetime.datetime.now()
        billing_start = current_time - datetime.timedelta(days=10)
        billing_end = current_time + datetime.timedelta(days=20)
        
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "personal_monthly",
            "billingCycleStart": billing_start,
            "billingCycleEnd": billing_end,
            "caseQuotaTotal": 10,
            "caseQuotaUsed": 10,  # Quota is fully used
            "stripeCustomerId": "cus_test_123",
            "stripeSubscriptionId": "sub_test_123",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create a mock request for case creation with payment intent
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Case",
                "description": "This is a test case",
                "caseTier": 1,
                "paymentIntentId": payment_intent_id
            }
        )
        
        # Call the function
        response, status_code = cases.create_case(request)
        
        # Verify the response
        assert status_code == 201
        assert "caseId" in response
        assert response["userId"] == user_id
        assert response["caseTier"] == 1
        assert response["casePrice"] == 900
        assert response["paymentStatus"] == "paid_intent"
        assert response["paymentIntentId"] == payment_intent_id
        
        # Verify case was created in Firestore
        case_id = response["caseId"]
        case_doc = firestore_emulator_client.collection("cases").document(case_id).get()
        assert case_doc.exists
        
        case_data = case_doc.to_dict()
        assert case_data["userId"] == user_id
        assert case_data["title"] == "Test Case"
        assert case_data["description"] == "This is a test case"
        assert case_data["caseTier"] == 1
        assert case_data["casePrice"] == 900
        assert case_data["paymentStatus"] == "paid_intent"
        assert case_data["paymentIntentId"] == payment_intent_id
        
        # Verify user quota was NOT incremented (using payment instead)
        updated_user_doc = firestore_emulator_client.collection("users").document(user_id).get()
        updated_user_data = updated_user_doc.to_dict()
        assert updated_user_data["caseQuotaUsed"] == 10  # Still 10, no change

    def test_create_case_non_subscribed_user_no_payment(self, mocker, firestore_emulator_client, mock_request):
        """Test creating a case for a user with no subscription and no payment intent."""
        user_id = "test_user_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Create user with no subscription in Firestore
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "inactive",  # No active subscription
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create a mock request for case creation without payment intent
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Case",
                "description": "This is a test case",
                "caseTier": 1
                # No paymentIntentId provided
            }
        )
        
        # Call the function
        response, status_code = cases.create_case(request)
        
        # Verify the response indicates payment required
        assert status_code == 402  # Payment Required
        assert "error" in response
        assert "This case requires payment" in response["message"]
        
        # Verify no new case was created
        cases_query = firestore_emulator_client.collection("cases").where("title", "==", "Test Case").get()
        assert len(list(cases_query)) == 0

    def test_create_case_non_subscribed_user_with_payment(self, mocker, firestore_emulator_client, mock_request):
        """Test creating a case for a user with no subscription but with payment intent."""
        user_id = "test_user_123"
        payment_intent_id = "pi_test_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Mock Stripe PaymentIntent.retrieve
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = payment_intent_id
        mock_payment_intent.status = 'succeeded'
        mock_payment_intent.amount = 900  # $9.00
        
        stripe_mock = mocker.patch('stripe.PaymentIntent.retrieve')
        stripe_mock.return_value = mock_payment_intent
        
        # Create user with no subscription in Firestore
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "inactive",  # No active subscription
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create a mock request for case creation with payment intent
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Case",
                "description": "This is a test case",
                "caseTier": 1,
                "paymentIntentId": payment_intent_id
            }
        )
        
        # Call the function
        response, status_code = cases.create_case(request)
        
        # Verify the response
        assert status_code == 201
        assert "caseId" in response
        assert response["userId"] == user_id
        assert response["caseTier"] == 1
        assert response["casePrice"] == 900
        assert response["paymentStatus"] == "paid_intent"
        assert response["paymentIntentId"] == payment_intent_id
        
        # Verify case was created in Firestore
        case_id = response["caseId"]
        case_doc = firestore_emulator_client.collection("cases").document(case_id).get()
        assert case_doc.exists
        
        case_data = case_doc.to_dict()
        assert case_data["userId"] == user_id
        assert case_data["title"] == "Test Case"
        assert case_data["description"] == "This is a test case"
        assert case_data["caseTier"] == 1
        assert case_data["casePrice"] == 900
        assert case_data["paymentStatus"] == "paid_intent"
        assert case_data["paymentIntentId"] == payment_intent_id
        
    def test_create_case_expired_billing_cycle(self, mocker, firestore_emulator_client, mock_request):
        """Test creating a case when billing cycle has expired."""
        user_id = "test_user_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Create user with active subscription but expired billing cycle
        current_time = datetime.datetime.now()
        billing_start = current_time - datetime.timedelta(days=40)
        billing_end = current_time - datetime.timedelta(days=10)  # Expired 10 days ago
        
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "personal_monthly",
            "billingCycleStart": billing_start,
            "billingCycleEnd": billing_end,
            "caseQuotaTotal": 10,
            "caseQuotaUsed": 5,
            "stripeCustomerId": "cus_test_123",
            "stripeSubscriptionId": "sub_test_123",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create plan in Firestore
        plan_ref = firestore_emulator_client.collection("plans").document("personal_monthly")
        plan_ref.set({
            "planId": "personal_monthly",
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
        
        # Create a mock request for case creation without payment intent
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Case",
                "description": "This is a test case",
                "caseTier": 1
                # No paymentIntentId provided
            }
        )
        
        # Call the function
        response, status_code = cases.create_case(request)
        
        # Verify the response indicates payment required
        assert status_code == 402  # Payment Required
        assert "error" in response
        assert "payment" in response["message"].lower()
        
        # Verify no new case was created
        cases_query = firestore_emulator_client.collection("cases").where("title", "==", "Test Case").get()
        assert len(list(cases_query)) == 0
        
    def test_create_case_transaction_failure(self, mocker, firestore_emulator_client, mock_request):
        """Test creating a case when the Firestore transaction fails."""
        user_id = "test_user_123"
        
        # Mock auth to be a user
        auth_mock = mocker.patch('functions.src.auth.get_authenticated_user')
        auth_mock.return_value = ({"userId": user_id}, 200, None)
        
        # Create user with active subscription in Firestore
        current_time = datetime.datetime.now()
        billing_start = current_time - datetime.timedelta(days=10)
        billing_end = current_time + datetime.timedelta(days=20)
        
        user_ref = firestore_emulator_client.collection("users").document(user_id)
        user_ref.set({
            "userId": user_id,
            "email": "test@example.com",
            "displayName": "Test User",
            "subscriptionStatus": "active",
            "subscriptionPlanId": "personal_monthly",
            "billingCycleStart": billing_start,
            "billingCycleEnd": billing_end,
            "caseQuotaTotal": 10,
            "caseQuotaUsed": 5,
            "stripeCustomerId": "cus_test_123",
            "stripeSubscriptionId": "sub_test_123",
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Create plan in Firestore
        plan_ref = firestore_emulator_client.collection("plans").document("personal_monthly")
        plan_ref.set({
            "planId": "personal_monthly",
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
        
        # Mock the transaction to simulate failure
        mock_transaction = MagicMock()
        mock_transaction.side_effect = ValueError("Quota has been exhausted by a concurrent operation")
        mocker.patch('functions.src.cases.create_case_with_quota_in_transaction', mock_transaction)
        
        # Create a mock request for case creation
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Case",
                "description": "This is a test case",
                "caseTier": 1
                # No paymentIntentId provided - should try to use quota
            }
        )
        
        # Create a mock payment intent to check if fallback works
        payment_intent_id = "pi_test_123"
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = payment_intent_id
        mock_payment_intent.status = 'succeeded'
        mock_payment_intent.amount = 900  # $9.00
        
        stripe_mock = mocker.patch('stripe.PaymentIntent.retrieve')
        stripe_mock.return_value = mock_payment_intent
        
        # Update request to include payment intent (fallback)
        request = mock_request(
            headers={"Authorization": "Bearer fake_token"},
            json_data={
                "title": "Test Case",
                "description": "This is a test case",
                "caseTier": 1,
                "paymentIntentId": payment_intent_id  # Add payment intent for fallback
            }
        )
        
        # Call the function
        response, status_code = cases.create_case(request)
        
        # Verify the response - should fall back to using payment intent
        assert status_code == 201
        assert "caseId" in response
        assert response["userId"] == user_id
        assert response["caseTier"] == 1
        assert response["casePrice"] == 900
        assert response["paymentStatus"] == "paid_intent"
        assert response["paymentIntentId"] == payment_intent_id
``` 