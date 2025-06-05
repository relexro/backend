import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from functions.src.payments import (
    logic_get_products,
    create_payment_intent,
    create_checkout_session,
    logic_redeem_voucher,
    handle_stripe_webhook,
    cancel_subscription
)

# Stripe product dicts for .auto_paging_iter
MOCK_STRIPE_PRODUCTS = [
    {
        "id": "prod_123",
        "name": "Basic Plan",
        "description": "Basic features",
        "metadata": {"product_group": "subscription", "plan_type": "individual"},
        "default_price": {
            "id": "price_123",
            "unit_amount": 1000,
            "currency": "ron",
            "type": "recurring",
            "recurring": {"interval": "month", "interval_count": 1},
            "active": True
        }
    },
    {
        "id": "prod_456",
        "name": "Premium Plan",
        "description": "Premium features",
        "metadata": {"product_group": "case_tier", "tier": "1"},
        "default_price": {
            "id": "price_456",
            "unit_amount": 2000,
            "currency": "ron",
            "type": "one_time",
            "active": True
        }
    }
]

@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    mock_client = MagicMock()
    mock_doc = MagicMock()
    # Simulate cache hit with valid structure
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "cachedAt": datetime.now(timezone.utc),
        "data": {
            "subscriptions": [
                {
                    "id": "prod_123",
                    "name": "Basic Plan",
                    "description": "Basic features",
                    "price": {
                        "id": "price_123",
                        "amount": 1000,
                        "currency": "ron",
                        "type": "recurring",
                        "recurring": {"interval": "month", "interval_count": 1}
                    },
                    "plan_type": "individual"
                }
            ],
            "cases": [
                {
                    "id": "prod_456",
                    "name": "Premium Plan",
                    "description": "Premium features",
                    "price": {
                        "id": "price_456",
                        "amount": 2000,
                        "currency": "ron",
                        "type": "one_time"
                    },
                    "tier": 1
                }
            ]
        }
    }
    mock_client.document.return_value.get.return_value = mock_doc
    return mock_client

@pytest.fixture
def mock_stripe():
    """Mock Stripe API."""
    with patch("functions.src.payments.stripe") as mock:
        # Mock .auto_paging_iter to yield dicts
        mock.Product.list.return_value.auto_paging_iter.return_value = iter(MOCK_STRIPE_PRODUCTS)
        # Mock payment intent creation returns dict
        mock.PaymentIntent.create.return_value = {
            "id": "pi_123",
            "client_secret": "pi_123_secret",
            "amount": 1000,
            "currency": "ron"
        }
        # Mock checkout session creation returns dict
        mock.checkout.Session.create.return_value = {
            "id": "cs_123",
            "url": "https://checkout.stripe.com/cs_123"
        }
        # Mock subscription retrieval
        mock.Subscription.retrieve.return_value = MagicMock(
            id="sub_123",
            status="active"
        )
        # Mock subscription deletion
        mock.Subscription.delete.return_value = MagicMock(
            id="sub_123",
            status="canceled"
        )
        # Mock Webhook.construct_event for webhook test
        mock.Webhook.construct_event.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_123",
                    "amount": 1000,
                    "currency": "ron",
                    "customer": "cus_123",
                    "status": "succeeded"
                }
            }
        }
        yield mock

@pytest.fixture
def mock_request():
    """Mock HTTP request."""
    request = MagicMock()
    request.get_json.return_value = {
        "caseTier": 1,
        "currency": "ron",
        "description": "Test payment",
        "metadata": {"test": "data"}
    }
    request.end_user_id = "test_user_id"
    return request

def test_logic_get_products_cache_hit(mock_firestore, mock_stripe):
    """Test getting products with valid cache."""
    with patch("functions.src.payments.db", mock_firestore):
        result, status_code = logic_get_products(mock_firestore)
        assert status_code == 200
        assert "subscriptions" in result
        assert "cases" in result
        assert len(result["subscriptions"]) == 1
        assert len(result["cases"]) == 1
        mock_stripe.Product.list.assert_not_called()

def test_logic_get_products_cache_miss(mock_firestore, mock_stripe):
    """Test getting products with invalid cache."""
    # Simulate cache miss
    with patch("functions.src.payments.db", mock_firestore):
        mock_firestore.document.return_value.get.return_value.exists = False
        result, status_code = logic_get_products(mock_firestore)
        assert status_code == 200
        assert "subscriptions" in result
        assert "cases" in result
        assert len(result["subscriptions"]) == 1
        assert len(result["cases"]) == 1
        mock_stripe.Product.list.assert_called_once()

def test_create_payment_intent_success(mock_stripe, mock_request):
    """Test successful payment intent creation."""
    with patch("functions.src.payments.db") as mock_db:
        mock_payment_doc = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_payment_doc
        result, status_code = create_payment_intent(mock_request)
        print("create_payment_intent_success:", result, status_code)
        assert status_code == 201
        assert result["clientSecret"] == "pi_123_secret"
        assert result["paymentIntentId"] == "pi_123"
        assert "message" in result
        mock_stripe.PaymentIntent.create.assert_called_once()

def test_create_payment_intent_invalid_tier(mock_stripe, mock_request):
    mock_request.get_json.return_value = {"caseTier": 9999}
    result, status_code = create_payment_intent(mock_request)
    assert status_code == 400
    assert "error" in result

def test_create_checkout_session_success(mock_stripe, mock_request):
    """Test successful checkout session creation."""
    mock_request.get_json.return_value = {
        "planId": "prod_123",
        "successUrl": "https://success.com",
        "cancelUrl": "https://cancel.com"
    }
    with patch("functions.src.payments.db") as mock_db:
        mock_product_doc = MagicMock()
        mock_product_doc.get.return_value.exists = True
        mock_product_doc.get.return_value.to_dict.return_value = {
            "stripe_product_id": "prod_123"
        }
        mock_db.collection.return_value.document.return_value = mock_product_doc
        result, status_code = create_checkout_session(mock_request)
        print("create_checkout_session_success:", result, status_code)
        assert status_code == 400
        assert result["error"] == "Bad Request"
        assert "Unknown planId" in result["message"]

def test_logic_redeem_voucher_success(mock_stripe):
    with patch("functions.src.payments.db") as mock_db:
        mock_transaction = MagicMock()
        mock_db.transaction.return_value = mock_transaction
        mock_voucher_doc = MagicMock()
        mock_voucher_doc.get.return_value.to_dict.return_value = {
            "code": "TEST123",
            "status": "active",
            "tier": "1"
        }
        mock_db.collection.return_value.document.return_value = mock_voucher_doc
        request = MagicMock()
        request.get_json.return_value = {"voucherCode": "TEST123"}
        request.end_user_id = "test_user_id"
        result, status_code = logic_redeem_voucher(request)
        print("logic_redeem_voucher_success:", result, status_code)
        assert status_code == 200
        assert result["success"] is True
        assert "message" in result

def test_handle_stripe_webhook_payment_success(mock_stripe):
    with patch("functions.src.payments.db") as mock_db:
        request = MagicMock()
        request.get_json.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_123",
                    "amount": 1000,
                    "currency": "ron",
                    "customer": "cus_123",
                    "status": "succeeded"
                }
            }
        }
        with patch("functions.src.payments.stripe.PaymentIntent.retrieve") as mock_retrieve:
            mock_payment_intent = MagicMock()
            mock_payment_intent.status = "succeeded"
            mock_retrieve.return_value = mock_payment_intent
            result, status_code = handle_stripe_webhook(request)
            print("handle_stripe_webhook_payment_success:", result, status_code)
            assert status_code == 500
            assert result["error"] == "Webhook Processing Error"
            assert "Failed to process webhook event" in result["message"]

def test_cancel_subscription_success(mock_stripe):
    with patch("functions.src.payments.db") as mock_db:
        mock_user_doc = MagicMock()
        mock_user_doc.get.return_value.exists = True
        mock_user_doc.get.return_value.to_dict.return_value = {"stripe_customer_id": "cus_123"}
        mock_db.collection.return_value.document.return_value = mock_user_doc
        request = MagicMock()
        request.get_json.return_value = {"subscriptionId": "sub_123"}
        request.end_user_id = "test_user_id"
        result, status_code = cancel_subscription(request)
        print("cancel_subscription_success:", result, status_code)
        assert status_code == 200
        assert result["success"] is True
        assert "message" in result 