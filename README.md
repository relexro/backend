# Relex Backend

Backend for Relex, an AI-powered legal assistant platform built using Google Cloud Functions in Python and Terraform for infrastructure management. The platform focuses on Romanian legal cases and implements a sophisticated AI agent using LangGraph to orchestrate interactions between Gemini and Grok LLMs.

## Key Documentation

- [Architecture Overview](docs/architecture.md) - System architecture and components
- [API Documentation](docs/api.md) - Detailed API endpoints and usage
- [Setup and Deployment](docs/setup_deployment.md) - Comprehensive setup instructions
- [Data Models](docs/data_models.md) - Firestore collection schemas and relationships
- [Agent Implementation](docs/concepts/agent.md) - AI agent architecture and workflow
- [Product Overview](docs/product_overview.md) - User-facing features and value proposition

## Project Structure

- `functions/src/`: Contains Python modules for Cloud Functions
  - `main.py`: Main entry point that imports and exports all functions
  - `agent.py`: Core agent implementation using LangGraph
  - `agent_orchestrator.py`: LangGraph workflow definition
  - `agent_nodes.py`: Implementation of agent workflow nodes
  - `agent_tools.py`: Tool functions used by the agent
  - `llm_nodes.py`: LLM interaction nodes for Gemini and Grok
  - `agent_state.py`: State schema definitions for the agent
  - `agent_config.py`: Loads runtime configurations from agent-config directory
  - `auth.py`: Authentication and authorization functions
  - `cases.py`: Case management functions
  - `payments.py`: Payment processing with Stripe
  - `organization.py`: Organization account management
  - `organization_membership.py`: Organization membership management
  - `party.py`: Party information management
  - `user.py`: User profile management

- `functions/src/agent-config/`: **CRITICAL RUNTIME DIRECTORY** containing configuration files
  - `agent_loop.txt`: The primary and consolidated system prompt detailing the agent's operational flow, logic, personas, and protocols. (Romanian - Content iteratively refined by Operator)
  - `modules.txt`: Reusable Romanian text snippets and components for agent use, referenced by `agent_loop.txt`. (Romanian - Content iteratively refined by Operator)
  - `tools.json`: Tool definitions and schemas using OpenAI function format.
  - (`prompt.txt` is obsolete and has been removed from this source directory).

- `terraform/`: Contains Terraform configuration files
  - `main.tf`: Main Terraform configuration
  - `variables.tf`: Variable definitions
  - `outputs.tf`: Output definitions
  - `terraform.tfvars.example`: Example variable values
  - `openapi_spec.yaml`: API Gateway configuration
  - `deploy.sh`: Deployment script with OpenAPI validation

## Onboarding a New Lead Planner Session

This section outlines the process for the Operator (human user) to initiate a new working session with an AI Lead Planner instance for the Relex Backend System. The goal is to bring the Lead Planner up to speed quickly and effectively.

**Operator's Responsibilities for Onboarding:**

1.  **Provide Full Codebase:** Ensure the Lead Planner has access to the complete and latest version of the `backend_folder/` project directory. This is typically done by uploading the folder at the start of the session.

2.  **State Session Objective:** Clearly communicate the primary goal(s) for the current session (e.g., "Resolve outstanding API Gateway logging issue," "Implement feature X," "Perform comprehensive testing for module Y").

3.  **Highlight Critical Recent Manual Changes (If Any):** Inform the Lead Planner of any manual interventions or critical changes made to the GCP environment or codebase that might not yet be fully reflected in version control or standard documentation.

4.  **Direct Planner to Key Initial Documents:** Instruct the Lead Planner to begin by thoroughly reviewing the following documents in this order:
    * **`docs/PLANNER_GUIDE.md`**: This is the primary guide defining roles, responsibilities (including the Planner's persona), prompt guidelines, file path conventions (always relative to the project root, never including `backend_folder/`), the Operator's role in deployments, and the workflow for task management.
    * **This `README.md` file**: For overall project context.
    * **`docs/status.md`**: For the latest snapshot of system operational status, resolved issues, and critical known unresolved issues.
    * **`docs/TODO.md`**: For the list of outstanding tasks and planned work.
    * **`docs/architecture.md`**: For a high-level understanding of the system components and their interactions.
    * **`docs/concepts/authentication.md`**: Crucial for understanding the current multi-step authentication flow (Client Firebase JWT -> API Gateway -> Gateway Google OIDC Token using SA -> Backend Function which extracts original user from `X-Endpoint-API-Userinfo` header).
    * **`docs/api.md`**: For understanding the defined API endpoints.
    * **`terraform/openapi_spec.yaml`**: The API contract template.
    * **`docs/terraform_outputs.log`**: To find current deployed service URLs, especially the `api_gateway_url` (default Gateway URL, as the custom domain `api-dev.relex.ro` is **not** currently the operational endpoint).
    * **`docs/functions.md`**: Overview of implemented Cloud Functions.
    * Key source files for initial context (e.g., `functions/src/main.py`, `functions/src/auth.py`, `functions/src/user.py`).
    * Key Terraform module structures (e.g., root `main.tf`, `modules/cloud_functions/main.tf`, `modules/api_gateway/main.tf`).

5.  **Confirm Planner's Understanding:** Before proceeding with specific tasks, the Operator should expect the Lead Planner to acknowledge review of these core documents and confirm its understanding of the current project state and session objectives.

**Lead Planner's Persona and Output Requirements:**

* The Lead Planner MUST adopt and maintain a "hyper-rational, 10x software engineering planner" persona.
* All Executor prompts generated by the Lead Planner MUST be provided as **raw text, typically within a markdown code block**.
* File paths in prompts MUST be relative to the project root (e.g., `docs/api.md`, `functions/src/main.py`) and **NEVER** include the `backend_folder/` prefix.
* The Lead Planner designs the "what" and "how" for file modifications and specifies exact CLI commands. The Executor only executes.
* The Operator (human user) is responsible for all deployments (e.g., `terraform/deploy.sh`). The Lead Planner prepares changes, the Operator deploys.

By following this onboarding process, the Lead Planner will be equipped to analyze issues, design solutions, and generate precise, actionable prompts for the AI Executor, adhering to the project's established workflow.

## Setup Instructions

### Prerequisites

- Firebase CLI
- Terraform
- Python 3.10 (required for Cloud Functions runtime)
- Google Cloud SDK
- Cloudflare account with access to relex.ro domain
- Node.js and npm (for OpenAPI validation)
- Redocly CLI: `npm install -g @redocly/cli` (for validating OpenAPI specifications)
- **Stripe CLI**: Required for managing Stripe resources (products, prices, webhooks)
  - Install: [Stripe CLI Installation Guide](https://stripe.com/docs/stripe-cli)
  - Login: `stripe login`
  - Configure: `stripe config` (verify correct API key)

### Configuration

1. Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars` and update the values.
2. Set up Google Cloud authentication:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
   ```
3. Set up Cloudflare authentication for DNS management:
   ```bash
   export TF_VAR_cloudflare_api_token=your_cloudflare_api_token
   export TF_VAR_cloudflare_zone_id=your_cloudflare_zone_id
   export TF_VAR_cloudflare_account_id=your_cloudflare_account_id
   ```
4. Configure LLM and Exa API keys:
   ```bash
   export GEMINI_API_KEY=your_gemini_api_key
   export GROK_API_KEY=your_grok_api_key
   export EXA_API_KEY=your_exa_api_key
   ```
5. Configure Stripe API keys:
   ```bash
   export TF_VAR_stripe_secret_key=your_stripe_secret_key
   export TF_VAR_stripe_webhook_secret=your_stripe_webhook_secret
   ```

6. **Create all required secrets in Google Secret Manager:**
   - `gemini-api-key` (value: your GEMINI_API_KEY)
   - `grok-api-key` (value: your GROK_API_KEY)
   - `exa-api-key` (value: your EXA_API_KEY)
   - `stripe-secret-key` (value: your Stripe secret key)
   - `stripe-webhook-secret` (value: your Stripe webhook secret)

   Example for Exa:
   ```bash
   gcloud secrets create exa-api-key --replication-policy="automatic"
   echo -n "$EXA_API_KEY" | gcloud secrets versions add exa-api-key --data-file=-
   ```

### Secret Manager Permissions

When deploying with Terraform, you may encounter Secret Manager access issues. The error typically looks like:
```
Error: Error reading SecretVersion: googleapi: Error 403: Permission 'secretmanager.versions.access' denied for resource 'projects/PROJECT_ID/secrets/SECRET_NAME/versions/1'
```

Here's how to resolve this:

1. Identify which service account is being used by your GOOGLE_APPLICATION_CREDENTIALS:
   ```bash
   # Print the path to your credentials file
   echo $GOOGLE_APPLICATION_CREDENTIALS

   # Extract the service account email from your credentials file
   grep "client_email" $GOOGLE_APPLICATION_CREDENTIALS
   ```

2. Grant Secret Manager Admin permissions to this service account:
   ```bash
   gcloud projects add-iam-policy-binding $(gcloud config get project) \
     --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
     --role="roles/secretmanager.admin"
   ```

   Replace `SERVICE_ACCOUNT_EMAIL` with the email you found in step 1.

3. If you encounter issues with Secret Manager versions being in a "DESTROYED" state, manually delete and recreate the secrets:
   ```bash
   # Delete existing secrets
   gcloud secrets delete stripe-secret-key --quiet
   gcloud secrets delete stripe-webhook-secret --quiet
   gcloud secrets delete gemini-api-key --quiet
   gcloud secrets delete grok-api-key --quiet

   # Create secrets using environment variables
   gcloud secrets create stripe-secret-key --replication-policy="automatic"
   echo $TF_VAR_stripe_secret_key | gcloud secrets versions add stripe-secret-key --data-file=-

   gcloud secrets create stripe-webhook-secret --replication-policy="automatic"
   echo $TF_VAR_stripe_webhook_secret | gcloud secrets versions add stripe-webhook-secret --data-file=-

   gcloud secrets create gemini-api-key --replication-policy="automatic"
   echo $GEMINI_API_KEY | gcloud secrets versions add gemini-api-key --data-file=-

   gcloud secrets create grok-api-key --replication-policy="automatic"
   echo $GROK_API_KEY | gcloud secrets versions add grok-api-key --data-file=-
   ```

### Deployment

Deployment is now stable with all required secrets managed in Google Secret Manager. If you encounter a secret error, ensure the secret exists and is populated as described above.

The recommended way to deploy is using the provided deployment script:

   ```bash
   cd terraform
./deploy.sh
```

This script handles:
1. Terraform initialization
2. Terraform plan and apply
3. Post-deployment verification

Note: The script does NOT validate the OpenAPI specification. You should manually validate it before deployment:
```bash
npx @redocly/cli lint terraform/openapi_spec.yaml
```

For a clean deployment destroying all resources first:

   ```bash
cd terraform
./destroy.sh && ./deploy.sh
   ```

## Stripe Resource Management

The project includes a comprehensive Stripe resource management system for handling products, prices, coupons, and webhooks. All Stripe resources are managed through centralized configuration and scripts.

### Stripe Setup

1. **Install and configure Stripe CLI** (see Prerequisites above)
2. **Configure Stripe API keys** in your environment variables (see Configuration section)

### Managing Stripe Resources

All Stripe resources (products, prices, coupons, tax rates, webhooks) are managed through a single script with centralized configuration:

```bash
# View current Stripe configuration
../terraform/scripts/stripe/manage_stripe.sh config

# Create all Stripe resources from configuration
../terraform/scripts/stripe/manage_stripe.sh create

# List all current Stripe resources
../terraform/scripts/stripe/manage_stripe.sh list

# Delete/deactivate all Stripe resources
../terraform/scripts/stripe/manage_stripe.sh delete

# Validate configuration file
../terraform/scripts/stripe/manage_stripe.sh validate
```

### Customizing Stripe Resources

To modify products, prices, or other Stripe resources:

1. **Edit the configuration file**: `scripts/stripe/config.json`
   - Product names, descriptions, and statement descriptors
   - Pricing (amounts in cents: 900 = €9.00)
   - Webhook URL and events
   - Coupon and promotion code details
   - Tax rate information

2. **Validate your changes**: `../terraform/scripts/stripe/manage_stripe.sh validate`

3. **Preview the configuration**: `../terraform/scripts/stripe/manage_stripe.sh config`

4. **Apply the changes**: `../terraform/scripts/stripe/manage_stripe.sh create`

For detailed documentation and examples, see: [`scripts/stripe/README.md`](scripts/stripe/README.md)

## Development

To run functions locally:

```bash
cd functions
pip install -r requirements.txt
pip install -r requirements-dev.txt
functions-framework --target=cases_create_case
```

### Environment Variables

The Cloud Functions use the following environment variables:

- `GOOGLE_CLOUD_PROJECT`: The Google Cloud project ID (default: "relexro")
- `GOOGLE_CLOUD_REGION`: The Google Cloud region (default: "europe-west1")
- `STRIPE_SECRET_KEY`: The Stripe secret key (used in payment functions)
- `STRIPE_WEBHOOK_SECRET`: The Stripe webhook signing secret (used to verify webhook authenticity)
- `GEMINI_API_KEY`: The API key for Gemini LLM
- `GROK_API_KEY`: The API key for Grok LLM

These environment variables are set in the Terraform configuration (`terraform/main.tf`) and passed to each function.

## Monitoring and Debugging

The gcloud CLI is the recommended tool for monitoring and debugging Cloud Functions:

```bash
# View logs for a function
gcloud functions logs read relex-backend-create-case --gen2 --region=europe-west1

# Describe a function to get details
gcloud functions describe relex-backend-create-case --gen2 --region=europe-west1

# Test a function directly with HTTP
gcloud functions call relex-backend-create-case --gen2 --region=europe-west1 --data '{"title": "Test Case", "description": "Test Description"}'
```

## Agent System

The Relex Lawyer AI Agent is implemented using LangGraph, a framework for building LLM-powered applications with a state machine approach. The agent uses two core LLMs:

- **Gemini**: Handles user interaction, document analysis, tool usage, and drafting based on instructions
- **Grok**: Provides expert legal reasoning, strategic guidance, validation, and planning

The agent workflow is defined as a graph in `agent_orchestrator.py` with specialized nodes in `agent_nodes.py` and LLM interaction nodes in `llm_nodes.py`. The agent interacts with external systems through tool functions defined in `agent_tools.py`.

Runtime configuration for the agent is loaded from the `functions/src/agent-config/` directory, which contains prompt templates, tool definitions, and other essential configuration files. This directory must be included in any deployment.

For more details, see the [Agent Implementation Documentation](docs/concepts/agent.md).

## API Documentation

The API is documented using OpenAPI specification in `terraform/openapi_spec.yaml`. For a comprehensive API reference, see the [API Documentation](docs/api.md).

## Testing the API

To test the API endpoints:

1. **Find the API Gateway URL**:
   - After deployment, the API Gateway URL is saved in `docs/terraform_outputs.log` under the `api_gateway_url` key
   - This is the default Google-provided URL (e.g., `relex-api-gateway-dev-mvef5dk.ew.gateway.dev`)
   - Note: The custom domain `api-dev.relex.ro` is not currently the active endpoint for the API Gateway

2. **Obtain a Firebase JWT token**:
   - Navigate to the `tests/` directory
   - Start a local web server: `python3 -m http.server 8080`
   - Open `http://localhost:8080/test-auth.html` in your browser
   - Sign in with your Google account
   - Click "Show/Hide Token" to reveal your JWT token
   - Copy the entire token

3. **Generate and Set Test User Authentication Tokens**:

   The project includes a script to automatically create and manage Firebase test users and generate their ID tokens:

   ```bash
   # First-time setup: Install required dependencies
   pip install firebase-admin requests

   # Download your Firebase service account key from Firebase Console
   # (Project Settings > Service accounts > Generate new private key)
   # Save it as 'firebase-service-account-key.json' in the project root

   # Run the token management script
   ././terraform/scripts/manage_test_tokens.sh
   ```

   This script will:
   - Create or update three test user personas in Firebase Authentication:
     - Individual Test Account (`individual@test.org`, UID: `individual-test-acc-uid`)
     - Admin Test Account (`admin@test.org`, UID: `admin-test-acc-uid`)
     - User Test Account (`user@test.org`, UID: `user-test-acc-uid`)
   - Generate Firebase ID tokens for each user
   - Save the tokens as environment variables in `~/.zshenv`:
     - `RELEX_TEST_JWT` - For individual account testing
     - `RELEX_ORG_ADMIN_TEST_JWT` - For organization admin role testing
     - `RELEX_ORG_USER_TEST_JWT` - For organization user/staff role testing
   - Automatically source the environment variables in the current shell

   **Note**: Tokens are valid for 1 hour. Run `././terraform/scripts/manage_test_tokens.sh` again to generate fresh tokens.

   **Manual Token Setup (Alternative)**:
   ```bash
   # For regular user tests (Linux/macOS)
   export RELEX_TEST_JWT="your_token_for_individual@test.org"

   # For organization admin tests (Linux/macOS)
   export RELEX_ORG_ADMIN_TEST_JWT="your_token_for_admin@test.org"

   # For organization user tests (Linux/macOS)
   export RELEX_ORG_USER_TEST_JWT="your_token_for_user@test.org"

   # Windows (Command Prompt) equivalents
   set RELEX_TEST_JWT=your_token_for_individual@test.org
   set RELEX_ORG_ADMIN_TEST_JWT=your_token_for_admin@test.org
   set RELEX_ORG_USER_TEST_JWT=your_token_for_user@test.org

   # Windows (PowerShell) equivalents
   $env:RELEX_TEST_JWT="your_token_for_individual@test.org"
   $env:RELEX_ORG_ADMIN_TEST_JWT="your_token_for_admin@test.org"
   $env:RELEX_ORG_USER_TEST_JWT="your_token_for_user@test.org"
   ```

4. **Make authenticated API requests**:
   ```bash
   # Example using curl
   curl -H "Authorization: Bearer $RELEX_TEST_JWT" https://YOUR_API_GATEWAY_URL/v1/users/me
   ```

For more detailed testing instructions, see the [Tests README](tests/README.md).

## Additional Resources

- [Data Models](docs/data_models.md): Detailed schema definitions for Firestore collections
- [Authentication](docs/concepts/authentication.md): Authentication and authorization system
- [Payments](docs/concepts/payments.md): Payment and subscription system
- [Tools](docs/concepts/tools.md): Agent tools and capabilities
- [Prompts](docs/concepts/prompts.md): Prompt design for LLM interactions
- [Tiers](docs/concepts/tiers.md): Case tier system for complexity determination
- [Functions](docs/functions.md): Cloud Functions implementation details

## Status

- All secrets (Gemini, Grok, Exa, Stripe) are now managed in Google Secret Manager and injected at deploy/runtime.
- Deployment is stable and ready for API testing.

## How to Correctly Test Authentication (Step-by-Step)

### 1. Environment Setup
- Use Python 3.10 and create a virtual environment:
  ```bash
  python3.10 -m venv test_venv
  source test_venv/bin/activate
  pip install -r functions/src/requirements-dev.txt
  pip install -r functions/requirements.txt
  ```
- Ensure you have a valid Firebase service account key at `firebase-service-account-key.json` in the project root.

### 2. Generate Fresh JWT Tokens
- Use the provided script to generate and export tokens for all test personas:
  ```bash
  ./terraform/scripts/manage_test_tokens.sh
  source ~/.zshenv
  ```
- Tokens are exported as:
  - `RELEX_TEST_JWT` (individual)
  - `RELEX_ORG_ADMIN_TEST_JWT` (admin)
  - `RELEX_ORG_USER_TEST_JWT` (org user)
- **Tokens expire after 1 hour.** Always regenerate and re-source before testing.

### 3. Use the Correct API Gateway URL
- Always send requests to the API Gateway URL, not the raw Cloud Run function URL.
- Find the URL in `docs/terraform_outputs.log` under `api_gateway_url`.
- Example endpoint: `https://<api_gateway_url>/v1/users/me`

### 4. Make Authenticated Requests
- Example:
  ```bash
  curl -H "Authorization: Bearer $RELEX_TEST_JWT" https://<api_gateway_url>/v1/users/me
  ```
- For integration tests, ensure the correct token is used for the scenario.

### 5. Troubleshooting
- If you get `401 Jwt is expired`, regenerate tokens and re-source your environment.
- If you get `500` errors, check backend logs for function signature or import errors.
- Always check that the correct environment variable is loaded in your shell.

## Common Mistakes When Testing Auth
- Using an expired JWT (tokens expire after 1 hour)
- Not sourcing the environment after generating new tokens
- Sending requests to the wrong URL (use API Gateway, not Cloud Run)
- Forgetting to update `docs/terraform_outputs.log` after deployment
- Not having the Firebase service account key in place
- Not using Python 3.10 (required for local compatibility)
- Not deleting user profiles from Firestore before running tests that require user creation

## Authentication Architecture and Flow

### High-Level Flow

```
+-------------------+        +-------------------+        +-------------------+        +-------------------+
|   Client (User)   |        |   API Gateway     |        | Cloud Function    |        |   Backend Logic   |
|-------------------|        |-------------------|        |-------------------|        |-------------------|
| 1. Sends request  |  --->  | 2. Validates JWT  |  --->  | 3. Receives       |  --->  | 4. Handles        |
|   with            |        |    (Firebase)     |        |    request with   |        |    business logic |
|   Authorization   |        |                   |        |    headers        |        |                   |
|   header          |        |                   |        |                   |        |                   |
+-------------------+        +-------------------+        +-------------------+        +-------------------+
```

### Detailed Flow

1. **Client** authenticates with Firebase and receives a JWT.
2. **Client** sends API request to API Gateway with:
   - `Authorization: Bearer <firebase_jwt>`
3. **API Gateway**:
   - Validates the JWT using Firebase public keys.
   - If valid, forwards the request to the Cloud Function (backend) using IAM (service account).
   - Forwards the original user's claims as a base64-encoded JSON in the `X-Endpoint-API-Userinfo` or `X-Apigateway-Api-Userinfo` header.
   - Forwards the original `Authorization` header as `X-Forwarded-Authorization`.
4. **Cloud Function (Backend)**:
   - Receives the request with all headers.
   - The backend's `get_authenticated_user` function:
     - Checks for `X-Endpoint-API-Userinfo` or `X-Apigateway-Api-Userinfo` header and decodes it to extract user info (UID, email, etc).
     - If not present, falls back to validating the `Authorization` header as a Firebase JWT.
     - If neither is valid, returns 401 Unauthorized.
   - All endpoint handlers use a decorator (`inject_user_context`) to ensure authentication and inject user info into the request object.
   - Business logic functions (e.g., `get_user_profile`) expect the user context to be present on the request.

### OpenAPI Spec and Header Forwarding
- The OpenAPI spec (`terraform/openapi_spec.yaml`) is configured to forward all necessary headers from API Gateway to the backend, including:
  - `X-Endpoint-API-Userinfo`
  - `X-Apigateway-Api-Userinfo`
  - `X-Forwarded-Authorization`
  - `Authorization` (if needed)
- This ensures the backend always receives the required headers for authentication.

### Backend Header Expectations
- The backend expects:
  - `X-Endpoint-API-Userinfo` or `X-Apigateway-Api-Userinfo`: base64-encoded JSON with Firebase claims
  - `X-Forwarded-Authorization`: original JWT
  - `Authorization`: may be present, but not always trusted (depends on call path)

### How Backend Functions Call Auth
- All HTTP handlers are decorated with `@inject_user_context` (in `main.py`).
- This decorator calls `get_authenticated_user(request)` before any business logic runs.
- If authentication fails, the request is rejected with 401.
- If successful, user info is injected as attributes on the request (e.g., `request.end_user_id`).
- All business logic functions (e.g., `get_user_profile`, `update_user_profile`) expect these attributes to be present and use them for authorization and data access.

### Common Pitfalls
- If the OpenAPI spec does not forward the correct headers, authentication will fail.
- If the backend does not check the correct header, user identity will not be established.
- Always ensure the API Gateway and backend are in sync regarding header names and expectations.
