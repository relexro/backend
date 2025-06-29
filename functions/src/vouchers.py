import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
import uuid

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK (if not already initialized)
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

# Initialize Firestore client
db = firestore.client()

# Import auth functions
from auth import check_permission, PermissionCheckRequest, TYPE_ORGANIZATION

class VoucherCreateRequest(BaseModel):
    """Request model for creating a voucher."""
    code: str = Field(..., min_length=1, max_length=50, description="Voucher code")
    discount_percentage: float = Field(..., gt=0, le=100, description="Discount percentage (0-100)")
    expiration_date: Optional[datetime] = Field(None, description="Expiration date")
    usage_limit: int = Field(..., gt=0, description="Maximum number of times this voucher can be used")
    description: Optional[str] = Field(None, max_length=500, description="Voucher description")
    is_active: bool = Field(True, description="Whether the voucher is active")

    @field_validator('code')
    def validate_code(cls, v):
        """Validate voucher code format."""
        if not v.strip():
            raise ValueError('Voucher code cannot be empty')
        # Allow alphanumeric and hyphens/underscores
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Voucher code can only contain letters, numbers, hyphens, and underscores')
        return v.upper()  # Normalize to uppercase

class VoucherUpdateRequest(BaseModel):
    """Request model for updating a voucher."""
    discount_percentage: Optional[float] = Field(None, gt=0, le=100, description="Discount percentage (0-100)")
    expiration_date: Optional[datetime] = Field(None, description="Expiration date")
    usage_limit: Optional[int] = Field(None, gt=0, description="Maximum number of times this voucher can be used")
    description: Optional[str] = Field(None, max_length=500, description="Voucher description")
    is_active: Optional[bool] = Field(None, description="Whether the voucher is active")

def logic_create_voucher(request):
    """Create a new voucher (admin only).

    Handles POST requests for /v1/vouchers.

    Args:
        request (flask.Request): The Flask request object.
            - Expects JSON body containing voucher details.
            - Expects 'user_id' attribute attached by an auth wrapper.

    Returns:
        tuple: (response_body_dict, status_code)
    """
    try:
        # Get and validate request body
        try:
            body = request.get_json()
        except Exception:
            return {
                'error': 'InvalidJSON',
                'message': 'Request body must be valid JSON'
            }, 400

        if not isinstance(body, dict):
            return {
                'error': 'InvalidRequest',
                'message': 'Request body must be a JSON object'
            }, 400

        # Validate voucher data
        try:
            voucher_data = VoucherCreateRequest(**body)
        except Exception as e:
            return {
                'error': 'ValidationError',
                'message': str(e)
            }, 400

        # Get the requesting user ID from the request
        requesting_user_id = getattr(request, 'end_user_id', None)
        if not requesting_user_id:
            return {
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }, 401

        # Check if user is admin (you may need to implement admin role checking)
        # For now, we'll use a simple check - you can enhance this based on your admin system
        admin_check_request = PermissionCheckRequest(
            resourceType=TYPE_ORGANIZATION,
            resourceId="admin",  # This is a placeholder - implement proper admin checking
            action="manage_vouchers"
        )
        has_permission, error_message = check_permission(requesting_user_id, admin_check_request)

        if not has_permission:
            return {
                'error': 'Forbidden',
                'message': 'Admin privileges required to create vouchers'
            }, 403

        # Check if voucher code already exists
        voucher_ref = db.collection('vouchers').document(voucher_data.code)
        existing_voucher = voucher_ref.get()
        
        if existing_voucher.exists:
            return {
                'error': 'VoucherExists',
                'message': 'A voucher with this code already exists'
            }, 409

        # Create voucher document
        voucher_doc = {
            'code': voucher_data.code,
            'discountPercentage': voucher_data.discount_percentage,
            'expirationDate': voucher_data.expiration_date,
            'usageLimit': voucher_data.usage_limit,
            'usageCount': 0,
            'description': voucher_data.description,
            'isActive': voucher_data.is_active,
            'createdBy': requesting_user_id,
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        voucher_ref.set(voucher_doc)

        # Return the created voucher (without sensitive fields)
        response_data = {
            'id': voucher_data.code,
            'code': voucher_data.code,
            'discountPercentage': voucher_data.discount_percentage,
            'expirationDate': voucher_data.expiration_date.isoformat() if voucher_data.expiration_date else None,
            'usageLimit': voucher_data.usage_limit,
            'usageCount': 0,
            'description': voucher_data.description,
            'isActive': voucher_data.is_active,
            'createdAt': datetime.now(timezone.utc).isoformat()
        }

        return response_data, 201

    except Exception as e:
        logging.error(f"Error in logic_create_voucher: {str(e)}", exc_info=True)
        return {
            'error': 'InternalError',
            'message': 'An internal error occurred'
        }, 500

def logic_get_voucher(request, voucher_id):
    """Retrieve a voucher's details.

    Handles GET requests for /v1/vouchers/{voucherId}.

    Args:
        request (flask.Request): The Flask request object.
        voucher_id (str): The voucher ID/code.

    Returns:
        tuple: (response_body_dict, status_code)
    """
    try:
        # Get the requesting user ID from the request
        requesting_user_id = getattr(request, 'end_user_id', None)
        if not requesting_user_id:
            return {
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }, 401

        # Fetch voucher from Firestore
        voucher_ref = db.collection('vouchers').document(voucher_id)
        voucher_doc = voucher_ref.get()

        if not voucher_doc.exists:
            return {
                'error': 'VoucherNotFound',
                'message': 'Voucher not found'
            }, 404

        voucher_data = voucher_doc.to_dict()

        # Check if user is admin to see full details
        admin_check_request = PermissionCheckRequest(
            resourceType=TYPE_ORGANIZATION,
            resourceId="admin",
            action="manage_vouchers"
        )
        is_admin, _ = check_permission(requesting_user_id, admin_check_request)

        # Prepare response data
        response_data = {
            'id': voucher_data['code'],
            'code': voucher_data['code'],
            'discountPercentage': voucher_data['discountPercentage'],
            'isActive': voucher_data['isActive'],
            'description': voucher_data.get('description')
        }

        # Add admin-only fields
        if is_admin:
            response_data.update({
                'expirationDate': voucher_data['expirationDate'].isoformat() if voucher_data.get('expirationDate') else None,
                'usageLimit': voucher_data['usageLimit'],
                'usageCount': voucher_data['usageCount'],
                'createdBy': voucher_data['createdBy'],
                'createdAt': voucher_data['createdAt'].isoformat() if voucher_data.get('createdAt') else None,
                'updatedAt': voucher_data['updatedAt'].isoformat() if voucher_data.get('updatedAt') else None
            })

        return response_data, 200

    except Exception as e:
        logging.error(f"Error in logic_get_voucher: {str(e)}", exc_info=True)
        return {
            'error': 'InternalError',
            'message': 'An internal error occurred'
        }, 500

def logic_update_voucher(request, voucher_id):
    """Update a voucher's details (admin only).

    Handles PUT requests for /v1/vouchers/{voucherId}.

    Args:
        request (flask.Request): The Flask request object.
        voucher_id (str): The voucher ID/code.

    Returns:
        tuple: (response_body_dict, status_code)
    """
    try:
        # Get and validate request body
        try:
            body = request.get_json()
        except Exception:
            return {
                'error': 'InvalidJSON',
                'message': 'Request body must be valid JSON'
            }, 400

        if not isinstance(body, dict):
            return {
                'error': 'InvalidRequest',
                'message': 'Request body must be a JSON object'
            }, 400

        # Validate voucher data
        try:
            voucher_data = VoucherUpdateRequest(**body)
        except Exception as e:
            return {
                'error': 'ValidationError',
                'message': str(e)
            }, 400

        # Get the requesting user ID from the request
        requesting_user_id = getattr(request, 'end_user_id', None)
        if not requesting_user_id:
            return {
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }, 401

        # Check if user is admin
        admin_check_request = PermissionCheckRequest(
            resourceType=TYPE_ORGANIZATION,
            resourceId="admin",
            action="manage_vouchers"
        )
        has_permission, error_message = check_permission(requesting_user_id, admin_check_request)

        if not has_permission:
            return {
                'error': 'Forbidden',
                'message': 'Admin privileges required to update vouchers'
            }, 403

        # Fetch existing voucher
        voucher_ref = db.collection('vouchers').document(voucher_id)
        existing_voucher = voucher_ref.get()

        if not existing_voucher.exists:
            return {
                'error': 'VoucherNotFound',
                'message': 'Voucher not found'
            }, 404

        existing_data = existing_voucher.to_dict()

        # Prepare update data
        update_data = {
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        # Add fields that are being updated
        if voucher_data.discount_percentage is not None:
            update_data['discountPercentage'] = voucher_data.discount_percentage
        if voucher_data.expiration_date is not None:
            update_data['expirationDate'] = voucher_data.expiration_date
        if voucher_data.usage_limit is not None:
            # Ensure new usage limit is not less than current usage count
            current_usage = existing_data.get('usageCount', 0)
            if voucher_data.usage_limit < current_usage:
                return {
                    'error': 'InvalidUsageLimit',
                    'message': f'Usage limit cannot be less than current usage count ({current_usage})'
                }, 400
            update_data['usageLimit'] = voucher_data.usage_limit
        if voucher_data.description is not None:
            update_data['description'] = voucher_data.description
        if voucher_data.is_active is not None:
            update_data['isActive'] = voucher_data.is_active

        # Update voucher
        voucher_ref.update(update_data)

        # Fetch updated voucher for response
        updated_voucher = voucher_ref.get()
        updated_data = updated_voucher.to_dict()

        # Return the updated voucher
        response_data = {
            'id': updated_data['code'],
            'code': updated_data['code'],
            'discountPercentage': updated_data['discountPercentage'],
            'expirationDate': updated_data['expirationDate'].isoformat() if updated_data.get('expirationDate') else None,
            'usageLimit': updated_data['usageLimit'],
            'usageCount': updated_data['usageCount'],
            'description': updated_data.get('description'),
            'isActive': updated_data['isActive'],
            'createdBy': updated_data['createdBy'],
            'createdAt': updated_data['createdAt'].isoformat() if updated_data.get('createdAt') else None,
            'updatedAt': updated_data['updatedAt'].isoformat() if updated_data.get('updatedAt') else None
        }

        return response_data, 200

    except Exception as e:
        logging.error(f"Error in logic_update_voucher: {str(e)}", exc_info=True)
        return {
            'error': 'InternalError',
            'message': 'An internal error occurred'
        }, 500

def logic_delete_voucher(request, voucher_id):
    """Delete a voucher (admin only).

    Handles DELETE requests for /v1/vouchers/{voucherId}.

    Args:
        request (flask.Request): The Flask request object.
        voucher_id (str): The voucher ID/code.

    Returns:
        tuple: (response_body_dict, status_code)
    """
    try:
        # Get the requesting user ID from the request
        requesting_user_id = getattr(request, 'end_user_id', None)
        if not requesting_user_id:
            return {
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }, 401

        # Check if user is admin
        admin_check_request = PermissionCheckRequest(
            resourceType=TYPE_ORGANIZATION,
            resourceId="admin",
            action="manage_vouchers"
        )
        has_permission, error_message = check_permission(requesting_user_id, admin_check_request)

        if not has_permission:
            return {
                'error': 'Forbidden',
                'message': 'Admin privileges required to delete vouchers'
            }, 403

        # Fetch voucher to check if it exists
        voucher_ref = db.collection('vouchers').document(voucher_id)
        existing_voucher = voucher_ref.get()

        if not existing_voucher.exists:
            return {
                'error': 'VoucherNotFound',
                'message': 'Voucher not found'
            }, 404

        # Delete voucher
        voucher_ref.delete()

        return {
            'message': 'Voucher deleted successfully'
        }, 200

    except Exception as e:
        logging.error(f"Error in logic_delete_voucher: {str(e)}", exc_info=True)
        return {
            'error': 'InternalError',
            'message': 'An internal error occurred'
        }, 500

def validate_voucher_code(voucher_code: str) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Validate a voucher code and return voucher data if valid.
    
    Args:
        voucher_code (str): The voucher code to validate
        
    Returns:
        tuple: (is_valid, voucher_data, error_message)
    """
    try:
        voucher_ref = db.collection('vouchers').document(voucher_code.upper())
        voucher_doc = voucher_ref.get()

        if not voucher_doc.exists:
            return False, None, 'Voucher code not found'

        voucher_data = voucher_doc.to_dict()

        # Check if voucher is active
        if not voucher_data.get('isActive', False):
            return False, None, 'Voucher is not active'

        # Check expiration date
        expires_at = voucher_data.get('expirationDate')
        if expires_at and expires_at.timestamp() < datetime.now(timezone.utc).timestamp():
            return False, None, 'Voucher has expired'

        # Check usage limit
        usage_limit = voucher_data.get('usageLimit', 0)
        usage_count = voucher_data.get('usageCount', 0)
        if usage_limit > 0 and usage_count >= usage_limit:
            return False, None, 'Voucher usage limit reached'

        return True, voucher_data, None

    except Exception as e:
        logging.error(f"Error validating voucher code: {str(e)}", exc_info=True)
        return False, None, 'Error validating voucher' 