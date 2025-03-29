# Relex Backend Functions

## Function Overview

The backend consists of several modules, each handling specific functionality:

### Main Entry Points (`main.py`)
- HTTP Cloud Functions that handle routing and initial request processing
- Authentication and error handling wrappers
- Function exports for deployment

### Authentication (`auth.py`)
- `validate_user`: Token validation
- `check_permissions`: Modular permission checking for different resource types
- `get_user_role`: Role retrieval for organizations
- `get_authenticated_user`: Authentication helper

#### Key Components in `auth.py`:
- **Centralized Permission Map**: Defines allowed actions by role and resource type
- **Resource-Specific Checkers**: Modular functions for each resource type
- **Pydantic Validation**: Ensures request data meets expected schema
- **Staff Assignment Validation**: Verifies staff members only access assigned cases
- **Document Permission Mapping**: Maps document actions to parent case permissions

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

### Party Management (`party.py`)
- `create_party`: 
  - Creates parties with conditional field validation based on partyType
  - Supports 'individual' type with firstName, lastName, and CNP validation
  - Supports 'organization' type with companyName, CUI, and RegCom validation
  - Verifies proper format for Romanian identification codes (CNP, CUI, RegCom)
  - Handles optional contact and signature data

- `get_party`: 
  - Retrieves party details with ownership verification
  - Only allows the creator/owner to access their parties

- `update_party`: 
  - Updates party details while maintaining type constraints
  - Ensures updates comply with the existing partyType schema
  - Prevents mixing of individual and organization fields

- `delete_party`: 
  - Removes parties after ownership verification
  - Blocks deletion if the party is attached to any cases

- `list_parties`: 
  - Lists parties owned by the authenticated user
  - Supports filtering by partyType

### Case-Party Relationship (`cases.py`)
- `attach_party_to_case`:
  - Attaches an existing party to a case 
  - Verifies case update permission
  - Verifies party ownership
  - Updates the case's attachedPartyIds array using ArrayUnion

- `detach_party_from_case`:
  - Removes a party from a case
  - Verifies case update permission
  - Updates the case's attachedPartyIds array using ArrayRemove

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
# Define permissions mapping
PERMISSIONS = {
    "case": {
        "administrator": {"read", "update", "delete", "archive", "upload_file", ...},
        "staff": {"read", "update", "upload_file", ...},
        "owner": {"read", "update", "delete", "archive", ...}
    },
    "organization": { ... },
    "party": { ... },
    "document": { ... }
}

def check_permissions(request):
    """Check if a user can perform an action on a resource."""
    # Extract and validate request data using Pydantic
    # Authenticate user with Firebase
    # Dispatch to resource-specific checker based on resourceType:
    #   - Case: Check ownership, org membership, and staff assignment
    #   - Organization: Check membership and role
    #   - Party: Verify ownership (only creator can manage)
    #   - Document: Map to parent case permissions
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
    # Check permissions using check_permissions (document:upload)
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
    # Check admin permissions using check_permissions (organization:manage_members)
    # Create membership record
    # Return membership details
```

### Party Management
```python
def create_party(request):
    """Create a new party with conditional field validation based on partyType."""
    # Validate input data
    # Check partyType constraints
    # Create party document
    # Return party details
```

### Case-Party Relationship
```python
def attach_party_to_case(request):
    """Attach an existing party to a case."""
    # Validate input
    # Verify case permission using check_permissions (case:attach_party)
    # Verify party ownership
    # Update case's attachedPartyIds array
    # Return success message
```

## Error Handling

All functions implement consistent error handling:
```python
try:
    # Function logic
except ValidationError as e:
    # Handle Pydantic validation errors with detailed messages
    return {"error": "Bad Request", "message": str(e)}, 400
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
3. Organization-based permission model with staff assignment checks
4. Pydantic validation for request schemas
5. Resource-specific permission checking
6. Firestore for data storage
7. Firebase Storage for files
8. Stripe for payments (individual cases)