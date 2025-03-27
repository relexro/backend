# Relex API Gateway

This document explains the API Gateway setup for the Relex backend, which provides a RESTful API structure for accessing the existing Cloud Functions.

## Overview

The API Gateway acts as a central entry point for all Relex API requests, providing the following benefits:
- Consistent RESTful URL structure
- Centralized security and authentication
- Path-based routing to appropriate backend functions
- Potential for rate limiting and monitoring
- **Enhanced security through restricted direct function access**

## Architecture

The API Gateway maps RESTful endpoints to the existing Cloud Functions:

```
[Client] → [API Gateway] → [Cloud Functions]
```

For example, a request to `https://{gateway-url}/v1/organizations/{organizationId}` is routed to the `get_organization` Cloud Function.

### Security Enhancements

The backend Cloud Functions have been configured with restricted access:
- Cloud Functions use `ingress_settings: ALLOW_INTERNAL_AND_GCLB` to restrict direct public HTTP access
- Only the API Gateway service account and Google Cloud Load Balancers can invoke the functions directly
- IAM permissions enforce that only authorized service accounts can trigger the functions
- Functions process requests forwarded by the API Gateway, handling path parameters, query parameters, and request bodies

## API Structure

The API follows RESTful conventions:

### Organizations
- `GET /v1/organizations` - List user's organizations
- `POST /v1/organizations` - Create a new organization
- `GET /v1/organizations/{organizationId}` - Get organization details
- `PUT /v1/organizations/{organizationId}` - Update organization

### Organization Members
- `GET /v1/organizations/{organizationId}/members` - List organization members
- `POST /v1/organizations/{organizationId}/members` - Add member to organization
- `PUT /v1/organizations/{organizationId}/members/{userId}` - Update member role
- `DELETE /v1/organizations/{organizationId}/members/{userId}` - Remove member

### Cases
- `GET /v1/organizations/{organizationId}/cases` - List cases for an organization
- `POST /v1/organizations/{organizationId}/cases` - Create a new case
- `GET /v1/cases/{caseId}` - Get case details
- `POST /v1/cases/{caseId}` - Archive a case
- `DELETE /v1/cases/{caseId}` - Delete a case

### Files
- `POST /v1/cases/{caseId}/files` - Upload file to a case
- `GET /v1/files/{fileId}` - Download a file

## Implementation

The implementation consists of two primary components:

1. **Terraform Configuration** - Defines the API Gateway infrastructure resources and secures Cloud Functions
   - `terraform/api_gateway.tf` - API Gateway infrastructure
   - `terraform/main.tf` - Cloud Functions with security configurations
   - `terraform/openapi_spec.yaml` - API specification (referenced by api_gateway.tf)

2. **OpenAPI Specification** - Defines the API structure and routing

### Terraform Resources

- `google_api_gateway_api` - Defines the API as a whole
- `google_api_gateway_api_config` - References the OpenAPI specification
- `google_service_account` - Service account for the API Gateway
- `google_project_iam_member` - Grants function invocation permissions
- `google_api_gateway_gateway` - Deploys the API config
- `google_cloudfunctions2_function` - Cloud Functions with ingress settings to restrict direct access

### Cloud Functions Configuration

Cloud Functions are configured with:
- `ingress_settings: ALLOW_INTERNAL_AND_GCLB` - Restricts direct public HTTP access
- IAM permissions that allow only the API Gateway service account to invoke the functions
- Python code that properly handles requests forwarded by API Gateway

### OpenAPI Configuration

The OpenAPI specification defines:
- API paths and methods
- Request and response schemas
- Authentication requirements
- Routing to backend Cloud Functions

## Authentication

The API Gateway uses Firebase Authentication:
- Requests must include a Firebase ID token in the Authorization header
- The API Gateway validates the token using the Firebase issuer and JWKS
- Token validation uses the `x-google-issuer` and `x-google-jwks_uri` extensions
- The API Gateway forwards authentication headers to the backend Cloud Functions

## Deployment

To deploy the API Gateway:

1. Make sure you have the required permissions:
   ```
   roles/apigateway.admin
   roles/iam.serviceAccountAdmin
   roles/cloudfunctions.invoker
   ```

2. Apply the Terraform configuration:
   ```bash
   cd terraform
   terraform init
   terraform apply -auto-approve
   ```

3. The API Gateway URL will be output after successful deployment.

## File Organization

The API Gateway configuration files are organized as follows:
- `terraform/api_gateway.tf` - Terraform configuration for API Gateway
- `terraform/openapi_spec.yaml` - OpenAPI specification 
- `terraform/main.tf` - Cloud Functions configuration with security settings
- `api_gateway_readme.md` (this file) - Documentation

## Testing the API

To test the API Gateway:

1. Get a Firebase ID token:
   ```bash
   # Use gcloud CLI to get a token
   TOKEN=$(gcloud auth print-identity-token)
   ```

2. Make a request to the API Gateway:
   ```bash
   # List organizations example
   curl -X GET "https://{gateway-url}/v1/organizations" \
     -H "Authorization: Bearer $TOKEN"
   ```

3. The API Gateway will route the request to the appropriate Cloud Function.

## Request Flow

When a client makes a request:

1. The request reaches the API Gateway
2. The API Gateway validates authentication
3. The API Gateway routes the request to the appropriate Cloud Function, preserving:
   - Path parameters (e.g., `organizationId`)
   - Query parameters
   - Headers (including authentication)
   - Request body
4. The Cloud Function processes the request and returns a response
5. The API Gateway forwards the response back to the client

## Additional Resources

- [Google API Gateway Documentation](https://cloud.google.com/api-gateway/docs)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Google Cloud Functions](https://cloud.google.com/functions)
- [Firebase Authentication](https://firebase.google.com/docs/auth)

## Troubleshooting

### Common Issues

1. **403 Forbidden Errors**
   - Ensure the API Gateway service account has `cloudfunctions.invoker` role
   - Verify the Firebase ID token is valid and not expired
   - Check Cloud Functions ingress settings allow access from API Gateway

2. **404 Not Found Errors**
   - Check that the path in the request matches a defined path in the OpenAPI spec
   - Verify the backend Cloud Function exists and is deployed

3. **500 Internal Server Errors**
   - Check Cloud Function logs for issues
   - Verify the API Gateway configuration is correct
   - Ensure Cloud Functions correctly handle requests forwarded by API Gateway

### Viewing Logs

To view API Gateway logs:
```bash
gcloud logging read "resource.type=api_gateway_gateway AND resource.labels.gateway_id=relex-gateway"
```

To view Cloud Function logs:
```bash
gcloud functions logs read relex-backend-create-organization --gen2 --region=europe-west3
``` 