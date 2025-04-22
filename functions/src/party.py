import firebase_admin
from firebase_admin import firestore
from datetime import datetime
import re
import json
from flask import Request, jsonify
import flask # Keep flask import
import logging
import uuid
# Removed google.cloud.firestore import
from auth import check_permission, PermissionCheckRequest, TYPE_PARTY as RESOURCE_TYPE_PARTY, ACTION_READ, ACTION_UPDATE, ACTION_DELETE, get_authenticated_user # Corrected import

logging.basicConfig(level=logging.INFO)

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

db = firestore.client() # Use firebase_admin's firestore client

def create_party(request: Request):
    logging.info("Logic function create_party called")
    try:
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        request_data = request.get_json(silent=True)
        if not request_data:
            return {"error": "Bad Request", "message": "Request body required"}, 400

        party_type = request_data.get("partyType")
        if party_type not in ["individual", "organization"]:
            return {"error": "Bad Request", "message": "partyType must be 'individual' or 'organization'"}, 400

        # Permission check: User can always create their own parties
        # No specific orgId check here unless parties are tied to orgs at creation

        party_data = {
            "userId": user_id, "partyType": party_type,
            "createdAt": firestore.SERVER_TIMESTAMP, "updatedAt": firestore.SERVER_TIMESTAMP
        }

        name_details = request_data.get("nameDetails", {})
        validated_name_details = {}
        if party_type == "individual":
            first_name = name_details.get("firstName")
            last_name = name_details.get("lastName")
            if not first_name or not last_name: return {"error": "Bad Request", "message": "firstName and lastName required for individuals"}, 400
            validated_name_details["firstName"] = first_name.strip()
            validated_name_details["lastName"] = last_name.strip()
        elif party_type == "organization":
            company_name = name_details.get("companyName")
            if not company_name: return {"error": "Bad Request", "message": "companyName required for organizations"}, 400
            validated_name_details["companyName"] = company_name.strip()
        party_data["nameDetails"] = validated_name_details

        identity_codes = request_data.get("identityCodes", {})
        validated_identity_codes = {}
        if party_type == "individual":
            cnp = identity_codes.get("cnp")
            if not cnp: return {"error": "Bad Request", "message": "CNP required for individuals"}, 400
            if not re.match(r'^\d{13}$', cnp): return {"error": "Bad Request", "message": "CNP must be 13 digits"}, 400
            validated_identity_codes["cnp"] = cnp
        elif party_type == "organization":
            cui = identity_codes.get("cui")
            reg_com = identity_codes.get("regCom")
            if not cui or not reg_com: return {"error": "Bad Request", "message": "CUI and RegCom required for organizations"}, 400
            # Add stricter validation if needed
            # if not re.match(r'^RO?\d+$', cui, re.IGNORECASE): return {"error": "Bad Request", "message": "Invalid CUI"}, 400
            # if not re.match(r'^J\d+/\d+/\d+$', reg_com, re.IGNORECASE): return {"error": "Bad Request", "message": "Invalid RegCom"}, 400
            validated_identity_codes["cui"] = cui
            validated_identity_codes["regCom"] = reg_com
        party_data["identityCodes"] = validated_identity_codes

        contact_info = request_data.get("contactInfo", {})
        address = contact_info.get("address") # Assuming address is a dict or string
        if not address: return {"error": "Bad Request", "message": "address required in contactInfo"}, 400
        validated_contact_info = {"address": address}
        email = contact_info.get("email")
        if email:
            # Basic email format check
            # if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            #     return {"error": "Bad Request", "message": "Invalid email format"}, 400
            validated_contact_info["email"] = email
        phone = contact_info.get("phone")
        if phone:
             validated_contact_info["phone"] = phone # Basic validation possible
        party_data["contactInfo"] = validated_contact_info

        signature_data = request_data.get("signatureData")
        if signature_data and isinstance(signature_data, dict):
            storage_path = signature_data.get("storagePath")
            if storage_path:
                party_data["signatureData"] = {"storagePath": storage_path, "capturedAt": firestore.SERVER_TIMESTAMP}

        party_ref = db.collection("parties").document()
        party_ref.set(party_data)
        party_id = party_ref.id

        result = party_ref.get().to_dict() # Read back data to include timestamps
        result["partyId"] = party_id
        if isinstance(result.get("createdAt"), datetime.datetime): result["createdAt"] = result["createdAt"].isoformat()
        if isinstance(result.get("updatedAt"), datetime.datetime): result["updatedAt"] = result["updatedAt"].isoformat()
        if result.get("signatureData") and isinstance(result["signatureData"].get("capturedAt"), datetime.datetime):
            result["signatureData"]["capturedAt"] = result["signatureData"]["capturedAt"].isoformat()

        return result, 201
    except Exception as e:
        logging.error(f"Error creating party: {str(e)}", exc_info=True)
        return {"error": "Internal Server Error", "message": str(e)}, 500

def get_party(request: Request):
    logging.info("Logic function get_party called")
    try:
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        party_id = request.args.get("partyId") # Get ID from query param
        if not party_id:
            # Fallback: try getting from path if main.py routes differently
            path_parts = request.path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[-2] == 'parties':
                 party_id = path_parts[-1]
            if not party_id:
                 return {"error": "Bad Request", "message": "partyId is required in query parameters or URL path"}, 400

        party_ref = db.collection("parties").document(party_id)
        party_doc = party_ref.get()
        if not party_doc.exists:
            return {"error": "Not Found", "message": "Party not found"}, 404

        party_data = party_doc.to_dict()
        # Check permission using the central function
        permission_request = PermissionCheckRequest(resourceType=RESOURCE_TYPE_PARTY, resourceId=party_id, action=ACTION_READ)
        allowed, message = check_permission(user_id, permission_request)
        if not allowed:
            return {"error": message}, 403

        result = party_data
        result["partyId"] = party_id
        if isinstance(result.get("createdAt"), datetime.datetime): result["createdAt"] = result["createdAt"].isoformat()
        if isinstance(result.get("updatedAt"), datetime.datetime): result["updatedAt"] = result["updatedAt"].isoformat()
        if result.get("signatureData") and isinstance(result["signatureData"].get("capturedAt"), datetime.datetime):
            result["signatureData"]["capturedAt"] = result["signatureData"]["capturedAt"].isoformat()

        return result, 200
    except Exception as e:
        logging.error(f"Error getting party: {str(e)}", exc_info=True)
        return {"error": "Internal Server Error", "message": str(e)}, 500


def update_party(request: Request):
    logging.info("Logic function update_party called")
    try:
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        request_data = request.get_json(silent=True)
        if not request_data: return {"error": "Bad Request", "message": "Request body required"}, 400

        party_id = request_data.get("partyId") # ID must be in body for updates
        if not party_id: return {"error": "Bad Request", "message": "partyId is required in request body"}, 400

        party_ref = db.collection("parties").document(party_id)
        party_doc = party_ref.get()
        if not party_doc.exists: return {"error": "Not Found", "message": "Party not found"}, 404

        existing_party = party_doc.to_dict()
        # Check permission using the central function
        permission_request = PermissionCheckRequest(resourceType=RESOURCE_TYPE_PARTY, resourceId=party_id, action=ACTION_UPDATE)
        allowed, message = check_permission(user_id, permission_request)
        if not allowed:
            return {"error": message}, 403
        party_type = existing_party["partyType"] # Cannot change type

        update_data = {}
        validated = False # Track if any valid field was updated

        if "nameDetails" in request_data:
            name_details = request_data["nameDetails"]
            validated_name = {}
            if party_type == "individual":
                if "firstName" in name_details: validated_name["firstName"] = name_details["firstName"].strip()
                if "lastName" in name_details: validated_name["lastName"] = name_details["lastName"].strip()
                if not validated_name.get("firstName") and not validated_name.get("lastName"):
                     # Allow clearing maybe? Or require both if updating name?
                     pass # Decide on update logic: allow partial update?
                if "companyName" in name_details: return {"error": "Bad Request", "message": "companyName invalid for individual"}, 400
            elif party_type == "organization":
                if "companyName" in name_details: validated_name["companyName"] = name_details["companyName"].strip()
                if not validated_name.get("companyName"): return {"error": "Bad Request", "message": "companyName cannot be empty"}, 400
                if "firstName" in name_details or "lastName" in name_details: return {"error": "Bad Request", "message": "firstName/lastName invalid for organization"}, 400
            if validated_name:
                 update_data["nameDetails"] = validated_name
                 validated = True

        if "identityCodes" in request_data:
            identity_codes = request_data["identityCodes"]
            validated_codes = {}
            if party_type == "individual":
                if "cnp" in identity_codes:
                    cnp = identity_codes["cnp"]
                    if not cnp or not re.match(r'^\d{13}$', cnp): return {"error": "Bad Request", "message": "Valid CNP required"}, 400
                    validated_codes["cnp"] = cnp
                if "cui" in identity_codes or "regCom" in identity_codes: return {"error": "Bad Request", "message": "CUI/RegCom invalid for individual"}, 400
            elif party_type == "organization":
                if "cui" in identity_codes: validated_codes["cui"] = identity_codes["cui"] # Add validation
                if "regCom" in identity_codes: validated_codes["regCom"] = identity_codes["regCom"] # Add validation
                if not validated_codes.get("cui") and not validated_codes.get("regCom"):
                     pass # Allow partial update?
                if "cnp" in identity_codes: return {"error": "Bad Request", "message": "CNP invalid for organization"}, 400
            if validated_codes:
                 update_data["identityCodes"] = validated_codes
                 validated = True

        if "contactInfo" in request_data:
            contact_info = request_data["contactInfo"]
            validated_contact = {}
            if "address" in contact_info: validated_contact["address"] = contact_info["address"] # Require non-empty?
            if "email" in contact_info: validated_contact["email"] = contact_info["email"] # Validate format
            if "phone" in contact_info: validated_contact["phone"] = contact_info["phone"] # Validate format
            if validated_contact:
                update_data["contactInfo"] = validated_contact
                validated = True

        if "signatureData" in request_data:
             signature_data = request_data["signatureData"]
             if signature_data is None:
                  update_data["signatureData"] = firestore.DELETE_FIELD
                  validated = True
             elif isinstance(signature_data, dict) and "storagePath" in signature_data:
                  update_data["signatureData"] = {"storagePath": signature_data["storagePath"], "capturedAt": firestore.SERVER_TIMESTAMP}
                  validated = True
             # Else: ignore invalid signatureData format

        if not validated: return {"error": "Bad Request", "message": "No valid fields provided for update"}, 400

        update_data["updatedAt"] = firestore.SERVER_TIMESTAMP
        party_ref.update(update_data) # Use update, not set

        updated_doc = party_ref.get()
        result = updated_doc.to_dict()
        result["partyId"] = party_id
        if isinstance(result.get("createdAt"), datetime.datetime): result["createdAt"] = result["createdAt"].isoformat()
        if isinstance(result.get("updatedAt"), datetime.datetime): result["updatedAt"] = result["updatedAt"].isoformat()
        if result.get("signatureData") and isinstance(result["signatureData"].get("capturedAt"), datetime.datetime):
            result["signatureData"]["capturedAt"] = result["signatureData"]["capturedAt"].isoformat()

        return result, 200
    except Exception as e:
        logging.error(f"Error updating party: {str(e)}", exc_info=True)
        return {"error": "Internal Server Error", "message": str(e)}, 500

def delete_party(request: Request):
    logging.info("Logic function delete_party called")
    try:
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        party_id = request.args.get("partyId") # Get ID from query param
        if not party_id:
            path_parts = request.path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[-2] == 'parties':
                 party_id = path_parts[-1]
            if not party_id:
                 return {"error": "Bad Request", "message": "partyId is required in query parameters or URL path"}, 400

        party_ref = db.collection("parties").document(party_id)
        party_doc = party_ref.get()
        if not party_doc.exists: return {"error": "Not Found", "message": "Party not found"}, 404

        party_data = party_doc.to_dict()
        # Check permission using the central function
        permission_request = PermissionCheckRequest(resourceType=RESOURCE_TYPE_PARTY, resourceId=party_id, action=ACTION_DELETE)
        allowed, message = check_permission(user_id, permission_request)
        if not allowed:
            return {"error": message}, 403

        # Check if party is attached to any *active* cases?
        cases_query = db.collection("cases").where("attachedPartyIds", "array_contains", party_id).where("status", "!=", "deleted").limit(1).stream()
        if list(cases_query):
            return {"error": "Conflict", "message": "Cannot delete party attached to active cases"}, 409

        party_ref.delete()
        return "", 204 # No content on successful delete
    except Exception as e:
        logging.error(f"Error deleting party: {str(e)}", exc_info=True)
        return {"error": "Internal Server Error", "message": str(e)}, 500

def list_parties(request: Request):
    logging.info("Logic function list_parties called")
    try:
        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        parties_query = db.collection("parties").where("userId", "==", user_id).order_by("createdAt", direction=firestore.Query.DESCENDING)

        party_type_filter = request.args.get("partyType")
        if party_type_filter:
            if party_type_filter not in ["individual", "organization"]:
                return {"error": "Bad Request", "message": "Invalid partyType filter"}, 400
            parties_query = parties_query.where("partyType", "==", party_type_filter)

        # Add pagination?
        limit = int(request.args.get("limit", "100")) # Default limit
        offset = int(request.args.get("offset", "0"))
        limit = min(limit, 500) # Cap limit for safety
        # parties_query = parties_query.limit(limit).offset(offset) # Basic pagination

        parties_docs = parties_query.stream()
        parties = []
        for doc in parties_docs:
            party_data = doc.to_dict()
            party_data["partyId"] = doc.id
            if isinstance(party_data.get("createdAt"), datetime.datetime): party_data["createdAt"] = party_data["createdAt"].isoformat()
            if isinstance(party_data.get("updatedAt"), datetime.datetime): party_data["updatedAt"] = party_data["updatedAt"].isoformat()
            if party_data.get("signatureData") and isinstance(party_data["signatureData"].get("capturedAt"), datetime.datetime):
                 party_data["signatureData"]["capturedAt"] = party_data["signatureData"]["capturedAt"].isoformat()
            parties.append(party_data)

        # Add pagination info to response if implementing pagination
        return {"parties": parties}, 200
    except Exception as e:
        logging.error(f"Error listing parties: {str(e)}", exc_info=True)
        return {"error": "Internal Server Error", "message": str(e)}, 500