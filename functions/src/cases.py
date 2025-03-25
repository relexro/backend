import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
from firebase_admin import storage
import json
import os
import uuid
import datetime

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
        
        # Validate businessId if provided
        business_id = data.get("businessId")
        if business_id is not None and (not isinstance(business_id, str) or not business_id.strip()):
            logging.error("Bad Request: Invalid businessId")
            return ({"error": "Bad Request", "message": "Business ID must be a non-empty string"}, 400)
        
        # Get the authenticated user ID
        user_id = getattr(request, 'user_id', 'test-user')
        logging.info(f"Creating case for user: {user_id}")
        
        # Extract fields
        title = data["title"].strip()
        description = data["description"].strip()
        
        # Initialize Firestore client
        db = firestore.client()
        case_ref = db.collection("cases").document()
        
        # Prepare case data
        case_data = {
            "userId": user_id,
            "businessId": business_id,
            "title": title,
            "description": description,
            "status": "open",
            "creationDate": firestore.SERVER_TIMESTAMP
        }
        
        # Write to Firestore
        case_ref.set(case_data)
        logging.info(f"Case created with ID: {case_ref.id}")
        return ({"caseId": case_ref.id, "message": "Case created successfully"}, 201)
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
    """List cases for a user or business.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to list cases")
    
    try:
        # Extract status filter from query parameters if provided
        status = request.args.get("status")
        
        # Validate status if provided
        valid_statuses = ["open", "closed", "archived"]
        if status and status not in valid_statuses:
            logging.warning(f"Invalid status filter: {status}, ignoring filter")
            status = None
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Create query
        query = db.collection("cases")
        
        # Apply status filter if provided
        if status:
            query = query.where("status", "==", status)
        
        # Execute query
        case_docs = query.get()
        
        # Convert documents to dictionaries with case IDs
        cases = []
        for doc in case_docs:
            case_data = doc.to_dict()
            case_data["caseId"] = doc.id
            cases.append(case_data)
        
        # Return the list of cases
        logging.info(f"Successfully retrieved {len(cases)} cases")
        return ({"cases": cases}, 200)
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
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the case document reference
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        
        # Check if the case exists
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
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
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the case document reference
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        
        # Check if the case exists
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
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
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Verify the case exists
        case_doc = db.collection("cases").document(case_id).get()
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
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
            "uploadedBy": "test-user"  # Placeholder until auth is implemented
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
