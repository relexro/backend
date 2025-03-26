# Relex API Gateway

This document explains the API Gateway setup for the Relex backend, which provides a RESTful API structure for accessing the existing Cloud Functions.

## Overview

The API Gateway acts as a central entry point for all Relex API requests, providing the following benefits:
- Consistent RESTful URL structure
- Centralized security and authentication
- Path-based routing to appropriate backend functions
- Potential for rate limiting and monitoring

## Architecture

The API Gateway maps RESTful endpoints to the existing Cloud Functions:

```
[Client] → [API Gateway] → [Cloud Functions]
```

For example, a request to `https://{gateway-url}/v1/organizations/{organizationId}` is routed to the `get_organization` Cloud Function.

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

1. **Terraform Configuration (`api_gateway.tf`)** - Defines the API Gateway infrastructure resources
2. **OpenAPI Specification (`openapi_spec.yaml`)** - Defines the API structure and routing

### Terraform Resources

- `google_api_gateway_api` - Defines the API as a whole
- `google_api_gateway_api_config` - References the OpenAPI specification
- `google_service_account` - Service account for the API Gateway
- `google_project_iam_member` - Grants function invocation permissions
- `google_api_gateway_gateway` - Deploys the API config

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

2. **404 Not Found Errors**
   - Check that the path in the request matches a defined path in the OpenAPI spec
   - Verify the backend Cloud Function exists and is deployed

3. **500 Internal Server Errors**
   - Check Cloud Function logs for issues
   - Verify the API Gateway configuration is correct

### Viewing Logs

To view API Gateway logs:
```bash
gcloud logging read "resource.type=api_gateway_gateway AND resource.labels.gateway_id=relex-gateway"
```

To view Cloud Function logs:
```bash
gcloud functions logs read relex-backend-create-organization --gen2 --region=europe-west3
``` 