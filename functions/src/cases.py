import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
from firebase_admin import storage
import json
import os
import uuid
import datetime
from auth import get_authenticated_user

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

        # Validate paymentIntentId (required field)
        if "paymentIntentId" not in data:
            logging.error("Bad Request: Missing paymentIntentId")
            return ({"error": "Bad Request", "message": "paymentIntentId is required"}, 400)
            
        if not isinstance(data["paymentIntentId"], str) or not data["paymentIntentId"].strip():
            logging.error("Bad Request: Invalid paymentIntentId")
            return ({"error": "Bad Request", "message": "paymentIntentId must be a non-empty string"}, 400)
        
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
            payment_intent_id = data["paymentIntentId"]
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
        except ImportError:
            logging.error("Stripe library not available")
            return ({"error": "Configuration Error", "message": "Payment processing is not properly configured"}, 500)
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error verifying payment: {str(e)}")
            return ({"error": "Payment Verification Failed", "message": str(e)}, 400)
        
        # Extract organization ID if provided
        organization_id = data.get("organizationId")
        
        # Prepare case data
        case_data = {
            "userId": user_id,
            "title": data["title"].strip(),
            "description": data["description"].strip(),
            "status": "open",
            "caseTier": case_tier,
            "casePrice": expected_amount,
            "paymentStatus": "paid",
            "paymentIntentId": payment_intent_id,
            "creationDate": firestore.SERVER_TIMESTAMP
        }
        
        # HANDLE ORGANIZATION CASE
        if organization_id:
            logging.info(f"Creating organization case for organization: {organization_id}")
            
            if not isinstance(organization_id, str) or not organization_id.strip():
                logging.error("Bad Request: Invalid organizationId")
                return ({"error": "Bad Request", "message": "Organization ID must be a non-empty string"}, 400)
            
            # Check if user has permission to create a case for this organization
            permission_check = {
                "userId": user_id,
                "resourceId": organization_id,
                "action": "create_case",
                "resourceType": "organization"
            }
            
            # Call check_permissions function
            from auth import check_permissions as check_permissions_func
            permission_response, permission_status = check_permissions_func(type('obj', (object,), {'get_json': lambda silent=True: permission_check}))
            
            if permission_status != 200 or not permission_response.get("allowed", False):
                logging.error(f"Forbidden: User {user_id} does not have permission to create a case for organization {organization_id}")
                return ({"error": "Forbidden", "message": "You do not have permission to create a case for this organization"}, 403)
            
            # Add organization ID to the case
            case_data["organizationId"] = organization_id
            
        # HANDLE INDIVIDUAL CASE
        else:
            logging.info(f"Creating individual case for user: {user_id}")
            # Explicitly set organizationId to null for individual cases
            case_data["organizationId"] = None
        
        # Create case in Firestore
        case_ref = db.collection("cases").document()
        case_ref.set(case_data)
        
        # Add case ID to response data
        response_data = {
            "caseId": case_ref.id,
            "userId": user_id,
            "caseTier": case_tier,
            "casePrice": expected_amount,
            "message": "Case created successfully"
        }
        
        # Add organization ID to response if it exists
        if organization_id:
            response_data["organizationId"] = organization_id
        
        logging.info(f"Case created with ID: {case_ref.id}")
        return (response_data, 201)
    except Exception as e:
        logging.error(f"Error creating case: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to create case"}, 500)

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
            permission_check = {
                "userId": user_id,
                "resourceId": organization_id,
                "action": "read",
                "resourceType": "organization"
            }
            
            # Call check_permissions function
            from auth import check_permissions as check_permissions_func
            permission_response, permission_status = check_permissions_func(type('obj', (object,), {'get_json': lambda silent=True: permission_check}))
            
            if permission_status != 200 or not permission_response.get("allowed", False):
                logging.error(f"Forbidden: User {user_id} does not have permission to list cases for organization {organization_id}")
                return ({"error": "Forbidden", "message": "You do not have permission to list cases for this organization"}, 403)
            
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
        permission_check = {
            "userId": user_id,
            "resourceId": case_id,
            "action": "delete",  # archive is considered a delete action for permissions
            "resourceType": "case",
            "organizationId": organization_id
        }
        
        # Call check_permissions function
        from auth import check_permissions as check_permissions_func
        permission_response, permission_status = check_permissions_func(type('obj', (object,), {'get_json': lambda silent=True: permission_check}))
        
        if permission_status != 200 or not permission_response.get("allowed", False):
            logging.error(f"Forbidden: User {user_id} does not have permission to archive case {case_id}")
            return ({"error": "Forbidden", "message": "You do not have permission to archive this case"}, 403)
        
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
        permission_check = {
            "userId": user_id,
            "resourceId": case_id,
            "action": "delete",
            "resourceType": "case",
            "organizationId": organization_id
        }
        
        # Call check_permissions function
        from auth import check_permissions as check_permissions_func
        permission_response, permission_status = check_permissions_func(type('obj', (object,), {'get_json': lambda silent=True: permission_check}))
        
        if permission_status != 200 or not permission_response.get("allowed", False):
            logging.error(f"Forbidden: User {user_id} does not have permission to delete case {case_id}")
            return ({"error": "Forbidden", "message": "You do not have permission to delete this case"}, 403)
        
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
        permission_check = {
            "userId": user_id,
            "resourceId": case_id,
            "action": "upload_file",
            "resourceType": "case",
            "organizationId": organization_id
        }
        
        # Call check_permissions function
        from auth import check_permissions as check_permissions_func
        permission_response, permission_status = check_permissions_func(type('obj', (object,), {'get_json': lambda silent=True: permission_check}))
        
        if permission_status != 200 or not permission_response.get("allowed", False):
            logging.error(f"Forbidden: User {user_id} does not have permission to upload files to case {case_id}")
            return ({"error": "Forbidden", "message": "You do not have permission to upload files to this case"}, 403)
        
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
