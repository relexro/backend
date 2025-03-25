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

Tests will be added in future updates. 