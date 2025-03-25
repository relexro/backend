# Relex Backend

Backend for Relex, an AI-powered legal chat application built using Firebase Functions in Python and Terraform for infrastructure management.

## Project Structure

- `functions/src/`: Contains Python modules for Firebase Functions
  - `cases.py`: Case management functions
  - `chat.py`: Chat and AI interaction functions
  - `auth.py`: Authentication functions
  - `payments.py`: Payment processing functions
  - `business.py`: Business account management functions
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

### Configuration

1. Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars` and update the values.
2. Set up Google Cloud authentication:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
   ```

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

4. Once authenticated, you'll see your user ID and can view your ID token

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

### Testing the create_case Function

You can test the `create_case` function using curl or a tool like Postman:

#### Success Case
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Case", "description": "Test Description"}' \
  <FUNCTION_URL>
```

Expected response (HTTP 201):
```json
{
  "caseId": "<generated-id>",
  "message": "Case created successfully"
}
```

#### With Business ID
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": "Business Case", "description": "Business Description", "businessId": "test-business-id"}' \
  <FUNCTION_URL>
```

#### Validation Failure: Missing Title
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"description": "No title"}' \
  <FUNCTION_URL>
```

Expected response (HTTP 400):
```json
{
  "error": "Bad Request",
  "message": "Title is required"
}
```

#### Validation Failure: Empty Fields
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": "", "description": ""}' \
  <FUNCTION_URL>
```

Expected response (HTTP 400):
```json
{
  "error": "Bad Request",
  "message": "Title cannot be empty"
}
```

**Note**: The function currently uses a placeholder user ID (`"test-user"`) since authentication has not yet been implemented.

### Verifying Data
After creating a case, you can verify it was created successfully by checking the Firebase Console:
1. Go to the Firebase Console (https://console.firebase.google.com/)
2. Select your project (`relexro`)
3. Navigate to Firestore Database
4. Look for the `cases` collection
5. Find the document with the matching `caseId` returned in the API response

### Testing the get_case Function

You can test the `get_case` function using curl or a tool like Postman:

#### Success Case
```bash
curl -X GET \
  <FUNCTION_URL>/<CASE_ID>
```

Replace `<CASE_ID>` with an actual case ID from a previously created case.

Expected response (HTTP 200):
```json
{
  "caseId": "<case-id>",
  "title": "Test Case",
  "description": "Test Description",
  "status": "open",
  "userId": "test-user",
  "creationDate": { ... }
}
```

#### Not Found Case
```bash
curl -X GET \
  <FUNCTION_URL>/nonexistent-case-id
```

Expected response (HTTP 404):
```json
{
  "error": "Not Found",
  "message": "Case not found"
}
```

#### Missing Case ID
```bash
curl -X GET \
  <FUNCTION_URL>/
```

Expected response (HTTP 400):
```json
{
  "error": "Bad Request",
  "message": "Case ID is required"
}
```

### Testing the list_cases Function

You can test the `list_cases` function using curl or a tool like Postman:

#### List All Cases
```bash
curl -X GET \
  <FUNCTION_URL>
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
      "userId": "test-user",
      "creationDate": { ... }
    },
    {
      "caseId": "<case-id-2>",
      "title": "Test Case 2",
      "description": "Test Description 2",
      "status": "closed",
      "userId": "test-user",
      "creationDate": { ... }
    }
  ]
}
```

#### Filter Cases by Status
```bash
curl -X GET \
  <FUNCTION_URL>?status=open
```

Expected response (HTTP 200, only includes cases with "open" status):
```json
{
  "cases": [
    {
      "caseId": "<case-id-1>",
      "title": "Test Case 1",
      "description": "Test Description 1",
      "status": "open",
      "userId": "test-user",
      "creationDate": { ... }
    }
  ]
}
```

### Testing the archive_case Function

You can test the `archive_case` function using curl or a tool like Postman:

#### Success Case
```bash
curl -X POST \
  <FUNCTION_URL>/<CASE_ID>
```

Replace `<CASE_ID>` with an actual case ID from a previously created case.

Expected response (HTTP 200):
```json
{
  "message": "Case archived successfully"
}
```

#### Not Found Case
```bash
curl -X POST \
  <FUNCTION_URL>/nonexistent-case-id
```

Expected response (HTTP 404):
```json
{
  "error": "Not Found",
  "message": "Case not found"
}
```

#### Missing Case ID
```bash
curl -X POST \
  <FUNCTION_URL>/
```

Expected response (HTTP 400):
```json
{
  "error": "Bad Request",
  "message": "Case ID is required"
}
```

### Testing the delete_case Function

You can test the `delete_case` function using curl or a tool like Postman:

#### Success Case
```bash
curl -X DELETE \
  <FUNCTION_URL>/<CASE_ID>
```

Replace `<CASE_ID>` with an actual case ID from a previously created case.

Expected response (HTTP 200):
```json
{
  "message": "Case marked as deleted successfully"
}
```

#### Not Found Case
```bash
curl -X DELETE \
  <FUNCTION_URL>/nonexistent-case-id
```

Expected response (HTTP 404):
```json
{
  "error": "Not Found",
  "message": "Case not found"
}
```

#### Missing Case ID
```bash
curl -X DELETE \
  <FUNCTION_URL>/
```

Expected response (HTTP 400):
```json
{
  "error": "Bad Request",
  "message": "Case ID is required"
}
```

### Verifying Archive and Delete Operations
After archiving or deleting a case, you can verify it was updated successfully by:
1. Using the `get_case` function to check the updated status
2. Checking the Firebase Console:
   - Go to the Firebase Console (https://console.firebase.google.com/)
   - Select your project (`relexro`)
   - Navigate to Firestore Database
   - Look for the `cases` collection
   - Find the document with the matching `caseId`
   - Verify the `status` field is set to either `"archived"` or `"deleted"`
   - Verify the `archiveDate` or `deletionDate` field is set

### Testing the upload_file Function

You can test the `upload_file` function using curl or a tool like Postman:

#### Success Case
```bash
curl -X POST \
  -F "file=@/path/to/your/file.pdf" \
  <FUNCTION_URL>/<CASE_ID>
```

Replace `<CASE_ID>` with an actual case ID from a previously created case. Replace `/path/to/your/file.pdf` with the path to the file you want to upload.

Expected response (HTTP 201):
```json
{
  "documentId": "<generated-document-id>",
  "filename": "<generated-filename>",
  "originalFilename": "file.pdf",
  "storagePath": "cases/<case-id>/documents/<generated-filename>",
  "message": "File uploaded successfully"
}
```

#### Not Found Case
```bash
curl -X POST \
  -F "file=@/path/to/your/file.pdf" \
  <FUNCTION_URL>/nonexistent-case-id
```

Expected response (HTTP 404):
```json
{
  "error": "Not Found",
  "message": "Case not found"
}
```

#### Missing File
```bash
curl -X POST \
  <FUNCTION_URL>/<CASE_ID>
```

Expected response (HTTP 400):
```json
{
  "error": "Bad Request",
  "message": "No file uploaded"
}
```

#### Using Postman
For testing with Postman:
1. Set the method to POST
2. Enter the function URL with the case ID
3. Go to the "Body" tab
4. Select "form-data"
5. Add a key named "file" and select "File" from the dropdown
6. Click "Select Files" and choose the file to upload
7. Click Send

### Testing the download_file Function

You can test the `download_file` function using curl or a browser:

#### Success Case
```bash
curl -X GET \
  <FUNCTION_URL>/<DOCUMENT_ID>
```

Replace `<DOCUMENT_ID>` with a document ID returned from a successful file upload.

Expected response (HTTP 200):
```json
{
  "downloadUrl": "<signed-url>",
  "filename": "original-filename.pdf",
  "documentId": "<document-id>",
  "message": "Download URL generated successfully"
}
```

You can then use the `downloadUrl` in a browser to download the file.

#### Not Found Document
```bash
curl -X GET \
  <FUNCTION_URL>/nonexistent-document-id
```

Expected response (HTTP 404):
```json
{
  "error": "Not Found",
  "message": "Document not found"
}
```

#### Missing Document ID
```bash
curl -X GET \
  <FUNCTION_URL>/
```

Expected response (HTTP 400):
```json
{
  "error": "Bad Request",
  "message": "Document ID is required"
}
```

### Verifying File Upload and Download Operations
After uploading a file, you can verify it was stored correctly by:
1. Using the `download_file` function to generate a signed URL and download the file
2. Checking the Firebase Console:
   - Go to the Firebase Console (https://console.firebase.google.com/)
   - Select your project (`relexro`)
   - Navigate to Storage
   - Look for the file at path `cases/<case-id>/documents/<generated-filename>`
   - Verify the file metadata in Firestore's `documents` collection

### Testing Authentication Functions

#### Testing the validate_user Function

You can test the `validate_user` function using curl or a tool like Postman:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  <FUNCTION_URL>
```

Replace `<ID_TOKEN>` with a valid Firebase Authentication ID token.

Expected response (HTTP 200):
```json
{
  "userId": "<user-id>",
  "email": "user@example.com",
  "isValid": true
}
```

#### Without Authentication Token
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  <FUNCTION_URL>
```

Expected response (HTTP 401):
```json
{
  "error": "Unauthorized",
  "message": "No authentication token provided"
}
```

#### With Invalid Token
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid-token" \
  <FUNCTION_URL>
```

Expected response (HTTP 401):
```json
{
  "error": "Unauthorized",
  "message": "Invalid authentication token"
}
```

#### Testing the check_permissions Function

You can test the `check_permissions` function using curl or a tool like Postman:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"resourceType": "case", "resourceId": "<CASE_ID>", "action": "read"}' \
  <FUNCTION_URL>
```

Replace `<ID_TOKEN>` with a valid Firebase Authentication ID token and `<CASE_ID>` with an actual case ID.

Expected response (HTTP 200):
```json
{
  "hasPermission": true
}
```

#### Missing Parameters
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"resourceType": "case"}' \
  <FUNCTION_URL>
```

Expected response (HTTP 400):
```json
{
  "error": "Bad Request",
  "message": "resourceId and action are required"
}
```

#### Testing the get_user_role Function

```bash
curl -X GET \
  -H "Authorization: Bearer <ID_TOKEN>" \
  <FUNCTION_URL>/<BUSINESS_ID>
```

Replace `<ID_TOKEN>` with a valid Firebase Authentication ID token and `<BUSINESS_ID>` with an actual business ID.

Expected response (HTTP 200):
```json
{
  "userId": "<user-id>",
  "businessId": "<business-id>",
  "role": "admin"
}
```

#### User Not in Business
```bash
curl -X GET \
  -H "Authorization: Bearer <ID_TOKEN>" \
  <FUNCTION_URL>/<BUSINESS_ID>
```

Expected response (HTTP 404):
```json
{
  "error": "Not Found",
  "message": "User not found in business"
}
```

### Testing Business Account Management Functions

#### Testing the create_business Function

You can test the `create_business` function using curl or a tool like Postman:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"name": "Test Business", "industry": "Legal", "size": "small"}' \
  <FUNCTION_URL>
```

Replace `<ID_TOKEN>` with a valid Firebase Authentication ID token.

Expected response (HTTP 201):
```json
{
  "businessId": "<generated-id>",
  "message": "Business created successfully"
}
```

#### Validation Failure
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"industry": "Legal"}' \
  <FUNCTION_URL>
```

Expected response (HTTP 400):
```json
{
  "error": "Bad Request",
  "message": "Business name is required"
}
```

#### Testing the get_business Function

```bash
curl -X GET \
  -H "Authorization: Bearer <ID_TOKEN>" \
  <FUNCTION_URL>/<BUSINESS_ID>
```

Replace `<ID_TOKEN>` with a valid Firebase Authentication ID token and `<BUSINESS_ID>` with an actual business ID.

Expected response (HTTP 200):
```json
{
  "businessId": "<business-id>",
  "name": "Test Business",
  "industry": "Legal",
  "size": "small",
  "creationDate": { ... }
}
```

#### Not Found Business
```bash
curl -X GET \
  -H "Authorization: Bearer <ID_TOKEN>" \
  <FUNCTION_URL>/nonexistent-business-id
```

Expected response (HTTP 404):
```json
{
  "error": "Not Found",
  "message": "Business not found"
}
```

#### Testing the add_business_user Function

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"userId": "<USER_ID>", "role": "member"}' \
  <FUNCTION_URL>/<BUSINESS_ID>
```

Replace `<ID_TOKEN>` with a valid Firebase Authentication ID token, `<BUSINESS_ID>` with an actual business ID, and `<USER_ID>` with the ID of the user to add.

Expected response (HTTP 200):
```json
{
  "message": "User added to business successfully"
}
```

#### Testing the set_user_role Function

```bash
curl -X PUT \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"userId": "<USER_ID>", "role": "admin"}' \
  <FUNCTION_URL>/<BUSINESS_ID>
```

Replace `<ID_TOKEN>` with a valid Firebase Authentication ID token, `<BUSINESS_ID>` with an actual business ID, and `<USER_ID>` with the ID of the user whose role should be updated.

Expected response (HTTP 200):
```json
{
  "message": "User role updated successfully"
}
```

### Testing Chat Functions

#### Testing the receive_prompt Function

You can test the `receive_prompt` function using curl or a tool like Postman:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"message": "What is the statute of limitations for personal injury in California?", "conversationId": "<CONVERSATION_ID>"}' \
  <FUNCTION_URL>
```

Replace `<ID_TOKEN>` with a valid Firebase Authentication ID token. The `conversationId` is optional and can be omitted for a new conversation.

Expected response (HTTP 200):
```json
{
  "promptId": "<generated-id>",
  "conversationId": "<conversation-id>",
  "message": "Prompt received successfully"
}
```

#### Testing the send_to_vertex_ai Function

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"prompt": "What is the statute of limitations for personal injury in California?", "conversationId": "<CONVERSATION_ID>"}' \
  <FUNCTION_URL>
```

Replace `<ID_TOKEN>` with a valid Firebase Authentication ID token and `<CONVERSATION_ID>` with an actual conversation ID.

Expected response (HTTP 200):
```json
{
  "responseId": "<generated-id>",
  "response": "In California, the statute of limitations for personal injury claims is generally two years from the date of the injury...",
  "conversationId": "<conversation-id>"
}
```

#### Testing the store_conversation Function

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ID_TOKEN>" \
  -d '{"conversationId": "<CONVERSATION_ID>", "prompt": "What is the statute of limitations for personal injury in California?", "response": "In California, the statute of limitations for personal injury claims is generally two years from the date of the injury..."}' \
  <FUNCTION_URL>
```

Replace `<ID_TOKEN>` with a valid Firebase Authentication ID token and `<CONVERSATION_ID>` with an actual conversation ID.

Expected response (HTTP 200):
```json
{
  "messageId": "<generated-id>",
  "conversationId": "<conversation-id>",
  "message": "Conversation stored successfully"
}
```

Tests will be added in future updates.

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