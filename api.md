# Relex Backend API Documentation

## Base URL
All endpoints are deployed to `https://europe-west3-relexro.cloudfunctions.net/`

## Authentication
All authenticated endpoints require a Firebase ID token in the Authorization header:
```
Authorization: Bearer <firebase_id_token>
```

You can test authentication using the `test-auth.html` utility which provides a simple UI for:
1. Signing in with Google
2. Obtaining an ID token
3. Testing API endpoints with the token

### CORS Support
The authentication endpoints support CORS (Cross-Origin Resource Sharing), allowing them to be called from web applications on different domains. The `validate_user` function specifically handles OPTIONS preflight requests and includes the appropriate CORS headers:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, POST, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Authorization`
- `Access-Control-Max-Age: 3600`

---

## Authentication Functions

### Validate User
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-validate-user`
- **Method**: GET, OPTIONS (for CORS preflight)
- **Description**: Validates a user's authentication token
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Response**: 
  ```json
  {
    "userId": "KLjII3AJP1YMfMZOBd9N6wJg0VU2",
    "email": "user@example.com"
  }
  ```
- **CORS Support**: This endpoint includes CORS headers and supports preflight requests
- **Errors**:
  - 401: Unauthorized (invalid/expired token)
  - 500: Internal server error

### Check Permissions
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-check-permissions`
- **Method**: POST
- **Description**: Checks if a user has permission to perform an action on a resource
- **Request Body**:
  ```json
  {
    "userId": "user123",
    "resourceId": "case456",
    "action": "read",
    "resourceType": "case",
    "organizationId": "organization789" 
  }
  ```
- **Response**:
  ```json
  {
    "allowed": true
  }
  ```
- **Valid Actions**:
  - `read`: View the resource
  - `update`: Edit the resource
  - `delete`: Delete or archive the resource
  - `upload_file`: Upload files to the resource
  - `manage_access`: Manage who has access to the resource
- **Permission Rules**:
  - **For Case Resources**:
    - Case owners have full access to all actions
    - Organization administrators have full access to cases in their organization
    - Organization staff members can `read`, `update`, and `upload_file` to cases in their organization
    - Staff members cannot `delete` or `manage_access` to cases
  - **For Organization Resources** (where `resourceId` is the `organizationId`):
    - Organization administrators have full access to organization resources
    - Organization staff members can only `read` organization information
- **Parameters**:
  - `userId` (required): The ID of the user requesting access
  - `resourceId` (required): The ID of the resource being accessed
  - `action` (required): The action being performed on the resource
  - `resourceType` (optional, default: "case"): The type of resource being accessed
  - `organizationId` (optional): The ID of the organization the resource belongs to (for cases)
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 500: Internal server error

### Get User Role
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-get-user-role`
- **Method**: POST
- **Description**: Gets a user's role in an organization
- **Request Body**:
  ```json
  {
    "userId": "user123",
    "organizationId": "organization456"
  }
  ```
- **Response**:
  ```json
  {
    "role": "admin" 
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 404: Not Found (user not in organization)
  - 500: Internal server error

---

## Organization Functions

### Create Organization
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-create-organization`
- **Method**: POST
- **Description**: Creates a new organization account
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "name": "Organization Name",
    "type": "law_firm",
    "address": "123 Organization St",
    "phone": "+40721234567",
    "email": "organization@example.com"
  }
  ```
- **Response**:
  ```json
  {
    "organizationId": "organization123",
    "name": "Organization Name",
    "type": "law_firm",
    "address": "123 Organization St",
    "phone": "+40721234567",
    "email": "organization@example.com",
    "createdAt": "2023-10-15T10:30:00Z",
    "ownerId": "user123"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 500: Internal server error

### Get Organization
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-get-organization`
- **Method**: GET
- **Description**: Retrieves an organization by ID
- **Query Parameters**:
  - `organizationId`: ID of the organization to retrieve
- **Response**:
  ```json
  {
    "organizationId": "organization123",
    "name": "Organization Name",
    "type": "law_firm",
    "address": "123 Organization St",
    "phone": "+40721234567",
    "email": "organization@example.com",
    "createdAt": "2023-10-15T10:30:00Z",
    "ownerId": "user123"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing organizationId)
  - 404: Not Found
  - 500: Internal server error

### Add Organization User
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-add-organization-user`
- **Method**: POST
- **Description**: Adds a user to an organization
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "organizationId": "organization123",
    "userId": "user456",
    "role": "member"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "userId": "user456",
    "organizationId": "organization123",
    "role": "member"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 403: Forbidden (no permissions)
  - 500: Internal server error

### Set User Role
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-set-user-role`
- **Method**: POST
- **Description**: Updates a user's role in an organization
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "organizationId": "organization123",
    "userId": "user456",
    "role": "admin"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "userId": "user456",
    "organizationId": "organization123",
    "role": "admin"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 403: Forbidden (no permissions)
  - 500: Internal server error

### Update Organization
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-update-organization`
- **Method**: POST
- **Description**: Updates an organization account
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "organizationId": "organization123",
    "name": "Updated Organization Name",
    "address": "456 New Address Ave",
    "phone": "+40723456789"
  }
  ```
- **Response**:
  ```json
  {
    "organizationId": "organization123",
    "name": "Updated Organization Name",
    "type": "law_firm",
    "address": "456 New Address Ave",
    "phone": "+40723456789",
    "email": "organization@example.com",
    "updatedAt": "2023-10-16T14:45:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 403: Forbidden (no permissions)
  - 500: Internal server error

### List Organization Users
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-list-organization-users`
- **Method**: GET
- **Description**: Lists users in an organization
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Query Parameters**:
  - `organizationId`: ID of the organization
- **Response**:
  ```json
  {
    "users": [
      {
        "userId": "user123",
        "email": "owner@example.com",
        "role": "admin"
      },
      {
        "userId": "user456",
        "email": "member@example.com",
        "role": "member"
      }
    ]
  }
  ```
- **Errors**:
  - 400: Bad Request (missing organizationId)
  - 401: Unauthorized
  - 403: Forbidden (no permissions)
  - 500: Internal server error

### Remove Organization User
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-remove-organization-user`
- **Method**: POST
- **Description**: Removes a user from an organization
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "organizationId": "organization123",
    "userId": "user456"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "userId": "user456",
    "organizationId": "organization123"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 403: Forbidden (no permissions)
  - 500: Internal server error

---

## Organization Membership Functions

### Add Organization Member
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-add-organization-member`
- **Method**: POST
- **Description**: Adds a member to an organization
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "organizationId": "organization123",
    "userId": "user456",
    "role": "staff"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "membershipId": "membership789",
    "userId": "user456",
    "organizationId": "organization123",
    "role": "staff",
    "email": "user@example.com",
    "displayName": "User Name"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 403: Forbidden (no permissions)
  - 404: Not Found (organization not found)
  - 409: Conflict (user already a member)
  - 500: Internal server error

### Set Organization Member Role
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-set-organization-member-role`
- **Method**: POST
- **Description**: Updates a member's role in an organization
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "organizationId": "organization123",
    "userId": "user456",
    "newRole": "administrator"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "membershipId": "membership789",
    "userId": "user456",
    "organizationId": "organization123",
    "role": "administrator",
    "email": "user@example.com",
    "displayName": "User Name"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 403: Forbidden (no permissions or attempting to change last administrator)
  - 404: Not Found (organization or membership not found)
  - 500: Internal server error

### List Organization Members
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-list-organization-members`
- **Method**: GET
- **Description**: Lists all members of an organization
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Query Parameters**:
  - `organizationId`: ID of the organization
- **Response**:
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
- **Errors**:
  - 400: Bad Request (missing organizationId)
  - 401: Unauthorized
  - 403: Forbidden (not a member of organization)
  - 404: Not Found (organization not found)
  - 500: Internal server error

### Remove Organization Member
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-remove-organization-member`
- **Method**: POST
- **Description**: Removes a member from an organization
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "organizationId": "organization123",
    "userId": "user456"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "userId": "user456",
    "organizationId": "organization123"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters or attempting to remove self)
  - 401: Unauthorized
  - 403: Forbidden (no administrator permissions or attempting to remove last administrator)
  - 404: Not Found (organization or membership not found)
  - 500: Internal server error

### Get User Organization Role
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-get-user-organization-role`
- **Method**: POST
- **Description**: Gets a user's role in a specific organization
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "userId": "user456",
    "organizationId": "organization123"
  }
  ```
- **Response**:
  ```json
  {
    "role": "staff"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 404: Not Found (organization not found or user not a member)
  - 500: Internal server error

---

## Case Functions

### Create Case
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-create-case`
- **Method**: POST
- **Description**: Creates a new case
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "title": "Case Title",
    "description": "Case description",
    "caseType": "legal_advice",
    "organizationId": "organization123" 
  }
  ```
- **Response**:
  ```json
  {
    "caseId": "case789",
    "title": "Case Title",
    "description": "Case description",
    "caseType": "legal_advice",
    "userId": "user123",
    "organizationId": "organization123",
    "status": "active",
    "createdAt": "2023-10-16T15:30:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 500: Internal server error

### Get Case
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-get-case`
- **Method**: GET
- **Description**: Retrieves a case by ID
- **Query Parameters**:
  - `caseId`: ID of the case to retrieve
- **Response**:
  ```json
  {
    "caseId": "case789",
    "title": "Case Title",
    "description": "Case description",
    "caseType": "legal_advice",
    "userId": "user123",
    "organizationId": "organization123",
    "status": "active",
    "createdAt": "2023-10-16T15:30:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing caseId)
  - 404: Not Found
  - 500: Internal server error

### List Cases
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-list-cases`
- **Method**: GET
- **Description**: Lists cases
- **Query Parameters**:
  - `userId`: (optional) Filter by user ID
  - `organizationId`: (optional) Filter by organization ID
  - `status`: (optional) Filter by status
  - `limit`: (optional) Maximum number of cases to return
- **Response**:
  ```json
  {
    "cases": [
      {
        "caseId": "case789",
        "title": "Case Title",
        "description": "Case description",
        "caseType": "legal_advice",
        "userId": "user123",
        "organizationId": "organization123",
        "status": "active",
        "createdAt": "2023-10-16T15:30:00Z"
      }
    ]
  }
  ```
- **Errors**:
  - 500: Internal server error

### Archive Case
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-archive-case`
- **Method**: POST
- **Description**: Archives a case
- **Request Body**:
  ```json
  {
    "caseId": "case789"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "caseId": "case789",
    "status": "archived",
    "archivedAt": "2023-10-17T09:15:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing caseId)
  - 404: Not Found
  - 500: Internal server error

### Delete Case
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-delete-case`
- **Method**: POST
- **Description**: Marks a case as deleted
- **Request Body**:
  ```json
  {
    "caseId": "case789"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "caseId": "case789",
    "status": "deleted",
    "deletedAt": "2023-10-17T10:00:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing caseId)
  - 404: Not Found
  - 500: Internal server error

---

## File Functions

### Upload File
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-upload-file`
- **Method**: POST
- **Description**: Uploads a file to a case
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
  - `Content-Type: multipart/form-data`
- **Form Data**:
  - `file`: The file to upload
  - `caseId`: ID of the case
  - `fileName`: (optional) Custom file name
- **Response**:
  ```json
  {
    "success": true,
    "fileId": "file123",
    "fileName": "document.pdf",
    "fileUrl": "https://storage.googleapis.com/relexro.appspot.com/files/case789/document.pdf",
    "caseId": "case789",
    "uploadedAt": "2023-10-17T11:30:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing file or caseId)
  - 401: Unauthorized
  - 500: Internal server error

### Download File
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-download-file`
- **Method**: GET
- **Description**: Downloads a file
- **Query Parameters**:
  - `fileId`: ID of the file to download
- **Response**: The file content with appropriate Content-Type header
- **Errors**:
  - 400: Bad Request (missing fileId)
  - 404: Not Found
  - 500: Internal server error

---

## Chat Functions

### Receive Prompt
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-receive-prompt`
- **Method**: POST
- **Description**: Receives a prompt from the user
- **Request Body**:
  ```json
  {
    "userId": "user123",
    "caseId": "case789",
    "prompt": "What is the legal status of my case?",
    "conversationId": "conv456"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "promptId": "prompt123",
    "userId": "user123",
    "caseId": "case789",
    "conversationId": "conv456",
    "receivedAt": "2023-10-17T13:00:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 500: Internal server error

### Send to Vertex AI
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-send-to-vertex-ai`
- **Method**: POST
- **Description**: Sends a prompt to Vertex AI
- **Request Body**:
  ```json
  {
    "prompt": "What is the legal status of my case?",
    "context": "This is a legal case about...",
    "conversationId": "conv456"
  }
  ```
- **Response**:
  ```json
  {
    "response": "Based on the information provided, your case is...",
    "promptId": "prompt123",
    "conversationId": "conv456",
    "processedAt": "2023-10-17T13:01:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 500: Internal server error

### Store Conversation
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-store-conversation`
- **Method**: POST
- **Description**: Stores a conversation
- **Request Body**:
  ```json
  {
    "userId": "user123",
    "caseId": "case789",
    "prompt": "What is the legal status of my case?",
    "response": "Based on the information provided, your case is...",
    "conversationId": "conv456"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "conversationId": "conv456",
    "messageId": "msg789",
    "storedAt": "2023-10-17T13:02:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 500: Internal server error

### Enrich Prompt
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-enrich-prompt`
- **Method**: POST
- **Description**: Enriches a prompt with context
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "prompt": "What is the legal status of my case?",
    "caseId": "case789",
    "conversationId": "conv456"
  }
  ```
- **Response**:
  ```json
  {
    "enrichedPrompt": "What is the legal status of my case? [Context: This is a legal case about...]",
    "prompt": "What is the legal status of my case?",
    "caseId": "case789",
    "conversationId": "conv456",
    "context": "This is a legal case about..."
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 500: Internal server error

---

## Payment Functions

### Create Payment Intent
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-create-payment-intent`
- **Method**: POST
- **Description**: Creates a Stripe Payment Intent
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "amount": 5000,
    "currency": "usd",
    "caseId": "case789",
    "description": "Payment for legal consultation"
  }
  ```
- **Response**:
  ```json
  {
    "clientSecret": "pi_1234_secret_5678",
    "amount": 5000,
    "currency": "usd",
    "paymentIntentId": "pi_1234",
    "caseId": "case789",
    "createdAt": "2023-10-17T14:30:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 500: Internal server error

### Create Checkout Session
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-create-checkout-session`
- **Method**: POST
- **Description**: Creates a Stripe Checkout Session
- **Headers**: 
  - `Authorization: Bearer <firebase_id_token>`
- **Request Body**:
  ```json
  {
    "priceId": "price_1234",
    "successUrl": "https://example.com/success",
    "cancelUrl": "https://example.com/cancel",
    "caseId": "case789"
  }
  ```
- **Response**:
  ```json
  {
    "sessionId": "cs_1234",
    "url": "https://checkout.stripe.com/c/pay/cs_1234",
    "caseId": "case789",
    "createdAt": "2023-10-17T15:00:00Z"
  }
  ```
- **Errors**:
  - 400: Bad Request (missing parameters)
  - 401: Unauthorized
  - 500: Internal server error

---

## Test Function

### Test Function
- **URL**: `https://europe-west3-relexro.cloudfunctions.net/relex-backend-test-function`
- **Method**: GET
- **Description**: Test function to verify deployment
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Test function is working!"
  }
  ```
- **Errors**:
  - 500: Internal server error

---

## Testing Authentication with test-auth.html

1. Open the `test-auth.html` file in a local web server:
   ```bash
   python3 -m http.server 8000
   ```

2. Visit `http://localhost:8000/test-auth.html` in your browser

3. Click "Sign in with Google" and complete the authentication flow

4. Once authenticated, you'll see your user ID and can access your ID token

5. Enter any API endpoint URL in the test section and click "Test API with Token" to make an authenticated request

6. The API response will be displayed in the response section 