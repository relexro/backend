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
        
        # Get metadata
        metadata = data.get("metadata", {})
        
        price_id = None
        if plan_id:
            # Query Firestore for plan details
            db = firestore.client()
            plan_doc = db.collection("plans").document(plan_id).get()
            
            if not plan_doc.exists:
                logging.error(f"Plan not found: {plan_id}")
                return ({"error": "Bad Request", "message": f"Plan not found: {plan_id}"}, 400)
                
            plan_data = plan_doc.to_dict()
            
            # Check if plan is active
            if not plan_data.get("isActive", False):
                logging.error(f"Plan is not active: {plan_id}")
                return ({"error": "Bad Request", "message": f"Plan is not active: {plan_id}"}, 400)
            
            # Get the Stripe price ID
            price_id = plan_data.get("stripePriceId")
            if not price_id:
                logging.error(f"Invalid plan configuration, missing stripePriceId: {plan_id}")
                return ({"error": "Internal Server Error", "message": "Invalid plan configuration"}, 500)
            
            # Add plan ID to metadata
            metadata["planId"] = plan_id
            metadata["caseQuotaTotal"] = plan_data.get("caseQuotaTotal", 0)
            
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
            
            # Ensure we're storing the organization ID explicitly for business subscriptions
            if plan_id and plan_id.startswith("business_"):
                if not organization_id:
                    logging.error("Organization ID is required for business plans")
                    return ({"error": "Bad Request", "message": "Organization ID is required for business plans"}, 400)
        
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
    
    Args:
        request (flask.Request): HTTP request object with Stripe event data.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received Stripe webhook event")
    
    # Get the webhook secret from environment variables
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    if not webhook_secret:
        logging.error("Webhook secret not configured")
        return ({"error": "Configuration Error", "message": "Webhook secret not configured"}, 500)
    
    # Get the request body and signature header
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    if not sig_header:
        logging.error("No Stripe signature header in request")
        return ({"error": "Bad Request", "message": "No Stripe signature header"}, 400)
    
    # Verify the event came from Stripe
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        logging.error(f"Invalid payload: {str(e)}")
        return ({"error": "Bad Request", "message": "Invalid payload"}, 400)
    except stripe.error.SignatureVerificationError as e:
        logging.error(f"Invalid signature: {str(e)}")
        return ({"error": "Unauthorized", "message": "Invalid signature"}, 401)
    
    # Initialize Firestore
    db = firestore.client()
    
    # Handle specific event types
    event_type = event['type']
    logging.info(f"Processing Stripe event: {event_type}")
    
    try:
        # Handle checkout.session.completed event
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            
            # Process based on the session mode
            if session.get('mode') == 'subscription':
                # Extract metadata
                metadata = session.get('metadata', {})
                plan_id = metadata.get('planId')
                user_id = metadata.get('userId')
                organization_id = metadata.get('organizationId')
                
                # Get subscription details
                subscription_id = session.get('subscription')
                if not subscription_id:
                    logging.error("No subscription ID in completed session")
                    return ({"error": "Processing Error", "message": "No subscription ID found"}, 400)
                
                # Fetch subscription to get billing period details
                subscription = stripe.Subscription.retrieve(subscription_id)
                customer_id = subscription.get('customer')
                
                # Get plan details from Firestore
                if not plan_id:
                    logging.error("No plan ID in session metadata")
                    return ({"error": "Processing Error", "message": "No plan ID in metadata"}, 400)
                
                plan_doc = db.collection("plans").document(plan_id).get()
                if not plan_doc.exists:
                    logging.error(f"Plan not found: {plan_id}")
                    return ({"error": "Processing Error", "message": f"Plan not found: {plan_id}"}, 400)
                
                plan_data = plan_doc.to_dict()
                case_quota_total = plan_data.get("caseQuotaTotal", 0)
                
                # Determine current billing period
                current_period_start = subscription.get('current_period_start')
                current_period_end = subscription.get('current_period_end')
                
                # Update user or organization document based on the subscription
                if organization_id:
                    # This is a business subscription - update organization
                    org_ref = db.collection("organizations").document(organization_id)
                    org_ref.update({
                        "stripeCustomerId": customer_id,
                        "stripeSubscriptionId": subscription_id,
                        "subscriptionPlanId": plan_id,
                        "subscriptionStatus": "active",
                        "caseQuotaTotal": case_quota_total,
                        "caseQuotaUsed": 0,
                        "billingCycleStart": firestore.Timestamp.from_seconds(current_period_start),
                        "billingCycleEnd": firestore.Timestamp.from_seconds(current_period_end),
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Updated organization {organization_id} with new subscription {subscription_id}")
                elif user_id:
                    # This is a personal subscription - update user
                    user_ref = db.collection("users").document(user_id)
                    user_ref.update({
                        "stripeCustomerId": customer_id,
                        "stripeSubscriptionId": subscription_id,
                        "subscriptionPlanId": plan_id,
                        "subscriptionStatus": "active",
                        "caseQuotaTotal": case_quota_total,
                        "caseQuotaUsed": 0,
                        "billingCycleStart": firestore.Timestamp.from_seconds(current_period_start),
                        "billingCycleEnd": firestore.Timestamp.from_seconds(current_period_end),
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Updated user {user_id} with new subscription {subscription_id}")
                else:
                    logging.error("Neither user_id nor organization_id found in session metadata")
                    return ({"error": "Processing Error", "message": "No user or organization ID in metadata"}, 400)
            
            elif session.get('mode') == 'payment':
                # This is a one-time payment (e.g., for an individual case)
                metadata = session.get('metadata', {})
                case_id = metadata.get('caseId')
                
                if case_id:
                    # Update the case payment status
                    case_ref = db.collection("cases").document(case_id)
                    case_ref.update({
                        "paymentStatus": "paid_intent",
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Updated case {case_id} payment status to 'paid_intent'")
        
        # Handle invoice.paid event (subscription renewals)
        elif event_type == 'invoice.paid':
            invoice = event['data']['object']
            
            # Only process subscription invoices
            if invoice.get('subscription'):
                subscription_id = invoice.get('subscription')
                customer_id = invoice.get('customer')
                
                # Fetch subscription to get the latest details
                subscription = stripe.Subscription.retrieve(subscription_id)
                current_period_start = subscription.get('current_period_start')
                current_period_end = subscription.get('current_period_end')
                
                # Find user or organization by subscription ID
                # First check organizations
                org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
                if len(org_query) > 0:
                    # Reset quota for organization
                    org_doc = org_query[0]
                    org_ref = db.collection("organizations").document(org_doc.id)
                    
                    # Get plan ID from organization to fetch current quota
                    plan_id = org_doc.get("subscriptionPlanId")
                    case_quota_total = org_doc.get("caseQuotaTotal", 0)
                    
                    # If plan ID exists, try to get the latest quota from the plan
                    if plan_id:
                        plan_doc = db.collection("plans").document(plan_id).get()
                        if plan_doc.exists:
                            case_quota_total = plan_doc.to_dict().get("caseQuotaTotal", case_quota_total)
                    
                    # Update organization with new billing period and reset quota
                    org_ref.update({
                        "subscriptionStatus": "active",
                        "caseQuotaUsed": 0,
                        "caseQuotaTotal": case_quota_total,
                        "billingCycleStart": firestore.Timestamp.from_seconds(current_period_start),
                        "billingCycleEnd": firestore.Timestamp.from_seconds(current_period_end),
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Reset quota for organization {org_doc.id} with subscription {subscription_id}")
                else:
                    # Check users if not found in organizations
                    user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
                    if len(user_query) > 0:
                        # Reset quota for user
                        user_doc = user_query[0]
                        user_ref = db.collection("users").document(user_doc.id)
                        
                        # Get plan ID from user to fetch current quota
                        plan_id = user_doc.get("subscriptionPlanId")
                        case_quota_total = user_doc.get("caseQuotaTotal", 0)
                        
                        # If plan ID exists, try to get the latest quota from the plan
                        if plan_id:
                            plan_doc = db.collection("plans").document(plan_id).get()
                            if plan_doc.exists:
                                case_quota_total = plan_doc.to_dict().get("caseQuotaTotal", case_quota_total)
                        
                        # Update user with new billing period and reset quota
                        user_ref.update({
                            "subscriptionStatus": "active",
                            "caseQuotaUsed": 0,
                            "caseQuotaTotal": case_quota_total,
                            "billingCycleStart": firestore.Timestamp.from_seconds(current_period_start),
                            "billingCycleEnd": firestore.Timestamp.from_seconds(current_period_end),
                            "updatedAt": firestore.SERVER_TIMESTAMP
                        })
                        logging.info(f"Reset quota for user {user_doc.id} with subscription {subscription_id}")
        
        # Handle invoice.payment_failed
        elif event_type == 'invoice.payment_failed':
            invoice = event['data']['object']
            
            # Only process subscription invoices
            if invoice.get('subscription'):
                subscription_id = invoice.get('subscription')
                
                # Mark subscription as past_due in Firestore
                # Check organizations first
                org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
                if len(org_query) > 0:
                    org_doc = org_query[0]
                    org_ref = db.collection("organizations").document(org_doc.id)
                    org_ref.update({
                        "subscriptionStatus": "past_due",
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Updated organization {org_doc.id} subscription status to 'past_due'")
                else:
                    # Check users
                    user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
                    if len(user_query) > 0:
                        user_doc = user_query[0]
                        user_ref = db.collection("users").document(user_doc.id)
                        user_ref.update({
                            "subscriptionStatus": "past_due",
                            "updatedAt": firestore.SERVER_TIMESTAMP
                        })
                        logging.info(f"Updated user {user_doc.id} subscription status to 'past_due'")
        
        # Handle customer.subscription.deleted
        elif event_type == 'customer.subscription.deleted':
            subscription = event['data']['object']
            subscription_id = subscription.get('id')
            
            # Mark subscription as canceled in Firestore
            # Check organizations first
            org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
            if len(org_query) > 0:
                org_doc = org_query[0]
                org_ref = db.collection("organizations").document(org_doc.id)
                org_ref.update({
                    "subscriptionStatus": "inactive",
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })
                logging.info(f"Updated organization {org_doc.id} subscription status to 'inactive'")
            else:
                # Check users
                user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
                if len(user_query) > 0:
                    user_doc = user_query[0]
                    user_ref = db.collection("users").document(user_doc.id)
                    user_ref.update({
                        "subscriptionStatus": "inactive",
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Updated user {user_doc.id} subscription status to 'inactive'")
        
        # Handle customer.subscription.updated
        elif event_type == 'customer.subscription.updated':
            subscription = event['data']['object']
            subscription_id = subscription.get('id')
            status = subscription.get('status')
            
            # Only update if subscription found
            org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
            if len(org_query) > 0:
                org_doc = org_query[0]
                org_ref = db.collection("organizations").document(org_doc.id)
                
                # Map Stripe status to our status
                subscription_status = "active"
                if status == "canceled" or status == "unpaid":
                    subscription_status = "inactive"
                elif status == "past_due":
                    subscription_status = "past_due"
                elif status == "active" and subscription.get('cancel_at_period_end'):
                    subscription_status = "canceled"
                
                # Update organization with new status
                update_data = {
                    "subscriptionStatus": subscription_status,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                }
                
                # If cancel_at_period_end is true, update billingCycleEnd
                if subscription.get('cancel_at_period_end'):
                    update_data["billingCycleEnd"] = firestore.Timestamp.from_seconds(subscription.get('current_period_end'))
                
                org_ref.update(update_data)
                logging.info(f"Updated organization {org_doc.id} subscription status to '{subscription_status}'")
            else:
                # Check users
                user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
                if len(user_query) > 0:
                    user_doc = user_query[0]
                    user_ref = db.collection("users").document(user_doc.id)
                    
                    # Map Stripe status to our status
                    subscription_status = "active"
                    if status == "canceled" or status == "unpaid":
                        subscription_status = "inactive"
                    elif status == "past_due":
                        subscription_status = "past_due"
                    elif status == "active" and subscription.get('cancel_at_period_end'):
                        subscription_status = "canceled"
                    
                    # Update user with new status
                    update_data = {
                        "subscriptionStatus": subscription_status,
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    }
                    
                    # If cancel_at_period_end is true, update billingCycleEnd
                    if subscription.get('cancel_at_period_end'):
                        update_data["billingCycleEnd"] = firestore.Timestamp.from_seconds(subscription.get('current_period_end'))
                    
                    user_ref.update(update_data)
                    logging.info(f"Updated user {user_doc.id} subscription status to '{subscription_status}'")
        
        # Handle payment_intent events for individual case payments
        elif event_type == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            payment_intent_id = payment_intent.get('id')
            metadata = payment_intent.get('metadata', {})
            
            # Check if this is for a case payment
            if 'caseId' in metadata:
                case_id = metadata.get('caseId')
                case_ref = db.collection("cases").document(case_id)
                case_ref.update({
                    "paymentStatus": "paid_intent",
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })
                logging.info(f"Updated case {case_id} payment status to 'paid_intent'")
        
        # Return success for any processed event
        return ({"success": True, "message": f"Webhook processed: {event_type}"}, 200)
        
    except Exception as e:
        logging.error(f"Error processing webhook event: {str(e)}")
        return ({"error": "Processing Error", "message": f"Failed to process webhook event: {str(e)}"}, 500)

@functions_framework.http
def cancel_subscription(request):
    """Cancel a Stripe subscription at the end of the current billing period.
    
    Args:
        request (flask.Request): HTTP request object with subscription ID.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to cancel subscription")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "subscriptionId" not in data:
            logging.error("Bad Request: Missing subscriptionId")
            return ({"error": "Bad Request", "message": "subscriptionId is required"}, 400)
        
        # Get authenticated user ID
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            logging.error("Unauthorized: User not authenticated")
            return ({"error": "Unauthorized", "message": "Authentication required"}, 401)
        
        subscription_id = data["subscriptionId"]
        
        # Initialize Firestore
        db = firestore.client()
        
        # Check if the subscription exists in Stripe
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error retrieving subscription: {str(e)}")
            return ({"error": "Payment Processing Error", "message": str(e)}, 400)
        
        # First, check if this is a personal subscription for the current user
        user_doc = db.collection("users").document(user_id).get()
        if user_doc.exists and user_doc.get("stripeSubscriptionId") == subscription_id:
            # User is canceling their own subscription - allowed
            pass
        else:
            # Check if it's an organization subscription
            org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).get()
            
            if not org_query:
                logging.error(f"Subscription {subscription_id} not found in database")
                return ({"error": "Not Found", "message": "Subscription not found"}, 404)
            
            org_doc = org_query[0]
            organization_id = org_doc.id
            
            # Check if user is an administrator of the organization
            membership_query = db.collection("organization_memberships").where("organizationId", "==", organization_id).where("userId", "==", user_id).where("role", "==", "administrator").limit(1).get()
            
            if not membership_query:
                logging.error(f"User {user_id} not authorized to cancel organization subscription")
                return ({"error": "Forbidden", "message": "You must be an administrator to cancel an organization subscription"}, 403)
        
        # User is authorized to cancel the subscription, proceed with cancellation
        try:
            # Cancel the subscription at the end of the current period
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            
            # Return success response
            # Note: We don't update the status in Firestore here. The webhook handler will
            # catch the subscription.updated event from Stripe and update the status accordingly.
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