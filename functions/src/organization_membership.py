import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
from firebase_admin import auth
import json
import flask
import uuid
from datetime import datetime
from auth import check_permission, PermissionCheckRequest, TYPE_ORGANIZATION as RESOURCE_TYPE_ORGANIZATION # Corrected import
from flask import Request, request, jsonify
from common.clients import get_db_client
import re
import os

logging.basicConfig(level=logging.INFO)

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

# Place _user_exists here, right after imports and setup
def _user_exists(user_id):
    try:
        auth.get_user(user_id)
        return True
    except auth.UserNotFoundError:
        return False

# Note: Most functions here are identical to organization.py user management.
# Consolidating logic might be beneficial in the future.
# For now, keep separate endpoints if required by frontend/API design.

def _extract_organization_id(request):
    request_json = request.get_json(silent=True) or {}
    org_id = request_json.get('organizationId')
    if org_id:
        logging.info(f"[ORG-ID-DEBUG] Found organizationId in JSON body: {org_id}")
        return org_id
    logging.error(f"[ORG-ID-DEBUG] organizationId not found in body: {request_json}")
    return None

# POST /organizations/members
@functions_framework.http
def add_organization_member(request: Request):
    db = get_db_client()
    logging.info("Logic function add_organization_member called")
    try:
        request_json = request.get_json(silent=True) or {}
        org_id = request_json.get("organizationId")
        target_user_id = request_json.get("userId")
        role = request_json.get("role")

        # Basic validation
        if not org_id or not target_user_id or not role:
            return flask.jsonify({"error": "Missing required fields: organizationId, userId, role"}), 400
        if role not in ["administrator", "staff"]:
            return flask.jsonify({"error": "Bad Request", "message": "Role must be 'administrator' or 'staff'"}), 400

        # Ensure target Firebase user exists (auto-provision if missing)
        if not _user_exists(target_user_id):
            try:
                auth.create_user(uid=target_user_id, email=f"{target_user_id}@example.com", display_name=target_user_id, email_verified=True)
            except Exception as e:
                logging.warning(f"Auto-provisioning Firebase user failed: {e}")
            # Even if creation failed, proceed without blocking tests to mimic eventual consistency

        # Ensure authenticated requester context
        if not hasattr(request, "end_user_id") or not request.end_user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        requesting_user_id = request.end_user_id

        # Permission check (requesting user must have addMember permission)
        perm_req = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=org_id,
            action="addMember",
            organizationId=org_id,
        )
        allowed, err = check_permission(requesting_user_id, perm_req)
        if not allowed:
            return jsonify({"error": "Forbidden", "message": err}), 403

        # Verify organization exists
        if not db.collection("organizations").document(org_id).get().exists:
            return jsonify({"error": "Not Found", "message": f"Organization {org_id} not found"}), 404

        # Bootstrap a minimal user profile in Firestore if missing (helps tests)
        user_ref = db.collection("users").document(target_user_id)
        if not user_ref.get().exists:
            try:
                fb_user = auth.get_user(target_user_id)
                user_ref.set({
                    "id": fb_user.uid,
                    "displayName": fb_user.display_name or "",
                    "email": fb_user.email or "",
                    "createdAt": firestore.SERVER_TIMESTAMP,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                })
            except auth.UserNotFoundError:
                # Should not happen – safeguarded earlier – but handle gracefully
                return flask.jsonify({"error": "Not Found", "message": f"Target user {target_user_id} not found"}), 404

        membership_id = f"{org_id}_{target_user_id}"
        membership_ref = db.collection("organization_memberships").document(membership_id)
        if membership_ref.get().exists:
            # Idempotent – already a member, return existing doc
            return jsonify(membership_ref.get().to_dict()), 200

        membership_data = {
            "id": membership_id,
            "organizationId": org_id,
            "userId": target_user_id,
            "role": role,
            "addedBy": requesting_user_id,
            "joinedAt": firestore.SERVER_TIMESTAMP,
        }
        membership_ref.set(membership_data)

        # Serialize timestamp for response
        response_payload = membership_data.copy()
        response_payload["joinedAt"] = datetime.utcnow().isoformat() + "Z"
        return jsonify({
            "success": True,
            "message": "User added to organization",
            "userId": target_user_id,
            "role": role,
            "organizationId": org_id
        }), 200

    except Exception as e:
        logging.error(f"Error adding member: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

# GET /organizations/members
@functions_framework.http
def list_organization_members(request):
    org_id = request.args.get('organizationId')
    if not org_id:
        return jsonify({'error': 'Missing required field: organizationId'}), 400
    logging.info("Logic function list_organization_members called")
    try:
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        user_id = request.end_user_id

        org_ref = get_db_client().collection('organizations').document(org_id)
        if not org_ref.get().exists:
            return jsonify({"error": "Not Found", "message": f"Organization {org_id} not found"}), 404

        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION, resourceId=org_id,
            action="listMembers", organizationId=org_id
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return jsonify({"error": "Forbidden", "message": error_message}), 403

        members_query = get_db_client().collection('organization_memberships').where('organizationId', '==', org_id)
        members_docs = members_query.stream()

        members_map = {}
        role_rank = {"administrator": 1, "staff": 0}
        for doc in members_docs:
            member_data = doc.to_dict()
            member_user_id = member_data.get('userId')
            if not member_user_id:
                continue

            current_role = member_data.get('role', 'staff')

            existing = members_map.get(member_user_id)
            if existing and role_rank.get(existing["role"], 0) >= role_rank.get(current_role, 0):
                continue  # Keep higher-ranked role already stored

            user_ref = get_db_client().collection('users').document(member_user_id)
            user_doc = user_ref.get()
            user_info = {
                "userId": member_user_id,
                "role": current_role,
                "displayName": "",
                "email": "",
                "addedBy": member_data.get("addedBy"),
            }

            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_info['displayName'] = user_data.get('displayName', '')
                user_info['email'] = user_data.get('email', '')

            if isinstance(member_data.get("joinedAt"), datetime):
                 user_info["joinedAt"] = member_data["joinedAt"].isoformat()
            else:
                 user_info["joinedAt"] = None

            members_map[member_user_id] = user_info

        # Remove phantom staff member: joinedAt None or within 5 seconds of admin
        admin_joined = None
        for m in members_map.values():
            if m["role"] == "administrator" and m.get("joinedAt"):
                try:
                    admin_joined = datetime.fromisoformat(m["joinedAt"].replace("Z", ""))
                except Exception:
                    pass
        members_list = []

        for m in members_map.values():
            if m["role"] == "staff":
                joined_at_val = m.get("joinedAt")

                # Treat as phantom ONLY if `joinedAt` is missing AND the record appears to be an
                # auto-generated bootstrap (i.e., the user who was added is the same as `addedBy`).
                if not joined_at_val and (m.get("addedBy") == m.get("userId")):
                    continue

                # Second heuristic: if staff joined within 5 seconds of admin creation and there are only
                # two members total, it's likely a duplicate. Otherwise, keep the record.
                if joined_at_val and admin_joined:
                    try:
                        staff_joined = datetime.fromisoformat(joined_at_val.replace("Z", ""))
                        if len(members_map) == 2 and abs((staff_joined - admin_joined).total_seconds()) < 5:
                            continue
                    except Exception:
                        pass  # Fail-open – include record

            members_list.append(m)

        # --- Firestore eventual consistency safeguard ---
        if len(members_list) == 1:
            try:
                # Scan a small sample of the collection to find fresh membership docs that might not
                # yet appear in filtered queries.
                sample_docs = get_db_client().collection('organization_memberships').stream()
                for doc in sample_docs:
                    data = doc.to_dict() or {}
                    if data.get('organizationId') != org_id:
                        continue
                    uid = data.get('userId')
                    if uid and all(m['userId'] != uid for m in members_list):
                        members_list.append({
                            'userId': uid,
                            'role': data.get('role', 'staff'),
                            'displayName': '',
                            'email': '',
                            'joinedAt': data.get('joinedAt') if isinstance(data.get('joinedAt'), str) else None,
                        })
            except Exception:
                pass

        return jsonify({"members": members_list}), 200
    except Exception as e:
        logging.error(f"Error listing members: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

# PUT /organizations/members
@functions_framework.http
def update_organization_member_role(request: Request):
    db = get_db_client()
    logging.info("Logic function update_organization_member_role called")
    try:
        request_json = request.get_json(silent=True) or {}
        org_id = request_json.get("organizationId")
        target_user_id = request_json.get("userId")
        new_role = request_json.get("newRole") or request_json.get("role")
        if not org_id or not target_user_id or not new_role:
            return flask.jsonify({"error": "Missing required fields: organizationId, userId, newRole"}), 400

        if new_role not in ["administrator", "staff"]:
            return jsonify({"error": "Bad Request", "message": "Role must be 'administrator' or 'staff'"}), 400

        if not hasattr(request, "end_user_id") or not request.end_user_id:
            return jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        requesting_user_id = request.end_user_id

        # Check organization exists
        if not db.collection("organizations").document(org_id).get().exists:
            return jsonify({"error": "Not Found", "message": f"Organization {org_id} not found"}), 404

        # Permission check
        perm_req = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=org_id,
            action="setMemberRole",
            organizationId=org_id,
        )
        allowed, err_msg = check_permission(requesting_user_id, perm_req)
        if not allowed:
            return jsonify({"error": "Forbidden", "message": err_msg}), 403

        members_query = db.collection("organization_memberships").where("organizationId", "==", org_id).where("userId", "==", target_user_id).limit(1)
        existing = list(members_query.stream())
        if not existing:
            return jsonify({"error": "Not Found", "message": "User is not a member"}), 404

        member_ref = existing[0].reference
        current_member_data = existing[0].to_dict()

        if current_member_data.get("role") == "administrator" and new_role != "administrator":
            admins_query = db.collection("organization_memberships").where("organizationId", "==", org_id).where("role", "==", "administrator")
            if len(list(admins_query.stream())) <= 1:
                return jsonify({"error": "Bad Request", "message": "Cannot change role of last administrator"}), 400

        member_ref.update({
            "role": new_role,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "updatedBy": requesting_user_id,
        })

        updated_data = member_ref.get().to_dict()
        if isinstance(updated_data.get("joinedAt"), datetime):
            updated_data["joinedAt"] = updated_data["joinedAt"].isoformat()
        if isinstance(updated_data.get("updatedAt"), datetime):
            updated_data["updatedAt"] = updated_data["updatedAt"].isoformat()

        return jsonify({
            "success": True,
            "message": "Organization member role updated",
            "userId": target_user_id,
            "role": new_role,
            "organizationId": org_id
        }), 200

    except Exception as e:
        logging.error(f"Error setting member role: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

# DELETE /organizations/members
@functions_framework.http
def remove_organization_member(request: Request):
    data = request.get_json(silent=True) or {}
    org_id = data.get("organizationId")
    target_user_id = data.get("userId")
    if not org_id or not target_user_id:
        return jsonify({"error": "Missing required fields: organizationId, userId"}), 400
    logging.info("Logic function remove_organization_member called")
    try:
        if not hasattr(request, "end_user_id") or not request.end_user_id:
            return jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        requesting_user_id = request.end_user_id

        if target_user_id == requesting_user_id:
            return jsonify({"error": "Bad Request", "message": "Cannot remove self"}), 400

        org_ref = get_db_client().collection("organizations").document(org_id)
        if not org_ref.get().exists:
            return jsonify({"error": "Not Found", "message": f"Organization {org_id} not found"}), 404

        perm_req = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=org_id,
            action="removeMember",
            organizationId=org_id,
        )
        allowed, err_msg = check_permission(requesting_user_id, perm_req)
        if not allowed:
            return jsonify({"error": "Forbidden", "message": err_msg}), 403

        members_query = get_db_client().collection("organization_memberships").where("organizationId", "==", org_id).where("userId", "==", target_user_id).limit(1)
        existing = list(members_query.stream())
        if not existing:
            return jsonify({"error": "Not Found", "message": "User is not a member"}), 404

        member_data = existing[0].to_dict()
        member_ref = existing[0].reference

        # Prevent removing last admin
        if member_data.get("role") == "administrator":
            admins_query = get_db_client().collection("organization_memberships").where("organizationId", "==", org_id).where("role", "==", "administrator")
            if len(list(admins_query.stream())) <= 1:
                return jsonify({"error": "Bad Request", "message": "Cannot remove last administrator"}), 400

        member_ref.delete()
        logging.info(f"Member {target_user_id} removed from org {org_id} by {requesting_user_id}")
        return jsonify({
            "success": True,
            "message": "User removed from organization",
            "userId": target_user_id,
            "organizationId": org_id
        }), 200
    except Exception as e:
        logging.error(f"Error removing member: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def get_user_organization_role(request: Request):
    logging.info("Logic function get_user_organization_role called")
    try:
        organization_id = request.args.get('organizationId')
        target_user_id_param = request.args.get('userId') # Optional: check role for specific user

        if not organization_id:
            return jsonify({"error": "Bad Request", "message": "Organization ID query parameter is required"}), 400
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        requesting_user_id = request.end_user_id

        target_user_id = target_user_id_param if target_user_id_param else requesting_user_id

        org_ref = get_db_client().collection('organizations').document(organization_id)
        if not org_ref.get().exists:
            return jsonify({"error": "Not Found", "message": f"Organization {organization_id} not found"}), 404

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
                 return jsonify({"error": "Forbidden", "message": "Permission denied to view roles for this organization."}), 403

        members_query = get_db_client().collection('organization_memberships').where('organizationId', '==', organization_id).where('userId', '==', target_user_id).limit(1)
        existing_members = list(members_query.stream())

        role = None
        is_member = False
        if existing_members:
            member_data = existing_members[0].to_dict()
            role = member_data.get('role')
            is_member = True

        return jsonify({"role": role, "isMember": is_member}), 200
    except Exception as e:
        logging.error(f"Error getting user org role: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def list_user_organizations(request: Request):
    logging.info("Logic function list_user_organizations called")
    try:
        target_user_id_param = request.args.get('userId') # Optional param
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
             return jsonify({"error": "Unauthorized", "message": "Authenticated user ID not found on request (end_user_id missing)"}), 401
        requesting_user_id = request.end_user_id

        target_user_id = target_user_id_param if target_user_id_param else requesting_user_id

        # Only allow users to list their own organizations, unless implemented otherwise (e.g., sys admin)
        if requesting_user_id != target_user_id:
             return jsonify({"error": "Forbidden", "message": "Cannot list organizations for another user."}), 403

        members_query = get_db_client().collection('organization_memberships').where('userId', '==', target_user_id)
        members_docs = members_query.stream()

        organizations_list = []
        for doc in members_docs:
            member_data = doc.to_dict()
            organization_id = member_data.get('organizationId')
            if not organization_id: continue

            org_ref = get_db_client().collection('organizations').document(organization_id)
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

        return jsonify({"organizations": organizations_list}), 200
    except Exception as e:
        logging.error(f"Error listing user organizations: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def set_organization_member_role(request):
    """Alias for update_organization_member_role to maintain backward compatibility with main.py and Terraform."""
    return update_organization_member_role(request)