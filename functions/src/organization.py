import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
from firebase_admin import auth
import json
import flask
import uuid
import google.cloud.firestore
from datetime import datetime
from auth import check_permission, PermissionCheckRequest, RESOURCE_TYPE_ORGANIZATION

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK (if not already initialized)
try:
    firebase_admin.get_app()
except ValueError:
    # Use the application default credentials
    firebase_admin.initialize_app()

# Initialize Firestore client
db = google.cloud.firestore.Client()

@functions_framework.http
def create_organization(request):
    """Create a new organization account.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Parse request JSON data
        request_json = request.get_json(silent=True)
        
        user_id = request.user_id
        if not user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "User ID not provided"}), 401
        
        logging.info(f"Creating organization for user: {user_id}")
        
        # Validate required fields
        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400
        
        name = request_json.get('name')
        if not name:
            return flask.jsonify({"error": "Bad Request", "message": "Organization name is required"}), 400
        
        # Get optional fields
        description = request_json.get('description', '')
        address = request_json.get('address', {})
        contact_info = request_json.get('contactInfo', {})
        
        # Generate a unique ID for the organization
        organization_id = str(uuid.uuid4())
        
        # Initialize Firestore transaction
        transaction = db.transaction()
        
        # Define transaction operation
        @google.cloud.firestore.transactional
        def create_org_in_transaction(transaction, organization_id, name, description, address, contact_info, user_id):
            # Create the organization document
            org_ref = db.collection('organizations').document(organization_id)
            
            # Prepare the organization data
            org_data = {
                'id': organization_id,
                'name': name,
                'description': description,
                'address': address,
                'contactInfo': contact_info,
                'createdBy': user_id,
                'createdAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow()
            }
            
            # Create the organization in Firestore
            transaction.set(org_ref, org_data)
            
            # Add the user as an admin of the organization
            member_id = str(uuid.uuid4())
            member_ref = db.collection('organizationMembers').document(member_id)
            
            member_data = {
                'id': member_id,
                'organizationId': organization_id,
                'userId': user_id,
                'role': 'admin',  # Creator is always an admin
                'joinedAt': datetime.utcnow()
            }
            
            transaction.set(member_ref, member_data)
            
            return org_data
        
        # Execute the transaction
        org_data = create_org_in_transaction(transaction, organization_id, name, description, address, contact_info, user_id)
        
        # Return the created organization data
        return flask.jsonify(org_data), 201
    
    except Exception as e:
        logging.error(f"Error creating organization: {str(e)}")
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

@functions_framework.http
def get_organization(request):
    """Get an organization account by ID.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Get organization ID from request
        organization_id = request.args.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        
        user_id = request.user_id
        if not user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "User ID not provided"}), 401
        
        logging.info(f"Retrieving organization {organization_id} for user: {user_id}")
        
        # Get the organization document from Firestore
        org_ref = db.collection('organizations').document(organization_id)
        org_doc = org_ref.get()
        
        # Check if the organization exists
        if not org_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization with ID {organization_id} not found"}), 404
        
        # Check if user has permission to view this organization
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=organization_id,
            action="read",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403
        
        # Get organization data
        org_data = org_doc.to_dict()
        
        # Return the organization data
        return flask.jsonify(org_data), 200
    
    except Exception as e:
        logging.error(f"Error retrieving organization: {str(e)}")
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

@functions_framework.http
def add_organization_user(request):
    """Add a user to an organization account.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Parse request JSON data
        request_json = request.get_json(silent=True)
        
        user_id = request.user_id
        if not user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "User ID not provided"}), 401
        
        # Validate required fields
        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400
        
        organization_id = request_json.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        
        target_user_id = request_json.get('userId')
        if not target_user_id:
            return flask.jsonify({"error": "Bad Request", "message": "User ID is required"}), 400
        
        role = request_json.get('role', 'member')  # Default role is 'member'
        
        logging.info(f"Adding user {target_user_id} to organization {organization_id}")
        
        # Check if the organization exists
        org_ref = db.collection('organizations').document(organization_id)
        org_doc = org_ref.get()
        
        if not org_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization with ID {organization_id} not found"}), 404
        
        # Check if the target user exists
        user_ref = db.collection('users').document(target_user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"User with ID {target_user_id} not found"}), 404
        
        # Check if user has permission to add users to this organization
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=organization_id,
            action="addUser",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403
        
        # Check if user is already a member of the organization
        members_query = db.collection('organizationMembers').where('organizationId', '==', organization_id).where('userId', '==', target_user_id)
        existing_members = list(members_query.stream())
        
        if existing_members:
            return flask.jsonify({"error": "Conflict", "message": "User is already a member of this organization"}), 409
        
        # Generate a unique ID for the membership
        member_id = str(uuid.uuid4())
        
        # Create the membership document
        member_ref = db.collection('organizationMembers').document(member_id)
        
        # Prepare the membership data
        member_data = {
            'id': member_id,
            'organizationId': organization_id,
            'userId': target_user_id,
            'role': role,
            'addedBy': user_id,
            'joinedAt': datetime.utcnow()
        }
        
        # Create the membership in Firestore
        member_ref.set(member_data)
        
        # Return the created membership data
        return flask.jsonify(member_data), 201
    
    except Exception as e:
        logging.error(f"Error adding user to organization: {str(e)}")
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

@functions_framework.http
def set_user_role(request):
    """Assign or update a user's role in an organization.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Parse request JSON data
        request_json = request.get_json(silent=True)
        
        user_id = request.user_id
        if not user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "User ID not provided"}), 401
        
        # Validate required fields
        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400
        
        organization_id = request_json.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        
        target_user_id = request_json.get('userId')
        if not target_user_id:
            return flask.jsonify({"error": "Bad Request", "message": "User ID is required"}), 400
        
        role = request_json.get('role')
        if not role:
            return flask.jsonify({"error": "Bad Request", "message": "Role is required"}), 400
        
        logging.info(f"Setting role for user {target_user_id} in organization {organization_id} to {role}")
        
        # Check if the organization exists
        org_ref = db.collection('organizations').document(organization_id)
        org_doc = org_ref.get()
        
        if not org_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization with ID {organization_id} not found"}), 404
        
        # Check if user has permission to set roles in this organization
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=organization_id,
            action="setRole",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403
        
        # Find the membership document
        members_query = db.collection('organizationMembers').where('organizationId', '==', organization_id).where('userId', '==', target_user_id)
        existing_members = list(members_query.stream())
        
        if not existing_members:
            return flask.jsonify({"error": "Not Found", "message": "User is not a member of this organization"}), 404
        
        # Update the role of the membership
        member_ref = existing_members[0].reference
        
        # Update the role
        member_ref.update({
            'role': role,
            'updatedAt': datetime.utcnow(),
            'updatedBy': user_id
        })
        
        # Get the updated membership data
        updated_member = member_ref.get().to_dict()
        
        # Return the updated membership data
        return flask.jsonify(updated_member), 200
    
    except Exception as e:
        logging.error(f"Error setting user role: {str(e)}")
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

@functions_framework.http
def update_organization(request):
    """Update an organization account.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Parse request JSON data
        request_json = request.get_json(silent=True)
        
        user_id = request.user_id
        if not user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "User ID not provided"}), 401
        
        # Validate required fields
        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400
        
        organization_id = request_json.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        
        logging.info(f"Updating organization {organization_id} for user: {user_id}")
        
        # Get the organization document from Firestore
        org_ref = db.collection('organizations').document(organization_id)
        org_doc = org_ref.get()
        
        # Check if the organization exists
        if not org_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization with ID {organization_id} not found"}), 404
        
        # Check if user has permission to update this organization
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=organization_id,
            action="update",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403
        
        # Prepare the update data
        update_data = {}
        
        # Update fields if provided
        if 'name' in request_json:
            name = request_json.get('name')
            if not name:
                return flask.jsonify({"error": "Bad Request", "message": "Organization name cannot be empty"}), 400
            update_data['name'] = name
        
        if 'description' in request_json:
            update_data['description'] = request_json.get('description', '')
        
        if 'address' in request_json:
            update_data['address'] = request_json.get('address', {})
        
        if 'contactInfo' in request_json:
            update_data['contactInfo'] = request_json.get('contactInfo', {})
        
        # If no updates were provided, return early
        if not update_data:
            return flask.jsonify({"message": "No updates provided"}), 200
        
        # Add update timestamp
        update_data['updatedAt'] = datetime.utcnow()
        
        # Apply the updates to Firestore
        org_ref.update(update_data)
        
        # Get the updated organization data
        updated_org = org_ref.get().to_dict()
        
        # Return the updated organization data
        return flask.jsonify(updated_org), 200
    
    except Exception as e:
        logging.error(f"Error updating organization: {str(e)}")
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

@functions_framework.http
def list_organization_users(request):
    """List all users in an organization."""
    try:
        # Get organization ID from request
        organization_id = request.args.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        
        user_id = request.user_id
        if not user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "User ID not provided"}), 401
        
        logging.info(f"Listing users in organization {organization_id}")
        
        # Check if the organization exists
        org_ref = db.collection('organizations').document(organization_id)
        org_doc = org_ref.get()
        
        if not org_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization with ID {organization_id} not found"}), 404
        
        # Check if user has permission to list users in this organization
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=organization_id,
            action="listUsers",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403
        
        # Get all memberships for the organization
        members_query = db.collection('organizationMembers').where('organizationId', '==', organization_id)
        
        # Execute the query
        members_docs = members_query.stream()
        
        # Process the results
        members = []
        for doc in members_docs:
            member_data = doc.to_dict()
            member_user_id = member_data.get('userId')
            
            # Fetch basic user info
            user_ref = db.collection('users').document(member_user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                
                # Include only necessary user information
                user_info = {
                    'userId': member_user_id,
                    'displayName': user_data.get('displayName', ''),
                    'email': user_data.get('email', ''),
                    'role': member_data.get('role', 'member'),
                    'joinedAt': member_data.get('joinedAt')
                }
                
                members.append(user_info)
        
        # Return the list of users
        return flask.jsonify({"users": members}), 200
    
    except Exception as e:
        logging.error(f"Error listing organization users: {str(e)}")
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500

@functions_framework.http
def remove_organization_user(request):
    """Remove a user from an organization.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Parse request JSON data
        request_json = request.get_json(silent=True)
        
        user_id = request.user_id
        if not user_id:
            return flask.jsonify({"error": "Unauthorized", "message": "User ID not provided"}), 401
        
        # Validate required fields
        if not request_json:
            return flask.jsonify({"error": "Bad Request", "message": "No JSON data provided"}), 400
        
        organization_id = request_json.get('organizationId')
        if not organization_id:
            return flask.jsonify({"error": "Bad Request", "message": "Organization ID is required"}), 400
        
        target_user_id = request_json.get('userId')
        if not target_user_id:
            return flask.jsonify({"error": "Bad Request", "message": "User ID is required"}), 400
        
        logging.info(f"Removing user {target_user_id} from organization {organization_id}")
        
        # Check if the organization exists
        org_ref = db.collection('organizations').document(organization_id)
        org_doc = org_ref.get()
        
        if not org_doc.exists:
            return flask.jsonify({"error": "Not Found", "message": f"Organization with ID {organization_id} not found"}), 404
        
        # Check if user has permission to remove users from this organization
        permission_request = PermissionCheckRequest(
            resourceType=RESOURCE_TYPE_ORGANIZATION,
            resourceId=organization_id,
            action="removeUser",
            organizationId=organization_id
        )
        
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return flask.jsonify({"error": "Forbidden", "message": error_message}), 403
        
        # Find the membership document
        members_query = db.collection('organizationMembers').where('organizationId', '==', organization_id).where('userId', '==', target_user_id)
        existing_members = list(members_query.stream())
        
        if not existing_members:
            return flask.jsonify({"error": "Not Found", "message": "User is not a member of this organization"}), 404
        
        # Get the member role to make sure we're not removing the last admin
        member_role = existing_members[0].to_dict().get('role')
        
        # If we're removing an admin, check if there are other admins
        if member_role == 'admin':
            # Count the number of admins in the organization
            admins_query = db.collection('organizationMembers').where('organizationId', '==', organization_id).where('role', '==', 'admin')
            admin_count = len(list(admins_query.stream()))
            
            if admin_count <= 1:
                return flask.jsonify({
                    "error": "Bad Request", 
                    "message": "Cannot remove the last admin of an organization. Promote another user to admin first."
                }), 400
        
        # Remove the user from the organization
        for member in existing_members:
            member.reference.delete()
        
        # Return success response
        return flask.jsonify({"message": f"User {target_user_id} has been removed from organization {organization_id}"}), 200
    
    except Exception as e:
        logging.error(f"Error removing user from organization: {str(e)}")
        return flask.jsonify({"error": "Internal Server Error", "message": str(e)}), 500 