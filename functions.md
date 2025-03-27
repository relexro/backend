# Relex Backend Functions

## Function Overview

The backend consists of several modules, each handling specific functionality:

### Main Entry Points (`main.py`)
- HTTP Cloud Functions that handle routing and initial request processing
- Authentication and error handling wrappers
- Function exports for deployment

### Authentication (`auth.py`)
- `validate_user`: Token validation
- `check_permissions`: Permission checking for resources
- `get_user_role`: Role retrieval for organizations
- `get_authenticated_user`: Authentication helper

### Cases (`cases.py`)
- `create_case`: Case creation (individual or organization)
- `get_case`: Case retrieval with permission checks
- `list_cases`: Case listing with filters
- `archive_case`: Case archival
- `delete_case`: Case deletion
- `upload_file`: File upload to cases
- `download_file`: File download with signed URLs

### Organization Management
Split across multiple files for different aspects:

#### Core Organization (`organization.py`)
- `create_organization`: Organization creation
- `get_organization`: Organization retrieval
- `update_organization`: Organization updates

#### Membership Management (`organization_membership.py`)
- `add_organization_member`: Member addition with role validation
- `set_organization_member_role`: Role updates with admin checks
- `list_organization_members`: Member listing with pagination
- `remove_organization_member`: Member removal with safeguards
- `get_user_organization_role`: Role retrieval
- `list_user_organizations`: Organization listing for users

### User Management (`user.py`)
- `create_user_profile`: Profile creation (Firebase Auth trigger)
- `get_user_profile`: Profile retrieval
- `update_user_profile`: Profile updates

### Payment Processing (`payments.py`)
- `create_payment_intent`: Stripe payment intent creation
- `create_checkout_session`: Checkout session creation
- `handle_stripe_webhook`: Webhook handling

## Implementation Details

### Authentication Flow
```python
def get_authenticated_user(request):
    """Helper function to validate a user's authentication token and return user info."""
    # Token extraction from Authorization header
    # Firebase token validation
    # Return user data or error
```

### Permission Model
```python
def check_permissions(request):
    """Check if a user can perform an action on a resource."""
    # Extract request data
    # Validate action type
    # Check organization membership if applicable
    # Verify role permissions or individual case ownership
    # Return permission status
```

### Case Management
```python
def create_case(request):
    """Create a new case (individual or organization)."""
    # Validate input data
    # Check organization permissions if applicable
    # Handle payment for individual cases
    # Create case document
    # Return case details
```

### File Operations
```python
def upload_file(request):
    """Upload a file to a case."""
    # Validate file and permissions
    # Generate storage path
    # Upload to Firebase Storage
    # Create document record
    # Return file details
```

### Organization Management
```python
def add_organization_member(request):
    """Add a member to an organization."""
    # Validate input
    # Check admin permissions
    # Create membership record
    # Return membership details
```

## Error Handling

All functions implement consistent error handling:
```python
try:
    # Function logic
except Exception as e:
    return {"error": str(e)}, 500
```

Common error responses:
- 400: Bad Request (invalid input)
- 401: Unauthorized (invalid token)
- 403: Forbidden (insufficient permissions)
- 404: Not Found (resource doesn't exist)
- 500: Internal Server Error

## Development Notes

1. All functions require Firebase Authentication
2. Dual case ownership model (individual/organization)
3. Organization-based permission model
4. Firestore for data storage
5. Firebase Storage for files
6. Stripe for payments (individual cases)