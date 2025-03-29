import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import re
import json
from flask import Request, jsonify

# Get Firestore client
db = firestore.client()

def create_party(request: Request):
    """Create a new party (individual or organization).
    
    Args:
        request (Request): The HTTP request containing the party data
        
    Returns:
        tuple: HTTP response containing party data or error, and status code
    """
    try:
        # Get authenticated user from auth middleware
        from auth import get_authenticated_user
        user = get_authenticated_user(request)
        if not user:
            return {"error": "Unauthorized", "message": "Authentication required"}, 401
        
        # Extract request data
        request_data = request.get_json()
        if not request_data:
            return {"error": "Bad Request", "message": "Request body is required"}, 400
        
        # Validate partyType (required)
        party_type = request_data.get("partyType")
        if not party_type:
            return {"error": "Bad Request", "message": "partyType is required"}, 400
        
        if party_type not in ["individual", "organization"]:
            return {"error": "Bad Request", "message": "partyType must be 'individual' or 'organization'"}, 400
        
        # Initialize data structure
        party_data = {
            "userId": user["userId"],
            "partyType": party_type,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        # Validate nameDetails based on partyType
        name_details = request_data.get("nameDetails", {})
        if not name_details:
            return {"error": "Bad Request", "message": "nameDetails is required"}, 400
        
        # Validate name details based on party type
        validated_name_details = {}
        if party_type == "individual":
            # Validate firstName and lastName for individuals
            first_name = name_details.get("firstName")
            last_name = name_details.get("lastName")
            
            if not first_name:
                return {"error": "Bad Request", "message": "firstName is required for individual parties"}, 400
            if not last_name:
                return {"error": "Bad Request", "message": "lastName is required for individual parties"}, 400
                
            validated_name_details["firstName"] = first_name
            validated_name_details["lastName"] = last_name
            
        elif party_type == "organization":
            # Validate companyName for organizations
            company_name = name_details.get("companyName")
            if not company_name:
                return {"error": "Bad Request", "message": "companyName is required for organization parties"}, 400
                
            validated_name_details["companyName"] = company_name
        
        party_data["nameDetails"] = validated_name_details
        
        # Validate identityCodes based on partyType
        identity_codes = request_data.get("identityCodes", {})
        if not identity_codes:
            return {"error": "Bad Request", "message": "identityCodes is required"}, 400
        
        validated_identity_codes = {}
        if party_type == "individual":
            # Validate CNP for individuals
            cnp = identity_codes.get("cnp")
            if not cnp:
                return {"error": "Bad Request", "message": "CNP is required for individual parties"}, 400
                
            # Romanian CNP validation (13 digits)
            if not re.match(r'^\d{13}$', cnp):
                return {"error": "Bad Request", "message": "CNP must be a 13-digit number"}, 400
                
            validated_identity_codes["cnp"] = cnp
            
        elif party_type == "organization":
            # Validate CUI and RegCom for organizations
            cui = identity_codes.get("cui")
            reg_com = identity_codes.get("regCom")
            
            if not cui:
                return {"error": "Bad Request", "message": "CUI is required for organization parties"}, 400
            if not reg_com:
                return {"error": "Bad Request", "message": "RegCom is required for organization parties"}, 400
                
            # Basic validation for CUI and RegCom
            if not re.match(r'^RO?\d+$', cui, re.IGNORECASE):
                return {"error": "Bad Request", "message": "Invalid CUI format"}, 400
                
            if not re.match(r'^J\d+/\d+/\d+$', reg_com, re.IGNORECASE):
                return {"error": "Bad Request", "message": "Invalid RegCom format (should be Jxx/xxx/xxxx)"}, 400
                
            validated_identity_codes["cui"] = cui
            validated_identity_codes["regCom"] = reg_com
        
        party_data["identityCodes"] = validated_identity_codes
        
        # Validate contactInfo (common to both types)
        contact_info = request_data.get("contactInfo", {})
        if not contact_info:
            return {"error": "Bad Request", "message": "contactInfo is required"}, 400
            
        # Address is required
        address = contact_info.get("address")
        if not address:
            return {"error": "Bad Request", "message": "address is required in contactInfo"}, 400
            
        validated_contact_info = {"address": address}
        
        # Email and phone are optional but should be validated if present
        email = contact_info.get("email")
        if email:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return {"error": "Bad Request", "message": "Invalid email format"}, 400
            validated_contact_info["email"] = email
            
        phone = contact_info.get("phone")
        if phone:
            # Basic phone validation
            if not re.match(r'^\+?[0-9\s\-\(\)]+$', phone):
                return {"error": "Bad Request", "message": "Invalid phone format"}, 400
            validated_contact_info["phone"] = phone
            
        party_data["contactInfo"] = validated_contact_info
        
        # Handle optional signatureData
        signature_data = request_data.get("signatureData")
        if signature_data and isinstance(signature_data, dict):
            storage_path = signature_data.get("storagePath")
            if storage_path:
                party_data["signatureData"] = {
                    "storagePath": storage_path,
                    "capturedAt": datetime.utcnow()
                }
        
        # Create the party document in Firestore
        party_ref = db.collection("parties").document()
        party_ref.set(party_data)
        
        # Get the new party ID
        party_id = party_ref.id
        
        # Return the created party data
        result = party_data.copy()
        result["partyId"] = party_id
        
        # Convert datetime objects to ISO format strings for JSON serialization
        result["createdAt"] = result["createdAt"].isoformat()
        result["updatedAt"] = result["updatedAt"].isoformat()
        if "signatureData" in result and "capturedAt" in result["signatureData"]:
            result["signatureData"]["capturedAt"] = result["signatureData"]["capturedAt"].isoformat()
        
        return result, 201
        
    except Exception as e:
        print(f"Error creating party: {str(e)}")
        return {"error": "Internal Server Error", "message": str(e)}, 500

def get_party(request: Request):
    """Get a party by ID with ownership verification.
    
    Args:
        request (Request): The HTTP request containing the party ID
        
    Returns:
        tuple: HTTP response containing party data or error, and status code
    """
    try:
        # Get authenticated user from auth middleware
        from auth import get_authenticated_user
        user = get_authenticated_user(request)
        if not user:
            return {"error": "Unauthorized", "message": "Authentication required"}, 401
        
        # Extract party ID from request
        party_id = request.args.get("partyId")
        if not party_id:
            return {"error": "Bad Request", "message": "partyId is required"}, 400
        
        # Get the party document
        party_ref = db.collection("parties").document(party_id)
        party_doc = party_ref.get()
        
        if not party_doc.exists:
            return {"error": "Not Found", "message": "Party not found"}, 404
        
        # Get party data
        party_data = party_doc.to_dict()
        
        # Verify ownership
        if party_data["userId"] != user["userId"]:
            return {"error": "Forbidden", "message": "You don't have permission to access this party"}, 403
        
        # Add party ID to the response
        result = party_data.copy()
        result["partyId"] = party_id
        
        # Convert datetime objects to ISO format strings for JSON serialization
        result["createdAt"] = result["createdAt"].isoformat()
        result["updatedAt"] = result["updatedAt"].isoformat()
        if "signatureData" in result and "capturedAt" in result["signatureData"]:
            result["signatureData"]["capturedAt"] = result["signatureData"]["capturedAt"].isoformat()
        
        return result, 200
        
    except Exception as e:
        print(f"Error getting party: {str(e)}")
        return {"error": "Internal Server Error", "message": str(e)}, 500

def update_party(request: Request):
    """Update a party with validation based on the existing partyType.
    
    Args:
        request (Request): The HTTP request containing the party data
        
    Returns:
        tuple: HTTP response containing updated party data or error, and status code
    """
    try:
        # Get authenticated user from auth middleware
        from auth import get_authenticated_user
        user = get_authenticated_user(request)
        if not user:
            return {"error": "Unauthorized", "message": "Authentication required"}, 401
        
        # Extract request data
        request_data = request.get_json()
        if not request_data:
            return {"error": "Bad Request", "message": "Request body is required"}, 400
        
        # Extract party ID from request
        party_id = request_data.get("partyId")
        if not party_id:
            return {"error": "Bad Request", "message": "partyId is required"}, 400
        
        # Get the existing party document
        party_ref = db.collection("parties").document(party_id)
        party_doc = party_ref.get()
        
        if not party_doc.exists:
            return {"error": "Not Found", "message": "Party not found"}, 404
        
        # Get existing party data
        existing_party = party_doc.to_dict()
        
        # Verify ownership
        if existing_party["userId"] != user["userId"]:
            return {"error": "Forbidden", "message": "You don't have permission to update this party"}, 403
        
        # Get the existing partyType (cannot be changed)
        party_type = existing_party["partyType"]
        
        # Initialize update data
        update_data = {
            "updatedAt": datetime.utcnow()
        }
        
        # Validate nameDetails update
        if "nameDetails" in request_data:
            name_details = request_data["nameDetails"]
            validated_name_details = {}
            
            if party_type == "individual":
                # For individual: only firstName and lastName can be updated
                if "firstName" in name_details:
                    if not name_details["firstName"]:
                        return {"error": "Bad Request", "message": "firstName cannot be empty"}, 400
                    validated_name_details["firstName"] = name_details["firstName"]
                
                if "lastName" in name_details:
                    if not name_details["lastName"]:
                        return {"error": "Bad Request", "message": "lastName cannot be empty"}, 400
                    validated_name_details["lastName"] = name_details["lastName"]
                
                # Prevent adding companyName to an individual
                if "companyName" in name_details:
                    return {"error": "Bad Request", "message": "companyName is not valid for individual parties"}, 400
                
            elif party_type == "organization":
                # For organization: only companyName can be updated
                if "companyName" in name_details:
                    if not name_details["companyName"]:
                        return {"error": "Bad Request", "message": "companyName cannot be empty"}, 400
                    validated_name_details["companyName"] = name_details["companyName"]
                
                # Prevent adding firstName or lastName to an organization
                if "firstName" in name_details or "lastName" in name_details:
                    return {"error": "Bad Request", "message": "firstName and lastName are not valid for organization parties"}, 400
            
            # If there are validated name details, update them
            if validated_name_details:
                update_data["nameDetails"] = firestore.firestore.UPDATE_SENTINEL
                for key, value in validated_name_details.items():
                    update_data[f"nameDetails.{key}"] = value
        
        # Validate identityCodes update
        if "identityCodes" in request_data:
            identity_codes = request_data["identityCodes"]
            validated_identity_codes = {}
            
            if party_type == "individual":
                # For individual: only CNP can be updated
                if "cnp" in identity_codes:
                    cnp = identity_codes["cnp"]
                    if not cnp:
                        return {"error": "Bad Request", "message": "CNP cannot be empty"}, 400
                    
                    # Romanian CNP validation (13 digits)
                    if not re.match(r'^\d{13}$', cnp):
                        return {"error": "Bad Request", "message": "CNP must be a 13-digit number"}, 400
                    
                    validated_identity_codes["cnp"] = cnp
                
                # Prevent adding CUI or RegCom to an individual
                if "cui" in identity_codes or "regCom" in identity_codes:
                    return {"error": "Bad Request", "message": "CUI and RegCom are not valid for individual parties"}, 400
                
            elif party_type == "organization":
                # For organization: CUI and RegCom can be updated
                if "cui" in identity_codes:
                    cui = identity_codes["cui"]
                    if not cui:
                        return {"error": "Bad Request", "message": "CUI cannot be empty"}, 400
                    
                    # Basic validation for CUI
                    if not re.match(r'^RO?\d+$', cui, re.IGNORECASE):
                        return {"error": "Bad Request", "message": "Invalid CUI format"}, 400
                    
                    validated_identity_codes["cui"] = cui
                
                if "regCom" in identity_codes:
                    reg_com = identity_codes["regCom"]
                    if not reg_com:
                        return {"error": "Bad Request", "message": "RegCom cannot be empty"}, 400
                    
                    # Basic validation for RegCom
                    if not re.match(r'^J\d+/\d+/\d+$', reg_com, re.IGNORECASE):
                        return {"error": "Bad Request", "message": "Invalid RegCom format (should be Jxx/xxx/xxxx)"}, 400
                    
                    validated_identity_codes["regCom"] = reg_com
                
                # Prevent adding CNP to an organization
                if "cnp" in identity_codes:
                    return {"error": "Bad Request", "message": "CNP is not valid for organization parties"}, 400
            
            # If there are validated identity codes, update them
            if validated_identity_codes:
                update_data["identityCodes"] = firestore.firestore.UPDATE_SENTINEL
                for key, value in validated_identity_codes.items():
                    update_data[f"identityCodes.{key}"] = value
        
        # Validate contactInfo update (common to both types)
        if "contactInfo" in request_data:
            contact_info = request_data["contactInfo"]
            validated_contact_info = {}
            
            if "address" in contact_info:
                address = contact_info["address"]
                if not address:
                    return {"error": "Bad Request", "message": "address cannot be empty"}, 400
                validated_contact_info["address"] = address
            
            if "email" in contact_info:
                email = contact_info["email"]
                if email:  # Email can be null/empty
                    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                        return {"error": "Bad Request", "message": "Invalid email format"}, 400
                validated_contact_info["email"] = email
            
            if "phone" in contact_info:
                phone = contact_info["phone"]
                if phone:  # Phone can be null/empty
                    if not re.match(r'^\+?[0-9\s\-\(\)]+$', phone):
                        return {"error": "Bad Request", "message": "Invalid phone format"}, 400
                validated_contact_info["phone"] = phone
            
            # If there are validated contact info fields, update them
            if validated_contact_info:
                update_data["contactInfo"] = firestore.firestore.UPDATE_SENTINEL
                for key, value in validated_contact_info.items():
                    update_data[f"contactInfo.{key}"] = value
        
        # Handle optional signatureData update
        if "signatureData" in request_data:
            signature_data = request_data["signatureData"]
            if signature_data and isinstance(signature_data, dict):
                storage_path = signature_data.get("storagePath")
                if storage_path:
                    update_data["signatureData"] = {
                        "storagePath": storage_path,
                        "capturedAt": datetime.utcnow()
                    }
                elif storage_path == "":
                    # If storagePath is empty string, remove signatureData
                    update_data["signatureData"] = firestore.DELETE_FIELD
            elif signature_data is None:
                # If signatureData is explicitly set to null, remove it
                update_data["signatureData"] = firestore.DELETE_FIELD
        
        # Ensure we have fields to update
        if len(update_data) <= 1:  # Only updatedAt is present
            return {"error": "Bad Request", "message": "No valid fields to update"}, 400
        
        # Update the party document with validated fields
        # First, filter out special Firestore sentinel values from the update data
        filtered_update = {k: v for k, v in update_data.items() 
                          if v != firestore.firestore.UPDATE_SENTINEL}
        
        # Perform the update operation
        party_ref.update(filtered_update)
        
        # Get the updated party document
        updated_doc = party_ref.get()
        updated_party = updated_doc.to_dict()
        
        # Add the party ID to the result
        result = updated_party.copy()
        result["partyId"] = party_id
        
        # Convert datetime objects to ISO format strings for JSON serialization
        result["createdAt"] = result["createdAt"].isoformat()
        result["updatedAt"] = result["updatedAt"].isoformat()
        if "signatureData" in result and "capturedAt" in result["signatureData"]:
            result["signatureData"]["capturedAt"] = result["signatureData"]["capturedAt"].isoformat()
        
        return result, 200
        
    except Exception as e:
        print(f"Error updating party: {str(e)}")
        return {"error": "Internal Server Error", "message": str(e)}, 500

def delete_party(request: Request):
    """Delete a party with ownership verification.
    
    Args:
        request (Request): The HTTP request containing the party ID
        
    Returns:
        tuple: HTTP response indicating success or error, and status code
    """
    try:
        # Get authenticated user from auth middleware
        from auth import get_authenticated_user
        user = get_authenticated_user(request)
        if not user:
            return {"error": "Unauthorized", "message": "Authentication required"}, 401
        
        # Extract party ID from request
        party_id = request.args.get("partyId")
        if not party_id:
            return {"error": "Bad Request", "message": "partyId is required"}, 400
        
        # Get the party document
        party_ref = db.collection("parties").document(party_id)
        party_doc = party_ref.get()
        
        if not party_doc.exists:
            return {"error": "Not Found", "message": "Party not found"}, 404
        
        # Get party data
        party_data = party_doc.to_dict()
        
        # Verify ownership
        if party_data["userId"] != user["userId"]:
            return {"error": "Forbidden", "message": "You don't have permission to delete this party"}, 403
        
        # Check if the party is attached to any cases
        cases_query = db.collection("cases").where("attachedPartyIds", "array_contains", party_id).limit(1).get()
        
        if len(cases_query) > 0:
            return {"error": "Conflict", "message": "Cannot delete a party that is attached to one or more cases"}, 409
        
        # Delete the party document
        party_ref.delete()
        
        # Return success response with no content
        return "", 204
        
    except Exception as e:
        print(f"Error deleting party: {str(e)}")
        return {"error": "Internal Server Error", "message": str(e)}, 500

def list_parties(request: Request):
    """List parties owned by the authenticated user.
    
    Args:
        request (Request): The HTTP request
        
    Returns:
        tuple: HTTP response containing list of parties or error, and status code
    """
    try:
        # Get authenticated user from auth middleware
        from auth import get_authenticated_user
        user = get_authenticated_user(request)
        if not user:
            return {"error": "Unauthorized", "message": "Authentication required"}, 401
        
        # Query Firestore for parties owned by this user
        parties_query = db.collection("parties").where("userId", "==", user["userId"]).order_by("createdAt", direction=firestore.Query.DESCENDING)
        
        # Process query parameters for filtering
        party_type = request.args.get("partyType")
        if party_type:
            if party_type not in ["individual", "organization"]:
                return {"error": "Bad Request", "message": "partyType must be 'individual' or 'organization'"}, 400
            parties_query = parties_query.where("partyType", "==", party_type)
        
        # Execute the query
        parties_docs = parties_query.get()
        
        # Build the result list
        parties = []
        for doc in parties_docs:
            party_data = doc.to_dict()
            party_data["partyId"] = doc.id
            
            # Convert datetime objects to ISO format strings for JSON serialization
            party_data["createdAt"] = party_data["createdAt"].isoformat()
            party_data["updatedAt"] = party_data["updatedAt"].isoformat()
            if "signatureData" in party_data and "capturedAt" in party_data["signatureData"]:
                party_data["signatureData"]["capturedAt"] = party_data["signatureData"]["capturedAt"].isoformat()
            
            parties.append(party_data)
        
        return {"parties": parties}, 200
        
    except Exception as e:
        print(f"Error listing parties: {str(e)}")
        return {"error": "Internal Server Error", "message": str(e)}, 500 