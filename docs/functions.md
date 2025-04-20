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
- `create_organization`: Organization creation with proper collection naming for membership
- `get_organization`: Organization retrieval
- `update_organization`: Organization updates with enhanced error handling
- `delete_organization`: Organization deletion with proper cleanup:
  - Verifies administrator permissions
  - Checks for active subscription (prevents deletion if active)
  - Uses transaction to ensure atomic operations:
    - Deletes all organization memberships
    - Marks all organization cases as deleted
    - Deletes the organization document
  - Includes proper error handling and logging

#### Membership Management (`organization_membership.py`)
- `add_organization_member`: Member addition with role validation, using the correct `organization_memberships` collection. Exported as function `relex_backend_add_organization_member`. Used by the `/organizations/{organizationId}/members` POST endpoint.
- `set_organization_member_role`: Role updates with admin checks, operating on the `organization_memberships` collection. Exported as function `relex_backend_set_organization_member_role`. Used by the `/organizations/{organizationId}/members/{userId}` PUT endpoint.
- `list_organization_members`: Member listing with pagination, querying the `organization_memberships` collection. Exported as function `relex_backend_list_organization_members`. Used by the `/organizations/{organizationId}/members` GET endpoint.
- `remove_organization_member`: Member removal with safeguards, operating on the `organization_memberships` collection. Exported as function `relex_backend_remove_organization_member`. Used by the `/organizations/{organizationId}/members/{userId}` DELETE endpoint.
- `get_user_organization_role`: Role retrieval, working with the `organization_memberships` collection.
- `list_user_organizations`: Organization listing for users.

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
- `logic_get_products`:
  - Fetches active products and prices from Stripe with Firestore caching
  - Uses 1-hour cache TTL to minimize Stripe API calls
  - Categorizes products into subscriptions and case tiers based on metadata
  - Handles both recurring subscription prices and one-time case payments
  - Returns structured response with prices in cents/smallest currency unit
  - No authentication required - public endpoint

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
  - Processes Stripe webhook events securely with added safeguards for data access
  - Handles checkout.session.completed for subscription and payment events
  - Handles invoice.payment_failed to update subscription status
  - Handles customer.subscription.deleted/updated events
  - Updates relevant Firestore records based on events
  - Includes robust error handling for nested data access

- `cancel_subscription`: 
  - Allows users to cancel their subscriptions
  - Verifies appropriate permissions (own subscription or org admin)
  - Schedules cancellation at period end (better UX)
  - Actual status update happens via webhook when processed by Stripe

### Chat Management (`chat.py`)
- `receive_prompt`: Receives and stores a user prompt
- `enrich_prompt`: Adds case context to a prompt
- `send_to_vertex_ai`: Sends prompts to Vertex AI
- `store_conversation`: 
  - Stores conversation in a case's subcollection
  - Includes proper permission checks to verify user has update access to the parent case
  - Ensures security by checking organization membership and role

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
        "administrator": {"read", "update", "delete", "archive", "upload_file", 
                         "download_file", "attach_party", "detach_party", "assign_case",
                         "create", "list"},
        "staff": {"read", "update", "upload_file", "download_file", 
                 "attach_party", "detach_party", "create", "list"},
        "owner": {"read", "update", "delete", "archive", "upload_file", 
                 "download_file", "attach_party", "detach_party", "create", "list"}
    },
    "organization": {
        "administrator": {"read", "update", "delete", "manage_members", 
                         "create_case", "list_cases", "assign_case", "addMember", 
                         "setMemberRole", "removeMember", "listMembers"},
        "staff": {"read", "create_case", "list_cases", "listMembers"}
    },
    "party": {
        "owner": {"read", "update", "delete", "create", "list"}
    },
    "document": {
        "administrator": {"read", "delete"},
        "staff": {"read"},
        "owner": {"read", "delete"}
    }
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

### Organization Membership
```python
def add_organization_member(request):
    """Add a member to an organization."""
    # Validate input
    # Check admin permissions using check_permissions (organization:manage_members)
    # Query organization_memberships collection to check for existing membership
    # Create membership record in organization_memberships collection
    # Return membership details
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

### Chat Integration
```python
def send_chat_message(request):
    """Unified chat endpoint that handles the full RAG + LLM flow.
    
    - Authenticates user and verifies case access permissions
    - Stores user message in Cloud Storage
    - Retrieves case type configuration with agent instructions
    - Fetches relevant case context (history, documents)
    - Queries the main RAG system (Vertex AI Search) with TXT direct indexing
    - Constructs a comprehensive prompt
    - Calls external LLM with prepared context
    - Stores response and returns to user
    """
    # Auth check and case validation
    # Store user message in GCS (chat_history.jsonl)
    # Get caseTypeId and config from Firestore
    # Fetch chat history from GCS
    # Get processed document text if relevant
    # Query Vertex AI Search for legislation/jurisprudence
    # Build prompt with all context sources
    # Call external LLM API
    # Store AI response in GCS
    # Return formatted response with sources
```

```python
def get_chat_history(request):
    """Retrieves chat history for a case.
    
    - Authenticates user and verifies case access permissions
    - Reads chat history from Cloud Storage
    - Supports pagination and filtering
    """
    # Auth check and case validation
    # Read messages from GCS
    # Apply pagination/filtering
    # Return formatted message list
```

```python
def store_conversation(request):
    """Store a conversation in a case's subcollection (legacy).
    
    Note: This function is being replaced by the unified chat flow
    that stores messages directly in Cloud Storage.
    """
    # Authenticate user
    # Validate input data (caseId, promptId, prompt, response)
    # Get case document to ensure it exists
    # Perform permission check to verify user can update the case
    # Write conversation to the subcollection
    # Return success message
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
    logging.error(f"Error in function: {str(e)}", exc_info=True)
    return {"error": "Internal Server Error", "message": str(e)}, 500
```

Common error responses:
- 400: Bad Request (invalid input)
- 401: Unauthorized (invalid token)
- 402: Payment Required (subscription quota exhausted)
- 403: Forbidden (insufficient permissions)
- 404: Not Found (resource doesn't exist)
- 409: Conflict (e.g., user already a member)
- 500: Internal Server Error

## Development Notes

1. All functions require Firebase Authentication
2. Dual case ownership model (individual/organization)
3. Organization-based permission model with staff assignment checks
4. Pydantic validation for request schemas
5. Resource-specific permission checking
6. Firestore collection names are standardized:
   - `organization_memberships` for organization member relationships
   - `users` for user profiles
   - `organizations` for organization data
   - `cases` for case information
   - `parties` for party data
   - Subcollection `conversations` under cases for chat history
7. Firestore for data storage
8. Firebase Storage for files
9. Stripe for payments (individual cases)

### Planned Functions (Not yet implemented)
- `assign_case`: Will handle assigning cases to staff members within an organization
  - Currently implemented as a stub function that returns 501 Not Implemented
  - Exposed as `relex_backend_assign_case` in main.py
  - Will be called via the `/v1/cases/{caseId}/assign` endpoint
  - Included in the Terraform configuration and OpenAPI spec

- `redeem_voucher`: Will handle voucher code redemption for users or organizations
  - Currently implemented as a stub function that returns 501 Not Implemented
  - Exposed as `relex_backend_redeem_voucher` in main.py
  - Will be called via the `/v1/vouchers/redeem` endpoint 
  - Included in the Terraform configuration and OpenAPI spec

### Organization Cases List Function
- `list_organization_cases`: A specialized version of the list_cases function that is focused on listing only cases belonging to a specific organization. This is exposed as `relex_backend_list_organization_cases` in main.py.


----- UPDATES -----
# Backend Cloud Functions Overview

The Relex backend logic is implemented as a set of Python Cloud Functions triggered via HTTP requests routed by API Gateway, and potentially by other events (e.g., Stripe webhooks, Pub/Sub).

*(Refer to `backend_folder/functions/src/` for source code.)*

## Core Function Modules (`*.py` files in `src`)

* **`main.py`:** Entry point, likely defining the Flask/FastAPI app and registering blueprints/routers from other modules. Handles request dispatching.
* **`auth.py`:** Handles user registration, login (JWT generation), potentially password reset flows.
* **`user.py`:** Manages user profile CRUD operations.
* **`organization.py`:** Manages organization CRUD, member invitations.
* **`organization_membership.py`:** Handles logic related to user roles within organizations.
* **`party.py`:** Manages CRUD operations for `/parties` collection. **Includes strict security controls for PII.**
* **`cases.py`:** Handles CRUD for `/cases` collection (metadata), attaching/detaching parties, managing attachments (links to Cloud Storage).
* **`payments.py`:** Integrates with Stripe for creating checkout sessions (subscriptions, per-case payments), handling payment webhooks, updating subscription statuses in Firestore.

## NEW/Modified Functions for Lawyer AI Agent

* **`agent_handler.py` (or significantly modified `chat.py`):**
    * **Trigger:** HTTP POST to `/cases/{caseId}/agent/message`.
    * **Responsibilities:**
        * Authenticates and authorizes the request.
        * Loads case context (`case_details`, `case_processing_state`, history) from Firestore.
        * Initializes and invokes the LangGraph Lawyer AI Agent with the current state and user message.
        * Manages the agent execution lifecycle (within the function's timeout).
        * Handles state saving before timeout, potentially using `case_processing_state`.
        * Saves updated `case_details` and agent history to Firestore upon completion or state save.
        * Formats and returns the agent's final reply to the frontend.
    * **Dependencies:** LangGraph library, Google AI SDK (Gemini), Grok API client, Firestore client, other tool functions.
* **`agent_tools.py` (or integrated within relevant modules):**
    * **Purpose:** Contains the implementations of the function tools defined in `tools.md`. These are called *by* the LangGraph agent, not directly by the frontend.
    * **Functions:**
        * `query_bigquery_tool(...)`: Executes SQL on BigQuery.
        * `get_party_id_by_name_tool(...)`: Looks up party ID in `case_details`.
        * `generate_draft_pdf_tool(...)`: Securely generates PDF, substitutes PII, uploads to GCS, updates Firestore. **Requires careful permission setup.**
        * `check_quota_tool(...)`: Checks Firestore for subscription quota.
        * `get_case_details_tool(...)`: Reads from Firestore.
        * `update_case_details_tool(...)`: Writes updates to Firestore.
        * `create_support_ticket_tool(...)`: Integrates with support system/Firestore.
        * `(Optional) consult_grok_tool(...)`: Wraps Grok API call if needed.
    * **Security:** Tool implementations must validate inputs and handle errors robustly. The PDF tool needs special care regarding PII access.

## Other Key Functions/Endpoints

* **`get_drafts_list.py` (or within `cases.py`):**
    * **Trigger:** HTTP GET to `/cases/{caseId}/drafts`.
    * **Responsibilities:** Reads `case_details.draft_status` array and returns the list of draft metadata.
* **`download_draft.py` (or within `cases.py`):**
    * **Trigger:** HTTP GET to `/cases/{caseId}/drafts/{draftFirestoreId}`.
    * **Responsibilities:** Finds the draft metadata, gets the GCS path, fetches the PDF from Cloud Storage, and returns it to the user. Requires permissions check.

## Dependencies

* Key Python libraries listed in `requirements.txt` (e.g., `google-cloud-firestore`, `google-cloud-storage`, `google-cloud-bigquery`, `langgraph`, `google-generativeai`, potentially `stripe`, PDF generation library like `weasyprint` or `markdown-pdf`, API framework like `Flask` or `FastAPI`).

## Deployment & Infrastructure

* Deployed as Google Cloud Functions.
* Managed via Terraform (see `backend_folder/terraform/`).
* API exposed via API Gateway configured using `openapi_spec.yaml`.

This structure provides a modular and scalable backend capable of supporting both standard CRUD operations and the complex interactions of the Lawyer AI Agent.