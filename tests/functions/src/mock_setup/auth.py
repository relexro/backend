"""Mock auth module for testing."""
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Constants to match the real auth module
TYPE_CASE = "case"
TYPE_ORGANIZATION = "organization"
TYPE_PARTY = "party"
TYPE_DOCUMENT = "document"

ROLE_ADMIN = "administrator"
ROLE_STAFF = "staff"
ROLE_OWNER = "owner"

ACTION_READ = "read"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_CREATE = "create"
ACTION_LIST = "list"

# Mock user ID for tests
_mock_user_id = "test_user_id"
_mock_auth_status = 200
_mock_auth_message = None
_mock_permissions_allowed = True
_mock_permissions_status = 200

# Mock class for PermissionCheckRequest
@dataclass
class PermissionCheckRequest:
    resourceId: Optional[str] = None
    action: str = ""
    resourceType: str = ""
    organizationId: Optional[str] = None

def configure_mock(
    user_id=None,
    auth_status=None,
    auth_message=None,
    permissions_allowed=None,
    permissions_status=None
):
    """Configure the mock auth module with the specified values."""
    global _mock_user_id, _mock_auth_status, _mock_auth_message, _mock_permissions_allowed, _mock_permissions_status

    if user_id is not None:
        _mock_user_id = user_id
    if auth_status is not None:
        _mock_auth_status = auth_status
    if auth_message is not None:
        _mock_auth_message = auth_message
    if permissions_allowed is not None:
        _mock_permissions_allowed = permissions_allowed
    if permissions_status is not None:
        _mock_permissions_status = permissions_status

    logging.info(f"Mock auth configured: user_id={_mock_user_id}, permissions_allowed={_mock_permissions_allowed}")

def get_authenticated_user(request):
    """Mock implementation of get_authenticated_user."""
    # Return a tuple of (user_data, status_code, error_message)
    if _mock_auth_status == 200:
        return {"userId": _mock_user_id}, _mock_auth_status, _mock_auth_message
    else:
        return None, _mock_auth_status, _mock_auth_message or "Unauthorized"

def check_permissions(request):
    """Mock implementation of check_permissions."""
    # Return a tuple of (response_data, status_code)
    if _mock_permissions_allowed:
        return {"allowed": True}, _mock_permissions_status
    else:
        return {"allowed": False, "reason": "Permission denied"}, _mock_permissions_status

def check_permission(request):
    """Mock implementation of check_permission (singular)."""
    # Return a tuple of (response_data, status_code)
    if _mock_permissions_allowed:
        return {"allowed": True}, _mock_permissions_status
    else:
        return {"allowed": False, "reason": "Permission denied"}, _mock_permissions_status

def requires_auth(f):
    """Mock decorator for requires_auth."""
    def wrapper(request):
        # Add user_id to request
        request.end_user_id = _mock_user_id
        return f(request)
    return wrapper

def has_permission(user_id, resource_type, resource_id, action):
    """Mock implementation of has_permission."""
    return _mock_permissions_allowed

def can_access_resource(user_id, resource_type, resource_id):
    """Mock implementation of can_access_resource."""
    return _mock_permissions_allowed

def get_user_roles(user_id):
    """Mock implementation of get_user_roles."""
    return ["user"]
