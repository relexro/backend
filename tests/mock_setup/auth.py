"""Mock implementation of auth.py for testing."""

# Global variables for configuring responses
_mock_user_id = "test_user_id"
_mock_user_auth_status = 200
_mock_user_auth_message = None
_mock_permissions_allowed = True
_mock_permissions_status = 200

def configure_mock(user_id=None, auth_status=None, auth_message=None, permissions_allowed=None, permissions_status=None):
    """Configure the mock responses."""
    global _mock_user_id, _mock_user_auth_status, _mock_user_auth_message, _mock_permissions_allowed, _mock_permissions_status
    
    if user_id is not None:
        _mock_user_id = user_id
    
    if auth_status is not None:
        _mock_user_auth_status = auth_status
    
    if auth_message is not None:
        _mock_user_auth_message = auth_message
    
    if permissions_allowed is not None:
        _mock_permissions_allowed = permissions_allowed
    
    if permissions_status is not None:
        _mock_permissions_status = permissions_status

def get_authenticated_user(request):
    """Mock implementation of get_authenticated_user."""
    if _mock_user_auth_status != 200:
        return (None, _mock_user_auth_status, _mock_user_auth_message or "Unauthorized")
    
    return ({"userId": _mock_user_id}, _mock_user_auth_status, _mock_user_auth_message)

def check_permissions(request):
    """Mock implementation of check_permissions."""
    return ({"allowed": _mock_permissions_allowed}, _mock_permissions_status) 