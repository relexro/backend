import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
import json
import os

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
        
        # Extract fields
        title = data["title"].strip()
        description = data["description"].strip()
        
        # Initialize Firestore client
        db = firestore.client()
        case_ref = db.collection("cases").document()
        
        # Prepare case data
        case_data = {
            "userId": "test-user",  # Placeholder until auth is implemented
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

def get_case(request):
    """Get a case by ID."""
    pass

def list_cases(request):
    """List cases for a user or business."""
    pass

def archive_case(request):
    """Archive a case."""
    pass

def delete_case(request):
    """Delete a case."""
    pass

def upload_file(request):
    """Upload a file to a case."""
    pass

def download_file(request):
    """Download a file from a case."""
    pass
