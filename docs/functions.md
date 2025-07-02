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
- `add_organization_member(request)`: Adds a member to an organization. Expects `organizationId`, `userId`, and `role` in the request body.
- `list_organization_members(request)`: Lists members of an organization. Expects `organizationId` in the query string.
- `update_organization_member_role(request)`: Updates a member's role. Expects `organizationId`, `userId`, and `newRole` in the request body.
- `remove_organization_member(request)`: Removes a member from an organization. Expects `organizationId` and `userId` in the request body.

**Note:** All previous function signatures and endpoints using path parameters (e.g., `/organizations/{organizationId}/members`) are deprecated and removed. All membership operations now use body or query parameters as described above.

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

### Lawyer AI Agent (`agent_handler.py`)
- `cloud_function_handler`: Main entry point for the Lawyer AI Agent
  - Handles incoming requests for the agent
  - Manages the LangGraph agent workflow
  - Processes user input and generates responses
  - Interacts with Gemini and Grok LLMs
  - Performs legal research using Exa
  - Generates document drafts
  - Manages case state in Firestore

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

### Lawyer AI Agent Integration
```python
def relex_backend_agent_handler(request):
    """Main entry point for the Lawyer AI Agent.

    - Authenticates user and verifies case access permissions
    - Processes the user's message using the agent_handler module
    - Manages the LangGraph agent workflow
    - Handles agent state and execution
    - Returns the agent's response
    """
    # Call the agent_handler's cloud_function_handler
    # Handle response status codes
    # Format and return the response
```

```python
def cloud_function_handler(request):
    """Core handler function in agent_handler.py.

    - Parses the request JSON
    - Creates an event loop for async execution
    - Calls the handle_request function
    - Returns the agent's response
    """
    # Parse request JSON
    # Create event loop
    # Run handle_request asynchronously
    # Return response
```

```python
async def handle_request(request_json):
    """Process incoming requests based on type.

    - Handles user input requests
    - Handles payment webhook requests
    - Calls the appropriate agent handler method
    """
    # Determine request type
    # Call appropriate handler method
    # Return response
```

```python
async def handle_user_input(case_id, user_id, input_text, user_info):
    """Handle user input by initializing or restoring agent state and executing the graph.

    - Gets or creates case details
    - Initializes agent state
    - Executes the agent graph
    - Saves final state
    - Prepares response
    """
    # Get or create case details
    # Initialize agent state
    # Execute agent graph
    # Save final state
    # Prepare and return response
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
    * **Trigger:** HTTP POST to `/cases/{caseId}/agent/messages`.
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

* Key Python libraries listed in `requirements.txt` (e.g., `google-cloud-firestore`, `google-cloud-storage`, `exa-py`, `langgraph`, `google-generativeai`, potentially `stripe`, PDF generation library like `weasyprint` or `markdown-pdf`, API framework like `Flask` or `FastAPI`).

## Deployment & Infrastructure

* Deployed as Google Cloud Functions.
* Managed via Terraform (see `backend_folder/terraform/`).
* API exposed via API Gateway configured using `openapi_spec.yaml`.

This structure provides a modular and scalable backend capable of supporting both standard CRUD operations and the complex interactions of the Lawyer AI Agent.

# Cloud Functions

This document details the Cloud Functions that make up the Relex backend API. These functions are deployed to Google Cloud Functions (2nd gen) and exposed through API Gateway.

## Overview

The Relex backend is organized as a collection of serverless functions, each with specific responsibilities. Functions are grouped by module in the `functions/src/` directory, and each module handles a specific domain of functionality.

## Core Modules

### main.py

Entry point for all Cloud Functions. This file imports and exports all function handles, ensuring they are available for deployment. It uses a standard pattern for function definition to ensure consistency across the API.

```python
# Standard function definition pattern
@functions_framework.http
def function_name(request):
    """Function documentation."""
    return _authenticate_and_call(
        request,
        handler_function,
        requires_auth=True  # or False for public endpoints
    )
```

### auth.py

Handles authentication and authorization for API requests.

**Key Functions:**
- `_authenticate_and_call`: Decorator function that validates Firebase Auth tokens and extracts user information.
- `get_user_id_from_token`: Extracts the user ID from a Firebase Auth token.
- `has_permission`: Checks if a user has a specific permission on a resource type.
- `can_access_resource`: Checks if a user can access a specific resource instance.
- `get_user_roles`: Retrieves all roles assigned to a user, including organization roles.

### user.py

Manages user profiles and user-specific operations.

**Key Functions:**
- `get_user_profile`: Retrieves a user's profile information.
- `update_user_profile`: Updates a user's profile information.
- `get_user_subscription`: Gets a user's subscription status.
- `update_user_subscription`: Updates a user's subscription information.

### organization.py

Handles organization management operations.

**Key Functions:**
- `create_organization`: Creates a new organization.
- `get_organization`: Retrieves organization details.
- `update_organization`: Updates organization information.
- `delete_organization`: Deletes an organization.
- `list_user_organizations`: Lists organizations a user belongs to.

### organization_membership.py

Manages the relationship between users and organizations.

**Key Functions:**
- `create_organization_membership`: Adds a user to an organization.
- `get_organization_membership`: Gets details of a user's membership in an organization.
- `update_organization_membership`: Updates a user's role or status in an organization.
- `delete_organization_membership`: Removes a user from an organization.
- `list_organization_members`: Lists all members of an organization.

### cases.py

Handles case management operations.

**Key Functions:**
- `create_case`: Creates a new case.
- `get_case`: Retrieves case details.
- `update_case`: Updates case information.
- `delete_case`: Deletes a case.
- `list_cases`: Lists cases based on various criteria.
- `archive_case`: Marks a case as archived.
- `get_case_documents`: Retrieves documents associated with a case.

### party.py

Manages party information (individuals or entities involved in cases).

**Key Functions:**
- `create_party`: Creates a new party.
- `get_party`: Retrieves party details.
- `update_party`: Updates party information.
- `delete_party`: Deletes a party.
- `list_parties`: Lists parties based on various criteria.
- `add_party_to_case`: Associates a party with a case.
- `remove_party_from_case`: Removes a party from a case.

### payments.py

Handles payment processing and subscription management.

**Key Functions:**
- `create_checkout_session`: Creates a Stripe Checkout session for subscription purchases.
- `create_payment_intent`: Creates a Stripe Payment Intent for one-time purchases.
- `handle_stripe_webhook`: Processes Stripe webhook events.
- `check_quota`: Verifies if a user/organization has sufficient quota.
- `update_quota`: Updates quota based on payments and usage.
- `get_payment_history`: Retrieves payment history for a user or organization.

## Agent Implementation

The agent implementation has been refactored for a cleaner separation of concerns between HTTP handling and core logic.

### agent.py

Handles the core agent logic and serves as the entry point for agent interactions.

**Key Functions:**
- `handle_agent_request`: Entry point function that processes user messages and delegates to the Agent class.
- `Agent`: Class that encapsulates the core agent functionality, including:
  - Instantiating the LangGraph workflow
  - Managing agent state in Firestore
  - Executing agent operations
  - Handling errors and timeouts
  - Returning structured responses

### agent_orchestrator.py

Defines the LangGraph workflow for the agent.

**Key Functions:**
- `create_agent_graph`: Creates the LangGraph workflow definition.
- `agent_executor_factory`: Factory function to create agent executor instances.
- Various utility functions for graph structure and node connections.

### agent_nodes.py

Implements specialized nodes for the LangGraph workflow.

**Key Functions:**
- `determine_case_tier`: Node for determining the complexity tier of a case.
- `check_quota_node`: Node for checking if the user has sufficient quota.
- `get_case_details_node`: Node for retrieving case details from Firestore.
- `update_case_details_node`: Node for updating case details in Firestore.
- `execute_tool_node`: Generic node for executing agent tools.
- `router_node`: Node for routing the agent workflow based on conditions.

### llm_nodes.py

Implements nodes specifically for LLM interactions.

**Key Functions:**
- `gemini_node`: Node for interacting with the Gemini model.
- `grok_node`: Node for interacting with the Grok model.
- `parse_llm_response`: Utility function for parsing structured responses from LLMs.
- Various prompt construction and formatting functions.

### agent_tools.py

Implements tools that the agent can use to interact with external systems.

**Key Functions:**
- `get_case_details`: Retrieves detailed information about a case.
- `update_case_details`: Updates information in a case document.
- `query_bigquery`: Searches Romanian legal databases for relevant information.
- `generate_draft_pdf`: Generates a PDF document from Markdown content.
- `get_party_id_by_name`: Resolves a party name to a party ID.
- `check_quota`: Checks if a user/organization has sufficient quota for a case.

### agent_state.py

Defines the state structures for the agent workflow.

**Key Classes:**
- `AgentState`: Class representing the agent's workflow state.
- Various utility functions for state manipulation and validation.

### agent_config.py

Manages configuration for the agent, including prompts and tool definitions.

**Key Functions:**
- `load_agent_config`: Loads the agent configuration from files.
- `get_system_prompt`: Constructs the system prompt for the agent.
- `get_tool_descriptions`: Gets the available tools and their descriptions.

### llm_integration.py

Handles direct integration with LLM services.

**Key Functions:**
- `call_gemini`: Makes a call to the Gemini API.
- `call_grok`: Makes a call to the Grok API.
- Various utility functions for handling API responses and errors.

### gemini_util.py

Utility functions specifically for interacting with the Gemini API.

**Key Functions:**
- `create_gemini_client`: Creates a client for the Gemini API.
- `format_gemini_messages`: Formats messages for the Gemini chat API.
- `extract_gemini_response`: Extracts structured data from Gemini responses.

## Additional Modules

### draft_templates.py

Manages templates for legal document generation.

**Key Functions:**
- `get_template`: Retrieves a template by ID.
- `list_templates`: Lists available templates.
- `render_template`: Renders a template with provided data.

### template_validation.py

Validates template content and structure.

**Key Functions:**
- `validate_template`: Validates a template against its schema.
- `validate_template_variables`: Validates template variables against expected formats.

### response_templates.py

Manages templates for API responses.

**Key Functions:**
- `create_success_response`: Creates a standardized success response.
- `create_error_response`: Creates a standardized error response.
- Various utility functions for specific response types.

### domain_nodes.py

Implements domain-specific nodes for the LangGraph workflow.

**Key Functions:**
- `legal_analysis_node`: Node for legal analysis operations.
- `document_generation_node`: Node for document generation operations.
- Various utility functions for domain-specific operations.

## Module Dependencies

The modules have the following general dependency structure:

```
main.py
  ├── auth.py
  ├── user.py
  │     └── auth.py
  ├── organization.py
  │     └── auth.py
  ├── organization_membership.py
  │     ├── auth.py
  │     └── organization.py
  ├── cases.py
  │     ├── auth.py
  │     └── payments.py
  ├── party.py
  │     └── auth.py
  ├── payments.py
  │     ├── auth.py
  │     └── user.py
  └── agent.py
        ├── auth.py
        ├── agent_orchestrator.py
        │     ├── agent_nodes.py
        │     │     ├── agent_tools.py
        │     │     └── agent_state.py
        │     └── llm_nodes.py
        │           ├── llm_integration.py
        │           │     └── gemini_util.py
        │           └── agent_config.py
        └── cases.py
```

* `find_legislation(...)`: Searches for official legislation using Exa.
* `find_case_law(...)`: Searches for case law using Exa.

- `find_legislation`: Searches for official legislation using Exa.
- `find_case_law`: Searches for case law using Exa.