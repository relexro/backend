import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
from firebase_admin import auth as firebase_auth # Renamed import
import json
import flask
import uuid
from datetime import datetime
from auth import check_permission, PermissionCheckRequest, TYPE_ORGANIZATION as RESOURCE_TYPE_ORGANIZATION # Corrected import
from flask import Request

logging.basicConfig(level=logging.INFO)

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

db = firestore.client()

# Note: Most functions here are identical to organization.py user management.
# Consolidating logic might be beneficial in the future.
# For now, keep separate endpoints if required by frontend/API design.

def add_organization_member(request: Request):
    logging.info("Logic function add_organization_member called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id # User performing the action

        if not request_json: return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        organization_id = request_json.get('organizationId')
        target_user_id = request_json.get('userId') # User being added
        role = request_json.get('role', 'staff') # Default role 'staff'

        if not organization_id: return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        if not target_user_id: return flask.jsonify({"error": "Bad Request", "message": "Target User ID (userId) is required"}), 400
        if role not in ['administrator', 'staff']: return flask.jsonify({"error": "Bad Request", "message": "Role must be 'administrator' or 'staff'"}), 400

        org_ref = db.collection('organizations').document(organization_id)
        if not org_ref.get().exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        target_user_ref = db.collection('users').document(target_user_id)
        if not target_user_ref.get().exists:
             return flask.jsonify({"error": "Not Found", "message": f"Target user {target_user_id} not found"}), 404

        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=organization_id,
            action="addMember", organizationId=organization_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        # Changed collection name from 'organizationMembers' to 'organization_memberships'
        members_query = db.collection('organization_memberships').where('organizationId', '==', organization_id).where('userId', '==', target_user_id).limit(1)
        if list(members_query.stream()):
            return flask.jsonify({"error": "Conflict", "message": "User is already a member"}), 409

        member_id = str(uuid.uuid4())
        # Changed collection name from 'organizationMembers' to 'organization_memberships'
        member_ref = db.collection('organization_memberships').document(member_id)
        member_data = {
            'id': member_id, 'organizationId': organization_id, 'userId': target_user_id,
            'role': role, 'addedBy': user_id, 'joinedAt': firestore.SERVER_TIMESTAMP
        }
        member_ref.set(member_data)

        # Create a copy of member_data with sentinel values replaced for JSON serialization
        response_data = member_data.copy()
        # Replace SERVER_TIMESTAMP with current time for JSON serialization
        if response_data.get('joinedAt') == firestore.SERVER_TIMESTAMP:
            response_data['joinedAt'] = datetime.now().isoformat()
        return flask.jsonify(response_data), 201
    except Exception as e:
        logging.error(f"Error adding member: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500
def set_organization_member_role(request: Request):
    logging.info("Logic function set_organization_member_role called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id # User performing action

        if not request_json: return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        organization_id = request_json.get('organizationId')
        target_user_id = request_json.get('userId') # User whose role is being set
        role = request_json.get('role')

        if not organization_id: return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        if not target_user_id: return flask.jsonify({"error": "Bad Request", "message": "Target User ID (userId) is required"}), 400
        if not role: return flask.jsonify({"error": "Bad Request", "message": "Role is required"}), 400
        if role not in ['administrator', 'staff']: return flask.jsonify({"error": "Bad Request", "message": "Role must be 'administrator' or 'staff'"}), 400

        org_ref = db.collection('organizations').document(organization_id)
        if not org_ref.get().exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=organization_id,
            action="setMemberRole", organizationId=organization_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        # Changed collection name from 'organizationMembers' to 'organization_memberships'
        members_query = db.collection('organization_memberships').where('organizationId', '==', organization_id).where('userId', '==', target_user_id).limit(1)
        existing_members = list(members_query.stream())
        if not existing_members:
            return flask.jsonify({"error": "Not Found", "message": "User is not a member"}), 404

        member_ref = existing_members[0].reference
        current_member_data = existing_members[0].to_dict()

        if current_member_data.get('role') == 'administrator' and role != 'administrator':
             # Changed collection name from 'organizationMembers' to 'organization_memberships'
             admins_query = db.collection('organization_memberships').where('organizationId', '==', organization_id).where('role', '==', 'administrator')
             admin_count = len(list(admins_query.stream()))
             if admin_count <= 1:
                 return flask.jsonify({"error": "Bad Request", "message": "Cannot change role of last administrator"}), 400

        update_data = {
            'role': role, 'updatedAt': firestore.SERVER_TIMESTAMP, 'updatedBy': user_id
        }
        member_ref.update(update_data)

        # Get the updated data
        updated_member_data = member_ref.get().to_dict()
        if isinstance(updated_member_data.get("joinedAt"), datetime):
             updated_member_data["joinedAt"] = updated_member_data["joinedAt"].isoformat()
        if isinstance(updated_member_data.get("updatedAt"), datetime):
             updated_member_data["updatedAt"] = updated_member_data["updatedAt"].isoformat()

        return flask.jsonify(updated_member_data), 200
    except Exception as e:
        logging.error(f"Error setting member role: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def list_organization_members(request: Request):
    logging.info("Logic function list_organization_members called")
    try:
        organization_id = request.args.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID query parameter is required"}), 400
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id

        org_ref = db.collection('organizations').document(organization_id)
        if not org_ref.get().exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=organization_id,
            action="listMembers", organizationId=organization_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        members_query = db.collection('organization_memberships').where('organizationId', '==', organization_id)
        members_docs = members_query.stream()

        members_list = []
        for doc in members_docs:
            member_data = doc.to_dict()
            member_user_id = member_data.get('userId')
            if not member_user_id: continue

            user_ref = db.collection('users').document(member_user_id)
            user_doc = user_ref.get()
            user_info = {"userId": member_user_id, "role": member_data.get('role', 'staff')}

            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_info['displayName'] = user_data.get('displayName', '')
                user_info['email'] = user_data.get('email', '')
            else:
                 user_info['displayName'] = "Profile N/A"
                 user_info['email'] = "N/A"

            if isinstance(member_data.get("joinedAt"), datetime):
                 user_info["joinedAt"] = member_data["joinedAt"].isoformat()
            else:
                 user_info["joinedAt"] = None
            members_list.append(user_info)

        return flask.jsonify({"members": members_list}), 200
    except Exception as e:
        logging.error(f"Error listing members: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def remove_organization_member(request: Request):
    logging.info("Logic function remove_organization_member called")
    try:
        request_json = request.get_json(silent=True)
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id # User performing action

        if not request_json: return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400

        organization_id = request_json.get('organizationId')
        target_user_id = request_json.get('userId') # User being removed

        if not organization_id: return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        if not target_user_id: return flask.jsonify({"error": "Bad Request", "message": "Target User ID (userId) is required"}), 400
        if user_id == target_user_id:
            return flask.jsonify({"error": "Bad Request", "message": "Cannot remove self"}), 400

        org_ref = db.collection('organizations').document(organization_id)
        if not org_ref.get().exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=organization_id,
            action="removeMember", organizationId=organization_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403

        # Changed collection name from 'organizationMembers' to 'organization_memberships'
        members_query = db.collection('organization_memberships').where('organizationId', '==', organization_id).where('userId', '==', target_user_id).limit(1)
        existing_members = list(members_query.stream())
        if not existing_members:
            return flask.jsonify({"error": "Not Found", "message": "User is not a member"}), 404

        member_data = existing_members[0].to_dict()
        member_ref = existing_members[0].reference

        if member_data.get('role') == 'administrator':
            # Changed collection name from 'organizationMembers' to 'organization_memberships'
            admins_query = db.collection('organization_memberships').where('organizationId', '==', organization_id).where('role', '==', 'administrator')
            admin_count = len(list(admins_query.stream()))
            if admin_count <= 1:
                return flask.jsonify({"error": "Bad Request", "message": "Cannot remove last administrator"}), 400

        member_ref.delete()
        logging.info(f"Member {target_user_id} removed from org {organization_id} by {user_id}")
        return flask.jsonify({"message": f"User {target_user_id} removed"}), 200
    except Exception as e:
        logging.error(f"Error removing member: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500
def get_user_organization_role(request: Request):
    logging.info("Logic function get_user_organization_role called")
    try:
        organization_id = request.args.get('organizationId')
        target_user_id_param = request.args.get('userId') # Optional: check role for specific user

        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID query parameter is required"}), 400
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        requesting_user_id = request.end_user_id

        target_user_id = target_user_id_param if target_user_id_param else requesting_user_id

        org_ref = db.collection('organizations').document(organization_id)
        if not org_ref.get().exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

        # Permission check: User can always check their own role.
        # To check others' roles, need 'listMembers' permission.
        if requesting_user_id != target_user_id:
            permission_request = PermissionCheckRequest(
                resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=organization_id,
                action="listMembers", organizationId=organization_id
            )
            has_permission, error_message = check_permission(requesting_user_id, permission_request)
            if not has_permission:
                 # Provide less specific message for non-admins trying to check others
                 return flask.jsonify({"error": "Forbidden", "message": "Permission denied to view roles for this organization."}), 403

        members_query = db.collection('organization_memberships').where('organizationId', '==', organization_id).where('userId', '==', target_user_id).limit(1)
        existing_members = list(members_query.stream())

        role = None
        is_member = False
        if existing_members:
            member_data = existing_members[0].to_dict()
            role = member_data.get('role')
            is_member = True

        return flask.jsonify({"role": role, "isMember": is_member}), 200
    except Exception as e:
        logging.error(f"Error getting user org role: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def list_user_organizations(request: Request):
    logging.info("Logic function list_user_organizations called")
    try:
        target_user_id_param = request.args.get('userId') # Optional param
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        requesting_user_id = request.end_user_id

        target_user_id = target_user_id_param if target_user_id_param else requesting_user_id

        # Only allow users to list their own organizations, unless implemented otherwise (e.g., sys admin)
        if requesting_user_id != target_user_id:
             return flask.jsonify({"error": "Forbidden", "message": "Cannot list organizations for another user."}), 403

        members_query = db.collection('organization_memberships').where('userId', '==', target_user_id)
        members_docs = members_query.stream()

        organizations_list = []
        for doc in members_docs:
            member_data = doc.to_dict()
            organization_id = member_data.get('organizationId')
            if not organization_id: continue

            org_ref = db.collection('organizations').document(organization_id)
            org_doc = org_ref.get()
            if org_doc.exists:
                org_data = org_doc.to_dict()
                org_info = {
                    'organizationId': organization_id,
                    'name': org_data.get('name', ''),
                    'description': org_data.get('description', ''),
                    'role': member_data.get('role'), # Role in this specific org
                }
                # Convert joinedAt timestamp
                if isinstance(member_data.get("joinedAt"), datetime):
                     org_info["joinedAt"] = member_data["joinedAt"].isoformat()
                else:
                     org_info["joinedAt"] = None
                organizations_list.append(org_info)

        return flask.jsonify({"organizations": organizations_list}), 200
    except Exception as e:
        logging.error(f"Error listing user organizations: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500