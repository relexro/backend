import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
from firebase_admin import storage
import json
import os
import uuid
import datetime
from auth import get_authenticated_user, check_permission, PermissionCheckRequest, RESOURCE_TYPE_CASE

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK (if not already initialized)
try:
    firebase_admin.get_app()
except ValueError:
    # Use the application default credentials
    firebase_admin.initialize_app()

@functions_framework.http
def create_case(request):
    """Create a new case.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to create a case")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "title" not in data:
            logging.error("Bad Request: Missing title")
            return ({"error": "Bad Request", "message": "Title is required"}, 400)
            
        if not isinstance(data["title"], str):
            logging.error("Bad Request: Title must be a string")
            return ({"error": "Bad Request", "message": "Title must be a string"}, 400)
            
        if not data["title"].strip():
            logging.error("Bad Request: Title cannot be empty")
            return ({"error": "Bad Request", "message": "Title cannot be empty"}, 400)
        
        if "description" not in data:
            logging.error("Bad Request: Missing description")
            return ({"error": "Bad Request", "message": "Description is required"}, 400)
            
        if not isinstance(data["description"], str):
            logging.error("Bad Request: Description must be a string")
            return ({"error": "Bad Request", "message": "Description must be a string"}, 400)
            
        if not data["description"].strip():
            logging.error("Bad Request: Description cannot be empty")
            return ({"error": "Bad Request", "message": "Description cannot be empty"}, 400)

        # Validate caseTier (required field)
        if "caseTier" not in data:
            logging.error("Bad Request: Missing caseTier")
            return ({"error": "Bad Request", "message": "caseTier is required"}, 400)
            
        if not isinstance(data["caseTier"], int):
            logging.error("Bad Request: caseTier must be an integer")
            return ({"error": "Bad Request", "message": "caseTier must be an integer (1, 2, or 3)"}, 400)
            
        if data["caseTier"] not in [1, 2, 3]:
            logging.error("Bad Request: caseTier must be 1, 2, or 3")
            return ({"error": "Bad Request", "message": "caseTier must be 1, 2, or 3"}, 400)
        
        # Get the authenticated user
        user_info, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            logging.error(f"Unauthorized: {error_message}")
            return ({"error": "Unauthorized", "message": error_message}, status_code)
        
        user_id = user_info["userId"]
        logging.info(f"Authenticated user: {user_id}")
        
        # Initialize Firestore client
        db = firestore.client()

        # Define price map for case tiers (in cents)
        case_tier_prices = {
            1: 900,   # Tier 1 = €9.00
            2: 2900,  # Tier 2 = €29.00
            3: 9900   # Tier 3 = €99.00
        }
        
        # Get the expected price based on caseTier
        case_tier = data["caseTier"]
        expected_amount = case_tier_prices[case_tier]
        
        # Extract organization ID if provided
        organization_id = data.get("organizationId")
        payment_intent_id = data.get("paymentIntentId")
        
        # If organization_id is provided, check permission for creating a case
        if organization_id:
            if not isinstance(organization_id, str) or not organization_id.strip():
                logging.error("Bad Request: Invalid organizationId")
                return ({"error": "Bad Request", "message": "Organization ID must be a non-empty string"}, 400)
            
            # Check if user has permission to create a case for this organization
            permission_request = PermissionCheckRequest(
                resourceType=RESOURCE_TYPE_CASE,
                resourceId=None,  # No specific resource ID for creation
                action="create",
                organizationId=organization_id
            )
            
            has_permission, error_message = check_permission(user_id, permission_request)
            if not has_permission:
                logging.error(f"Forbidden: User {user_id} does not have permission to create a case for organization {organization_id}")
                return ({"error": "Forbidden", "message": error_message}), 403
                
        # Determine if we should check subscription for organization or user
        if organization_id:
            # Check organization subscription
            entity_ref = db.collection("organizations").document(organization_id)
            entity_type = "organization"
        else:
            # Check user subscription
            entity_ref = db.collection("users").document(user_id)
            entity_type = "user"
            
        # Get entity data to check subscription status
        entity_doc = entity_ref.get()
        if not entity_doc.exists:
            logging.error(f"{entity_type.capitalize()} not found")
            return ({"error": "Not Found", "message": f"{entity_type.capitalize()} not found"}, 404)
            
        entity_data = entity_doc.to_dict()
        
        # Check if entity has an active subscription
        subscription_status = entity_data.get("subscriptionStatus")
        subscription_plan_id = entity_data.get("subscriptionPlanId")
        current_time = datetime.datetime.now().timestamp()
        billing_cycle_start = entity_data.get("billingCycleStart")
        billing_cycle_end = entity_data.get("billingCycleEnd")
        
        # Convert Firestore timestamps to Unix timestamps for comparison
        if billing_cycle_start:
            billing_cycle_start = billing_cycle_start.timestamp()
        if billing_cycle_end:
            billing_cycle_end = billing_cycle_end.timestamp()
            
        # Check if subscription is active and within billing cycle
        has_active_subscription = (
            subscription_status == "active" and 
            subscription_plan_id and
            billing_cycle_start and
            billing_cycle_end and
            billing_cycle_start <= current_time <= billing_cycle_end
        )
        
        # Variable to store the payment status of the case
        payment_status = None
        
        # If entity has active subscription, check quota
        if has_active_subscription:
            # Get quota information
            quota_used = entity_data.get("caseQuotaUsed", 0)
            
            # Get quota total from the plan
            plan_ref = db.collection("plans").document(subscription_plan_id)
            plan_doc = plan_ref.get()
            
            if not plan_doc.exists:
                logging.error(f"Plan not found: {subscription_plan_id}")
                return ({"error": "Internal Server Error", "message": "Subscription plan details not found"}, 500)
                
            plan_data = plan_doc.to_dict()
            quota_total = plan_data.get("caseQuotaTotal", 0)
            
            # Check if quota is available
            if quota_used < quota_total:
                # Use a transaction to safely increment quota and create case
                transaction = db.transaction()
                
                @firestore.transactional
                def create_case_with_quota_in_transaction(transaction, entity_ref, quota_used, quota_total):
                    # Read the current quota usage within the transaction
                    entity_snap = entity_ref.get(transaction=transaction)
                    if not entity_snap.exists:
                        raise ValueError(f"{entity_type.capitalize()} not found in transaction")
                        
                    current_entity_data = entity_snap.to_dict()
                    current_quota_used = current_entity_data.get("caseQuotaUsed", 0)
                    
                    # Verify quota is still available
                    if current_quota_used >= quota_total:
                        raise ValueError("Quota has been exhausted by a concurrent operation")
                        
                    # Increment quota usage
                    transaction.update(entity_ref, {
                        "caseQuotaUsed": current_quota_used + 1,
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    
                    # Create the case document
                    case_ref = db.collection("cases").document()
                    case_data = {
                        "userId": user_id,
                        "title": data["title"].strip(),
                        "description": data["description"].strip(),
                        "status": "open",
                        "caseTier": case_tier,
                        "casePrice": expected_amount,
                        "paymentStatus": "covered_by_quota",
                        "creationDate": firestore.SERVER_TIMESTAMP,
                        "organizationId": organization_id
                    }
                    
                    transaction.set(case_ref, case_data)
                    
                    return case_ref.id
                
                try:
                    # Execute the transaction
                    case_id = create_case_with_quota_in_transaction(transaction, entity_ref, quota_used, quota_total)
                    payment_status = "covered_by_quota"
                    
                    # Return success response
                    response_data = {
                        "caseId": case_id,
                        "userId": user_id,
                        "caseTier": case_tier,
                        "casePrice": expected_amount,
                        "paymentStatus": payment_status,
                        "message": "Case created successfully using subscription quota"
                    }
                    
                    if organization_id:
                        response_data["organizationId"] = organization_id
                        
                    logging.info(f"Case created with ID: {case_id} using subscription quota")
                    return (response_data, 201)
                    
                except ValueError as e:
                    logging.error(f"Transaction failed: {str(e)}")
                    # Fall through to payment intent check if quota is exhausted
            
        # If we get here, entity either has no subscription, quota exhausted, or transaction failed
        # Check for payment intent
        if payment_intent_id:
            # Verify payment intent with Stripe
            try:
                import stripe
                import os
                
                # Initialize Stripe with the API key from environment variables
                stripe_api_key = os.environ.get('STRIPE_SECRET_KEY')
                if not stripe_api_key:
                    logging.error("Configuration Error: STRIPE_SECRET_KEY not set")
                    return ({"error": "Configuration Error", "message": "Payment processing is not properly configured"}, 500)
                    
                stripe.api_key = stripe_api_key
                
                # Retrieve the payment intent from Stripe
                intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                
                # Check if the payment intent status is 'succeeded'
                if intent.status != 'succeeded':
                    logging.error(f"Payment verification failed: Payment intent {payment_intent_id} has status {intent.status}, expected 'succeeded'")
                    return ({"error": "Payment Required", "message": "Payment has not been completed successfully"}, 402)
                
                # Check if the payment amount matches the expected amount for the case tier
                if intent.amount != expected_amount:
                    logging.error(f"Payment verification failed: Payment amount {intent.amount} does not match expected amount {expected_amount} for tier {case_tier}")
                    return ({"error": "Payment Verification Failed", "message": "Payment amount does not match the expected amount for the selected case tier"}, 400)
                    
                logging.info(f"Payment verification successful for payment intent {payment_intent_id}")
                payment_status = "paid_intent"
            except ImportError:
                logging.error("Stripe library not available")
                return ({"error": "Configuration Error", "message": "Payment processing is not properly configured"}, 500)
            except stripe.error.StripeError as e:
                logging.error(f"Stripe error verifying payment: {str(e)}")
                return ({"error": "Payment Verification Failed", "message": str(e)}, 400)
        else:
            # No quota, no payment intent - determine appropriate error message
            if has_active_subscription:
                logging.error("Quota exhausted and no payment intent provided")
                return ({"error": "Payment Required", "message": "Your subscription quota is exhausted. Please provide a payment for this case."}, 402)
            else:
                logging.error("No active subscription and no payment intent provided")
                return ({"error": "Payment Required", "message": "This case requires payment. Please provide a paymentIntentId."}, 402)
                
        # Create case with payment intent
        case_ref = db.collection("cases").document()
        case_data = {
            "userId": user_id,
            "title": data["title"].strip(),
            "description": data["description"].strip(),
            "status": "open",
            "caseTier": case_tier,
            "casePrice": expected_amount,
            "paymentStatus": payment_status,
            "paymentIntentId": payment_intent_id,
            "creationDate": firestore.SERVER_TIMESTAMP
        }
        
        # Add organization ID if provided
        if organization_id:
            case_data["organizationId"] = organization_id
        else:
            # Explicitly set organizationId to null for individual cases
            case_data["organizationId"] = None
            
        # Create case in Firestore
        case_ref.set(case_data)
        
        # Return success response
        response_data = {
            "caseId": case_ref.id,
            "userId": user_id,
            "caseTier": case_tier,
            "casePrice": expected_amount,
            "paymentStatus": payment_status,
            "message": "Case created successfully"
        }
        
        # Add organization ID to response if it exists
        if organization_id:
            response_data["organizationId"] = organization_id
            
        logging.info(f"Case created with ID: {case_ref.id} using payment intent")
        return (response_data, 201)
        
    except Exception as e:
        logging.error(f"Error creating case: {str(e)}")
        return ({"error": "Internal Server Error", "message": f"Failed to create case: {str(e)}"}, 500)

@functions_framework.http
def get_case(request):
    """Get a case by ID.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to get a case")
    
    try:
        # Extract case ID from the request path
        path_parts = request.path.split('/')
        case_id = path_parts[-1] if len(path_parts) > 0 else None
        
        # Validate case ID
        if not case_id or case_id == "":
            logging.error("Bad Request: Missing case ID")
            return ({"error": "Bad Request", "message": "Case ID is required"}, 400)
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the case document
        case_doc = db.collection("cases").document(case_id).get()
        
        # Check if the case exists
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
        # Convert the document to a dictionary and add the case ID
        case_data = case_doc.to_dict()
        case_data["caseId"] = case_id
        
        # Check if user has permission to view this case
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_CASE,
            resourceId=case_id,
            action="read",
            organizationId=case_data.get("organizationId")
        )
        
        has_permission, error_message = check_permission(request.user_id, permission_request)
        if not has_permission:
            logging.error(f"Forbidden: User {request.user_id} does not have permission to view case {case_id}")
            return ({"error": "Forbidden", "message": error_message}), 403
        
        # Return the case data
        logging.info(f"Successfully retrieved case with ID: {case_id}")
        return (case_data, 200)
    except Exception as e:
        logging.error(f"Error retrieving case: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to retrieve case"}, 500)

@functions_framework.http
def list_cases(request):
    """List cases for an organization or for an individual user.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to list cases")
    
    try:
        # Get the authenticated user
        user_info, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            logging.error(f"Unauthorized: {error_message}")
            return ({"error": "Unauthorized", "message": error_message}, status_code)
        
        user_id = user_info["userId"]
        logging.info(f"Authenticated user: {user_id}")
        
        # Extract organization ID from query parameters (optional)
        organization_id = request.args.get("organizationId")
        
        # Extract status filter from query parameters if provided
        status = request.args.get("status")
        
        # Validate status if provided
        valid_statuses = ["open", "closed", "archived"]
        if status and status not in valid_statuses:
            logging.warning(f"Invalid status filter: {status}, ignoring filter")
            status = None
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Extract pagination parameters if provided
        try:
            limit = int(request.args.get("limit", "50"))  # Default to 50 cases
            offset = int(request.args.get("offset", "0"))  # Default to start from beginning
        except ValueError:
            logging.warning("Invalid pagination parameters, using defaults")
            limit = 50
            offset = 0
            
        # Ensure limit is reasonable
        if limit > 100:
            limit = 100  # Cap at 100 for performance
        
        # HANDLE ORGANIZATION CASES
        if organization_id:
            logging.info(f"Listing cases for organization: {organization_id}")
            
            # Check if user has permission to list cases for this organization
            permission_request = PermissionCheckRequest(
                resourceType=RESOURCE_TYPE_CASE,
                resourceId=None,  # No specific resource ID for listing
                action="list",
                organizationId=organization_id
            )
            
            has_permission, error_message = check_permission(user_id, permission_request)
            if not has_permission:
                logging.error(f"Forbidden: User {user_id} does not have permission to list cases for organization {organization_id}")
                return ({"error": "Forbidden", "message": error_message}), 403
            
            # Create query that filters by organization ID
            query = db.collection("cases").where("organizationId", "==", organization_id)
        
        # HANDLE INDIVIDUAL CASES
        else:
            logging.info(f"Listing individual cases for user: {user_id}")
            
            # Query for cases where userId matches the authenticated user and organizationId is null
            query = db.collection("cases").where("userId", "==", user_id).where("organizationId", "==", None)
            
        # Apply status filter if provided
        if status:
            query = query.where("status", "==", status)
        
        # Get the total count (for pagination info)
        total_count = len(list(query.stream()))
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        case_docs = query.get()
        
        # Convert documents to dictionaries with case IDs
        cases = []
        for doc in case_docs:
            case_data = doc.to_dict()
            case_data["caseId"] = doc.id
            cases.append(case_data)
        
        # Return the list of cases with pagination info
        response_data = {
            "cases": cases,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "hasMore": (offset + len(cases)) < total_count
            }
        }
        
        if organization_id:
            response_data["organizationId"] = organization_id
            logging.info(f"Successfully retrieved {len(cases)} cases for organization {organization_id}")
        else:
            logging.info(f"Successfully retrieved {len(cases)} individual cases for user {user_id}")
            
        return (response_data, 200)
    except Exception as e:
        logging.error(f"Error listing cases: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to list cases"}, 500)

@functions_framework.http
def archive_case(request):
    """Archive a case by ID.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to archive a case")
    
    try:
        # Extract case ID from the request path
        path_parts = request.path.split('/')
        case_id = path_parts[-1] if len(path_parts) > 0 else None
        
        # Validate case ID
        if not case_id or case_id == "":
            logging.error("Bad Request: Missing case ID")
            return ({"error": "Bad Request", "message": "Case ID is required"}, 400)
        
        # Get the authenticated user
        user_info, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            logging.error(f"Unauthorized: {error_message}")
            return ({"error": "Unauthorized", "message": error_message}, status_code)
        
        user_id = user_info["userId"]
        logging.info(f"Authenticated user: {user_id}")
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the case document reference
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        
        # Check if the case exists
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
        # Get the case data to retrieve organizationId
        case_data = case_doc.to_dict()
        organization_id = case_data.get("organizationId")
        
        if not organization_id:
            logging.error(f"Error: Case {case_id} does not have an associated organization")
            return ({"error": "Bad Request", "message": "Case does not have an associated organization"}, 400)
        
        # Check if user has permission to archive this case
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_CASE,
            resourceId=case_id,
            action="update",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            logging.error(f"Forbidden: User {user_id} does not have permission to archive case {case_id}")
            return ({"error": "Forbidden", "message": error_message}), 403
        
        # Update the case status to archived
        case_ref.update({
            "status": "archived",
            "archiveDate": firestore.SERVER_TIMESTAMP
        })
        
        # Return success message
        logging.info(f"Successfully archived case with ID: {case_id}")
        return ({"message": "Case archived successfully"}, 200)
    except Exception as e:
        logging.error(f"Error archiving case: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to archive case"}, 500)

@functions_framework.http
def delete_case(request):
    """Mark a case as deleted (soft delete).
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to delete a case")
    
    try:
        # Extract case ID from the request path
        path_parts = request.path.split('/')
        case_id = path_parts[-1] if len(path_parts) > 0 else None
        
        # Validate case ID
        if not case_id or case_id == "":
            logging.error("Bad Request: Missing case ID")
            return ({"error": "Bad Request", "message": "Case ID is required"}, 400)
        
        # Get the authenticated user
        user_info, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            logging.error(f"Unauthorized: {error_message}")
            return ({"error": "Unauthorized", "message": error_message}, status_code)
        
        user_id = user_info["userId"]
        logging.info(f"Authenticated user: {user_id}")
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the case document reference
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        
        # Check if the case exists
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
        # Get the case data to retrieve organizationId
        case_data = case_doc.to_dict()
        organization_id = case_data.get("organizationId")
        
        if not organization_id:
            logging.error(f"Error: Case {case_id} does not have an associated organization")
            return ({"error": "Bad Request", "message": "Case does not have an associated organization"}, 400)
        
        # Check if user has permission to delete this case
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_CASE,
            resourceId=case_id,
            action="delete",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            logging.error(f"Forbidden: User {user_id} does not have permission to delete case {case_id}")
            return ({"error": "Forbidden", "message": error_message}), 403
        
        # Update the case status to deleted (soft delete)
        case_ref.update({
            "status": "deleted",
            "deletionDate": firestore.SERVER_TIMESTAMP
        })
        
        # Return success message
        logging.info(f"Successfully marked case with ID: {case_id} as deleted")
        return ({"message": "Case marked as deleted successfully"}, 200)
    except Exception as e:
        logging.error(f"Error deleting case: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to delete case"}, 500)

@functions_framework.http
def upload_file(request):
    """Upload a file to a case and store in Cloud Storage.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to upload a file")
    
    try:
        # Extract case ID from the request path
        path_parts = request.path.split('/')
        case_id = path_parts[-1] if len(path_parts) > 0 else None
        
        # Validate case ID
        if not case_id or case_id == "":
            logging.error("Bad Request: Missing case ID")
            return ({"error": "Bad Request", "message": "Case ID is required"}, 400)
        
        # Validate file presence
        if 'file' not in request.files:
            logging.error("Bad Request: No file uploaded")
            return ({"error": "Bad Request", "message": "No file uploaded"}, 400)
        
        file = request.files['file']
        
        # Validate file name
        if file.filename == '':
            logging.error("Bad Request: Empty filename")
            return ({"error": "Bad Request", "message": "Filename cannot be empty"}, 400)
        
        # Get the authenticated user
        user_info, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            logging.error(f"Unauthorized: {error_message}")
            return ({"error": "Unauthorized", "message": error_message}, status_code)
        
        user_id = user_info["userId"]
        logging.info(f"Authenticated user: {user_id}")
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Verify the case exists and get its data
        case_doc = db.collection("cases").document(case_id).get()
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
        # Get the case data to retrieve organizationId
        case_data = case_doc.to_dict()
        organization_id = case_data.get("organizationId")
        
        if not organization_id:
            logging.error(f"Error: Case {case_id} does not have an associated organization")
            return ({"error": "Bad Request", "message": "Case does not have an associated organization"}, 400)
        
        # Check if user has permission to upload files to this case
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_CASE,
            resourceId=case_id,
            action="update",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            logging.error(f"Forbidden: User {user_id} does not have permission to upload files to case {case_id}")
            return ({"error": "Forbidden", "message": error_message}), 403
        
        # Generate a unique filename
        unique_id = uuid.uuid4().hex
        original_filename = file.filename
        file_extension = os.path.splitext(original_filename)[1] if '.' in original_filename else ''
        filename = f"{unique_id}{file_extension}"
        
        # Define the storage path
        storage_path = f"cases/{case_id}/documents/{filename}"
        
        # Initialize Cloud Storage bucket
        bucket = storage.bucket("relex-files")
        blob = bucket.blob(storage_path)
        
        # Get content type or use default
        content_type = file.content_type or 'application/octet-stream'
        
        # Upload the file to Cloud Storage
        file_content = file.read()
        blob.upload_from_string(file_content, content_type=content_type)
        
        # Calculate file size
        file_size = len(file_content)
        
        # Save metadata in Firestore documents collection
        document_ref = db.collection("documents").document()
        document_data = {
            "caseId": case_id,
            "filename": filename,
            "originalFilename": original_filename,
            "fileType": content_type,
            "fileSize": file_size,
            "storagePath": storage_path,
            "uploadDate": firestore.SERVER_TIMESTAMP,
            "uploadedBy": user_id  # Now using the authenticated user ID
        }
        
        document_ref.set(document_data)
        document_id = document_ref.id
        
        # Return success response
        logging.info(f"File uploaded successfully for case {case_id} with document ID {document_id}")
        return ({
            "documentId": document_id,
            "filename": filename,
            "originalFilename": original_filename,
            "storagePath": storage_path,
            "message": "File uploaded successfully"
        }, 201)
    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}")
        return ({"error": "Internal Server Error", "message": f"Failed to upload file: {str(e)}"}, 500)

@functions_framework.http
def download_file(request):
    """Generate a signed URL for downloading a file.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to download a file")
    
    try:
        # Extract document ID from the request path
        path_parts = request.path.split('/')
        document_id = path_parts[-1] if len(path_parts) > 0 else None
        
        # Validate document ID
        if not document_id or document_id == "":
            logging.error("Bad Request: Missing document ID")
            return ({"error": "Bad Request", "message": "Document ID is required"}, 400)
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the document metadata
        document_doc = db.collection("documents").document(document_id).get()
        
        # Check if the document exists
        if not document_doc.exists:
            logging.error(f"Not Found: Document with ID {document_id} not found")
            return ({"error": "Not Found", "message": "Document not found"}, 404)
        
        # Get document data
        document_data = document_doc.to_dict()
        storage_path = document_data.get("storagePath")
        original_filename = document_data.get("originalFilename")
        
        # Validate storage path
        if not storage_path:
            logging.error(f"Error: Missing storage path for document {document_id}")
            return ({"error": "Internal Server Error", "message": "Document storage path not found"}, 500)
        
        # Initialize Cloud Storage bucket
        bucket = storage.bucket("relex-files")
        blob = bucket.blob(storage_path)
        
        # Check if the file exists in Cloud Storage
        if not blob.exists():
            logging.error(f"Not Found: File for document {document_id} not found in Cloud Storage")
            return ({"error": "Not Found", "message": "File not found in storage"}, 404)
        
        # Generate signed URL (valid for 15 minutes)
        expiration = datetime.timedelta(minutes=15)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method="GET"
        )
        
        # Return the signed URL
        logging.info(f"Generated signed URL for document {document_id}")
        return ({
            "downloadUrl": signed_url,
            "filename": original_filename,
            "documentId": document_id,
            "message": "Download URL generated successfully"
        }, 200)
    except Exception as e:
        logging.error(f"Error generating download URL: {str(e)}")
        return ({"error": "Internal Server Error", "message": f"Failed to generate download URL: {str(e)}"}, 500)

@functions_framework.http
def attach_party_to_case(request):
    """Attach a party to a case.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to attach a party to a case")
    
    try:
        # Extract case ID from the request path
        path_parts = request.path.split('/')
        if len(path_parts) < 4:
            logging.error("Bad Request: Invalid path format")
            return ({"error": "Bad Request", "message": "Invalid request path"}, 400)
            
        # Extract caseId from the path
        for i, part in enumerate(path_parts):
            if part == "cases" and i + 1 < len(path_parts):
                case_id = path_parts[i + 1]
                break
        else:
            logging.error("Bad Request: Missing caseId in path")
            return ({"error": "Bad Request", "message": "caseId is required in the path"}, 400)
        
        # Get the authenticated user
        user_info, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            logging.error(f"Unauthorized: {error_message}")
            return ({"error": "Unauthorized", "message": error_message}, status_code)
        
        user_id = user_info["userId"]
        logging.info(f"Authenticated user: {user_id}")
        
        # Extract party ID from request body
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "Request body is required"}, 400)
            
        party_id = data.get("partyId")
        if not party_id:
            logging.error("Bad Request: Missing partyId in request body")
            return ({"error": "Bad Request", "message": "partyId is required in the request body"}, 400)
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the case document
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        
        # Check if the case exists
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
        # Get the case data
        case_data = case_doc.to_dict()
        organization_id = case_data.get("organizationId")
        
        # Check if the user has permission to update this case
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_CASE,
            resourceId=case_id,
            action="update",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            logging.error(f"Forbidden: User {user_id} does not have permission to update case {case_id}")
            return ({"error": "Forbidden", "message": error_message}), 403
        
        # Get the party document to verify it exists and is owned by the user
        party_ref = db.collection("parties").document(party_id)
        party_doc = party_ref.get()
        
        # Check if the party exists
        if not party_doc.exists:
            logging.error(f"Not Found: Party with ID {party_id} not found")
            return ({"error": "Not Found", "message": "Party not found"}, 404)
        
        # Get the party data
        party_data = party_doc.to_dict()
        
        # Verify the party is owned by the user
        if party_data.get("userId") != user_id:
            logging.error(f"Forbidden: Party with ID {party_id} is not owned by user {user_id}")
            return ({"error": "Forbidden", "message": "You do not have permission to attach this party"}, 403)
        
        # Update the case document with the partyId in the attachedPartyIds array
        # If attachedPartyIds doesn't exist, it will be created
        case_ref.update({
            "attachedPartyIds": firestore.ArrayUnion([party_id]),
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        
        # Return success response
        response_data = {
            "success": True,
            "message": "Party successfully attached to case",
            "caseId": case_id,
            "partyId": party_id
        }
        
        logging.info(f"Successfully attached party {party_id} to case {case_id}")
        return (response_data, 200)
        
    except Exception as e:
        logging.error(f"Error attaching party to case: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to attach party to case"}, 500)

@functions_framework.http
def detach_party_from_case(request):
    """Detach a party from a case.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to detach a party from a case")
    
    try:
        # Extract case ID and party ID from the request path
        path_parts = request.path.split('/')
        if len(path_parts) < 6:
            logging.error("Bad Request: Invalid path format")
            return ({"error": "Bad Request", "message": "Invalid request path"}, 400)
            
        # Extract caseId and partyId from the path
        case_id = None
        party_id = None
        
        for i, part in enumerate(path_parts):
            if part == "cases" and i + 1 < len(path_parts):
                case_id = path_parts[i + 1]
            if part == "parties" and i + 1 < len(path_parts):
                party_id = path_parts[i + 1]
        
        if not case_id:
            logging.error("Bad Request: Missing caseId in path")
            return ({"error": "Bad Request", "message": "caseId is required in the path"}, 400)
            
        if not party_id:
            logging.error("Bad Request: Missing partyId in path")
            return ({"error": "Bad Request", "message": "partyId is required in the path"}, 400)
        
        # Get the authenticated user
        user_info, status_code, error_message = get_authenticated_user(request)
        if status_code != 200:
            logging.error(f"Unauthorized: {error_message}")
            return ({"error": "Unauthorized", "message": error_message}, status_code)
        
        user_id = user_info["userId"]
        logging.info(f"Authenticated user: {user_id}")
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the case document
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        
        # Check if the case exists
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
        # Get the case data
        case_data = case_doc.to_dict()
        organization_id = case_data.get("organizationId")
        
        # Check if the user has permission to update this case
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_CASE,
            resourceId=case_id,
            action="update",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            logging.error(f"Forbidden: User {user_id} does not have permission to update case {case_id}")
            return ({"error": "Forbidden", "message": error_message}), 403
        
        # Check if the party is attached to the case
        attached_party_ids = case_data.get("attachedPartyIds", [])
        if party_id not in attached_party_ids:
            logging.warning(f"Party {party_id} is not attached to case {case_id}")
            # We can either return an error or silently succeed since the end state is what the user wanted
            # Here we'll return a success with a note that the party wasn't attached
            return ({
                "success": True,
                "message": "Party was not attached to this case",
                "caseId": case_id,
                "partyId": party_id
            }, 200)
        
        # Update the case document to remove the party ID from the attachedPartyIds array
        case_ref.update({
            "attachedPartyIds": firestore.ArrayRemove([party_id]),
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        
        # Return success response
        response_data = {
            "success": True,
            "message": "Party successfully detached from case",
            "caseId": case_id,
            "partyId": party_id
        }
        
        logging.info(f"Successfully detached party {party_id} from case {case_id}")
        return (response_data, 200)
        
    except Exception as e:
        logging.error(f"Error detaching party from case: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to detach party from case"}, 500)
