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
1. OpenAPI validation
2. Terraform initialization
3. Terraform plan and apply
4. Post-deployment verification

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

## Additional Resources

- [Data Models](docs/data_models.md): Detailed schema definitions for Firestore collections
- [Authentication](docs/concepts/authentication.md): Authentication and authorization system
- [Payments](docs/concepts/payments.md): Payment and subscription system
- [Tools](docs/concepts/tools.md): Agent tools and capabilities
- [Prompts](docs/concepts/prompts.md): Prompt design for LLM interactions
- [Tiers](docs/concepts/tiers.md): Case tier system for complexity determination
- [Functions](docs/functions.md): Cloud Functions implementation details