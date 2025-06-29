#
import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore # Use Firestore from firebase_admin
import stripe
import os
import json
from datetime import datetime, timezone, timedelta
from vouchers import validate_voucher_code

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

# Constants for product caching
CACHE_TTL = 3600  # Cache duration in seconds (1 hour)
CACHE_DOC_PATH = "cache/stripe_products"  # Firestore path for cache

def logic_get_products(request):
    """Fetches active products and prices directly from Stripe, using Firestore for caching.

    Handles GET requests for the /v1/products endpoint. This endpoint does not require user authentication.

    Args:
        request (functions_framework.Request): The request object (not used for auth/body here).

    Returns:
        tuple: (response_body_dict, status_code)
    """
    logging.info("Request received for logic_get_products")
    cache_ref = db.document(CACHE_DOC_PATH)
    current_time_utc = datetime.now(timezone.utc)

    # 1. Check Firestore Cache
    try:
        cache_doc = cache_ref.get()
        if cache_doc.exists:
            cache_data = cache_doc.to_dict()
            cached_at_ts = cache_data.get("cachedAt") # Firestore Timestamp object
            cached_products = cache_data.get("data")

            if isinstance(cached_at_ts, datetime) and cached_products:
                # Ensure cached_at_ts is timezone-aware (Firestore timestamps are UTC)
                if cached_at_ts.tzinfo is None:
                     cached_at_ts = cached_at_ts.replace(tzinfo=timezone.utc)

                if cached_at_ts + timedelta(seconds=CACHE_TTL) > current_time_utc:
                    logging.info("Serving product list from Firestore cache.")
                    # Return the cached data structure directly
                    return cached_products, 200
                else:
                    logging.info("Firestore cache is stale.")
            else:
                logging.warning("Firestore cache document exists but is invalid.")
        else:
            logging.info("Product cache document not found in Firestore.")

    except Exception as e:
        logging.error(f"Error reading Firestore cache ({CACHE_DOC_PATH}): {str(e)}", exc_info=True)
        # Proceed to fetch from Stripe if cache read fails

    # 2. Cache Miss or Stale: Fetch from Stripe
    logging.info("Fetching products from Stripe...")
    if not stripe.api_key:
        logging.error("Stripe API key not configured.")
        return {"error": "Configuration Error", "message": "Stripe API key not configured"}, 500

    products_response = {
        "subscriptions": [],
        "cases": []
    }

    try:
        # 3. Fetch Active Products with Default Prices from Stripe
        # Use expand to include the default_price object directly
        stripe_products = stripe.Product.list(active=True, expand=['data.default_price'])

        # 4. Process Stripe Products
        for product in stripe_products.auto_paging_iter():
            price = product.get('default_price') # Access the expanded price object
            # Ensure the product has an active default price
            if not price or not price.get('active'):
                logging.warning(f"Product {product.get('id')} ({product.get('name')}) skipped (no active default price).")
                continue

            # Structure common product data
            product_data = {
                "id": product.get('id'),
                "name": product.get('name'),
                "description": product.get('description'),
                "price": {
                    "id": price.get('id'),
                    "amount": price.get('unit_amount'), # Amount in cents/smallest unit
                    "currency": price.get('currency'),
                    "type": price.get('type'), # 'recurring' or 'one_time'
                }
            }
            # Add recurring interval details if applicable
            if price.get('type') == 'recurring' and price.get('recurring'):
                recurring = price.get('recurring', {})
                product_data["price"]["recurring"] = {
                    "interval": recurring.get('interval'), # e.g., 'month', 'year'
                    "interval_count": recurring.get('interval_count')
                }

            # 5. Categorize using Stripe Metadata (CRUCIAL ASSUMPTION)
            # Assume metadata keys 'product_group' ('subscription' or 'case_tier')
            # and 'tier' ('1', '2', '3' for cases) are set on Stripe Products.
            metadata = product.get('metadata', {})
            product_group = metadata.get('product_group')
            case_tier = metadata.get('tier')

            if product_group == 'subscription':
                # Optionally add plan type (e.g., individual, org_basic) if stored in metadata
                plan_type = metadata.get('plan_type')
                if plan_type:
                    product_data['plan_type'] = plan_type
                products_response["subscriptions"].append(product_data)
            elif product_group == 'case_tier' and price.get('type') == 'one_time':
                 # Add tier information if available in metadata
                 if case_tier:
                     try:
                         product_data['tier'] = int(case_tier) # Store tier as integer
                     except ValueError:
                         logging.warning(f"Invalid non-integer tier metadata '{case_tier}' for product {product.get('id')}")
                 products_response["cases"].append(product_data)
            else:
                # Log products that don't fit the expected categories
                logging.warning(f"Product {product.get('id')} ({product.get('name')}) could not be categorized based on metadata. Group: '{product_group}', Price Type: '{price.get('type')}'")

        # Sort case tiers numerically for consistent frontend display
        products_response["cases"].sort(key=lambda x: x.get('tier', 99)) # Sort by tier, putting untiered last

        # 6. Write Fresh Data to Firestore Cache
        try:
            cache_payload = {
                "data": products_response, # Store the structured response
                "cachedAt": firestore.SERVER_TIMESTAMP # Use server timestamp for consistency
            }
            cache_ref.set(cache_payload) # Overwrite the cache document
            logging.info(f"Firestore cache updated ({CACHE_DOC_PATH}). Fetched {len(products_response['subscriptions'])} subscriptions and {len(products_response['cases'])} cases from Stripe.")
        except Exception as e:
            # Log error writing cache, but still return the fresh data fetched from Stripe
            logging.error(f"Error writing to Firestore cache ({CACHE_DOC_PATH}): {str(e)}", exc_info=True)

        # 7. Return Fresh Data
        return products_response, 200

    except stripe.error.StripeError as e:
        logging.error(f"Stripe API error fetching products: {str(e)}")
        # Don't update cache on error, return appropriate error
        return {"error": "Stripe Error", "message": f"Failed to retrieve products from Stripe: {str(e)}"}, 500
    except Exception as e:
        logging.error(f"Unexpected error fetching products: {str(e)}", exc_info=True)
        # Don't update cache on error, return internal server error
        return {"error": "Internal Server Error", "message": "An unexpected error occurred"}, 500

# Renamed function to avoid conflict with framework decorator if deployed individually
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
        user_id = getattr(request, 'end_user_id', None)
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
            payment_ref = db.collection("payments").document(payment_intent.get('id'))
            payment_data = {
                "paymentIntentId": payment_intent.get('id'),
                "amount": amount,
                "caseTier": case_tier,
                "currency": currency,
                "status": payment_intent.get('status'), # Initial status (e.g., requires_payment_method)
                "description": description,
                "userId": user_id,
                "caseId": case_id, # Link to case if provided
                "creationDate": firestore.SERVER_TIMESTAMP
            }
            payment_ref.set(payment_data)

            # Return the client secret (needed by frontend) and payment intent ID
            logging.info(f"Payment intent created with ID: {payment_intent.get('id')}")
            return ({
                "clientSecret": payment_intent.get('client_secret'),
                "paymentIntentId": payment_intent.get('id'),
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
        voucher_code = data.get("voucherCode")  # New: Extract voucher code
        # Define success/cancel URLs - consider making these configurable via env vars
        success_url = data.get("successUrl", os.environ.get("STRIPE_SUCCESS_URL", "https://relex.ro/success")) # Example default
        cancel_url = data.get("cancelUrl", os.environ.get("STRIPE_CANCEL_URL", "https://relex.ro/cancel"))   # Example default

        # Get metadata
        metadata = data.get("metadata", {})

        price_id = None # Stripe Price ID

        # Define a mapping for planIds to their environment variable names and Stripe mode
        # These plan_id keys (e.g., "individual_monthly") are what the API client should send.
        plan_details_map = {
            "individual_monthly": {"env_var": "STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY", "mode": "subscription"},
            "org_basic_monthly": {"env_var": "STRIPE_PRICE_ID_ORG_BASIC_MONTHLY", "mode": "subscription"},
            # Assuming case tiers can also be initiated via checkout session using a planId-like identifier
            "case_tier1": {"env_var": "STRIPE_PRICE_ID_CASE_TIER_1", "mode": "payment"},
            "case_tier2": {"env_var": "STRIPE_PRICE_ID_CASE_TIER_2", "mode": "payment"},
            "case_tier3": {"env_var": "STRIPE_PRICE_ID_CASE_TIER_3", "mode": "payment"},
        }

        if plan_id:
            plan_config = plan_details_map.get(plan_id)
            if not plan_config:
                logging.error(f"Unknown planId provided: {plan_id}")
                return ({"error": "Bad Request", "message": f"Unknown planId: {plan_id}"}, 400)

            env_var_name = plan_config["env_var"]
            price_id = os.environ.get(env_var_name)

            if not price_id:
                logging.error(f"Stripe Price ID for plan '{plan_id}' is not configured in environment variable '{env_var_name}'.")
                return ({"error": "Configuration Error", "message": f"Pricing for plan '{plan_id}' is not available at this moment."}, 500)

            mode = plan_config["mode"] # Override mode based on plan_id type
            metadata["planId"] = plan_id # Store the original planId in metadata for reference
            # Note: caseQuotaTotal is no longer sourced from Firestore here.
            # If quota is needed, it must be handled differently (e.g., defined in Stripe product metadata and fetched, or managed post-subscription).

        # Add case ID to metadata if provided (e.g., linking payment to a specific case)
        case_id = data.get("caseId")
        if case_id:
            metadata["caseId"] = case_id

        # Get authenticated user ID to associate with the payment/subscription
        user_id = getattr(request, 'end_user_id', None)
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

        # Validate and process voucher code if provided
        voucher_data = None
        if voucher_code:
            if not isinstance(voucher_code, str) or not voucher_code.strip():
                return ({"error": "Bad Request", "message": "Voucher code must be a non-empty string"}, 400)
            
            # Validate voucher code
            is_valid, voucher_data, error_message = validate_voucher_code(voucher_code.strip())
            if not is_valid:
                return ({"error": "InvalidVoucher", "message": error_message}, 400)
            
            # Add voucher information to metadata
            metadata["voucherCode"] = voucher_code.upper()
            metadata["voucherDiscountPercentage"] = voucher_data["discountPercentage"]
            logging.info(f"Voucher {voucher_code} validated with {voucher_data['discountPercentage']}% discount")

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

        # Prepare checkout session parameters
        checkout_params = {
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata
        }

        # Apply voucher discount if voucher is valid
        if voucher_data and voucher_data.get("discountPercentage", 0) > 0:
            # For Stripe, we can apply discounts using promotion codes or coupons
            # For now, we'll store the discount information in metadata and handle it in webhooks
            # In a more advanced implementation, you might create Stripe coupons dynamically
            checkout_params["metadata"]["appliedDiscountPercentage"] = voucher_data["discountPercentage"]
            logging.info(f"Applied {voucher_data['discountPercentage']}% discount from voucher {voucher_code}")

        # Create the checkout session in Stripe
        try:
            checkout_session = stripe.checkout.Session.create(**checkout_params)

            # Store checkout session details in Firestore for tracking
            session_ref = db.collection("checkoutSessions").document(checkout_session.get('id'))
            session_data = {
                "sessionId": checkout_session.get('id'),
                "mode": mode,
                "status": checkout_session.get('status'), # Initial status (e.g., 'open')
                "userId": user_id,
                "organizationId": organization_id,
                "caseId": case_id,
                "planId": plan_id if plan_id else None,
                "voucherCode": voucher_code.upper() if voucher_code else None,
                "voucherDiscountPercentage": voucher_data["discountPercentage"] if voucher_data else None,
                "creationDate": firestore.SERVER_TIMESTAMP
            }
            session_ref.set(session_data)

            # Return the session ID and URL (frontend redirects user to this URL)
            logging.info(f"Checkout session created with ID: {checkout_session.get('id')}")
            response_data = {
                "sessionId": checkout_session.get('id'),
                "url": checkout_session.get('url'),
                "message": "Checkout session created successfully"
            }
            
            # Add voucher information to response if voucher was applied
            if voucher_data:
                response_data["voucherApplied"] = {
                    "code": voucher_code.upper(),
                    "discountPercentage": voucher_data["discountPercentage"],
                    "description": voucher_data.get("description")
                }
            
            return (response_data, 201) # 201 Created
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error creating checkout session: {str(e)}")
            return ({"error": "Payment Processing Error", "message": str(e)}, 400)
    except Exception as e:
        logging.error(f"Error creating checkout session: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to create checkout session"}, 500)

# Placeholder for voucher logic if needed later
def logic_redeem_voucher(request):
    """Redeems a voucher code for a user or organization.

    Handles POST requests for /v1/vouchers/redeem.

    Args:
        request (flask.Request): The Flask request object.
            - Expects JSON body containing {'voucherCode': 'CODE', 'organizationId': 'org_id' (optional)}.
            - Expects 'user_id' attribute attached by an auth wrapper, representing the requesting user.

    Returns:
        tuple: (response_body_dict, status_code)
    """
    try:
        # Get and validate request body
        try:
            body = request.get_json()
        except Exception:
            return {
                'error': 'InvalidJSON',
                'message': 'Request body must be valid JSON'
            }, 400

        if not isinstance(body, dict) or 'voucherCode' not in body:
            return {
                'error': 'InvalidRequest',
                'message': 'Request body must contain voucherCode field'
            }, 400

        voucher_code = body.get('voucherCode')
        organization_id = body.get('organizationId')  # Optional

        if not isinstance(voucher_code, str) or not voucher_code.strip():
            return {
                'error': 'InvalidRequest',
                'message': 'voucherCode must be a non-empty string'
            }, 400

        if organization_id is not None and (not isinstance(organization_id, str) or not organization_id.strip()):
            return {
                'error': 'InvalidRequest',
                'message': 'organizationId must be a non-empty string if provided'
            }, 400

        # Get the requesting user ID from the request
        requesting_user_id = getattr(request, 'end_user_id', None)
        if not requesting_user_id:
            return {
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }, 401

        # Check organization permissions if needed
        if organization_id:
            permission_request = PermissionCheckRequest(
                resourceType=TYPE_ORGANIZATION,
                resourceId=organization_id,
                action="manage_billing",
                organizationId=organization_id
            )
            has_permission, error_message = check_permission(requesting_user_id, permission_request)

            if not has_permission:
                return {
                    'error': 'Forbidden',
                    'message': error_message or 'Permission denied to redeem voucher for this organization'
                }, 403

        # Use a transaction for atomic operations
        @db.transaction()
        def redeem_voucher_transaction(transaction):
            # Fetch and validate voucher
            voucher_ref = db.collection('vouchers').document(voucher_code)
            voucher_doc = voucher_ref.get(transaction=transaction)

            if not voucher_doc.exists:
                raise ValueError('Voucher code not found')

            voucher_data = voucher_doc.to_dict()

            # Validate voucher state
            if not voucher_data.get('isActive'):
                raise ValueError('Voucher is not active')

            expires_at = voucher_data.get('expiresAt')
            if expires_at and expires_at.timestamp() < datetime.now(timezone.utc).timestamp():
                raise ValueError('Voucher has expired')

            usage_limit = voucher_data.get('usageLimit', 0)
            usage_count = voucher_data.get('usageCount', 0)
            if usage_limit > 0 and usage_count >= usage_limit:
                raise ValueError('Voucher usage limit reached')

            # Get target entity (user or organization)
            target_ref = None
            if organization_id:
                target_ref = db.collection('organizations').document(organization_id)
            else:
                target_ref = db.collection('users').document(requesting_user_id)

            target_doc = target_ref.get(transaction=transaction)
            if not target_doc.exists:
                raise ValueError('Target profile not found')

            target_data = target_doc.to_dict()

            # Apply benefit based on voucher type
            voucher_type = voucher_data.get('voucherType')
            value = voucher_data.get('value', {})
            updates = {
                'updatedAt': firestore.SERVER_TIMESTAMP
            }

            if voucher_type == 'credit':
                amount = value.get('amount', 0)
                if amount <= 0:
                    raise ValueError('Invalid credit amount')
                current_balance = target_data.get('voucherBalance', 0)
                updates['voucherBalance'] = current_balance + amount

            elif voucher_type == 'free_case':
                tier = value.get('tier')
                if not isinstance(tier, int) or tier < 1 or tier > 3:  # Assuming tiers 1-3 are valid
                    raise ValueError('Invalid case tier')
                quantity = value.get('quantity', 1)
                if not isinstance(quantity, int) or quantity < 1:
                    raise ValueError('Invalid case quantity')
                free_cases = target_data.get('freeCases', {})
                tier_key = f'tier{tier}'
                updates['freeCases'] = {
                    **free_cases,
                    tier_key: free_cases.get(tier_key, 0) + quantity
                }

            elif voucher_type == 'subscription_discount':
                discount_type = value.get('type')
                if discount_type not in ['percentage', 'amount']:
                    raise ValueError('Invalid discount type')
                discount_value = value.get('value', 0)
                if not isinstance(discount_value, (int, float)) or discount_value <= 0:
                    raise ValueError('Invalid discount value')
                months = value.get('months', 1)
                if not isinstance(months, int) or months < 1:
                    raise ValueError('Invalid discount duration')
                updates['pendingDiscount'] = {
                    'type': discount_type,
                    'value': discount_value,
                    'months': months
                }
            else:
                raise ValueError('Invalid voucher type')

            # Update target entity
            target_ref.update(updates, transaction=transaction)

            # Update voucher usage
            voucher_updates = {
                'usageCount': usage_count + 1,
                f'redeemedBy.{requesting_user_id}': {
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'organizationId': organization_id
                }
            }
            voucher_ref.update(voucher_updates, transaction=transaction)

            return {
                'voucherType': voucher_type,
                'value': value,
                'description': voucher_data.get('description')
            }

        try:
            # Execute transaction
            result = redeem_voucher_transaction()

            return {
                'success': True,
                'message': 'Voucher redeemed successfully',
                'voucherType': result['voucherType'],
                'value': result['value'],
                'description': result['description']
            }, 200

        except ValueError as e:
            return {
                'error': 'InvalidVoucher',
                'message': str(e)
            }, 400

        except firestore.exceptions.TransactionError:
            return {
                'error': 'TransactionError',
                'message': 'Failed to redeem voucher due to concurrent modification'
            }, 409

    except Exception as e:
        logging.error(f"Error in logic_redeem_voucher: {str(e)}")
        return {
            'error': 'InternalError',
            'message': 'An internal error occurred'
        }, 500

# Placeholder for subscription status check if needed later
# def check_subscription_status(request):
#     """Check the status of a business subscription."""
#     pass

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
                    logging.error(f"Webhook Error: No plan ID in session metadata for session {session.get('id')}")
                    return ({"error": "Processing Error", "message": "No plan ID in metadata"}, 200)

                plan_doc = db.collection("plans").document(plan_id).get()
                if not plan_doc.exists:
                    logging.error(f"Webhook Error: Plan {plan_id} not found for session {session.get('id')}")
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
                    logging.error(f"Webhook Error: Neither user_id nor organization_id found in session metadata for session {session.get('id')}")
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
                        "stripeCheckoutSessionId": session.get('id'), # Store session ID for reference
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logging.info(f"Webhook: Updated case {case_id} payment status to 'paid_checkout'")

                # Update our payment intent record if linked via metadata (optional)
                payment_intent_id = session.get("payment_intent")
                if payment_intent_id:
                     payment_ref = db.collection("payments").document(payment_intent_id)
                     payment_ref.update({
                          "status": "succeeded", # Should be succeeded if session complete
                          "stripeCheckoutSessionId": session.get('id'),
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
                    plan_id = org_doc.to_dict().get("subscriptionPlanId")
                    case_quota_total = org_doc.to_dict().get("caseQuotaTotal", 0) # Use current value as default
                else:
                    # Check users if not found in organizations
                    user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
                    user_docs = list(user_query)
                    if len(user_docs) > 0:
                        user_doc = user_docs[0]
                        target_ref = db.collection("users").document(user_doc.id)
                        target_id = user_doc.id
                        target_type = "user"
                        plan_id = user_doc.to_dict().get("subscriptionPlanId")
                        case_quota_total = user_doc.to_dict().get("caseQuotaTotal", 0) # Use current value as default

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
                org_data = org_doc.to_dict()
                current_plan_id_in_db = org_data.get("subscriptionPlanId")
                current_quota_in_db = org_data.get("caseQuotaTotal", 0)
            else:
                # Check users
                user_query = db.collection("users").where("stripeSubscriptionId", "==", subscription_id).limit(1).stream()
                user_docs = list(user_query)
                if len(user_docs) > 0:
                    user_doc = user_docs[0]
                    target_ref = db.collection("users").document(user_doc.id)
                    target_id = user_doc.id
                    target_type = "user"
                    user_data = user_doc.to_dict()
                    current_plan_id_in_db = user_data.get("subscriptionPlanId")
                    current_quota_in_db = user_data.get("caseQuotaTotal", 0)

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
                stripe_plan_price_id = None
                items_data = subscription.get("items", {}).get("data", [])
                if items_data and len(items_data) > 0:
                    first_item = items_data[0]
                    if first_item and isinstance(first_item, dict):
                        price_data = first_item.get("price", {})
                        if price_data and isinstance(price_data, dict):
                            stripe_plan_price_id = price_data.get("id")

                firestore_plan_ref = None
                new_quota_total = current_quota_in_db # Default to existing quota

                if stripe_plan_price_id and stripe_plan_price_id != current_plan_id_in_db:
                     # Plan seems to have changed, find Firestore plan by Stripe Price ID
                     plan_query = db.collection("plans").where("stripePriceId", "==", stripe_plan_price_id).limit(1).stream()
                     plan_docs = list(plan_query)
                     if plan_docs:
                          plan_doc = plan_docs[0]
                          plan_data = plan_doc.to_dict() if plan_doc else {}
                          new_quota_total = plan_data.get("caseQuotaTotal", 0)
                          update_data["subscriptionPlanId"] = plan_doc.id
                          update_data["caseQuotaTotal"] = new_quota_total
                          # Consider resetting caseQuotaUsed if plan changes? Depends on business logic.
                          # update_data["caseQuotaUsed"] = 0
                          logging.info(f"Webhook: Plan changed for {target_type} {target_id} to {plan_doc.id} (Stripe Price ID: {stripe_plan_price_id})")
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
                    current_payment_status = case_snap.to_dict().get("paymentStatus")
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
        user_id = getattr(request, 'end_user_id', None)
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
            if subscription.get('cancel_at_period_end'):
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
