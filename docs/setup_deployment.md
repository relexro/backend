# Setup and Deployment

## Overview

This document outlines the process for setting up and deploying the Relex backend. The backend is built on Google Cloud Platform using Cloud Functions, Firestore, Storage, and API Gateway, with infrastructure defined and managed using Terraform.

## Prerequisites

Before deployment, ensure you have the following:

1. **Google Cloud Platform Account** with billing enabled
2. **Firebase Project** with Firestore, Authentication, and Storage enabled
3. **Stripe Account** for payment processing
4. **Cloud Storage Bucket** for storing files
5. **Cloudflare Account** (if using custom domain)
6. **LLM API Keys** for Gemini and Grok models

## Required Tools

- **Terraform** (version 1.0 or higher)
- **Google Cloud SDK** (latest version)
- **Firebase CLI** (latest version)
- **Node.js** and npm (for OpenAPI validation)
- **Python 3.10** (for local function development and Cloud Functions runtime)
- **Redocly CLI**: `npm install -g @redocly/cli` (for validating OpenAPI specifications)

## Authentication Setup

1. **Create a Service Account** with the following roles:
   - Cloud Functions Admin
   - Cloud Storage Admin
   - Firestore Admin
   - API Gateway Admin
   - Secret Manager Admin
   - Service Account User

2. **Generate and download a key file** for this service account

3. **Set up environment variable** for authentication:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
   ```

## Environment Variables

### Required Environment Variables

Set the following environment variables before deploying:

1. **Google Cloud Configuration**:
   ```bash
   export GOOGLE_CLOUD_PROJECT="relexro"  # Your project ID
   export GOOGLE_CLOUD_REGION="europe-west1"  # Your preferred region
   ```

2. **Cloudflare Configuration** (for DNS management):
   ```bash
   export TF_VAR_cloudflare_api_token=your_cloudflare_api_token
   export TF_VAR_cloudflare_zone_id=your_cloudflare_zone_id
   export TF_VAR_cloudflare_account_id=your_cloudflare_account_id
   ```

3. **Stripe Configuration**:
   ```bash
   export TF_VAR_stripe_secret_key=your_stripe_secret_key
   export TF_VAR_stripe_webhook_secret=your_stripe_webhook_secret
   ```

4. **LLM API Keys**:
   ```bash
   export GEMINI_API_KEY=your_gemini_api_key
   export GROK_API_KEY=your_grok_api_key
   ```

### Secret Manager Configuration

The deployment process requires the following secrets to be stored in Google Secret Manager:

1. **Stripe Secret Key**:
   ```bash
   gcloud secrets create stripe-secret-key --replication-policy="automatic"
   echo $TF_VAR_stripe_secret_key | gcloud secrets versions add stripe-secret-key --data-file=-
   ```

2. **Stripe Webhook Secret**:
   ```bash
   gcloud secrets create stripe-webhook-secret --replication-policy="automatic"
   echo $TF_VAR_stripe_webhook_secret | gcloud secrets versions add stripe-webhook-secret --data-file=-
   ```

3. **Gemini API Key**:
   ```bash
   gcloud secrets create gemini-api-key --replication-policy="automatic"
   echo $GEMINI_API_KEY | gcloud secrets versions add gemini-api-key --data-file=-
   ```

4. **Grok API Key**:
   ```bash
   gcloud secrets create grok-api-key --replication-policy="automatic"
   echo $GROK_API_KEY | gcloud secrets versions add grok-api-key --data-file=-
   ```

## Agent Configuration Directory

The `functions/src/agent-config/` directory contains critical runtime configuration files that must be included in the deployment:

1. **`prompt.txt`**: System prompts and templates for LLM interactions
2. **`modules.txt`**: Modular components used to assemble complete prompts
3. **`tools.json`**: Definitions and schemas for all available tools
4. **`agent_loop.txt`**: Description of the agent's operational flow

These files are loaded by `agent_config.py` at runtime and are essential for the agent's operation. If the directory doesn't exist, create it with these files before deployment.

## Deployment Process

### Using Deployment Scripts

The recommended deployment method is using the provided scripts in the `terraform` directory:

1. **Initialize the environment**:
   ```bash
   cd terraform
   ```

2. **Deploy using the deployment script**:
   ```bash
   ./deploy.sh
   ```

   This script handles:
   - Terraform initialization
   - Terraform planning and application
   - Post-deployment validation

   Note: The script does NOT validate the OpenAPI specification. You should manually validate it before deployment:
   ```bash
   npx @redocly/cli lint openapi_spec.yaml
   ```

3. **For clean deployment** (destroying existing resources first):
   ```bash
   ./destroy.sh && ./deploy.sh
   ```

### Manual Deployment Steps

If you need more control over the deployment process:

1. **Validate the OpenAPI specification**:
   ```bash
   cd terraform
   npx @redocly/cli lint openapi_spec.yaml
   ```

2. **Initialize Terraform**:
   ```bash
   terraform init
   ```

3. **Plan the deployment**:
   ```bash
   terraform plan -var project_id=$GOOGLE_CLOUD_PROJECT -var region=$GOOGLE_CLOUD_REGION -out=tfplan
   ```

4. **Apply the deployment**:
   ```bash
   terraform apply "tfplan"
   ```

5. **Verify the deployment**:
   ```bash
   gcloud functions list --gen2 --region=$GOOGLE_CLOUD_REGION
   ```

## Secret Manager Permissions

If you encounter Secret Manager access issues during deployment:

1. **Identify the service account**:
   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   grep "client_email" $GOOGLE_APPLICATION_CREDENTIALS
   ```

2. **Grant Secret Manager Admin permissions**:
   ```bash
   gcloud projects add-iam-policy-binding $(gcloud config get project) \
     --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
     --role="roles/secretmanager.admin"
   ```

## Troubleshooting

### Secret Manager Issues

If you encounter "DESTROYED" state secret versions:

```bash
# Delete existing secrets
gcloud secrets delete stripe-secret-key --quiet
gcloud secrets delete stripe-webhook-secret --quiet
gcloud secrets delete gemini-api-key --quiet
gcloud secrets delete grok-api-key --quiet

# Recreate secrets
gcloud secrets create stripe-secret-key --replication-policy="automatic"
echo $TF_VAR_stripe_secret_key | gcloud secrets versions add stripe-secret-key --data-file=-

gcloud secrets create stripe-webhook-secret --replication-policy="automatic"
echo $TF_VAR_stripe_webhook_secret | gcloud secrets versions add stripe-webhook-secret --data-file=-

gcloud secrets create gemini-api-key --replication-policy="automatic"
echo $GEMINI_API_KEY | gcloud secrets versions add gemini-api-key --data-file=-

gcloud secrets create grok-api-key --replication-policy="automatic"
echo $GROK_API_KEY | gcloud secrets versions add grok-api-key --data-file=-
```

### Deployment Failures

For deployment failures:

1. **Check Cloud Build logs**:
   ```bash
   gcloud builds list
   gcloud builds log [BUILD_ID]
   ```

2. **Check function logs**:
   ```bash
   gcloud functions logs read relex-backend-[FUNCTION_NAME] --gen2 --region=$GOOGLE_CLOUD_REGION
   ```

3. **Verify API Gateway**:
   ```bash
   gcloud api-gateway gateways describe relex-api-gateway --location=$GOOGLE_CLOUD_REGION
   ```

## Monitoring and Debugging

To monitor the deployed functions:

1. **View logs for a specific function**:
   ```bash
   gcloud functions logs read relex-backend-[FUNCTION_NAME] --gen2 --region=$GOOGLE_CLOUD_REGION
   ```

2. **Get function details**:
   ```bash
   gcloud functions describe relex-backend-[FUNCTION_NAME] --gen2 --region=$GOOGLE_CLOUD_REGION
   ```

3. **Test a function directly**:
   ```bash
   gcloud functions call relex-backend-[FUNCTION_NAME] --gen2 --region=$GOOGLE_CLOUD_REGION --data '{"key": "value"}'
   ```

## Local Development

For local development and testing:

1. **Install dependencies**:
   ```bash
   cd functions
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

2. **Run a function locally**:
   ```bash
   functions-framework --target=function_name
   ```

3. **Test with curl**:
   ```bash
   curl -X POST http://localhost:8080 -H "Content-Type: application/json" -d '{"key": "value"}'
   ```

## Post-Deployment Verification

After deployment, verify the following:

1. **API Gateway URL**:
   - Check the `docs/terraform_outputs.log` file for the `api_gateway_url` key
   - This is the default Google-provided URL (e.g., `relex-api-gateway-dev-mvef5dk.ew.gateway.dev`)
   - Note: The custom domain `api-dev.relex.ro` is not currently the active endpoint for the API Gateway

2. **Health Checks**:
   - Test function health checks by sending a GET request with the `X-Google-Health-Check` header:
     ```bash
     curl -H "X-Google-Health-Check: true" https://YOUR_API_GATEWAY_URL/v1/users/me
     ```
   - The response should be a 200 OK with a JSON body containing `{"status": "healthy", ...}`
   - Note: Health checks use the `X-Google-Health-Check` header rather than specific paths like `/_ah/health`

3. **Authentication**:
   - Obtain Firebase JWT tokens using the test utility:
     ```bash
     cd tests
     python3 -m http.server 8080
     # Open http://localhost:8080/test-auth.html in your browser
     # Sign in with the appropriate user account and copy the token

     # For regular user tests
     export RELEX_TEST_JWT="your_regular_user_token_here"

     # For organization admin tests
     export RELEX_ORG_ADMIN_TEST_JWT="your_org_admin_token_here"

     # For organization user tests
     export RELEX_ORG_USER_TEST_JWT="your_org_user_token_here"
     ```
   - Test authentication with the token:
     ```bash
     # Test with regular user token
     curl -H "Authorization: Bearer $RELEX_TEST_JWT" https://YOUR_API_GATEWAY_URL/v1/users/me

     # Test with organization admin token
     curl -H "Authorization: Bearer $RELEX_ORG_ADMIN_TEST_JWT" https://YOUR_API_GATEWAY_URL/v1/users/me
     ```

4. **API Endpoints**: Test key endpoints using curl or Postman with the correct API Gateway URL and authentication token

5. **Storage**: Check file upload and download functionality

6. **Firestore**: Verify database operations

7. **Stripe Integration**: Test payment flows

8. **Known Issues**:
   - API Gateway logs may not appear in Cloud Logging
   - The backend functions receive the service account identity, not the original end-user's Firebase UID

## Updating the Deployment

To update an existing deployment:

1. **Make code changes**: Update functions and configurations
2. **Run the deploy script**:
   ```bash
   cd terraform
   ./deploy.sh
   ```

The deployment script handles incremental updates, only redeploying functions that have changed.

### Secret Manager Setup

Before deploying, ensure all required secrets are created in Google Secret Manager:

- `gemini-api-key`
- `grok-api-key`
- `exa-api-key`
- `stripe-secret-key`
- `stripe-webhook-secret`

Example for Exa:
```bash
gcloud secrets create exa-api-key --replication-policy="automatic"
echo -n "$EXA_API_KEY" | gcloud secrets versions add exa-api-key --data-file=-
```

If you see an error about a missing secret during deployment, create the secret as shown above and re-run the deployment script.

Deployment is now stable. Next step: comprehensive API testing.