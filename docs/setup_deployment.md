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
- **Python 3.10 or higher** (for local function development)
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
   - OpenAPI spec validation
   - Terraform initialization
   - Terraform planning and application
   - Post-deployment validation

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

1. **API Endpoints**: Test key endpoints using a tool like Postman
2. **Authentication**: Verify Firebase Authentication is working
3. **Storage**: Check file upload and download functionality
4. **Firestore**: Verify database operations
5. **Stripe Integration**: Test payment flows

## Updating the Deployment

To update an existing deployment:

1. **Make code changes**: Update functions and configurations
2. **Run the deploy script**:
   ```bash
   cd terraform
   ./deploy.sh
   ```

The deployment script handles incremental updates, only redeploying functions that have changed. 