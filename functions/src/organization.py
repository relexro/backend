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

logging.basicConfig(level=logging.INFO)

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

db = firestore.client() # Use firebase_admin's firestore client

def create_organization(request: Request):
    logging.info("Logic function create_organization called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'user_id'):
             return flask.jsonify({"error": "Unauthorized", "message": "Authentication data missing"}), 401
        user_id = request.user_id

        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400
        name = request_json.get('name')
        if not name or not isinstance(name, str) or not name.strip():
            return flask.jsonify({"error": "Bad Request", "message": "Valid organization name is required"}), 400

        description = request_json.get('description', '')
        address = request_json.get('address', {})
        contact_info = request_json.get('contactInfo', {})

        organization_id = str(uuid.uuid4())
        transaction = db.transaction()

        @firestore.transactional # Use decorator from firebase_admin.firestore
        def create_org_in_transaction(transaction, organization_id, name, description, address, contact_info, user_id):
            org_ref = db.collection('organizations').document(organization_id)
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
            member_ref = db.collection('organization_memberships').document(member_id)
            member_data = {
                'id': member_id, 'organizationId': organization_id, 'userId': user_id,
                'role': 'administrator', # Role is correctly set to 'administrator'
                'addedBy': user_id, # Added tracking field
                'joinedAt': firestore.SERVER_TIMESTAMP
            }
            transaction.set(member_ref, member_data)
            return org_data

        org_data = create_org_in_transaction(transaction, organization_id, name, description, address, contact_info, user_id)

        # Convert timestamps for JSON response if needed
        if isinstance(org_data.get("createdAt"), datetime.datetime):
             org_data["createdAt"] = org_data["createdAt"].isoformat()
        if isinstance(org_data.get("updatedAt"), datetime.datetime):
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
        if not hasattr(request, 'user_id'):
             return flask.jsonify({"error": "Unauthorized", "message": "Authentication data missing"}), 401
        user_id = request.user_id

        org_ref = db.collection('organizations').document(organization_id)
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
        if isinstance(org_data.get("createdAt"), datetime.datetime):
             org_data["createdAt"] = org_data["createdAt"].isoformat()
        if isinstance(org_data.get("updatedAt"), datetime.datetime):
             org_data["updatedAt"] = org_data["updatedAt"].isoformat()
        if isinstance(org_data.get("billingCycleStart"), datetime.datetime):
             org_data["billingCycleStart"] = org_data["billingCycleStart"].isoformat()
        if isinstance(org_data.get("billingCycleEnd"), datetime.datetime):
             org_data["billingCycleEnd"] = org_data["billingCycleEnd"].isoformat()

        return flask.jsonify(org_data), 200
    except Exception as e:
        logging.error(f"Error retrieving organization: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500


def add_organization_user(request: Request):
    logging.info("Logic function add_organization_user called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'user_id'):
             return flask.jsonify({"error": "Unauthorized", "message": "Authentication data missing"}), 401
        user_id = request.user_id # This is the user performing the action

        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        organization_id = request_json.get('organizationId')
        target_user_id = request_json.get('userId') # User being added
        role = request_json.get('role', 'staff') # Default role 'staff'

        if not organization_id: return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        if not target_user_id: return flask.jsonify({"error": "Bad Request", "message": "Target User ID (userId) is required"}), 400
        if role not in ['administrator', 'staff']: return flask.jsonify({"error": "Bad Request", "message": "Role must be 'administrator' or 'staff'"}), 400

        org_ref = db.collection('organizations').document(organization_id)
        org_doc = org_ref.get()
        if not org_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        # Verify target user exists (optional, depends on workflow)
        # target_user_record = firebase_auth.get_user(target_user_id) # Check Firebase Auth
        target_user_ref = db.collection('users').document(target_user_id) # Check Firestore profile
        if not target_user_ref.get().exists:
             return flask.jsonify({"error": "Not Found", "message": f"Target user {target_user_id} not found"}), 404

        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=organization_id,
            action="addUser", organizationId=organization_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        members_query = db.collection('organizationMembers').where('organizationId', '==', organization_id).where('userId', '==', target_user_id).limit(1)
        existing_members = list(members_query.stream())
        if existing_members:
            return flask.jsonify({"error": "Conflict", "message": "User is already a member of this organization"}), 409

        member_id = str(uuid.uuid4())
        member_ref = db.collection('organizationMembers').document(member_id)
        member_data = {
            'id': member_id, 'organizationId': organization_id, 'userId': target_user_id,
            'role': role, 'addedBy': user_id, 'joinedAt': firestore.SERVER_TIMESTAMP
        }
        member_ref.set(member_data)

        # Convert timestamp for response
        member_data['joinedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return flask.jsonify(member_data), 201
    except firebase_auth.UserNotFoundError:
         return flask.jsonify({"error": "Not Found", "message": f"Target user {target_user_id} not found in Firebase Authentication"}), 404
    except Exception as e:
        logging.error(f"Error adding user to organization: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def set_user_role(request: Request):
    logging.info("Logic function set_user_role called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'user_id'):
             return flask.jsonify({"error": "Unauthorized", "message": "Authentication data missing"}), 401
        user_id = request.user_id # User performing the action

        if not request_json: return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        organization_id = request_json.get('organizationId')
        target_user_id = request_json.get('userId') # User whose role is being set
        role = request_json.get('role')

        if not organization_id: return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        if not target_user_id: return flask.jsonify({"error": "Bad Request", "message": "Target User ID (userId) is required"}), 400
        if not role: return flask.jsonify({"error": "Bad Request", "message": "Role is required"}), 400
        if role not in ['administrator', 'staff']: return flask.jsonify({"error": "Bad Request", "message": "Role must be 'administrator' or 'staff'"}), 400

        # Ensure target user is not trying to change their own role to prevent self-demotion issues?
        # if user_id == target_user_id:
        #     return flask.jsonify({"error": "Bad Request", "message": "Users cannot change their own role."}), 400

        org_ref = db.collection('organizations').document(organization_id)
        if not org_ref.get().exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=organization_id,
            action="setRole", organizationId=organization_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        members_query = db.collection('organizationMembers').where('organizationId', '==', organization_id).where('userId', '==', target_user_id).limit(1)
        existing_members = list(members_query.stream())
        if not existing_members:
            return flask.jsonify({"error": "Not Found", "message": "User is not a member of this organization"}), 404

        member_ref = existing_members[0].reference
        current_member_data = existing_members[0].to_dict()

        # Prevent removing the last administrator
        if current_member_data.get('role') == 'administrator' and role != 'administrator':
             admins_query = db.collection('organizationMembers').where('organizationId', '==', organization_id).where('role', '==', 'administrator')
             admin_count = len(list(admins_query.stream())) # Simple count
             if admin_count <= 1:
                 return flask.jsonify({"error": "Bad Request", "message": "Cannot change role of the last administrator."}), 400

        member_ref.update({
            'role': role,
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'updatedBy': user_id # Track who made the change
        })

        updated_member_doc = member_ref.get()
        updated_member_data = updated_member_doc.to_dict()

        # Convert timestamps for response
        if isinstance(updated_member_data.get("joinedAt"), datetime.datetime):
             updated_member_data["joinedAt"] = updated_member_data["joinedAt"].isoformat()
        if isinstance(updated_member_data.get("updatedAt"), datetime.datetime):
             updated_member_data["updatedAt"] = updated_member_data["updatedAt"].isoformat()

        return flask.jsonify(updated_member_data), 200
    except Exception as e:
        logging.error(f"Error setting user role: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def update_organization(request: Request):
    logging.info("Logic function update_organization called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'user_id'):
             return flask.jsonify({"error": "Unauthorized", "message": "Authentication data missing"}), 401
        user_id = request.user_id

        if not request_json: return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        organization_id = request_json.get('organizationId') # Get ID from body
        if not organization_id: return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required in request body"}), 400

        org_ref = db.collection('organizations').document(organization_id)
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
            if isinstance(updated_org_data.get("createdAt"), datetime.datetime):
                 updated_org_data["createdAt"] = updated_org_data["createdAt"].isoformat()
            if isinstance(updated_org_data.get("updatedAt"), datetime.datetime):
                 updated_org_data["updatedAt"] = updated_org_data["updatedAt"].isoformat()
            if isinstance(updated_org_data.get("billingCycleStart"), datetime.datetime):
                 updated_org_data["billingCycleStart"] = updated_org_data["billingCycleStart"].isoformat()
            if isinstance(updated_org_data.get("billingCycleEnd"), datetime.datetime):
                 updated_org_data["billingCycleEnd"] = updated_org_data["billingCycleEnd"].isoformat()

            return flask.jsonify(updated_org_data), 200
        except Exception as e:
            logging.error(f"Firestore update operation failed: {str(e)}", exc_info=True)
            return flask.jsonify({"error": "Database Error", "message": f"Failed to update organization: {str(e)}"}), 500
            
    except Exception as e:
        logging.error(f"Error updating organization: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500
    
def list_organization_users(request: Request):
    logging.info("Logic function list_organization_users called")
    try:
        organization_id = request.args.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID query parameter is required"}), 400
        if not hasattr(request, 'user_id'):
             return flask.jsonify({"error": "Unauthorized", "message": "Authentication data missing"}), 401
        user_id = request.user_id

        org_ref = db.collection('organizations').document(organization_id)
        if not org_ref.get().exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=organization_id,
            action="listUsers", organizationId=organization_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        members_query = db.collection('organizationMembers').where('organizationId', '==', organization_id)
        members_docs = members_query.stream()

        users_list = []
        for doc in members_docs:
            member_data = doc.to_dict()
            member_user_id = member_data.get('userId')
            if not member_user_id: continue # Skip if userId is missing

            user_ref = db.collection('users').document(member_user_id)
            user_doc = user_ref.get()
            user_info = {"userId": member_user_id, "role": member_data.get('role', 'staff')} # Default role

            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_info['displayName'] = user_data.get('displayName', '')
                user_info['email'] = user_data.get('email', '')
                # Add other desired user fields, e.g., photoURL
            else:
                 # User profile might not exist, handle gracefully
                 user_info['displayName'] = "User profile not found"
                 user_info['email'] = "Unknown"

            # Convert joinedAt timestamp
            if isinstance(member_data.get("joinedAt"), datetime.datetime):
                 user_info["joinedAt"] = member_data["joinedAt"].isoformat()
            else:
                 user_info["joinedAt"] = None

            users_list.append(user_info)

        return flask.jsonify({"users": users_list}), 200
    except Exception as e:
        logging.error(f"Error listing organization users: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500


def remove_organization_user(request: Request):
    logging.info("Logic function remove_organization_user called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'user_id'):
             return flask.jsonify({"error": "Unauthorized", "message": "Authentication data missing"}), 401
        user_id = request.user_id # User performing action

        if not request_json: return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        organization_id = request_json.get('organizationId')
        target_user_id = request_json.get('userId') # User being removed

        if not organization_id: return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        if not target_user_id: return flask.jsonify({"error": "Bad Request", "message": "Target User ID (userId) is required"}), 400

        # Prevent users from removing themselves?
        if user_id == target_user_id:
            return flask.jsonify({"error": "Bad Request", "message": "Users cannot remove themselves from an organization. Ask an administrator."}), 400

        org_ref = db.collection('organizations').document(organization_id)
        if not org_ref.get().exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=organization_id,
            action="removeUser", organizationId=organization_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        members_query = db.collection('organizationMembers').where('organizationId', '==', organization_id).where('userId', '==', target_user_id).limit(1)
        existing_members = list(members_query.stream())
        if not existing_members:
            return flask.jsonify({"error": "Not Found", "message": "User is not a member of this organization"}), 404

        member_data = existing_members[0].to_dict()
        member_ref = existing_members[0].reference

        # Prevent removing the last administrator
        if member_data.get('role') == 'administrator':
            admins_query = db.collection('organizationMembers').where('organizationId', '==', organization_id).where('role', '==', 'administrator')
            admin_count = len(list(admins_query.stream()))
            if admin_count <= 1:
                return flask.jsonify({"error": "Bad Request", "message": "Cannot remove the last administrator."}), 400

        member_ref.delete()
        logging.info(f"User {target_user_id} removed from org {organization_id} by user {user_id}")

        return flask.jsonify({"message": f"User {target_user_id} removed successfully"}), 200
    except Exception as e:
        logging.error(f"Error removing user from organization: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def delete_organization(request: Request):
    logging.info("Logic function delete_organization called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'user_id'):
             return flask.jsonify({"error": "Unauthorized", "message": "Authentication data missing"}), 401
        user_id = request.user_id

        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        organization_id = request_json.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400

        org_ref = db.collection('organizations').document(organization_id)
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
        transaction = db.transaction()

        @firestore.transactional
        def delete_org_in_transaction(transaction, org_id):
            # Delete all organization memberships
            members_query = db.collection('organization_memberships').where('organizationId', '==', org_id)
            members = list(members_query.stream())
            for member in members:
                transaction.delete(member.reference)

            # Mark all organization cases as deleted
            cases_query = db.collection('cases').where('organizationId', '==', org_id)
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