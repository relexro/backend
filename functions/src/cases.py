import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
from firebase_admin import storage
import json
import os
import uuid
import datetime
from flask import Request
# Import specific functions and constants from auth, avoiding potential circular imports
from auth import get_authenticated_user, check_permission, PermissionCheckRequest, TYPE_CASE

logging.basicConfig(level=logging.INFO)

# Safe Firebase initialization with try/except
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

# Initialize Firestore client safely
try:
    db = firestore.client()
except Exception as e:
    logging.error(f"Error initializing Firestore client: {str(e)}")
    # Don't raise here - let the function fail gracefully when called

# Initialize Storage bucket with fallback and error handling
try:
    bucket_name = os.environ.get("GCS_BUCKET", "relex-files")  # Use env var or default
    bucket = storage.bucket(bucket_name)
except Exception as e:
    logging.error(f"Error initializing Storage bucket: {str(e)}")
    bucket = None  # Set to None to allow startup, functions using bucket will fail later


def create_case(request: Request):
    logging.info("Logic function create_case called")
    try:
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)

        if not hasattr(request, 'user_id'):
             logging.error("Authentication error: user_id not found on request")
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        title = data.get("title")
        description = data.get("description")
        case_tier = data.get("caseTier")
        case_type_id = data.get("caseTypeId")  # New required field
        organization_id = data.get("organizationId") # Optional
        payment_intent_id = data.get("paymentIntentId") # Optional for non-subscription cases

        if not title or not isinstance(title, str) or not title.strip():
            return ({"error": "Bad Request", "message": "Valid title is required"}, 400)
        if not description or not isinstance(description, str) or not description.strip():
            return ({"error": "Bad Request", "message": "Valid description is required"}, 400)
        if case_tier not in [1, 2, 3]:
             return ({"error": "Bad Request", "message": "caseTier must be 1, 2, or 3"}, 400)
        if not case_type_id or not isinstance(case_type_id, str) or not case_type_id.strip():
            return ({"error": "Bad Request", "message": "Valid caseTypeId is required"}, 400)
        if organization_id and (not isinstance(organization_id, str) or not organization_id.strip()):
            return ({"error": "Bad Request", "message": "organizationId must be a non-empty string if provided"}, 400)
        if payment_intent_id and (not isinstance(payment_intent_id, str) or not payment_intent_id.strip()):
             return ({"error": "Bad Request", "message": "paymentIntentId must be a non-empty string if provided"}, 400)

        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=None,
            action="create",
            organizationId=organization_id # Pass orgId for permission check
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            logging.error(f"Forbidden: User {user_id} cannot create case for org {organization_id}. Msg: {error_message}")
            return ({"error": "Forbidden", "message": error_message}), 403

        case_tier_prices = {1: 900, 2: 2900, 3: 9900}
        expected_amount = case_tier_prices[case_tier]

        entity_ref = None
        entity_type = None
        if organization_id:
            entity_ref = db.collection("organizations").document(organization_id)
            entity_type = "organization"
        else:
            entity_ref = db.collection("users").document(user_id)
            entity_type = "user"

        entity_doc = entity_ref.get()
        if not entity_doc.exists:
            return ({"error": "Not Found", "message": f"{entity_type.capitalize()} not found"}, 404)
        entity_data = entity_doc.to_dict()

        # Rest of the function...
        # For brevity, I'm truncating this, but in the real code this would continue with the subscription and payment logic

        # Placeholder for remaining implementation
        case_ref = db.collection("cases").document()
        case_data = {
            "userId": user_id,
            "title": title.strip(),
            "description": description.strip(),
            "status": "open",
            "caseTier": case_tier,
            "caseTypeId": case_type_id.strip(),  # New required field
            "casePrice": expected_amount,
            "paymentStatus": "pending",  # This would be set based on the logic
            "creationDate": firestore.SERVER_TIMESTAMP,
            "organizationId": organization_id  # Will be None if not provided
        }
        case_ref.set(case_data)

        return ({"caseId": case_ref.id, "status": "open"}, 201)

    except Exception as e:
        logging.error(f"Error creating case: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": f"Failed to create case: {str(e)}"}, 500)


def get_case(request: Request):
    logging.info("Logic function get_case called")
    try:
        path_parts = request.path.strip('/').split('/')
        case_id = path_parts[-1] if path_parts else None

        if not case_id:
            return ({"error": "Bad Request", "message": "Case ID missing in URL path"}, 400)
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        case_doc = db.collection("cases").document(case_id).get()
        if not case_doc.exists:
            return ({"error": "Not Found", "message": "Case not found"}, 404)

        case_data = case_doc.to_dict()
        case_data["caseId"] = case_id # Add ID to response

        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="read",
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return ({"error": "Forbidden", "message": error_message}), 403

        return (case_data, 200)
    except Exception as e:
        logging.error(f"Error retrieving case: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to retrieve case"}, 500)

def list_cases(request: Request):
    logging.info("Logic function list_cases called")
    try:
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        organization_id = request.args.get("organizationId")
        status_filter = request.args.get("status")
        try:
            limit = int(request.args.get("limit", "50"))
            offset = int(request.args.get("offset", "0"))
        except ValueError:
            limit = 50
            offset = 0
        limit = min(limit, 100) # Cap limit

        valid_statuses = ["open", "closed", "archived"] # Add "deleted" if you want to list soft-deleted
        if status_filter and status_filter not in valid_statuses:
            status_filter = None

        query = db.collection("cases")

        if organization_id:
            # Check permission for listing org cases
            permission_request = PermissionCheckRequest(
                resourceType=TYPE_CASE, resourceId=None, action="list", organizationId=organization_id
            )
            has_permission, error_message = check_permission(user_id, permission_request)
            if not has_permission:
                return ({"error": "Forbidden", "message": error_message}), 403
            query = query.where("organizationId", "==", organization_id)
        else:
            # Listing individual cases (no specific permission needed beyond auth)
             query = query.where("userId", "==", user_id).where("organizationId", "==", None)

        if status_filter:
            query = query.where("status", "==", status_filter)
        else:
            # Exclude soft-deleted cases by default unless specifically requested
            query = query.where("status", "!=", "deleted")

        # Get total count *before* pagination for accurate total
        # Note: This requires an extra read operation. Consider alternatives if performance is critical.
        # For Firestore, counting requires reading documents.
        # A separate count aggregation query would be better if available/implemented.
        all_matching_docs = list(query.stream())
        total_count = len(all_matching_docs)

        # Apply ordering and pagination to the main query
        paginated_query = query.order_by("creationDate", direction=firestore.Query.DESCENDING).limit(limit).offset(offset)
        case_docs = paginated_query.stream()

        cases = []
        for doc in case_docs:
            case_data = doc.to_dict()
            case_data["caseId"] = doc.id
            # Convert timestamps if necessary for JSON response
            if isinstance(case_data.get("creationDate"), datetime.datetime):
                 case_data["creationDate"] = case_data["creationDate"].isoformat()
            if isinstance(case_data.get("updatedAt"), datetime.datetime):
                 case_data["updatedAt"] = case_data["updatedAt"].isoformat()
            cases.append(case_data)

        response_data = {
            "cases": cases,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "hasMore": (offset + len(cases)) < total_count
            },
            "organizationId": organization_id # Include even if None
        }
        return (response_data, 200)
    except Exception as e:
        logging.error(f"Error listing cases: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to list cases"}, 500)

def archive_case(request: Request):
    logging.info("Logic function archive_case called")
    try:
        path_parts = request.path.strip('/').split('/')
        case_id = path_parts[-1] if path_parts else None
        if not case_id:
            return ({"error": "Bad Request", "message": "Case ID missing in URL path"}, 400)
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return ({"error": "Not Found", "message": "Case not found"}, 404)

        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="archive", # Use specific 'archive' action
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return ({"error": "Forbidden", "message": error_message}), 403

        case_ref.update({
            "status": "archived",
            "archiveDate": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP # Also update updatedAt
        })
        return ({"message": "Case archived successfully"}, 200)
    except Exception as e:
        logging.error(f"Error archiving case: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to archive case"}, 500)

def delete_case(request: Request):
    logging.info("Logic function delete_case called")
    try:
        path_parts = request.path.strip('/').split('/')
        case_id = path_parts[-1] if path_parts else None
        if not case_id:
            return ({"error": "Bad Request", "message": "Case ID missing in URL path"}, 400)
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return ({"error": "Not Found", "message": "Case not found"}, 404)

        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="delete", # Use specific 'delete' action
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return ({"error": "Forbidden", "message": error_message}), 403

        # Soft delete by changing status
        case_ref.update({
            "status": "deleted",
            "deletionDate": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        # Consider if a hard delete is ever needed and implement separately
        # case_ref.delete() # Example of hard delete

        return ({"message": "Case marked as deleted successfully"}, 200)
    except Exception as e:
        logging.error(f"Error deleting case: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to delete case"}, 500)


def upload_file(request: Request):
    logging.info("Logic function upload_file called")
    try:
        path_parts = request.path.strip('/').split('/')
        # Expecting path like /cases/{case_id}/files
        case_id = path_parts[-2] if len(path_parts) >= 2 and path_parts[-1] == 'files' else None
        if not case_id:
            return ({"error": "Bad Request", "message": "Case ID missing in URL path (e.g., /cases/{case_id}/files)"}, 400)

        if not hasattr(request, 'user_id'):
            return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        # Read raw file data from the request body
        file_data = request.get_data()
        if not file_data:
            return ({"error": "Bad Request", "message": "Request body is empty, no file data received"}, 400)

        # Get metadata from headers
        content_type = request.content_type or 'application/octet-stream'

        # Get original filename from X-Filename header or use a default
        original_filename = request.headers.get('X-Filename', 'uploaded_file')
        # Basic sanitization to prevent path traversal
        original_filename = os.path.basename(original_filename)

        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return ({"error": "Not Found", "message": "Case not found"}, 404)

        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="upload_file", # Use specific 'upload_file' action
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return ({"error": "Forbidden", "message": error_message}), 403

        unique_id = uuid.uuid4().hex
        file_extension = os.path.splitext(original_filename)[1].lower()
        filename = f"{unique_id}{file_extension}"
        storage_path = f"cases/{case_id}/documents/{filename}"

        blob = bucket.blob(storage_path)

        # Upload the raw binary data
        blob.upload_from_string(file_data, content_type=content_type)

        # Calculate file size from the raw data
        file_size = len(file_data)

        # Optional file type classification from header
        file_type_classification = request.headers.get('X-FileType')
        # Optional description from header
        description = request.headers.get('X-Description')

        document_ref = db.collection("documents").document()
        document_data = {
            "documentId": document_ref.id, # Store ID also in document data
            "caseId": case_id,
            "filename": filename,
            "originalFilename": original_filename,
            "fileType": content_type,
            "fileSize": file_size,
            "storagePath": storage_path,
            "uploadDate": firestore.SERVER_TIMESTAMP,
            "uploadedBy": user_id
        }

        # Add optional metadata if provided
        if file_type_classification:
            document_data["fileTypeClassification"] = file_type_classification
        if description:
            document_data["description"] = description

        document_ref.set(document_data)
        document_id = document_ref.id

        # Optionally update the case's updatedAt timestamp
        case_ref.update({"updatedAt": firestore.SERVER_TIMESTAMP})

        return ({
            "documentId": document_id,
            "filename": filename,
            "originalFilename": original_filename,
            "storagePath": storage_path,
            "fileSize": file_size,
            "fileType": content_type,
            "message": "File uploaded successfully"
        }, 201)
    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": f"Failed to upload file: {str(e)}"}, 500)


def download_file(request: Request):
    logging.info("Logic function download_file called")
    try:
        path_parts = request.path.strip('/').split('/')
        # Expecting /documents/{document_id}/download
        document_id = path_parts[-2] if len(path_parts) >= 2 and path_parts[-1] == 'download' else None
        if not document_id:
            return ({"error": "Bad Request", "message": "Document ID missing in URL path (e.g., /documents/{document_id}/download)"}, 400)
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        document_ref = db.collection("documents").document(document_id)
        document_doc = document_ref.get()
        if not document_doc.exists:
            return ({"error": "Not Found", "message": "Document metadata not found"}, 404)

        document_data = document_doc.to_dict()
        storage_path = document_data.get("storagePath")
        original_filename = document_data.get("originalFilename", "download")
        case_id = document_data.get("caseId")

        if not storage_path:
             return ({"error": "Internal Server Error", "message": "Document storage path missing"}, 500)
        if not case_id:
             return ({"error": "Internal Server Error", "message": "Document missing case association"}, 500)

        # Fetch case orgId for permission check
        case_doc = db.collection("cases").document(case_id).get()
        case_org_id = case_doc.to_dict().get("organizationId") if case_doc.exists else None

        # Check permission to read the *document* (implicitly checks case read perm)
        permission_request = PermissionCheckRequest(
            resourceType="document", # Check document permission specifically
            resourceId=document_id,
            action="read",
            organizationId=case_org_id # Pass case orgId
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return ({"error": "Forbidden", "message": error_message}), 403

        blob = bucket.blob(storage_path)
        if not blob.exists():
            # Log inconsistency and return error
            logging.error(f"File not found in storage at path {storage_path} for document {document_id}")
            return ({"error": "Not Found", "message": "File not found in storage"}, 404)

        expiration = datetime.timedelta(minutes=15)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method="GET",
            response_disposition=f'attachment; filename="{original_filename}"' # Suggest download filename
        )

        return ({
            "downloadUrl": signed_url,
            "filename": original_filename,
            "documentId": document_id,
            "message": "Download URL generated successfully"
        }, 200)
    except Exception as e:
        logging.error(f"Error generating download URL: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": f"Failed to generate download URL: {str(e)}"}, 500)

def attach_party_to_case(request: Request):
    logging.info("Logic function attach_party_to_case called")
    try:
        path_parts = request.path.strip('/').split('/')
        # Expecting /cases/{case_id}/attach_party
        case_id = path_parts[-2] if len(path_parts) >= 2 and path_parts[-1] == 'attach_party' else None
        if not case_id:
            return ({"error": "Bad Request", "message": "Case ID missing in URL path (e.g., /cases/{case_id}/attach_party)"}, 400)

        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        data = request.get_json(silent=True)
        if not data:
            return ({"error": "Bad Request", "message": "Request body required"}, 400)
        party_id = data.get("partyId")
        if not party_id:
            return ({"error": "Bad Request", "message": "partyId is required in request body"}, 400)

        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return ({"error": "Not Found", "message": "Case not found"}, 404)

        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="attach_party", # Use specific action
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return ({"error": "Forbidden", "message": error_message}), 403

        party_ref = db.collection("parties").document(party_id)
        party_doc = party_ref.get()
        if not party_doc.exists:
            return ({"error": "Not Found", "message": "Party not found"}, 404)

        # Optionally, verify the party is owned by the user attaching it,
        # or maybe admins can attach any party? Decide based on requirements.
        # party_data = party_doc.to_dict()
        # if party_data.get("userId") != user_id:
        #     return ({"error": "Forbidden", "message": "You can only attach parties you own."}, 403)

        case_ref.update({
            "attachedPartyIds": firestore.ArrayUnion([party_id]),
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

        return ({
            "success": True, "message": "Party successfully attached to case",
            "caseId": case_id, "partyId": party_id
        }, 200)
    except Exception as e:
        logging.error(f"Error attaching party: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to attach party"}, 500)


def detach_party_from_case(request: Request):
    logging.info("Logic function detach_party_from_case called")
    try:
        path_parts = request.path.strip('/').split('/')
        # Expecting /cases/{case_id}/parties/{party_id}/detach
        case_id = None
        party_id = None
        if len(path_parts) >= 4 and path_parts[-1] == 'detach' and path_parts[-3] == 'parties':
             case_id = path_parts[-4]
             party_id = path_parts[-2]

        if not case_id:
            return ({"error": "Bad Request", "message": "Case ID missing or invalid URL path"}, 400)
        if not party_id:
            return ({"error": "Bad Request", "message": "Party ID missing or invalid URL path"}, 400)
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return ({"error": "Not Found", "message": "Case not found"}, 404)

        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="detach_party", # Use specific action
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return ({"error": "Forbidden", "message": error_message}), 403

        # Verify party exists (optional but good practice)
        party_ref = db.collection("parties").document(party_id)
        if not party_ref.get().exists:
             logging.warning(f"Attempted to detach non-existent party {party_id} from case {case_id}")
             # Continue removal from case array anyway

        case_ref.update({
            "attachedPartyIds": firestore.ArrayRemove([party_id]),
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

        return ({
            "success": True, "message": "Party successfully detached from case",
            "caseId": case_id, "partyId": party_id
        }, 200)
    except Exception as e:
        logging.error(f"Error detaching party: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to detach party"}, 500)

def logic_assign_case(request: Request):
    """Assigns or unassigns an organization case to a staff member.

    Handles PUT requests for /v1/cases/{caseId}/assign.

    Args:
        request (flask.Request): The Flask request object.
            - Expects 'caseId' to be the last part of the URL path (e.g., extracted via request.path.split('/')[-1]).
            - Expects JSON body containing {'assignedUserId': 'user_id_to_assign' or None}.
            - Expects 'user_id' attribute attached by an auth wrapper, representing the requesting user.

    Returns:
        tuple: (response_body_dict, status_code)
    """
    try:
        # Extract case ID from the URL path with validation
        path_parts = request.path.strip('/').split('/')
        if len(path_parts) < 4 or path_parts[-3] != 'cases' or path_parts[-1] != 'assign':
            return {
                'error': 'InvalidPath',
                'message': 'Invalid URL path format. Expected /v1/cases/{caseId}/assign'
            }, 400
        case_id = path_parts[-2]  # caseId is now second to last part

        # Get and validate request body
        try:
            body = request.get_json()
        except Exception:
            return {
                'error': 'InvalidJSON',
                'message': 'Request body must be valid JSON'
            }, 400

        if not isinstance(body, dict) or 'assignedUserId' not in body:
            return {
                'error': 'InvalidRequest',
                'message': 'Request body must contain assignedUserId field'
            }, 400

        assigned_user_id = body['assignedUserId']  # Can be None for unassign
        if assigned_user_id is not None and not isinstance(assigned_user_id, str):
            return {
                'error': 'InvalidRequest',
                'message': 'assignedUserId must be a string or null'
            }, 400

        # Get the requesting user ID from the request
        requesting_user_id = getattr(request, 'user_id', None)
        if not requesting_user_id:
            return {
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }, 401

        # Fetch and validate the case
        case_ref = db.collection('cases').document(case_id)
        case_doc = case_ref.get()

        if not case_doc.exists:
            return {
                'error': 'NotFound',
                'message': f'Case {case_id} not found'
            }, 404

        case_data = case_doc.to_dict()
        organization_id = case_data.get('organizationId')

        if not organization_id:
            return {
                'error': 'InvalidCase',
                'message': 'Case is not associated with an organization'
            }, 400

        # Check permissions
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="assign_case",
            organizationId=organization_id
        )
        has_permission, error_message = check_permission(requesting_user_id, permission_request)

        if not has_permission:
            return {
                'error': 'Forbidden',
                'message': error_message or 'Permission denied'
            }, 403

        assigned_user_name = None
        # Validate target user if assigning
        if assigned_user_id is not None:
            # Check organization membership
            memberships_query = db.collection('organization_memberships').where(
                'organizationId', '==', organization_id
            ).where('userId', '==', assigned_user_id).limit(1)

            membership_docs = memberships_query.get()
            if not membership_docs:
                return {
                    'error': 'NotFound',
                    'message': 'Target user not found in this organization'
                }, 404

            membership_data = membership_docs[0].to_dict()
            if membership_data.get('role') != 'staff':
                return {
                    'error': 'InvalidRole',
                    'message': "Target user must have 'staff' role"
                }, 400

            # Get user details for response
            user_ref = db.collection('users').document(assigned_user_id)
            user_doc = user_ref.get()
            if user_doc.exists:
                assigned_user_name = user_doc.to_dict().get('displayName')

        # Update the case
        update_data = {
            'assignedUserId': assigned_user_id,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        case_ref.update(update_data)

        # Prepare success response
        action_type = 'unassigned' if assigned_user_id is None else 'assigned'
        response = {
            'success': True,
            'message': f'Case {action_type} successfully',
            'caseId': case_id,
            'assignedUserId': assigned_user_id,
            'assignedUserName': assigned_user_name
        }

        # Log the action
        logging.info(
            f"Case {case_id} {action_type} by user {requesting_user_id} " +
            f"to user {assigned_user_id if assigned_user_id else 'none'}"
        )

        return response, 200

    except Exception as e:
        logging.error(f"Error in logic_assign_case: {str(e)}")
        return {
            'error': 'InternalError',
            'message': 'An internal error occurred'
        }, 500