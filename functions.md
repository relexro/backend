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
- `create_payment_intent`: 
  - Creates Stripe payment intent based on case tier (1, 2, 3)
  - Maps tier to appropriate amount (Tier 1=900, Tier 2=2900, Tier 3=9900 cents)
  - Stores payment metadata in Firestore
  - Returns client secret for frontend payment processing

- `create_checkout_session`: 
  - Creates Stripe checkout session for subscriptions or one-time payments
  - For subscriptions: Maps planId (e.g., 'personal_monthly') to Stripe priceId
  - Can be used for both user and organization subscriptions
  - Returns checkout URL for frontend redirection

- `handle_stripe_webhook`: 
  - Processes Stripe webhook events securely
  - Handles checkout.session.completed for subscription and payment events
  - Handles invoice.payment_failed to update subscription status
  - Handles customer.subscription.deleted/updated events
  - Updates relevant Firestore records based on events

- `cancel_subscription`: 
  - Allows users to cancel their subscriptions
  - Verifies appropriate permissions (own subscription or org admin)
  - Schedules cancellation at period end (better UX)
  - Actual status update happens via webhook when processed by Stripe

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
    # Validate input data including caseTier and paymentIntentId
    # Verify payment status with Stripe API
    # Check organization permissions if applicable
    # Validate payment amount matches caseTier price
    # Create case document with payment details and tier info
    # Return case details with price information
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