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
        if "caseTier" not in data:
            logging.error("Bad Request: Missing caseTier")
            return ({"error": "Bad Request", "message": "caseTier is required"}, 400)
            
        if not isinstance(data["caseTier"], int):
            logging.error("Bad Request: caseTier must be an integer")
            return ({"error": "Bad Request", "message": "caseTier must be an integer (1, 2, or 3)"}, 400)
            
        if data["caseTier"] not in [1, 2, 3]:
            logging.error("Bad Request: caseTier must be 1, 2, or 3")
            return ({"error": "Bad Request", "message": "caseTier must be 1, 2, or 3"}, 400)
        
        # Map caseTier to amount in cents
        case_tier_prices = {
            1: 900,   # Tier 1 = €9.00
            2: 2900,  # Tier 2 = €29.00
            3: 9900   # Tier 3 = €99.00
        }
        
        # Extract fields
        case_tier = data["caseTier"]
        amount = case_tier_prices[case_tier]
        currency = data.get("currency", "eur")
        description = data.get("description", "Relex legal service")
        metadata = data.get("metadata", {})
        
        # Add tier information to metadata
        metadata["caseTier"] = case_tier
        metadata["amount"] = amount
        
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
                "caseTier": case_tier,
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
        if "planId" not in data and "amount" not in data:
            logging.error("Bad Request: Missing planId or amount")
            return ({"error": "Bad Request", "message": "Either planId (for subscriptions) or amount (for one-time payments) is required"}, 400)
        
        # Validate amount if provided
        if "amount" in data and (not isinstance(data["amount"], int) or data["amount"] <= 0):
            logging.error("Bad Request: amount must be a positive integer")
            return ({"error": "Bad Request", "message": "amount must be a positive integer (in cents)"}, 400)
        
        # Extract fields
        mode = data.get("mode", "payment")  # payment, subscription, or setup
        plan_id = data.get("planId")
        amount = data.get("amount")
        currency = data.get("currency", "eur")
        product_name = data.get("productName", "Relex Legal Service")
        success_url = data.get("successUrl", "https://relex.ro/success")
        cancel_url = data.get("cancelUrl", "https://relex.ro/cancel")
        
        # Map planId to Stripe priceId if planId is provided
        plan_price_mapping = {
            "personal_monthly": "price_personal_monthly",  # Replace with actual Stripe price IDs
            "personal_yearly": "price_personal_yearly",
            "business_standard_monthly": "price_business_standard_monthly",
            "business_standard_yearly": "price_business_standard_yearly",
            "business_pro_monthly": "price_business_pro_monthly",
            "business_pro_yearly": "price_business_pro_yearly"
        }
        
        # Get metadata
        metadata = data.get("metadata", {})
        
        # Add planId to metadata if provided
        if plan_id:
            metadata["planId"] = plan_id
            price_id = plan_price_mapping.get(plan_id)
            if not price_id:
                logging.error(f"Invalid planId: {plan_id}")
                return ({"error": "Bad Request", "message": f"Invalid planId: {plan_id}"}, 400)
                
            # Set mode to subscription for plan-based checkouts
            mode = "subscription"
        
        # Add case ID to metadata if provided
        case_id = data.get("caseId")
        if case_id:
            metadata["caseId"] = case_id
        
        # Get authenticated user ID to associate with the payment
        user_id = getattr(request, 'user_id', None)
        if user_id:
            metadata["userId"] = user_id
        
        # Add organization ID to metadata if provided
        organization_id = data.get("organizationId")
        if organization_id:
            metadata["organizationId"] = organization_id
        
        # Define line items based on whether priceId or amount is provided
        line_items = []
        if plan_id:
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
                "organizationId": organization_id,
                "caseId": case_id,
                "planId": plan_id if plan_id else None,
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

@functions_framework.http
def handle_stripe_webhook(request):
    """Handle Stripe webhook events.
    
    Processes various Stripe webhook events to update Firestore data accordingly.
    - checkout.session.completed: Updates subscription or payment status
    - invoice.payment_failed: Updates subscription status to past_due
    - customer.subscription.deleted: Updates subscription status to canceled
    - customer.subscription.updated: Updates subscription plan details if changed
    
    Args:
        request (flask.Request): HTTP request object with Stripe webhook payload.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received Stripe webhook event")
    
    try:
        # Get the webhook payload
        payload = request.data.decode("utf-8")
        sig_header = request.headers.get("Stripe-Signature")
        
        if not sig_header:
            logging.error("Missing Stripe-Signature header")
            return ({"error": "Unauthorized", "message": "Missing Stripe-Signature header"}, 401)
        
        # Retrieve the webhook secret from environment variables
        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        if not webhook_secret:
            logging.error("STRIPE_WEBHOOK_SECRET environment variable not set")
            return ({"error": "Configuration Error", "message": "Webhook secret not configured"}, 500)
        
        # Verify the webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            # Invalid payload
            logging.error(f"Invalid payload: {str(e)}")
            return ({"error": "Bad Request", "message": "Invalid payload"}, 400)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            logging.error(f"Invalid signature: {str(e)}")
            return ({"error": "Unauthorized", "message": "Invalid signature"}, 401)
        
        # Log the event type
        event_type = event['type']
        logging.info(f"Processing Stripe event: {event_type}")
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Handle different event types
        if event_type == 'checkout.session.completed':
            # Get the session from the event
            session = event['data']['object']
            session_id = session['id']
            mode = session['mode']
            metadata = session.get('metadata', {})
            
            # Get relevant IDs from metadata
            user_id = metadata.get('userId')
            organization_id = metadata.get('organizationId')
            case_id = metadata.get('caseId')
            plan_id = metadata.get('planId')
            
            # Update the checkout session in Firestore
            session_ref = db.collection("checkoutSessions").document(session_id)
            session_ref.update({
                "status": session['status'],
                "updatedDate": firestore.SERVER_TIMESTAMP
            })
            
            if mode == 'subscription':
                # This is a subscription checkout
                customer_id = session.get('customer')
                subscription_id = session.get('subscription')
                
                if not customer_id or not subscription_id:
                    logging.error(f"Missing customer or subscription ID in session {session_id}")
                    return ({"error": "Processing Error", "message": "Missing subscription data"}, 400)
                
                # Fetch subscription details if needed
                subscription = stripe.Subscription.retrieve(subscription_id)
                current_period_end = subscription.get('current_period_end')
                
                if user_id:
                    # Personal subscription - update user's subscription status
                    user_ref = db.collection("users").document(user_id)
                    user_ref.update({
                        "subscriptionStatus": "active",
                        "stripeCustomerId": customer_id,
                        "stripeSubscriptionId": subscription_id,
                        "planId": plan_id,
                        "subscriptionCurrentPeriodEnd": current_period_end,
                        "subscriptionUpdatedDate": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Updated user {user_id} with subscription {subscription_id}")
                
                elif organization_id:
                    # Business subscription - update organization's subscription status
                    org_ref = db.collection("organizations").document(organization_id)
                    org_ref.update({
                        "subscriptionStatus": "active",
                        "stripeCustomerId": customer_id,
                        "stripeSubscriptionId": subscription_id,
                        "planId": plan_id,
                        "subscriptionCurrentPeriodEnd": current_period_end,
                        "subscriptionUpdatedDate": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Updated organization {organization_id} with subscription {subscription_id}")
                
            elif mode == 'payment' and case_id:
                # This is a one-time payment for a case
                # Update the case payment status
                case_ref = db.collection("cases").document(case_id)
                case_ref.update({
                    "paymentStatus": "paid",
                    "paymentDate": firestore.SERVER_TIMESTAMP,
                    "paymentSessionId": session_id
                })
                logging.info(f"Updated case {case_id} with payment session {session_id}")
            
        elif event_type == 'invoice.payment_failed':
            # Get the invoice from the event
            invoice = event['data']['object']
            customer_id = invoice.get('customer')
            subscription_id = invoice.get('subscription')
            
            if not customer_id or not subscription_id:
                logging.error("Missing customer or subscription ID in invoice")
                return ({"error": "Processing Error", "message": "Missing subscription data"}, 400)
            
            # Find the associated user or organization by customer ID
            user_query = db.collection("users").where("stripeCustomerId", "==", customer_id).limit(1).get()
            org_query = db.collection("organizations").where("stripeCustomerId", "==", customer_id).limit(1).get()
            
            if not user_query.empty:
                # Update user subscription status
                user_ref = db.collection("users").document(user_query[0].id)
                user_ref.update({
                    "subscriptionStatus": "past_due",
                    "subscriptionUpdatedDate": firestore.SERVER_TIMESTAMP
                })
                logging.info(f"Updated user {user_query[0].id} subscription status to past_due")
            
            elif not org_query.empty:
                # Update organization subscription status
                org_ref = db.collection("organizations").document(org_query[0].id)
                org_ref.update({
                    "subscriptionStatus": "past_due",
                    "subscriptionUpdatedDate": firestore.SERVER_TIMESTAMP
                })
                logging.info(f"Updated organization {org_query[0].id} subscription status to past_due")
            
        elif event_type == 'customer.subscription.deleted':
            # Get the subscription from the event
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            subscription_id = subscription.get('id')
            
            if not customer_id or not subscription_id:
                logging.error("Missing customer or subscription ID")
                return ({"error": "Processing Error", "message": "Missing subscription data"}, 400)
            
            # Find the associated user or organization by subscription ID
            user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
            org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
            
            if not user_query.empty:
                # Update user subscription status
                user_ref = db.collection("users").document(user_query[0].id)
                user_ref.update({
                    "subscriptionStatus": "canceled",
                    "subscriptionUpdatedDate": firestore.SERVER_TIMESTAMP
                })
                logging.info(f"Updated user {user_query[0].id} subscription status to canceled")
            
            elif not org_query.empty:
                # Update organization subscription status
                org_ref = db.collection("organizations").document(org_query[0].id)
                org_ref.update({
                    "subscriptionStatus": "canceled",
                    "subscriptionUpdatedDate": firestore.SERVER_TIMESTAMP
                })
                logging.info(f"Updated organization {org_query[0].id} subscription status to canceled")
            
        elif event_type == 'customer.subscription.updated':
            # Get the subscription from the event
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            subscription_id = subscription.get('id')
            current_period_end = subscription.get('current_period_end')
            status = subscription.get('status')
            
            if not customer_id or not subscription_id:
                logging.error("Missing customer or subscription ID")
                return ({"error": "Processing Error", "message": "Missing subscription data"}, 400)
            
            # Find the associated user or organization by subscription ID
            user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
            org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
            
            if not user_query.empty:
                # Update user subscription details
                update_data = {
                    "subscriptionStatus": status,
                    "subscriptionCurrentPeriodEnd": current_period_end,
                    "subscriptionUpdatedDate": firestore.SERVER_TIMESTAMP
                }
                
                user_ref = db.collection("users").document(user_query[0].id)
                user_ref.update(update_data)
                logging.info(f"Updated user {user_query[0].id} subscription details")
            
            elif not org_query.empty:
                # Update organization subscription details
                update_data = {
                    "subscriptionStatus": status,
                    "subscriptionCurrentPeriodEnd": current_period_end,
                    "subscriptionUpdatedDate": firestore.SERVER_TIMESTAMP
                }
                
                org_ref = db.collection("organizations").document(org_query[0].id)
                org_ref.update(update_data)
                logging.info(f"Updated organization {org_query[0].id} subscription details")
        
        # Return a success response
        return ({"success": True, "message": f"Webhook processed: {event_type}"}, 200)
        
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to process webhook"}, 500)

@functions_framework.http
def cancel_subscription(request):
    """Cancel a Stripe subscription.
    
    Args:
        request (flask.Request): HTTP request object with subscription ID.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to cancel a subscription")
    
    try:
        # Get authenticated user
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            logging.error("Unauthorized: No authenticated user")
            return ({"error": "Unauthorized", "message": "Authentication required"}, 401)
        
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "subscriptionId" not in data:
            logging.error("Bad Request: Missing subscriptionId")
            return ({"error": "Bad Request", "message": "subscriptionId is required"}, 400)
            
        subscription_id = data["subscriptionId"]
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Check permission to cancel this subscription
        # Look for the subscription in both user and organization records
        user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
        org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
        
        cancellation_allowed = False
        
        if not user_query.empty:
            # This is a user's personal subscription
            subscription_user_id = user_query[0].id
            
            # Only the subscription owner can cancel it
            if subscription_user_id == user_id:
                cancellation_allowed = True
            else:
                logging.error(f"Permission denied: User {user_id} cannot cancel subscription for user {subscription_user_id}")
                return ({"error": "Forbidden", "message": "You don't have permission to cancel this subscription"}, 403)
                
        elif not org_query.empty:
            # This is an organization subscription
            organization_id = org_query[0].id
            
            # Check if user is an admin of the organization
            member_query = db.collection("organizationMembers").where("organizationId", "==", organization_id).where("userId", "==", user_id).limit(1).get()
            
            if not member_query.empty:
                member_role = member_query[0].to_dict().get("role")
                
                # Only organization admins can cancel organization subscriptions
                if member_role == "admin":
                    cancellation_allowed = True
                else:
                    logging.error(f"Permission denied: User {user_id} has role {member_role}, not admin for organization {organization_id}")
                    return ({"error": "Forbidden", "message": "Only organization admins can cancel the subscription"}, 403)
            else:
                logging.error(f"Permission denied: User {user_id} is not a member of organization {organization_id}")
                return ({"error": "Forbidden", "message": "You don't have permission to cancel this subscription"}, 403)
        else:
            logging.error(f"Subscription not found: {subscription_id}")
            return ({"error": "Not Found", "message": "Subscription not found"}, 404)
        
        # Cancel the subscription if permission is granted
        if cancellation_allowed:
            try:
                # Cancel subscription at period end (better UX than immediate cancellation)
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
                
                # Log the cancellation request
                # Note: We don't update the status here - the webhook will handle that when 
                # the cancellation is processed by Stripe
                logging.info(f"Subscription {subscription_id} marked for cancellation at period end")
                
                return ({
                    "success": True,
                    "message": "Subscription has been scheduled for cancellation at the end of the current billing period"
                }, 200)
                
            except stripe.error.StripeError as e:
                logging.error(f"Stripe error canceling subscription: {str(e)}")
                return ({"error": "Payment Processing Error", "message": str(e)}, 400)
    except Exception as e:
        logging.error(f"Error canceling subscription: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to cancel subscription"}, 500) 