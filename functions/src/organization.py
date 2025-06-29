import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
from firebase_admin import auth as firebase_auth # Renamed import
import json
import flask
import uuid
# import google.cloud.firestore # Removed this line
from datetime import datetime
from auth import check_permission, PermissionCheckRequest, TYPE_ORGANIZATION as RESOURCE_TYPE_ORGANIZATION # Corrected import
from flask import Request
from common.clients import get_db_client

logging.basicConfig(level=logging.INFO)

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

def create_organization(request: Request):
    logging.info("Logic function create_organization called")
    try:
        request_json = request.get_json(silent=True)
        logging.debug(f"create_organization: Checking for end_user_id on request object. Available attributes: {dir(request)}")
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             logging.warning(f"create_organization: end_user_id missing or empty on request object. Flask request object: {request}")
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id
        logging.info(f"create_organization: Successfully retrieved end_user_id: {user_id} for organization creation.")

        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400
        name = request_json.get('name')
        if not name or not isinstance(name, str) or not name.strip():
            return flask.jsonify({"error": "Bad Request", "message": "Valid organization name is required"}), 400

        description = request_json.get('description', '')
        address = request_json.get('address', {})
        contact_info = request_json.get('contactInfo', {})

        organization_id = str(uuid.uuid4())
        transaction = get_db_client().transaction()

        @firestore.transactional # Use decorator from firebase_admin.firestore
        def create_org_in_transaction(transaction, organization_id, name, description, address, contact_info, user_id):
            org_ref = get_db_client().collection('organizations').document(organization_id)
            org_data = {
                'id': organization_id, 'name': name.strip(), 'description': description,
                'address': address, 'contactInfo': contact_info,
                'createdBy': user_id, 'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP,
                'subscriptionStatus': None, # Initialize subscription fields
                'stripeCustomerId': None,
                'stripeSubscriptionId': None,
                'subscriptionPlanId': None,
                'caseQuotaTotal': 0,
                'caseQuotaUsed': 0,
                'billingCycleStart': None,
                'billingCycleEnd': None
            }
            transaction.set(org_ref, org_data)

            member_id = str(uuid.uuid4())
            # Changed collection name from 'organizationMembers' to 'organization_memberships'
            member_ref = get_db_client().collection('organization_memberships').document(member_id)
            member_data = {
                'id': member_id, 'organizationId': organization_id, 'userId': user_id,
                'role': 'administrator', # Role is correctly set to 'administrator'
                'addedBy': user_id, # Added tracking field
                'joinedAt': firestore.SERVER_TIMESTAMP
            }
            transaction.set(member_ref, member_data)

            # Create a copy of org_data with sentinel values replaced for JSON serialization
            response_data = org_data.copy()
            # Replace SERVER_TIMESTAMP with None for JSON serialization
            if response_data.get('createdAt') == firestore.SERVER_TIMESTAMP:
                response_data['createdAt'] = None
            if response_data.get('updatedAt') == firestore.SERVER_TIMESTAMP:
                response_data['updatedAt'] = None
            return response_data

        org_data = create_org_in_transaction(transaction, organization_id, name, description, address, contact_info, user_id)

        # Convert timestamps for JSON response if needed
        if isinstance(org_data.get("createdAt"), datetime):
             org_data["createdAt"] = org_data["createdAt"].isoformat()
        if isinstance(org_data.get("updatedAt"), datetime):
             org_data["updatedAt"] = org_data["updatedAt"].isoformat()

        return flask.jsonify(org_data), 201
    except Exception as e:
        logging.error(f"Error creating organization: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def get_organization(request: Request):
    logging.info("Logic function get_organization called")
    try:
        organization_id = request.args.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID query parameter is required"}), 400
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id

        org_ref = get_db_client().collection('organizations').document(organization_id)
        org_doc = org_ref.get()
        if not org_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        # Use the centralized permission check function
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=organization_id,
            action="read",
            organizationId=organization_id # For org actions, resourceId and orgId are the same
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
             return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        org_data = org_doc.to_dict()
        # Convert timestamps for JSON response if needed
        if isinstance(org_data.get("createdAt"), datetime):
             org_data["createdAt"] = org_data["createdAt"].isoformat()
        if isinstance(org_data.get("updatedAt"), datetime):
             org_data["updatedAt"] = org_data["updatedAt"].isoformat()
        if isinstance(org_data.get("billingCycleStart"), datetime):
             org_data["billingCycleStart"] = org_data["billingCycleStart"].isoformat()
        if isinstance(org_data.get("billingCycleEnd"), datetime):
             org_data["billingCycleEnd"] = org_data["billingCycleEnd"].isoformat()

        return flask.jsonify(org_data), 200
    except Exception as e:
        logging.error(f"Error retrieving organization: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def update_organization(request: Request):
    logging.info("Logic function update_organization called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id

        if not request_json: return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        organization_id = request_json.get('organizationId') # Get ID from body
        if not organization_id: return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required in request body"}), 400

        org_ref = get_db_client().collection('organizations').document(organization_id)
        org_doc = org_ref.get()
        if not org_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=organization_id,
            action="update", organizationId=organization_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        update_data = {}
        allowed_fields = ['name', 'description', 'address', 'contactInfo']
        for field in allowed_fields:
            if field in request_json:
                 value = request_json[field]
                 # Add validation if needed (e.g., name cannot be empty)
                 if field == 'name' and (not value or not isinstance(value, str) or not value.strip()):
                     return flask.jsonify({"error": "Bad Request", "message": "Organization name cannot be empty"}), 400
                 update_data[field] = value

        if not update_data:
            return flask.jsonify({"message": "No valid fields provided for update"}), 200 # Or 400?

        update_data['updatedAt'] = firestore.SERVER_TIMESTAMP
        update_data['updatedBy'] = user_id # Track updater

        try:
            org_ref.update(update_data)
            updated_org_doc = org_ref.get()
            updated_org_data = updated_org_doc.to_dict()

            # Convert timestamps
            if isinstance(updated_org_data.get("createdAt"), datetime):
                 updated_org_data["createdAt"] = updated_org_data["createdAt"].isoformat()
            if isinstance(updated_org_data.get("updatedAt"), datetime):
                 updated_org_data["updatedAt"] = updated_org_data["updatedAt"].isoformat()
            if isinstance(updated_org_data.get("billingCycleStart"), datetime):
                 updated_org_data["billingCycleStart"] = updated_org_data["billingCycleStart"].isoformat()
            if isinstance(updated_org_data.get("billingCycleEnd"), datetime):
                 updated_org_data["billingCycleEnd"] = updated_org_data["billingCycleEnd"].isoformat()

            return flask.jsonify(updated_org_data), 200
        except Exception as e:
            logging.error(f"Firestore update operation failed: {str(e)}", exc_info=True)
            return flask.jsonify({"error": "Database Error", "message": f"Failed to update organization: {str(e)}"}), 500

    except Exception as e:
        logging.error(f"Error updating organization: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def delete_organization(request: Request):
    logging.info("Logic function delete_organization called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id

        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        organization_id = request_json.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400

        org_ref = get_db_client().collection('organizations').document(organization_id)
        org_doc = org_ref.get()
        if not org_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        # Check permissions
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=organization_id,
            action="delete",
            organizationId=organization_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        org_data = org_doc.to_dict()

        # Check if organization has an active subscription
        if org_data.get('subscriptionStatus') == 'active' and org_data.get('stripeSubscriptionId'):
            return flask.jsonify({
                "error": "Bad Request",
                "message": "Cannot delete organization with active subscription. Please cancel the subscription first."
            }), 400

        # Start a transaction to delete the organization and all related data
        transaction = get_db_client().transaction()

        @firestore.transactional
        def delete_org_in_transaction(transaction, org_id):
            # Delete all organization memberships
            members_query = get_db_client().collection('organization_memberships').where('organizationId', '==', org_id)
            members = list(members_query.stream())
            for member in members:
                transaction.delete(member.reference)

            # Mark all organization cases as deleted
            cases_query = get_db_client().collection('cases').where('organizationId', '==', org_id)
            cases = list(cases_query.stream())
            for case in cases:
                transaction.update(case.reference, {
                    'status': 'deleted',
                    'deletionDate': firestore.SERVER_TIMESTAMP,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                })

            # Delete the organization document
            transaction.delete(org_ref)

        try:
            delete_org_in_transaction(transaction, organization_id)
            logging.info(f"Organization {organization_id} and related data deleted by user {user_id}")
            return flask.jsonify({"message": "Organization deleted successfully"}), 200
        except Exception as e:
            logging.error(f"Transaction failed: {str(e)}", exc_info=True)
            return flask.jsonify({
                "error": "Database Error",
                "message": f"Failed to delete organization: {str(e)}"
            }), 500

    except Exception as e:
        logging.error(f"Error deleting organization: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500