# Relex Backend

Backend for Relex, an AI-powered legal chat application built using Firebase Functions in Python and Terraform for infrastructure management.

## Project Structure

- `functions/src/`: Contains Python modules for Firebase Functions
  - `cases.py`: Case management functions
  - `chat.py`: Chat and AI interaction functions
  - `auth.py`: Authentication functions
  - `payments.py`: Payment processing functions
  - `organization.py`: Organization account management functions
  - `organization_membership.py`: Organization membership management functions
  - `main.py`: Main entry point that imports and exports all functions

- `terraform/`: Contains Terraform configuration files
  - `main.tf`: Main Terraform configuration
  - `variables.tf`: Variable definitions
  - `outputs.tf`: Output definitions
  - `terraform.tfvars.example`: Example variable values

## Setup Instructions

### Prerequisites

- Firebase CLI
- Terraform
- Python 3.10 or higher
- Google Cloud SDK
- Cloudflare account with access to relex.ro domain

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

3. Run your Terraform commands again:
   ```bash
   cd terraform
   terraform apply -auto-approve
   ```

This ensures your Terraform deployment process has the necessary permissions to create and manage secrets.

### Deployment

1. Initialize Terraform:
   ```bash
   cd terraform
   terraform init
   ```

2. Deploy the infrastructure:
   ```bash
   terraform apply -auto-approve
   ```

**Note**: We always use `-auto-approve` flag with terraform apply to automate the deployment process.

## Development

To run functions locally:

```bash
cd functions
pip install -r requirements.txt
functions-framework --target=cases_create_case
```

### Environment Variables

The Cloud Functions use the following environment variables:

- `GOOGLE_CLOUD_PROJECT`: The Google Cloud project ID (default: "relexro")
- `GOOGLE_CLOUD_REGION`: The Google Cloud region (default: "europe-west3")
- `STRIPE_SECRET_KEY`: The Stripe secret key (used in payment functions)
- `STRIPE_WEBHOOK_SECRET`: The Stripe webhook signing secret (used to verify webhook authenticity)

These environment variables are set in the Terraform configuration (`terraform/main.tf`) and passed to each function.

## Deployment

### Using Terraform

```bash
cd terraform
terraform init
terraform apply -auto-approve
```

### Using gcloud CLI (Recommended for monitoring and debugging)

The gcloud CLI is the recommended tool for monitoring and debugging Cloud Functions:

```bash
# Deploy a function using gcloud (alternative to Terraform)
gcloud functions deploy relex-backend-create-case \
  --gen2 \
  --runtime=python310 \
  --region=europe-west3 \
  --source=./functions/src \
  --entry-point=cases_create_case \
  --trigger-http \
  --allow-unauthenticated

# View logs for a function
gcloud functions logs read relex-backend-create-case --gen2 --region=europe-west3

# Describe a function to get details
gcloud functions describe relex-backend-create-case --gen2 --region=europe-west3

# Test a function directly with HTTP
gcloud functions call relex-backend-create-case --gen2 --region=europe-west3 --data '{"title": "Test Case", "description": "Test Description"}'
```

**Note**: Always use gcloud CLI for monitoring and debugging functions rather than creating temporary testing solutions.

## Authentication Testing

### Testing with test-auth.html

We've included a simple HTML utility for testing Firebase Authentication:

1. Start a local web server:
   ```bash
   python3 -m http.server 8000
   ```

2. Navigate to http://localhost:8000/test-auth.html in your browser

3. Click "Sign in with Google" and complete the authentication flow

4. Once authenticated, you'll see your user ID and can access your ID token

5. Test API endpoints by entering the function URL in the input field and clicking "Test API with Token"
   - Example URL to test: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-validate-user`

6. The API response will be displayed, showing your authenticated user information

### CORS Support

The authentication API endpoints include CORS (Cross-Origin Resource Sharing) support to enable web applications to call them from different domains:

- The `validate_user` function handles OPTIONS preflight requests
- CORS headers are included in responses:
  - `Access-Control-Allow-Origin: *`
  - `Access-Control-Allow-Methods: GET, POST, OPTIONS`
  - `Access-Control-Allow-Headers: Content-Type, Authorization` 
  - `Access-Control-Max-Age: 3600`

This enables web applications to authenticate users and make API calls from browsers, even when hosted on different domains.

### Manual Authentication Testing with gcloud

For testing without a browser, you can obtain an ID token using gcloud:

1. Make sure you're authenticated with gcloud:
   ```bash
   gcloud auth login
   ```

2. Get an ID token:
   ```bash
   gcloud auth print-identity-token
   ```

3. Use the token in API requests:
   ```bash
   curl -X GET \
     -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
     https://europe-west3-relexro.cloudfunctions.net/relex-backend-validate-user
   ```

Expected response (HTTP 200):
```json
{
  "userId": "your-user-id",
  "email": "your-email@example.com"
}
```

**Important Note**: To use Firebase Authentication:
1. Google Sign-in must be enabled in Firebase Console (Authentication → Sign-in methods)
2. The OAuth consent screen must be properly configured
3. "localhost" must be added to authorized domains for local testing

## API Documentation

See [api.md](api.md) for complete documentation of all API endpoints.

## Custom Domain

The API is available at `https://api.relex.ro/v1`. This custom domain is configured using:

- Google Cloud API Gateway for hosting the API
- Cloudflare DNS for domain management
- Direct CNAME record (unproxied) pointing to the API Gateway hostname

The DNS configuration is managed via Terraform in the `modules/cloudflare` module, which creates an unproxied CNAME record to enable direct connections to the API Gateway without Cloudflare proxying.

## Deployment Troubleshooting

### Common Issues

1. **Missing Dependencies**: Ensure there's a `requirements.txt` file in the `functions/src` directory with all required packages.

2. **Dependency Version Conflicts**: Pin specific versions of packages that are known to work together:
   ```
   flask==2.2.3
   werkzeug==2.2.3
   ```

3. **Container Health Check Failures**: If you see "Container Healthcheck failed" errors, check the logs with:
   ```bash
   gcloud functions logs read <function-name> --gen2 --region=europe-west3
   ```

4. **Import Errors**: Make sure all imported modules are listed in requirements.txt with correct versions.

5. **Function Entry Point**: Verify the entry point in Terraform config matches the function name in `main.py`.

## Testing

### Testing the Permission Model

The case and file management functions now implement permission checks based on the organization roles and individual case ownership. Here's how to test these permissions:

#### 1. Setup Required Data

First, set up test data with different user roles:

1. Create an organization:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"name": "Test Organization", "type": "law_firm", "email": "test@example.com"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-create-organization
```

2. Add members with different roles:
```bash
# Add staff member
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"organizationId": "ORGANIZATION_ID", "userId": "STAFF_USER_ID", "role": "staff"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-add-organization-member

# Add administrator
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"organizationId": "ORGANIZATION_ID", "userId": "ADMIN_USER_ID", "role": "administrator"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-add-organization-member
```

#### 2. Test Case Creation

Test case creation with different user roles:

1. Create organization case as administrator:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"title": "Admin Test Case", "description": "Case created by admin", "organizationId": "ORGANIZATION_ID"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-create-case
```

2. Create organization case as staff member:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"title": "Staff Test Case", "description": "Case created by staff", "organizationId": "ORGANIZATION_ID"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-create-case
```

3. Create individual case (requires payment):
```bash
# First, create a payment intent
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"amount": 5000, "currency": "usd", "caseTitle": "Individual Test Case", "caseDescription": "Test case with payment"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-create-payment-intent-for-case

# Then create the case with the payment intent ID
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"title": "Individual Test Case", "description": "Test case with payment", "paymentIntentId": "PAYMENT_INTENT_ID"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-create-case
```

4. Test creating a case with non-member account (should fail with 403 Forbidden):
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"title": "Unauthorized Case", "description": "Should fail", "organizationId": "ORGANIZATION_ID"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-create-case
```

#### 3. Test Listing Cases

1. List organization cases:
```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "https://europe-west3-relexro.cloudfunctions.net/relex-backend-list-cases?organizationId=ORGANIZATION_ID"
```

2. List individual cases for the authenticated user:
```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "https://europe-west3-relexro.cloudfunctions.net/relex-backend-list-cases"
```

#### 4. Test Case Operations with Different Roles

1. Archive an organization case:
```bash
# As administrator (should succeed)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"caseId": "CASE_ID"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-archive-case

# As staff member (should fail with 403 Forbidden)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"caseId": "CASE_ID"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-archive-case
```

2. Archive an individual case:
```bash
# As case owner (should succeed)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"caseId": "INDIVIDUAL_CASE_ID"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-archive-case

# As different user (should fail with 403 Forbidden)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"caseId": "INDIVIDUAL_CASE_ID"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-archive-case
```

3. Delete a case:
```bash
# As administrator or case owner (should succeed)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"caseId": "CASE_ID"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-delete-case
```

#### 5. Test File Operations

1. Upload file to an organization case:
```bash
# Using multipart/form-data to upload a file
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -F "file=@/path/to/file.pdf" \
  -F "caseId=CASE_ID" \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-upload-file
```

2. Upload file to an individual case:
```bash
# Using multipart/form-data to upload a file (as case owner)
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -F "file=@/path/to/file.pdf" \
  -F "caseId=INDIVIDUAL_CASE_ID" \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-upload-file
```

#### 6. Verifying the Dual Case Ownership Model

To verify that the dual case ownership model is working correctly, you can:

1. Create both organization cases and individual cases
2. Verify that organization cases can be accessed by organization members according to their roles
3. Verify that individual cases can only be accessed by their owners
4. Test all operations with different user accounts to ensure permissions are enforced correctly
5. Examine Firestore to verify that:
   - Organization cases have a valid `organizationId` and `paymentStatus: "covered_by_subscription"`
   - Individual cases have `organizationId: null` and `paymentStatus: "paid"` with a `paymentIntentId`

The permission model ensures:
- Individual cases are only accessible to their owners
- Organization cases follow the role-based permission model
- Payment is required for individual cases
- All case and file operations properly respect both ownership models

### Testing the create_case Function

You can test the `create_case` function using curl or a tool like Postman:

#### Success Case
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"title": "Test Case", "description": "Test Description", "organizationId": "org123"}' \
  <FUNCTION_URL>
```

Expected response (HTTP 201):
```json
{
  "caseId": "<generated-id>",
  "message": "Case created successfully"
}
```

#### Validation Failure: Missing organizationId
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"title": "Test Case", "description": "Test Description"}' \
  <FUNCTION_URL>
```

Expected response (HTTP 400):
```json
{
  "error": "Bad Request",
  "message": "Organization ID is required"
}
```

#### Permission Failure: Not a member of the organization
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"title": "Test Case", "description": "Test Description", "organizationId": "org456"}' \
  <FUNCTION_URL>
```

Expected response (HTTP 403):
```json
{
  "error": "Forbidden",
  "message": "You do not have permission to create a case for this organization"
}
```

### Testing the archive_case Function

You can test the `archive_case` function using curl or a tool like Postman:

#### Success Case (Administrator)
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"caseId": "case123"}' \
  <FUNCTION_URL>
```

Expected response (HTTP 200):
```json
{
  "message": "Case archived successfully"
}
```

#### Permission Failure (Staff Member)
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"caseId": "case123"}' \
  <FUNCTION_URL>
```

Expected response (HTTP 403):
```json
{
  "error": "Forbidden",
  "message": "You do not have permission to archive this case"
}
```

### Testing the list_cases Function

You can test the `list_cases` function using curl or a tool like Postman:

#### List Cases for an Organization (Member)
```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "<FUNCTION_URL>?organizationId=org123"
```

Expected response (HTTP 200):
```json
{
  "cases": [
    {
      "caseId": "<case-id-1>",
      "title": "Test Case 1",
      "description": "Test Description 1",
      "status": "open",
      "userId": "user123",
      "organizationId": "org123",
      "creationDate": { ... }
    },
    {
      "caseId": "<case-id-2>",
      "title": "Test Case 2",
      "description": "Test Description 2",
      "status": "open",
      "userId": "user456",
      "organizationId": "org123",
      "creationDate": { ... }
    }
  ]
}
```

#### Permission Failure (Non-Member)
```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "<FUNCTION_URL>?organizationId=org456"
```

Expected response (HTTP 403):
```json
{
  "error": "Forbidden",
  "message": "You do not have permission to list cases for this organization"
}
```

### Testing the upload_file Function

You can test the `upload_file` function using curl or a tool like Postman:

#### Success Case (Administrator or Staff)
```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -F "file=@/path/to/file.pdf" \
  <FUNCTION_URL>/case123
```

Expected response (HTTP 201):
```json
{
  "documentId": "<generated-id>",
  "filename": "<generated-filename>",
  "originalFilename": "file.pdf",
  "storagePath": "cases/case123/documents/<generated-filename>",
  "message": "File uploaded successfully"
}
```

#### Permission Failure (Non-Member)
```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -F "file=@/path/to/file.pdf" \
  <FUNCTION_URL>/case123
```

Expected response (HTTP 403):
```json
{
  "error": "Forbidden",
  "message": "You do not have permission to upload files to this case"
}
```

### Verifying Permission Checks

After performing these operations, you can verify the permission checks by:

1. Using the Firebase Console to check the documents in Firestore
2. Examining the logs of the Cloud Functions:
   ```bash
   gcloud functions logs read relex-backend-create-case --gen2 --region=europe-west3
   gcloud functions logs read relex-backend-archive-case --gen2 --region=europe-west3
   gcloud functions logs read relex-backend-delete-case --gen2 --region=europe-west3
   gcloud functions logs read relex-backend-upload-file --gen2 --region=europe-west3
   gcloud functions logs read relex-backend-list-cases --gen2 --region=europe-west3
   ```

The permission model ensures that:
- Users can only access and modify resources within organizations they belong to
- Different actions are restricted based on the user's role in the organization
- All case and file operations now properly respect the role-based permission model

### Testing the organization membership functions

You can test the `add_organization_member` function using curl or a tool like Postman:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"organizationId": "org123", "userId": "user456", "role": "staff"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-add-organization-member
```

Expected response (HTTP 200):
```json
{
  "success": true,
  "membershipId": "membership789",
  "userId": "user456",
  "organizationId": "org123",
  "role": "staff",
  "email": "user@example.com",
  "displayName": "User Name"
}
```

### Testing the set_organization_member_role Function

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"organizationId": "org123", "userId": "user456", "newRole": "administrator"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-set-organization-member-role
```

Expected response (HTTP 200):
```json
{
  "success": true,
  "membershipId": "membership789",
  "userId": "user456",
  "organizationId": "org123",
  "role": "administrator",
  "email": "user@example.com",
  "displayName": "User Name"
}
```

### Testing the list_organization_members Function

```bash
curl -X GET \
  -H "Authorization: Bearer <ID_TOKEN>" \
  "https://europe-west3-relexro.cloudfunctions.net/relex-backend-list-organization-members?organizationId=org123"
```

Expected response (HTTP 200):
```json
{
  "members": [
    {
      "userId": "user123",
      "role": "administrator",
      "addedAt": "2023-10-15T10:30:00Z",
      "email": "admin@example.com",
      "displayName": "Admin User"
    },
    {
      "userId": "user456",
      "role": "staff",
      "addedAt": "2023-10-16T11:45:00Z",
      "email": "staff@example.com",
      "displayName": "Staff User"
    }
  ]
}
```

### Testing the remove_organization_member Function

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"organizationId": "org123", "userId": "user456"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-remove-organization-member
```

Expected response (HTTP 200):
```json
{
  "success": true,
  "userId": "user456",
  "organizationId": "org123"
}
```

### Testing the get_user_organization_role Function

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"userId": "user456", "organizationId": "org123"}' \
  https://europe-west3-relexro.cloudfunctions.net/relex-backend-get-user-organization-role
```

Expected response (HTTP 200):
```json
{
  "role": "staff"
}
```

### Testing the list_user_organizations Function

You can test the `list_user_organizations` function using curl or a tool like Postman:

```bash
curl -X GET \
  -H "Authorization: Bearer <ID_TOKEN>" \
  "https://europe-west3-relexro.cloudfunctions.net/relex-backend-list-user-organizations"
```

This will return all organizations the authenticated user belongs to.

Expected response (HTTP 200):
```json
{
  "organizations": [
    {
      "organizationId": "org123",
      "name": "Law Firm A",
      "type": "law_firm",
      "role": "administrator"
    },
    {
      "organizationId": "org456",
      "name": "Consulting B", 
      "type": "consulting",
      "role": "staff"
    }
  ]
}
```

You can also specify a user ID to view organizations for a specific user (only works if you're viewing your own organizations):

```bash
curl -X GET \
  -H "Authorization: Bearer <ID_TOKEN>" \
  "https://europe-west3-relexro.cloudfunctions.net/relex-backend-list-user-organizations?userId=YOUR_USER_ID"
```

Attempting to view another user's organizations will result in a 403 Forbidden error:

```bash
curl -X GET \
  -H "Authorization: Bearer <ID_TOKEN>" \
  "https://europe-west3-relexro.cloudfunctions.net/relex-backend-list-user-organizations?userId=ANOTHER_USER_ID"
```

Expected response (HTTP 403):
```json
{
  "error": "Forbidden",
  "message": "You can only view your own organizations"
}
```

### Verifying Organization Membership Operations
After performing organization membership operations, you can verify they were successful by:
1. Using the `list_organization_members` function to check all members of an organization
2. Using the `get_user_organization_role` function to check a specific user's role
3. Checking the Firebase Console:
   - Go to the Firebase Console (https://console.firebase.google.com/)
   - Select your project (`relexro`)
   - Navigate to Firestore Database
   - Look for the `organization_memberships` collection
   - Verify the membership data has been updated correctly

## Authentication Testing

To test the authentication endpoints with real Google credentials, follow these steps:

1. **Complete Firebase Authentication Setup in Console (Required First):**
   - Go to the Firebase console: https://console.firebase.google.com/
   - Select your project: `relexro`
   - Navigate to the Authentication section
   - Click "Get started" and enable Google Sign-in provider
   - Configure the OAuth consent screen properly
   - Add `localhost` to the authorized domains list

2. First, ensure you have the `gcloud` CLI installed and are logged in:
```bash
# Install gcloud CLI (if not already installed)
# macOS (with Homebrew):
brew install google-cloud-sdk

# Login with your Google account
gcloud auth login
```

3. Set up application default credentials:
```bash
gcloud auth application-default login
```

4. Get an ID token for testing:
```bash
# This will generate a JWT token valid for 1 hour
gcloud auth print-identity-token
```

5. Use the token in your API requests:
```bash
curl -X GET "https://europe-west3-relexro.cloudfunctions.net/relex-backend-validate-user" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Note: The token expires after 1 hour. You'll need to generate a new one using `gcloud auth print-identity-token` if you get authentication errors.

### Troubleshooting

- If you get a "quota exceeded" error, you may need to set up a quota project:
```bash
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

- If you get an "Invalid token" error, ensure that:
  1. You've completed the Firebase Authentication setup in the console
  2. Your token hasn't expired
  3. You're using the correct project ID
  4. The service account has the necessary IAM permissions
  
- The token from `gcloud auth print-identity-token` is a Google-signed token, but Firebase Authentication needs to be configured to accept it. See the setup steps in status.md for more details. 