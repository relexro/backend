#
import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore # Use Firestore from firebase_admin
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

# Initialize Firestore client (using the client from firebase_admin)
db = firestore.client()

# Initialize Stripe
# It's crucial to set STRIPE_SECRET_KEY as an environment variable in your Cloud Function
stripe_api_key = os.environ.get('STRIPE_SECRET_KEY')
if stripe_api_key:
    stripe.api_key = stripe_api_key
else:
    logging.error("STRIPE_SECRET_KEY environment variable not set. Payment functions will fail.")
    # Depending on your needs, you might want to raise an exception here
    # or allow the application to continue but log the error prominently.

# Renamed function to avoid conflict with framework decorator if deployed individually
# This function now contains only the business logic.
def create_payment_intent(request):
    """Create a Stripe Payment Intent.

    Args:
        request (flask.Request): HTTP request object. Needs 'user_id' attribute set by wrapper.

    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to create a payment intent")
    # Check if Stripe key is configured before proceeding
    if not stripe.api_key:
         logging.error("Stripe API key not configured.")
         return ({"error": "Configuration Error", "message": "Stripe API key not configured"}, 500)

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
        currency = data.get("currency", "eur") # Default to EUR
        description = data.get("description", "Relex legal service")
        metadata = data.get("metadata", {}) # Allow passing additional metadata

        # Add tier information to metadata
        metadata["caseTier"] = case_tier
        metadata["amount"] = amount # Store amount in metadata for reference

        # Add case ID to metadata if provided
        case_id = data.get("caseId")
        if case_id:
            metadata["caseId"] = case_id

        # Get authenticated user ID from the request attribute set by the wrapper
        user_id = getattr(request, 'user_id', None)
        if user_id:
            metadata["userId"] = user_id
        else:
             # This case should ideally be prevented by the authentication wrapper
             logging.error("User ID not found in request context for create_payment_intent")
             return ({"error": "Internal Server Error", "message": "User context missing"}, 500)


        # Create the payment intent in Stripe
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                description=description,
                metadata=metadata,
                automatic_payment_methods={"enabled": True} # Recommended by Stripe
            )

            # Store payment intent details in Firestore for tracking
            payment_ref = db.collection("payments").document(payment_intent.id)
            payment_data = {
                "paymentIntentId": payment_intent.id,
                "amount": amount,
                "caseTier": case_tier,
                "currency": currency,
                "status": payment_intent.status, # Initial status (e.g., requires_payment_method)
                "description": description,
                "userId": user_id,
                "caseId": case_id, # Link to case if provided
                "creationDate": firestore.SERVER_TIMESTAMP
            }
            payment_ref.set(payment_data)

            # Return the client secret (needed by frontend) and payment intent ID
            logging.info(f"Payment intent created with ID: {payment_intent.id}")
            return ({
                "clientSecret": payment_intent.client_secret,
                "paymentIntentId": payment_intent.id,
                "message": "Payment intent created successfully"
            }, 201) # 201 Created
        except stripe.error.StripeError as e:
            # Handle Stripe API errors specifically
            logging.error(f"Stripe error creating payment intent: {str(e)}")
            return ({"error": "Payment Processing Error", "message": str(e)}, 400) # Use 400 for client-side payment issues
    except Exception as e:
        # Catch any other unexpected errors
        logging.error(f"Error creating payment intent: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to create payment intent"}, 500)

# Renamed function to avoid conflict with framework decorator if deployed individually
def create_checkout_session(request):
    """Create a Stripe Checkout Session.

    Args:
        request (flask.Request): HTTP request object. Needs 'user_id' attribute set by wrapper.

    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to create a checkout session")
    if not stripe.api_key:
         logging.error("Stripe API key not configured.")
         return ({"error": "Configuration Error", "message": "Stripe API key not configured"}, 500)

    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)

        # Validate required fields - need either a plan or a one-time amount
        if "planId" not in data and "amount" not in data:
            logging.error("Bad Request: Missing planId or amount")
            return ({"error": "Bad Request", "message": "Either planId (for subscriptions) or amount (for one-time payments) is required"}, 400)

        # Validate amount if provided (for one-time payments)
        if "amount" in data and (not isinstance(data["amount"], int) or data["amount"] <= 0):
            logging.error("Bad Request: amount must be a positive integer")
            return ({"error": "Bad Request", "message": "amount must be a positive integer (in cents)"}, 400)

        # Extract fields
        mode = data.get("mode", "payment")  # payment, subscription, or setup
        plan_id = data.get("planId")
        amount = data.get("amount")
        currency = data.get("currency", "eur") # Default to EUR
        product_name = data.get("productName", "Relex Legal Service") # Default product name
        # Define success/cancel URLs - consider making these configurable via env vars
        success_url = data.get("successUrl", os.environ.get("STRIPE_SUCCESS_URL", "https://relex.ro/success")) # Example default
        cancel_url = data.get("cancelUrl", os.environ.get("STRIPE_CANCEL_URL", "https://relex.ro/cancel"))   # Example default

        # Get metadata
        metadata = data.get("metadata", {})

        price_id = None # Stripe Price ID
        if plan_id:
            # Query Firestore for plan details if planId is provided
            plan_doc = db.collection("plans").document(plan_id).get()

            if not plan_doc.exists:
                logging.error(f"Plan not found: {plan_id}")
                return ({"error": "Bad Request", "message": f"Plan not found: {plan_id}"}, 400)

            plan_data = plan_doc.to_dict()

            # Check if plan is active
            if not plan_data.get("isActive", False):
                logging.error(f"Plan is not active: {plan_id}")
                return ({"error": "Bad Request", "message": f"Plan is not active: {plan_id}"}, 400)

            # Get the Stripe price ID associated with the plan
            price_id = plan_data.get("stripePriceId")
            if not price_id:
                # This indicates a configuration issue with the plan in Firestore
                logging.error(f"Invalid plan configuration, missing stripePriceId: {plan_id}")
                return ({"error": "Internal Server Error", "message": "Invalid plan configuration"}, 500)

            # Add plan ID and quota info to metadata for webhook processing
            metadata["planId"] = plan_id
            metadata["caseQuotaTotal"] = plan_data.get("caseQuotaTotal", 0)

            # Set mode to subscription for plan-based checkouts
            mode = "subscription"

        # Add case ID to metadata if provided (e.g., linking payment to a specific case)
        case_id = data.get("caseId")
        if case_id:
            metadata["caseId"] = case_id

        # Get authenticated user ID to associate with the payment/subscription
        user_id = getattr(request, 'user_id', None)
        if user_id:
            metadata["userId"] = user_id
        else:
             # This case should ideally be prevented by the authentication wrapper
             logging.error("User ID not found in request context for create_checkout_session")
             return ({"error": "Internal Server Error", "message": "User context missing"}, 500)


        # Add organization ID to metadata if provided
        organization_id = data.get("organizationId")
        if organization_id:
            metadata["organizationId"] = organization_id

            # Ensure organization ID is provided specifically for business plans
            if plan_id and plan_id.startswith("business_"): # Assuming a naming convention
                if not organization_id:
                    logging.error("Organization ID is required for business plans")
                    return ({"error": "Bad Request", "message": "Organization ID is required for business plans"}, 400)

        # Define line items based on whether it's a subscription or one-time payment
        line_items = []
        if plan_id and price_id:
            # Subscription with an existing Stripe Price ID
            line_items.append({
                "price": price_id,
                "quantity": 1
            })
        elif amount:
            # One-time payment with custom amount
            line_items.append({
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": product_name
                    },
                    "unit_amount": amount # Amount in cents
                },
                "quantity": 1
            })
        else:
            # This should not happen due to earlier validation, but as a safeguard:
            logging.error("Invalid state: No planId/priceId or amount provided for line items.")
            return ({"error": "Internal Server Error", "message": "Could not determine items for checkout"}, 500)


        # Create the checkout session in Stripe
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode=mode,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata # Pass our metadata to Stripe
            )

            # Store checkout session details in Firestore for tracking
            session_ref = db.collection("checkoutSessions").document(checkout_session.id)
            session_data = {
                "sessionId": checkout_session.id,
                "mode": mode,
                "status": checkout_session.status, # Initial status (e.g., 'open')
                "userId": user_id,
                "organizationId": organization_id,
                "caseId": case_id,
                "planId": plan_id if plan_id else None,
                "creationDate": firestore.SERVER_TIMESTAMP
            }
            session_ref.set(session_data)

            # Return the session ID and URL (frontend redirects user to this URL)
            logging.info(f"Checkout session created with ID: {checkout_session.id}")
            return ({
                "sessionId": checkout_session.id,
                "url": checkout_session.url,
                "message": "Checkout session created successfully"
            }, 201) # 201 Created
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error creating checkout session: {str(e)}")
            return ({"error": "Payment Processing Error", "message": str(e)}, 400)
    except Exception as e:
        logging.error(f"Error creating checkout session: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to create checkout session"}, 500)

# Placeholder for voucher logic if needed later
# def redeem_voucher(request):
#     """Redeem a voucher code."""
#     pass

# Placeholder for subscription status check if needed later
# def check_subscription_status(request):
#     """Check the status of a business subscription."""
#     pass

# Renamed function to avoid conflict with framework decorator if deployed individually
def handle_stripe_webhook(request):
    """Handle Stripe webhook events. IMPORTANT: Secure this endpoint properly.

    Args:
        request (flask.Request): HTTP request object with Stripe event data.

    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received Stripe webhook event")

    # Get the webhook secret from environment variables - THIS IS CRITICAL FOR SECURITY
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    if not webhook_secret:
        logging.error("CRITICAL: STRIPE_WEBHOOK_SECRET environment variable not set. Cannot verify webhook.")
        # Return 500 because this is a server configuration issue
        return ({"error": "Configuration Error", "message": "Webhook secret not configured"}, 500)

    # Get the request body and signature header
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    if not sig_header:
        logging.error("Webhook Error: No Stripe signature header in request")
        # Return 400 Bad Request as the request is missing required headers
        return ({"error": "Bad Request", "message": "Missing Stripe signature header"}, 400)

    # Verify the event came from Stripe using the webhook secret
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        # Invalid payload
        logging.error(f"Webhook Error: Invalid payload: {str(e)}")
        return ({"error": "Bad Request", "message": "Invalid payload"}, 400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature - potentially malicious request
        logging.error(f"Webhook Error: Invalid signature: {str(e)}")
        return ({"error": "Unauthorized", "message": "Invalid signature"}, 401) # Use 401 Unauthorized

    # Handle specific event types
    event_type = event['type']
    logging.info(f"Processing verified Stripe event: {event_type}")

    try:
        # Handle checkout.session.completed event
        # This event signifies a successful checkout, often the start of a subscription
        # or a completed one-time payment via Checkout.
        if event_type == 'checkout.session.completed':
            session = event['data']['object']

            # Update our record of the checkout session status
            checkout_session_ref = db.collection("checkoutSessions").document(session.id)
            checkout_session_ref.update({
                "status": session.status, # e.g., 'complete'
                "paymentStatus": session.get("payment_status"), # e.g., 'paid'
                "updatedAt": firestore.SERVER_TIMESTAMP
            })

            # Process based on the session mode (subscription or one-time payment)
            if session.get('mode') == 'subscription':
                # Extract metadata we stored during session creation
                metadata = session.get('metadata', {})
                plan_id = metadata.get('planId')
                user_id = metadata.get('userId')
                organization_id = metadata.get('organizationId')

                # Get subscription details from the event
                subscription_id = session.get('subscription')
                if not subscription_id:
                    logging.error(f"Webhook Error: No subscription ID in completed session {session.id}")
                    # Acknowledge the event but log error, might need manual check
                    return ({"error": "Processing Error", "message": "No subscription ID found"}, 200) # Return 200 so Stripe doesn't retry

                # Fetch the subscription object from Stripe for full details
                subscription = stripe.Subscription.retrieve(subscription_id)
                customer_id = subscription.get('customer')

                # Get plan details from Firestore again to ensure we have the correct quota
                if not plan_id:
                    logging.error(f"Webhook Error: No plan ID in session metadata for session {session.id}")
                    return ({"error": "Processing Error", "message": "No plan ID in metadata"}, 200)

                plan_doc = db.collection("plans").document(plan_id).get()
                if not plan_doc.exists:
                    logging.error(f"Webhook Error: Plan {plan_id} not found for session {session.id}")
                    return ({"error": "Processing Error", "message": f"Plan not found: {plan_id}"}, 200)

                plan_data = plan_doc.to_dict()
                case_quota_total = plan_data.get("caseQuotaTotal", 0)

                # Determine current billing period from the subscription object
                current_period_start = subscription.get('current_period_start')
                current_period_end = subscription.get('current_period_end')

                # Prepare the update payload for Firestore user/org document
                update_payload = {
                    "stripeCustomerId": customer_id,
                    "stripeSubscriptionId": subscription_id,
                    "subscriptionPlanId": plan_id,
                    "subscriptionStatus": "active", # Mark as active on completion
                    "caseQuotaTotal": case_quota_total,
                    "caseQuotaUsed": 0, # Reset quota on new subscription start
                    "billingCycleStart": firestore.Timestamp.from_seconds(current_period_start) if current_period_start else None,
                    "billingCycleEnd": firestore.Timestamp.from_seconds(current_period_end) if current_period_end else None,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                }

                # Update user or organization document based on metadata
                if organization_id:
                    # This is a business subscription - update organization
                    target_ref = db.collection("organizations").document(organization_id)
                    target_id = organization_id
                    target_type = "organization"
                elif user_id:
                    # This is a personal subscription - update user
                    target_ref = db.collection("users").document(user_id)
                    target_id = user_id
                    target_type = "user"
                else:
                    # Should have either user_id or organization_id from session creation
                    logging.error(f"Webhook Error: Neither user_id nor organization_id found in session metadata for session {session.id}")
                    return ({"error": "Processing Error", "message": "No user or organization ID in metadata"}, 200)

                # Perform the Firestore update
                target_ref.update(update_payload)
                logging.info(f"Webhook: Updated {target_type} {target_id} with new subscription {subscription_id}")

            elif session.get('mode') == 'payment':
                # This is a one-time payment completed via Checkout
                metadata = session.get('metadata', {})
                case_id = metadata.get('caseId')

                if case_id:
                    # Update the case payment status
                    case_ref = db.collection("cases").document(case_id)
                    case_ref.update({
                        "paymentStatus": "paid_checkout", # Indicate payment via Checkout
                        "stripeCheckoutSessionId": session.id, # Store session ID for reference
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Webhook: Updated case {case_id} payment status to 'paid_checkout'")

                # Update our payment intent record if linked via metadata (optional)
                payment_intent_id = session.get("payment_intent")
                if payment_intent_id:
                     payment_ref = db.collection("payments").document(payment_intent_id)
                     payment_ref.update({
                          "status": "succeeded", # Should be succeeded if session complete
                          "stripeCheckoutSessionId": session.id,
                          "updatedAt": firestore.SERVER_TIMESTAMP
                     })


        # Handle invoice.paid event (subscription renewals primarily)
        elif event_type == 'invoice.paid':
            invoice = event['data']['object']

            # Only process subscription invoices (ignore one-off invoices if any)
            subscription_id = invoice.get('subscription')
            if subscription_id:
                customer_id = invoice.get('customer')

                # Fetch subscription to get the latest billing period details
                subscription = stripe.Subscription.retrieve(subscription_id)
                current_period_start = subscription.get('current_period_start')
                current_period_end = subscription.get('current_period_end')

                # Find user or organization by subscription ID
                target_ref = None
                target_id = None
                target_type = None
                plan_id = None
                case_quota_total = 0

                # First check organizations
                org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
                org_docs = list(org_query)
                if len(org_docs) > 0:
                    org_doc = org_docs[0]
                    target_ref = db.collection("organizations").document(org_doc.id)
                    target_id = org_doc.id
                    target_type = "organization"
                    plan_id = org_doc.get("subscriptionPlanId")
                    case_quota_total = org_doc.get("caseQuotaTotal", 0) # Use current value as default
                else:
                    # Check users if not found in organizations
                    user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
                    user_docs = list(user_query)
                    if len(user_docs) > 0:
                        user_doc = user_docs[0]
                        target_ref = db.collection("users").document(user_doc.id)
                        target_id = user_doc.id
                        target_type = "user"
                        plan_id = user_doc.get("subscriptionPlanId")
                        case_quota_total = user_doc.get("caseQuotaTotal", 0) # Use current value as default

                if target_ref:
                    # Get the latest quota total from the plan document if possible
                    if plan_id:
                        plan_doc = db.collection("plans").document(plan_id).get()
                        if plan_doc.exists:
                            case_quota_total = plan_doc.to_dict().get("caseQuotaTotal", case_quota_total)

                    # Update Firestore document: reset quota, update billing cycle, ensure active status
                    target_ref.update({
                        "subscriptionStatus": "active", # Ensure status is active on payment
                        "caseQuotaUsed": 0, # Reset usage quota
                        "caseQuotaTotal": case_quota_total, # Update quota total if it changed in plan
                        "billingCycleStart": firestore.Timestamp.from_seconds(current_period_start) if current_period_start else None,
                        "billingCycleEnd": firestore.Timestamp.from_seconds(current_period_end) if current_period_end else None,
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Webhook: Reset quota and updated billing cycle for {target_type} {target_id} with subscription {subscription_id}")
                else:
                     logging.warning(f"Webhook: Received invoice.paid for subscription {subscription_id} but found no matching user or organization.")


        # Handle invoice.payment_failed
        elif event_type == 'invoice.payment_failed':
            invoice = event['data']['object']

            # Only process subscription invoices
            subscription_id = invoice.get('subscription')
            if subscription_id:
                # Mark subscription as past_due in Firestore
                target_ref = None
                target_id = None
                target_type = None

                # Check organizations first
                org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
                org_docs = list(org_query)
                if len(org_docs) > 0:
                    org_doc = org_docs[0]
                    target_ref = db.collection("organizations").document(org_doc.id)
                    target_id = org_doc.id
                    target_type = "organization"
                else:
                    # Check users
                    user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
                    user_docs = list(user_query)
                    if len(user_docs) > 0:
                        user_doc = user_docs[0]
                        target_ref = db.collection("users").document(user_doc.id)
                        target_id = user_doc.id
                        target_type = "user"

                if target_ref:
                    target_ref.update({
                        "subscriptionStatus": "past_due", # Indicate payment failed
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Webhook: Updated {target_type} {target_id} subscription status to 'past_due' for sub {subscription_id}")
                else:
                     logging.warning(f"Webhook: Received invoice.payment_failed for subscription {subscription_id} but found no matching user or organization.")


        # Handle customer.subscription.deleted (when subscription is definitively canceled/removed)
        elif event_type == 'customer.subscription.deleted':
            # This event occurs when a subscription is canceled immediately or reaches the end
            # of the billing period after being scheduled for cancellation.
            subscription = event['data']['object']
            subscription_id = subscription.get('id')

            # Mark subscription as inactive and clear Stripe IDs in Firestore
            target_ref = None
            target_id = None
            target_type = None

            # Check organizations first
            org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
            org_docs = list(org_query)
            if len(org_docs) > 0:
                org_doc = org_docs[0]
                target_ref = db.collection("organizations").document(org_doc.id)
                target_id = org_doc.id
                target_type = "organization"
            else:
                # Check users
                user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
                user_docs = list(user_query)
                if len(user_docs) > 0:
                    user_doc = user_docs[0]
                    target_ref = db.collection("users").document(user_doc.id)
                    target_id = user_doc.id
                    target_type = "user"

            if target_ref:
                target_ref.update({
                    "subscriptionStatus": "inactive", # Or 'canceled'
                    "stripeSubscriptionId": firestore.DELETE_FIELD, # Remove association
                    "subscriptionPlanId": firestore.DELETE_FIELD, # Remove plan link
                    # Consider whether to delete stripeCustomerId or keep for history
                    #"stripeCustomerId": firestore.DELETE_FIELD,
                    "billingCycleStart": firestore.DELETE_FIELD,
                    "billingCycleEnd": firestore.DELETE_FIELD,
                    "caseQuotaTotal": firestore.DELETE_FIELD,
                    "caseQuotaUsed": firestore.DELETE_FIELD,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })
                logging.info(f"Webhook: Updated {target_type} {target_id} subscription status to 'inactive' and cleared Stripe IDs for sub {subscription_id}")
            else:
                logging.warning(f"Webhook: Received customer.subscription.deleted for subscription {subscription_id} but found no matching user or organization.")


        # Handle customer.subscription.updated (status changes, plan changes, etc.)
        elif event_type == 'customer.subscription.updated':
            subscription = event['data']['object']
            subscription_id = subscription.get('id')
            status = subscription.get('status') # e.g., active, past_due, unpaid, canceled, incomplete, etc.
            plan_id = subscription.get("plan", {}).get("id") # Get current plan ID from Stripe object

            # Find the corresponding user or organization
            target_ref = None
            target_id = None
            target_type = None
            current_plan_id_in_db = None
            current_quota_in_db = 0

            # Check organizations first
            org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
            org_docs = list(org_query)
            if len(org_docs) > 0:
                org_doc = org_docs[0]
                target_ref = db.collection("organizations").document(org_doc.id)
                target_id = org_doc.id
                target_type = "organization"
                current_plan_id_in_db = org_doc.get("subscriptionPlanId")
                current_quota_in_db = org_doc.get("caseQuotaTotal", 0)
            else:
                # Check users
                user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
                user_docs = list(user_query)
                if len(user_docs) > 0:
                    user_doc = user_docs[0]
                    target_ref = db.collection("users").document(user_doc.id)
                    target_id = user_doc.id
                    target_type = "user"
                    current_plan_id_in_db = user_doc.get("subscriptionPlanId")
                    current_quota_in_db = user_doc.get("caseQuotaTotal", 0)

            if target_ref:
                # Prepare Firestore update payload
                update_data = { "updatedAt": firestore.SERVER_TIMESTAMP }

                # Map Stripe status to our application's status
                new_app_status = "unknown"
                if status in ["active", "trialing"]:
                    new_app_status = "active"
                    # Check if it's scheduled to cancel at period end
                    if subscription.get('cancel_at_period_end'):
                         new_app_status = "canceled" # Indicate pending cancellation
                elif status in ["canceled", "unpaid", "incomplete_expired"]:
                     # Canceled means definitively ended or failed permanently
                    new_app_status = "inactive"
                elif status in ["past_due", "incomplete"]:
                     # Needs payment or action
                    new_app_status = "past_due"

                update_data["subscriptionStatus"] = new_app_status

                # Update billing cycle dates if status is active/trialing
                if status in ["active", "trialing"]:
                     current_period_start = subscription.get('current_period_start')
                     current_period_end = subscription.get('current_period_end')
                     if current_period_start:
                          update_data["billingCycleStart"] = firestore.Timestamp.from_seconds(current_period_start)
                     if current_period_end:
                          update_data["billingCycleEnd"] = firestore.Timestamp.from_seconds(current_period_end)
                     else: # Should always have an end date for active subs
                          update_data["billingCycleEnd"] = firestore.DELETE_FIELD
                else: # If not active, clear billing cycle dates
                     update_data["billingCycleStart"] = firestore.DELETE_FIELD
                     update_data["billingCycleEnd"] = firestore.DELETE_FIELD

                # Check if the plan changed
                stripe_plan_price_id = subscription.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
                firestore_plan_ref = None
                new_quota_total = current_quota_in_db # Default to existing quota

                if stripe_plan_price_id and stripe_plan_price_id != current_plan_id_in_db:
                     # Plan seems to have changed, find Firestore plan by Stripe Price ID
                     plan_query = db.collection("plans").where("stripePriceId", "==", stripe_plan_price_id).limit(1).stream()
                     plan_docs = list(plan_query)
                     if plan_docs:
                          firestore_plan_ref = plan_docs[0]
                          new_quota_total = firestore_plan_ref.get("caseQuotaTotal", 0)
                          update_data["subscriptionPlanId"] = firestore_plan_ref.id
                          update_data["caseQuotaTotal"] = new_quota_total
                          # Consider resetting caseQuotaUsed if plan changes? Depends on business logic.
                          # update_data["caseQuotaUsed"] = 0
                          logging.info(f"Webhook: Plan changed for {target_type} {target_id} to {firestore_plan_ref.id} (Stripe Price ID: {stripe_plan_price_id})")
                     else:
                          logging.warning(f"Webhook: Plan change detected for {target_type} {target_id}, but couldn't find matching plan in Firestore for Stripe Price ID {stripe_plan_price_id}. Keeping old plan ID.")
                          update_data["subscriptionPlanId"] = current_plan_id_in_db # Keep old plan ID if new one not found
                          update_data["caseQuotaTotal"] = current_quota_in_db


                # If subscription was canceled, clear Stripe IDs and relevant fields
                if new_app_status == "inactive": # Reflects Stripe status 'canceled' etc.
                     update_data["stripeSubscriptionId"] = firestore.DELETE_FIELD
                     update_data["subscriptionPlanId"] = firestore.DELETE_FIELD
                     update_data["billingCycleStart"] = firestore.DELETE_FIELD
                     update_data["billingCycleEnd"] = firestore.DELETE_FIELD
                     update_data["caseQuotaTotal"] = firestore.DELETE_FIELD
                     update_data["caseQuotaUsed"] = firestore.DELETE_FIELD

                # Apply the updates
                target_ref.update(update_data)
                logging.info(f"Webhook: Updated {target_type} {target_id} subscription status to '{new_app_status}' based on Stripe event status '{status}'")
            else:
                 logging.warning(f"Webhook: Received customer.subscription.updated for sub {subscription_id} but found no matching user or org.")


        # Handle payment_intent.succeeded for linking one-time payments
        elif event_type == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            payment_intent_id = payment_intent.get('id')
            metadata = payment_intent.get('metadata', {})

            # Update our payment record
            payment_ref = db.collection("payments").document(payment_intent_id)
            payment_ref.update({
                 "status": payment_intent.status, # Should be 'succeeded'
                 "updatedAt": firestore.SERVER_TIMESTAMP
            })

            # Check if this payment intent is linked to a case via metadata
            if 'caseId' in metadata:
                case_id = metadata.get('caseId')
                case_ref = db.collection("cases").document(case_id)
                # Update case only if it's not already covered by quota or another payment method
                case_snap = case_ref.get()
                if case_snap.exists:
                    current_payment_status = case_snap.get("paymentStatus")
                    # Only update if not already paid or covered
                    if current_payment_status not in ["paid_intent", "paid_checkout", "covered_by_quota"]:
                         case_ref.update({
                            "paymentStatus": "paid_intent",
                            "paymentIntentId": payment_intent_id, # Link the successful PI
                            "updatedAt": firestore.SERVER_TIMESTAMP
                         })
                         logging.info(f"Webhook: Updated case {case_id} payment status to 'paid_intent'")
                    else:
                         logging.info(f"Webhook: Case {case_id} already has payment status '{current_payment_status}'. Ignoring payment_intent.succeeded.")
                else:
                     logging.warning(f"Webhook: Received payment_intent.succeeded for case {case_id} but case not found.")


        # Handle other payment intent statuses (optional, for more detailed tracking)
        elif event_type in ['payment_intent.payment_failed', 'payment_intent.canceled']:
             payment_intent = event['data']['object']
             payment_intent_id = payment_intent.get('id')
             payment_ref = db.collection("payments").document(payment_intent_id)
             # Update our payment record status
             payment_ref.update({
                 "status": payment_intent.status,
                 "updatedAt": firestore.SERVER_TIMESTAMP
             })
             logging.info(f"Webhook: Updated payment intent {payment_intent_id} status to {payment_intent.status}")


        # --- Add handlers for other relevant events as needed ---
        # e.g., customer.subscription.trial_will_end

        # Acknowledge the event was received successfully
        # Return 200 OK to Stripe unless there's a *server-side* error preventing processing.
        # For business logic errors (e.g., user not found), log it but still return 200
        # so Stripe doesn't retry indefinitely for potentially unfixable issues.
        return ({"success": True, "message": f"Webhook processed: {event_type}"}, 200)

    except Exception as e:
        # Catch-all for unexpected errors during processing
        logging.error(f"Webhook Error: Failed processing event {event_type}: {str(e)}", exc_info=True)
        # Return 500 to indicate a server-side issue; Stripe might retry.
        return ({"error": "Webhook Processing Error", "message": f"Failed to process webhook event: {str(e)}"}, 500)

# Renamed function to avoid conflict with framework decorator if deployed individually
def cancel_subscription(request):
    """Cancel a Stripe subscription at the end of the current billing period.

    Args:
        request (flask.Request): HTTP request object with subscription ID. Needs 'user_id' set by wrapper.

    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to cancel subscription")
    if not stripe.api_key:
         logging.error("Stripe API key not configured.")
         return ({"error": "Configuration Error", "message": "Stripe API key not configured"}, 500)

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

        # Get authenticated user ID from wrapper
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            # Should be caught by wrapper, but check defensively
            logging.error("Unauthorized: User not authenticated")
            return ({"error": "Unauthorized", "message": "Authentication required"}, 401)

        subscription_id = data["subscriptionId"]

        # --- Authorization Check ---
        # Verify the user has permission to cancel THIS specific subscription.
        authorized = False
        is_personal_sub = False
        org_admin = False
        target_firestore_ref = None
        organization_id_for_logging = None # For logging context

        # Check if the subscription exists in Stripe first
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            # Check if already canceled
            if subscription.cancel_at_period_end:
                 logging.info(f"Subscription {subscription_id} is already scheduled for cancellation.")
                 return ({"success": True, "message": "Subscription is already scheduled for cancellation."}, 200)
        except stripe.error.InvalidRequestError:
             # Subscription ID doesn't exist in Stripe
             logging.error(f"Subscription {subscription_id} not found in Stripe")
             return ({"error": "Not Found", "message": "Subscription not found in Stripe"}, 404)
        except stripe.error.StripeError as e:
            # Other Stripe API error
            logging.error(f"Stripe error retrieving subscription {subscription_id}: {str(e)}")
            return ({"error": "Payment Processing Error", "message": str(e)}, 400)


        # 1. Check if it's the user's personal subscription
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists and user_doc.get("stripeSubscriptionId") == subscription_id:
            authorized = True
            is_personal_sub = True
            target_firestore_ref = user_ref
        else:
            # 2. If not personal, check if it belongs to an org where user is admin
            # Find organization linked to the subscription ID
            org_query = db.collection("organizations").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
            org_docs = list(org_query)

            if org_docs:
                org_doc = org_docs[0]
                organization_id = org_doc.id
                organization_id_for_logging = organization_id # Capture for logging
                # Check if the requesting user is an admin of this organization
                membership_query = db.collection("organization_memberships").where("organizationId", "==", organization_id).where("userId", "==", user_id).where("role", "==", "administrator").limit(1).stream()
                membership_docs = list(membership_query)

                if membership_docs:
                    authorized = True
                    org_admin = True
                    target_firestore_ref = db.collection("organizations").document(organization_id)
                else:
                    # User is not admin of the org owning the subscription
                    logging.warning(f"User {user_id} attempted to cancel subscription {subscription_id} belonging to org {organization_id} but is not an admin.")
            else:
                # Subscription ID not found for user or any org
                 logging.error(f"Subscription {subscription_id} requested for cancellation by user {user_id} not found associated with the user or any organization.")


        # If authorization check failed
        if not authorized:
            return ({"error": "Forbidden", "message": "You do not have permission to cancel this subscription"}, 403)

        # --- Perform Cancellation ---
        try:
            # Cancel the subscription at the end of the current period in Stripe
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True # Schedules cancellation, doesn't cancel immediately
            )

            # Update Firestore status immediately to reflect pending cancellation
            # The webhook for 'customer.subscription.updated' will also catch this,
            # but updating here provides immediate feedback in the application.
            status_update = {
                "subscriptionStatus": "canceled", # Indicate it *will* be canceled
                "updatedAt": firestore.SERVER_TIMESTAMP
            }
            if target_firestore_ref:
                 target_firestore_ref.update(status_update)
                 if is_personal_sub:
                      logging.info(f"User {user_id} scheduled personal subscription {subscription_id} for cancellation.")
                 elif org_admin:
                      logging.info(f"Admin {user_id} scheduled org {organization_id_for_logging}'s subscription {subscription_id} for cancellation.")
            else:
                 # Should not happen if authorized
                 logging.error(f"Cannot update Firestore status for subscription {subscription_id} cancellation: target_firestore_ref is None.")


            # Return success response
            return ({
                "success": True,
                "message": "Subscription has been scheduled for cancellation at the end of the current billing period"
            }, 200)
        except stripe.error.StripeError as e:
            # Handle errors during the Stripe cancellation API call
            logging.error(f"Stripe error canceling subscription {subscription_id}: {str(e)}")
            return ({"error": "Payment Processing Error", "message": str(e)}, 400)
    except Exception as e:
        logging.error(f"Error canceling subscription: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to cancel subscription"}, 500)