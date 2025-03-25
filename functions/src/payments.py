import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
import stripe
import os
import json

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK (if not already initialized)
try:
    firebase_admin.get_app()
except ValueError:
    # Use the application default credentials
    firebase_admin.initialize_app()

# Initialize Stripe
stripe_api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_51KGx9ySBqRYQv8xZY0PQnQkmQ2AwZsEZyHcLgjE8gMmL8GQbQYhIwzqnTCwGQ1zqOVlOZBHFGpPx')
stripe.api_key = stripe_api_key

@functions_framework.http
def create_payment_intent(request):
    """Create a Stripe Payment Intent.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to create a payment intent")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "amount" not in data:
            logging.error("Bad Request: Missing amount")
            return ({"error": "Bad Request", "message": "amount is required"}, 400)
            
        if not isinstance(data["amount"], int):
            logging.error("Bad Request: amount must be an integer")
            return ({"error": "Bad Request", "message": "amount must be an integer (in cents)"}, 400)
            
        if data["amount"] <= 0:
            logging.error("Bad Request: amount must be positive")
            return ({"error": "Bad Request", "message": "amount must be a positive integer"}, 400)
        
        # Extract fields
        amount = data["amount"]
        currency = data.get("currency", "eur")
        description = data.get("description", "Relex legal service")
        metadata = data.get("metadata", {})
        
        # Add case ID to metadata if provided
        case_id = data.get("caseId")
        if case_id:
            metadata["caseId"] = case_id
        
        # Get authenticated user ID to associate with the payment
        user_id = getattr(request, 'user_id', None)
        if user_id:
            metadata["userId"] = user_id
        
        # Create the payment intent in Stripe
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                description=description,
                metadata=metadata,
                automatic_payment_methods={"enabled": True}
            )
            
            # Store payment intent in Firestore
            db = firestore.client()
            payment_ref = db.collection("payments").document(payment_intent.id)
            payment_data = {
                "paymentIntentId": payment_intent.id,
                "amount": amount,
                "currency": currency,
                "status": payment_intent.status,
                "description": description,
                "userId": user_id,
                "caseId": case_id,
                "creationDate": firestore.SERVER_TIMESTAMP
            }
            payment_ref.set(payment_data)
            
            # Return the client secret and payment intent ID
            logging.info(f"Payment intent created with ID: {payment_intent.id}")
            return ({
                "clientSecret": payment_intent.client_secret,
                "paymentIntentId": payment_intent.id,
                "message": "Payment intent created successfully"
            }, 201)
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error creating payment intent: {str(e)}")
            return ({"error": "Payment Processing Error", "message": str(e)}, 400)
    except Exception as e:
        logging.error(f"Error creating payment intent: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to create payment intent"}, 500)

@functions_framework.http
def create_checkout_session(request):
    """Create a Stripe Checkout Session.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to create a checkout session")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "priceId" not in data and "amount" not in data:
            logging.error("Bad Request: Missing priceId or amount")
            return ({"error": "Bad Request", "message": "Either priceId (for subscriptions) or amount (for one-time payments) is required"}, 400)
        
        # Validate amount if provided
        if "amount" in data and (not isinstance(data["amount"], int) or data["amount"] <= 0):
            logging.error("Bad Request: amount must be a positive integer")
            return ({"error": "Bad Request", "message": "amount must be a positive integer (in cents)"}, 400)
        
        # Extract fields
        mode = data.get("mode", "payment")  # payment, subscription, or setup
        price_id = data.get("priceId")
        amount = data.get("amount")
        currency = data.get("currency", "eur")
        product_name = data.get("productName", "Relex Legal Service")
        success_url = data.get("successUrl", "https://relex.ro/success")
        cancel_url = data.get("cancelUrl", "https://relex.ro/cancel")
        
        # Get metadata
        metadata = data.get("metadata", {})
        
        # Add case ID to metadata if provided
        case_id = data.get("caseId")
        if case_id:
            metadata["caseId"] = case_id
        
        # Get authenticated user ID to associate with the payment
        user_id = getattr(request, 'user_id', None)
        if user_id:
            metadata["userId"] = user_id
        
        # Define line items based on whether priceId or amount is provided
        line_items = []
        if price_id:
            # Subscription with an existing price
            line_items.append({
                "price": price_id,
                "quantity": 1
            })
        else:
            # One-time payment with custom amount
            line_items.append({
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": product_name
                    },
                    "unit_amount": amount
                },
                "quantity": 1
            })
        
        # Create the checkout session in Stripe
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode=mode,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata
            )
            
            # Store checkout session in Firestore
            db = firestore.client()
            session_ref = db.collection("checkoutSessions").document(checkout_session.id)
            session_data = {
                "sessionId": checkout_session.id,
                "mode": mode,
                "status": checkout_session.status,
                "userId": user_id,
                "caseId": case_id,
                "creationDate": firestore.SERVER_TIMESTAMP
            }
            session_ref.set(session_data)
            
            # Return the session ID and URL
            logging.info(f"Checkout session created with ID: {checkout_session.id}")
            return ({
                "sessionId": checkout_session.id,
                "url": checkout_session.url,
                "message": "Checkout session created successfully"
            }, 201)
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error creating checkout session: {str(e)}")
            return ({"error": "Payment Processing Error", "message": str(e)}, 400)
    except Exception as e:
        logging.error(f"Error creating checkout session: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to create checkout session"}, 500)

def redeem_voucher(request):
    """Redeem a voucher code."""
    pass

def check_subscription_status(request):
    """Check the status of a business subscription."""
    pass

def handle_stripe_webhook(request):
    """Handle Stripe webhook events."""
    pass 