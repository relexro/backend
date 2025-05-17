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
  - `prompt.txt`: System prompts and templates for LLM interactions
  - `modules.txt`: Modular components used in prompts
  - `tools.json`: Tool definitions and schemas using OpenAI function format
  - `agent_loop.txt`: Description of the agent's operational flow

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
- Python 3.10 or higher
- Google Cloud SDK
- Cloudflare account with access to relex.ro domain
- Node.js and npm (for OpenAPI validation)
- Redocly CLI: `npm install -g @redocly/cli` (for validating OpenAPI specifications)

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
4. Configure LLM API keys:
   ```bash
   export GEMINI_API_KEY=your_gemini_api_key
   export GROK_API_KEY=your_grok_api_key
   ```
5. Configure Stripe API keys:
   ```bash
   export TF_VAR_stripe_secret_key=your_stripe_secret_key
   export TF_VAR_stripe_webhook_secret=your_stripe_webhook_secret
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

3. **Set the authentication token environment variable**:
   ```bash
   # Linux/macOS
   export RELEX_TEST_JWT="your_token_here"

   # Windows (Command Prompt)
   set RELEX_TEST_JWT=your_token_here

   # Windows (PowerShell)
   $env:RELEX_TEST_JWT="your_token_here"
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