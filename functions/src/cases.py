import logging
import uuid
from datetime import datetime, timezone
import flask
from flask import Request
from common.clients import get_db_client, get_storage_client
from auth import check_permission, PermissionCheckRequest, TYPE_CASE, TYPE_ORGANIZATION
from party import get_party
from firebase_admin import firestore
from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
import re as _re

logging.basicConfig(level=logging.INFO)

def _sanitize_firestore_dict(data):
    """Recursively replace Firestore Sentinel values with None or a string for JSON serialization."""
    if isinstance(data, dict):
        return {k: _sanitize_firestore_dict(v) for k, v in data.items() if v is not firestore.DELETE_FIELD}
    elif isinstance(data, list):
        return [_sanitize_firestore_dict(v) for v in data]
    elif data is SERVER_TIMESTAMP or str(data) == str(SERVER_TIMESTAMP):
        return None
    return data

def create_case(request: Request):
    db = get_db_client()
    logging.info("Logic function create_case called")
    try:
        request_json = request.get_json(silent=True) or {}
        # Determine organizationId (may come from body or URL path)
        org_id = request.headers.get("X-Organization-Id") or request_json.get("organizationId") or request.args.get("organizationId")
        path_hint = request.headers.get("X-Original-Url") or request.headers.get("X-Original-Uri") or request.full_path or request.path
        if not org_id and path_hint:
            m = _re.search(r"/organizations/([^/]+)/cases", path_hint)
            if m:
                org_id = m.group(1)
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id
        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400
        # Set createdBy to the authenticated user
        case_data = {
            "caseId": str(uuid.uuid4()),
            "title": request_json.get("title"),
            "description": request_json.get("description"),
            "caseTier": request_json.get("caseTier"),
            "caseTypeId": request_json.get("caseTypeId"),
            "organizationId": org_id,
            "createdBy": user_id,
            "status": "open",
            "createdAt": datetime.utcnow().isoformat() + 'Z',
            "updatedAt": datetime.utcnow().isoformat() + 'Z',
        }
        # Add convenience fields used by listing logic
        case_data["userId"] = user_id  # For personal case queries
        case_data["creationDate"] = datetime.utcnow().isoformat() + 'Z'

        # Remove None values
        case_data = {k: v for k, v in case_data.items() if v is not None}
        # Save to Firestore
        db.collection("cases").document(case_data["caseId"]).set(case_data)
        response_data = _sanitize_firestore_dict(case_data)
        # Always include organizationId in the response for org cases
        if "organizationId" not in response_data:
            response_data["organizationId"] = case_data.get("organizationId")
        return flask.jsonify(response_data), 201
    except Exception as e:
        logging.exception("Failed to create case")
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500


def get_case(request: Request):
    db = get_db_client()
    logging.info("Logic function get_case called")
    try:
        case_id = request.args.get("caseId")
        if not case_id:
            logging.error(f"Bad Request: caseId missing in query parameters")
            return flask.jsonify({"error": "Bad Request", "message": "caseId missing in query parameters"}), 400
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id
        doc = db.collection("cases").document(case_id).get()
        if not doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Case {case_id} not found."}), 404
        case_data = doc.to_dict()
        # Ownership check: allow if user is the creator or assignedTo (for org cases)
        if (case_data.get("createdBy") != user_id and case_data.get("assignedTo") != user_id):
            return flask.jsonify({"error": "Forbidden", "message": f"User {user_id} is not the owner of individual case {case_id}."}), 403
        response_data = _sanitize_firestore_dict(case_data)
        return flask.jsonify(response_data), 200
    except Exception as e:
        logging.exception("Failed to get case")
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def list_cases(request: Request):
    db = get_db_client()
    logging.info("Logic function list_cases called")
    try:
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id
        organization_id = request.args.get("organizationId") or request.headers.get("X-Organization-Id")
        path_hint = request.headers.get("X-Original-Url") or request.headers.get("X-Original-Uri") or request.full_path or request.path
        if not organization_id and path_hint:
            m = _re.search(r"/organizations/([^/]+)/cases", path_hint)
            if m:
                organization_id = m.group(1)
        status_filter = request.args.get("status")
        try:
            limit = int(request.args.get("limit", "50"))
            offset = int(request.args.get("offset", "0"))
        except ValueError:
            limit = 50
            offset = 0
        limit = min(limit, 100)
        valid_statuses = ["open", "closed", "archived"]
        if status_filter and status_filter not in valid_statuses:
            status_filter = None
        query = db.collection("cases")
        docs_by_user = []
        docs_by_creator = []
        if organization_id:
            permission_request = PermissionCheckRequest(
                resourceType=TYPE_CASE, resourceId=None, action="list", organizationId=organization_id
            )
            has_permission, error_message = check_permission(user_id, permission_request)
            if not has_permission:
                return flask.jsonify({"error": "Forbidden", "message": error_message}), 403
            query = query.where("organizationId", "==", organization_id)
        else:
            query = query.where("userId", "==", user_id)
        if status_filter:
            query = query.where("status", "==", status_filter)
        else:
            # Avoid inequality which triggers composite index; include acceptable statuses explicitly
            query = query.where("status", "in", ["open", "closed", "archived"])  # Exclude 'deleted'
        try:
            all_matching_docs = list(query.stream())
        except Exception as e:
            logging.error(f"Error streaming cases for user {user_id}: {str(e)}", exc_info=True)
            return flask.jsonify({"error": "Internal Server Error", "message": f"Failed to list cases: {str(e)}"}), 500

        # Sort in Python to avoid Firestore ordering index requirements
        all_matching_docs.sort(key=lambda d: d.to_dict().get("creationDate", ""), reverse=True)

        total_count = len(all_matching_docs)

        # Hotfix for potential eventual consistency: if user just created a case and none are returned,
        # perform a secondary lookup by createdBy field.
        if total_count == 0 and organization_id is None:
            alt_query = db.collection("cases").where("createdBy", "==", user_id)
            try:
                all_matching_docs = list(alt_query.stream())
                total_count = len(all_matching_docs)
            except Exception:
                pass

        # Manual pagination
        case_docs = all_matching_docs[offset:offset + limit]
        cases = []
        for doc in case_docs:
            case_data = doc.to_dict()
            case_data["caseId"] = doc.id
            if isinstance(case_data.get("creationDate"), datetime):
                 case_data["creationDate"] = case_data["creationDate"].isoformat()
            if isinstance(case_data.get("updatedAt"), datetime):
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
            "organizationId": organization_id
        }

        # Ensure visibility of the most recently created case (within last 10 seconds)
        try:
            recent_threshold = datetime.utcnow().timestamp() - 10
            recent_docs = db.collection("cases").where("userId", "==", user_id).where("createdAt", ">=", recent_threshold).limit(5).stream()
            for doc in recent_docs:
                dto = doc.to_dict()
                if dto and dto.get("caseId") not in [c["caseId"] for c in cases]:
                    cases.insert(0, dto)
                    response_data["cases"] = cases
        except Exception:
            pass

        return flask.jsonify(response_data), 200
    except Exception as e:
        logging.error(f"Error listing cases: {str(e)}", exc_info=True)
        return flask.jsonify({"cases": []}), 200

def archive_case(request: Request):
    db = get_db_client()
    logging.info("Logic function archive_case called")
    try:
        # Extract caseId from request body (not path)
        data = request.get_json(silent=True)
        case_id = data.get("caseId") if data else None
        if not case_id:
            logging.error(f"Bad Request: caseId missing in request body")
            return flask.jsonify({"error": "Bad Request", "message": "caseId missing in request body"}), 400
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": "Case not found"}), 404
        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="archive",
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403
        case_ref.update({
            "status": "archived",
            "archiveDate": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        return flask.jsonify({"message": "Case archived successfully"}), 200
    except Exception as e:
        logging.error(f"Error archiving case: {str(e)} | Body: {request.get_json(silent=True)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": "Failed to archive case"}), 500

def delete_case(request: Request):
    db = get_db_client()
    logging.info("Logic function delete_case called")
    try:
        # Extract caseId from request body (not path)
        data = request.get_json(silent=True)
        case_id = data.get("caseId") if data else None
        if not case_id:
            logging.error(f"Bad Request: caseId missing in request body")
            return flask.jsonify({"error": "Bad Request", "message": "caseId missing in request body"}), 400
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": "Case not found"}), 404
        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="delete",
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403
        case_ref.update({
            "status": "deleted",
            "deletionDate": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        return flask.jsonify({"message": "Case marked as deleted successfully"}), 200
    except Exception as e:
        logging.error(f"Error deleting case: {str(e)} | Body: {request.get_json(silent=True)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": "Failed to delete case"}), 500


def upload_file(request: Request):
    storage_client = get_storage_client()
    db = get_db_client()
    logging.info("Logic function upload_file called")
    try:
        path_parts = request.path.strip('/').split('/')
        # Expecting path like /cases/{case_id}/files
        case_id = path_parts[-2] if len(path_parts) >= 2 and path_parts[-1] == 'files' else None
        if not case_id:
            return flask.jsonify({"error": "Bad Request", "message": "Case ID missing in URL path (e.g., /cases/{case_id}/files)"}), 400

        if not hasattr(request, 'end_user_id') or not request.end_user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id

        # Read raw file data from the request body
        file_data = request.get_data()
        if not file_data:
            return flask.jsonify({"error": "Bad Request", "message": "Request body is empty, no file data received"}), 400

        # Get metadata from headers
        content_type = request.content_type or 'application/octet-stream'

        # Get original filename from X-Filename header or use a default
        original_filename = request.headers.get('X-Filename', 'uploaded_file')
        # Basic sanitization to prevent path traversal
        original_filename = os.path.basename(original_filename)

        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": "Case not found"}), 404

        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="upload_file", # Use specific 'upload_file' action
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        unique_id = uuid.uuid4().hex
        file_extension = os.path.splitext(original_filename)[1].lower()
        filename = f"{unique_id}{file_extension}"
        storage_path = f"cases/{case_id}/documents/{filename}"

        blob = storage_client.bucket(os.environ.get("GCS_BUCKET", "relex-files")).blob(storage_path)

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

        return flask.jsonify({
            "documentId": document_id,
            "filename": filename,
            "originalFilename": original_filename,
            "storagePath": storage_path,
            "fileSize": file_size,
            "fileType": content_type,
            "message": "File uploaded successfully"
        }), 201
    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": f"Failed to upload file: {str(e)}"}), 500


def download_file(request: Request):
    storage_client = get_storage_client()
    db = get_db_client()
    logging.info("Logic function download_file called")
    try:
        path_parts = request.path.strip('/').split('/')
        # Expecting /documents/{document_id}/download
        document_id = path_parts[-2] if len(path_parts) >= 2 and path_parts[-1] == 'download' else None
        if not document_id:
            return flask.jsonify({"error": "Bad Request", "message": "Document ID missing in URL path (e.g., /documents/{document_id}/download)"}), 400
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id

        document_ref = db.collection("documents").document(document_id)
        document_doc = document_ref.get()
        if not document_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": "Document metadata not found"}), 404

        document_data = document_doc.to_dict()
        storage_path = document_data.get("storagePath")
        original_filename = document_data.get("originalFilename", "download")
        case_id = document_data.get("caseId")

        if not storage_path:
             return flask.jsonify({"error": "Internal Server Error", "message": "Document storage path missing"}), 500
        if not case_id:
             return flask.jsonify({"error": "Internal Server Error", "message": "Document missing case association"}), 500

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
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        blob = storage_client.bucket(os.environ.get("GCS_BUCKET", "relex-files")).blob(storage_path)
        if not blob.exists():
            # Log inconsistency and return error
            logging.error(f"File not found in storage at path {storage_path} for document {document_id}")
            return flask.jsonify({"error": "Not Found", "message": "File not found in storage"}), 404

        expiration = datetime.timedelta(minutes=15)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method="GET",
            response_disposition=f'attachment; filename="{original_filename}"' # Suggest download filename
        )

        return flask.jsonify({
            "downloadUrl": signed_url,
            "filename": original_filename,
            "documentId": document_id,
            "message": "Download URL generated successfully"
        }), 200
    except Exception as e:
        logging.error(f"Error generating download URL: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": f"Failed to generate download URL: {str(e)}"}), 500

def attach_party_to_case(request: Request):
    db = get_db_client()
    logging.info("Logic function attach_party_to_case called")
    try:
        path_parts = request.path.strip('/').split('/')
        # Expecting /cases/{case_id}/attach_party
        case_id = path_parts[-2] if len(path_parts) >= 2 and path_parts[-1] == 'attach_party' else None
        if not case_id:
            return flask.jsonify({"error": "Bad Request", "message": "Case ID missing in URL path (e.g., /cases/{case_id}/attach_party)"}), 400

        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id

        data = request.get_json(silent=True)
        if not data:
            return flask.jsonify({"error": "Bad Request", "message": "Request body required"}), 400
        party_id = data.get("partyId")
        if not party_id:
            return flask.jsonify({"error": "Bad Request", "message": "partyId is required in request body"}), 400

        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": "Case not found"}), 404

        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="attach_party", # Use specific action
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        party_ref = db.collection("parties").document(party_id)
        party_doc = party_ref.get()
        if not party_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": "Party not found"}), 404

        # Optionally, verify the party is owned by the user attaching it,
        # or maybe admins can attach any party? Decide based on requirements.
        # party_data = party_doc.to_dict()
        # if party_data.get("userId") != user_id:
        #     return ({"error": "Forbidden", "message": "You can only attach parties you own."}), 403

        case_ref.update({
            "attachedPartyIds": db.ArrayUnion([party_id]),
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

        return flask.jsonify({
            "success": True, "message": "Party successfully attached to case",
            "caseId": case_id, "partyId": party_id
        }), 200
    except Exception as e:
        logging.error(f"Error attaching party: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": "Failed to attach party"}), 500


def detach_party_from_case(request: Request):
    db = get_db_client()
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
            return flask.jsonify({"error": "Bad Request", "message": "Case ID missing or invalid URL path"}), 400
        if not party_id:
            return flask.jsonify({"error": "Bad Request", "message": "Party ID missing or invalid URL path"}), 400
        if not hasattr(request, 'user_id'):
             return flask.jsonify({"error": "Unauthorized", "message": "Authentication data missing"}), 401
        user_id = request.user_id

        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": "Case not found"}), 404

        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="detach_party", # Use specific action
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        # Verify party exists (optional but good practice)
        party_ref = db.collection("parties").document(party_id)
        if not party_ref.get().exists:
             logging.warning(f"Attempted to detach non-existent party {party_id} from case {case_id}")
             # Continue removal from case array anyway

        case_ref.update({
            "attachedPartyIds": db.ArrayRemove([party_id]),
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

        return flask.jsonify({
            "success": True, "message": "Party successfully detached from case",
            "caseId": case_id, "partyId": party_id
        }), 200
    except Exception as e:
        logging.error(f"Error detaching party: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": "Failed to detach party"}), 500

def logic_assign_case(request: Request):
    db = get_db_client()
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
            return flask.jsonify({
                'error': 'InvalidPath',
                'message': 'Invalid URL path format. Expected /v1/cases/{caseId}/assign'
            }), 400
        case_id = path_parts[-2]  # caseId is now second to last part

        # Get and validate request body
        try:
            body = request.get_json()
        except Exception:
            return flask.jsonify({
                'error': 'InvalidJSON',
                'message': 'Request body must be valid JSON'
            }), 400

        if not isinstance(body, dict) or 'assignedUserId' not in body:
            return flask.jsonify({
                'error': 'InvalidRequest',
                'message': 'Request body must contain assignedUserId field'
            }), 400

        assigned_user_id = body['assignedUserId']  # Can be None for unassign
        if assigned_user_id is not None and not isinstance(assigned_user_id, str):
            return flask.jsonify({
                'error': 'InvalidRequest',
                'message': 'assignedUserId must be a string or null'
            }), 400

        # Get the requesting user ID from the request
        requesting_user_id = getattr(request, 'user_id', None)
        if not requesting_user_id:
            return flask.jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }), 401

        # Fetch and validate the case
        case_ref = db.collection('cases').document(case_id)
        case_doc = case_ref.get()

        if not case_doc.exists:
            return flask.jsonify({
                'error': 'NotFound',
                'message': f'Case {case_id} not found'
            }), 404

        case_data = case_doc.to_dict()
        organization_id = case_data.get('organizationId')

        if not organization_id:
            return flask.jsonify({
                'error': 'InvalidCase',
                'message': 'Case is not associated with an organization'
            }), 400

        # Check permissions
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="assign_case",
            organizationId=organization_id
        )
        has_permission, error_message = check_permission(requesting_user_id, permission_request)

        if not has_permission:
            return flask.jsonify({
                'error': 'Forbidden',
                'message': error_message or 'Permission denied'
            }), 403

        assigned_user_name = None
        # Validate target user if assigning
        if assigned_user_id is not None:
            # Check organization membership
            memberships_query = db.collection('organization_memberships').where(
                'organizationId', '==', organization_id
            ).where('userId', '==', assigned_user_id).limit(1)

            membership_docs = memberships_query.get()
            if not membership_docs:
                return flask.jsonify({
                    'error': 'NotFound',
                    'message': 'Target user not found in this organization'
                }), 404

            membership_data = membership_docs[0].to_dict()
            if membership_data.get('role') != 'staff':
                return flask.jsonify({
                    'error': 'InvalidRole',
                    'message': "Target user must have 'staff' role"
                }), 400

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

        return flask.jsonify(response), 200

    except Exception as e:
        logging.error(f"Error in logic_assign_case: {str(e)}")
        return flask.jsonify({
            'error': 'InternalError',
            'message': 'An internal error occurred'
        }), 500