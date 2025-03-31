# Relex Backend API Documentation

## Base URL
All endpoints are deployed to `https://api.relex.ro/v1`

> **Note:** The custom domain is configured as a direct CNAME to the API Gateway (unproxied), allowing for direct connections to Google Cloud without Cloudflare intermediation.

## Authentication
All endpoints require Firebase Authentication. Include the ID token in the Authorization header:
```
Authorization: Bearer <firebase_id_token>
```

### Firebase Authentication Setup
1. Initialize Firebase in your client application:
```javascript
const firebaseConfig = {
  apiKey: "your-api-key",
  authDomain: "relexro.firebaseapp.com",
  projectId: "relexro"
};
firebase.initializeApp(firebaseConfig);
```

2. Sign in users using Firebase Authentication methods:
```javascript
// Example with Google (only authentication method in MVP)
const provider = new firebase.auth.GoogleAuthProvider();
await firebase.auth().signInWithPopup(provider);
```

3. Get the ID token for API calls:
```javascript
const user = firebase.auth().currentUser;
const idToken = await user.getIdToken();
```

## API Gateway Structure

The API is organized into the following groups:

### Authentication
- `GET /v1/auth/validate-user`
- `POST /v1/auth/check-permissions`
- `GET /v1/auth/user-role`

### User Management
- `GET /v1/users/me`
- `PUT /v1/users/me`
- `GET /v1/users/me/organizations`
- `GET /v1/users/me/cases`

### Organization Management
- `POST /v1/organizations`
- `GET /v1/organizations/{organizationId}`
- `PUT /v1/organizations/{organizationId}`
- `DELETE /v1/organizations/{organizationId}` (requires admin role, no active subscription)

### Organization Membership
- `POST /v1/organizations/{organizationId}/members` (uses relex-backend-add-organization-member function)
- `GET /v1/organizations/{organizationId}/members` (uses relex-backend-list-organization-members function)
- `PUT /v1/organizations/{organizationId}/members/{userId}` (uses relex-backend-set-organization-member-role function)
- `DELETE /v1/organizations/{organizationId}/members/{userId}` (uses relex-backend-remove-organization-member function)

### Organization Membership Details

#### Add Member to Organization
- **Method**: POST
- **Path**: `/v1/organizations/{organizationId}/members`
- **Description**: Adds a new member to an organization with a specific role. Only administrators can add members. Internally uses the `relex-backend-add-organization-member` function.
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "userId": "string",
    "role": "staff|administrator"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "membershipId": "string",
    "userId": "string",
    "organizationId": "string",
    "role": "staff|administrator",
    "email": "string",
    "displayName": "string"
  }
  ```
- **Error Responses**:
  - 400: Invalid request (missing fields or validation errors)
  - 401: Unauthorized (invalid token)
  - 403: Forbidden (caller is not an administrator)
  - 404: Organization not found
  - 409: User is already a member
  - 500: Server error

#### List Organization Members
- **Method**: GET
- **Path**: `/v1/organizations/{organizationId}/members`
- **Description**: Lists all members of an organization. Accessible by organization members. Internally uses the `relex-backend-list-organization-members` function.
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Response**:
  ```json
  {
    "members": [
      {
        "userId": "string",
        "role": "administrator|staff",
        "addedAt": "2023-04-01T00:00:00Z",
        "email": "string",
        "displayName": "string"
      }
    ]
  }
  ```
- **Error Responses**:
  - 401: Unauthorized (invalid token)
  - 403: Forbidden (not a member of the organization)
  - 404: Organization not found
  - 500: Server error

#### Update Member Role
- **Method**: PUT
- **Path**: `/v1/organizations/{organizationId}/members/{userId}`
- **Description**: Updates a member's role in the organization. Only administrators can update roles. Internally uses the `relex-backend-set-organization-member-role` function.
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "newRole": "staff|administrator"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "membershipId": "string",
    "userId": "string",
    "organizationId": "string",
    "role": "staff|administrator",
    "email": "string",
    "displayName": "string"
  }
  ```
- **Error Responses**:
  - 400: Invalid request (missing fields or validation errors)
  - 401: Unauthorized (invalid token)
  - 403: Forbidden (caller is not an administrator)
  - 404: Member or organization not found
  - 500: Server error

#### Remove Member
- **Method**: DELETE
- **Path**: `/v1/organizations/{organizationId}/members/{userId}`
- **Description**: Removes a member from an organization. Only administrators can remove members. Internally uses the `relex-backend-remove-organization-member` function.
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Response**:
  ```json
  {
    "success": true,
    "userId": "string",
    "organizationId": "string"
  }
  ```
- **Error Responses**:
  - 401: Unauthorized (invalid token)
  - 403: Forbidden (caller is not an administrator)
  - 404: Member or organization not found
  - 500: Server error

### Cases
- `POST /v1/cases` (individual cases)
- `POST /v1/organizations/{organizationId}/cases` (organization cases)
- `GET /v1/cases/{caseId}`
- `GET /v1/users/me/cases` (list individual cases)
- `GET /v1/organizations/{organizationId}/cases` (list organization cases)
- `POST /v1/cases/{caseId}/archive`
- `DELETE /v1/cases/{caseId}`
- `PUT /v1/cases/{caseId}/assign` (assign case to staff - for Organization Admin only) (PLANNED - not yet implemented)

### Party Management
- `POST /v1/parties` (create a new party)
- `GET /v1/parties/{partyId}` (get a party by ID)
- `PUT /v1/parties/{partyId}` (update a party)
- `DELETE /v1/parties/{partyId}` (delete a party)
- `GET /v1/parties` (list all parties for the authenticated user)
- `POST /v1/cases/{caseId}/parties` (attach a party to a case)
- `DELETE /v1/cases/{caseId}/parties/{partyId}` (detach a party from a case)

### Files
- `POST /v1/cases/{caseId}/files` (upload a file to a case)
- `GET /v1/files/{fileId}` (download a file)

### Chat
- `POST /v1/cases/{caseId}/messages` (send a message in the case chat)
- `GET /v1/cases/{caseId}/messages` (get chat history for a case)
- `POST /v1/cases/{caseId}/enrich-prompt` (enrich a prompt with case context)
- `POST /v1/cases/{caseId}/send-to-vertex` (send a prompt to Vertex AI)

### Payments
- `POST /v1/payments/payment-intent` (create payment intent)
- `POST /v1/payments/checkout-session` (create checkout session)
- `DELETE /v1/subscriptions/{subscriptionId}` (cancel subscription)
- `POST /v1/payments/webhook` (handle Stripe webhooks)
- `POST /v1/vouchers/redeem` (redeem a voucher code) (PLANNED - not yet implemented)

## Detailed Endpoints

### Authentication

#### Validate User
- **Method**: GET
- **Path**: `/v1/auth/validate-user`
- **Description**: Validates user's authentication token
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Response**:
  ```json
  {
    "userId": "string",
    "email": "string",
    "isValid": true
  }
  ```

#### Check Permissions
- **Method**: POST
- **Path**: `/v1/auth/check-permissions`
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "resourceType": "case|organization|party|document",
    "resourceId": "string",
    "action": "read|update|delete|archive|upload_file|download_file|attach_party|detach_party|assign_case|manage_members|create_case|list_cases",
    "organizationId": "string" // Optional, only needed for certain organization actions
  }
  ```
- **Description**: Validates if the authenticated user has permission to perform a specific action on a resource. The system uses resource-specific permission checkers based on the resourceType:
  - **case**: Checks ownership, organization membership, and staff assignment status
  - **organization**: Checks membership role (administrator or staff)
  - **party**: Checks direct ownership (only the creator can manage their parties)
  - **document**: Maps to parent case permissions (document access follows case access)

- **Response**:
  ```json
  {
    "allowed": true
  }
  ```

- **Error Responses**:
  - 400: Invalid request (missing fields or validation errors)
  - 401: Unauthorized (invalid token)
  - 404: Resource not found
  - 500: Server error

#### Get User Role
- **Method**: GET
- **Path**: `/v1/auth/user-role`
- **Description**: Gets the user's role within an organization
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Query Parameters**:
  - `organizationId`: The ID of the organization
- **Response**:
  ```json
  {
    "role": "admin|staff|none"
  }
  ```

### User Management

#### Get User Profile
- **Method**: GET
- **Path**: `/v1/users/me`
- **Description**: Get the authenticated user's profile
- **Response**:
  ```json
  {
    "userId": "string",
    "email": "string",
    "displayName": "string",
    "photoURL": "string",
    "role": "user|admin",
    "subscriptionStatus": "active|inactive",
    "subscriptionPlanId": "string",
    "billingCycleStart": "2023-04-01T00:00:00Z",
    "billingCycleEnd": "2023-05-01T00:00:00Z",
    "caseQuotaTotal": {
      "tier1": 5,
      "tier2": 2,
      "tier3": 1
    },
    "caseQuotaUsed": {
      "tier1": 3,
      "tier2": 1,
      "tier3": 0
    },
    "stripeCustomerId": "string",
    "stripeSubscriptionId": "string",
    "languagePreference": "en|ro",
    "voucherBalance": 0,
    "createdAt": "string",
    "updatedAt": "string"
  }
  ```

#### Update User Profile
- **Method**: PUT
- **Path**: `/v1/users/me`
- **Description**: Update the authenticated user's profile
- **Body**:
  ```json
  {
    "displayName": "string",
    "photoURL": "string",
    "languagePreference": "en|ro"
  }
  ```
- **Response**: Same as Get User Profile

#### List User's Organizations
- **Method**: GET
- **Path**: `/v1/users/me/organizations`
- **Description**: List organizations the user is a member of
- **Response**:
  ```json
  {
    "organizations": [
      {
        "organizationId": "string",
        "name": "string",
        "type": "law_firm|corporate|individual",
        "role": "admin|staff"
      }
    ]
  }
  ```

### Organization Management

#### Create Organization
- **Method**: POST
- **Path**: `/v1/organizations`
- **Body**:
  ```json
  {
    "name": "string",
    "type": "law_firm|corporate|individual",
    "address": "string",
    "phone": "string",
    "email": "string"
  }
  ```
- **Response**:
  ```json
  {
    "organizationId": "string",
    "name": "string",
    "type": "string",
    "createdAt": "string",
    "subscriptionStatus": "inactive"
  }
  ```

#### Get Organization
- **Method**: GET
- **Path**: `/v1/organizations/{organizationId}`
- **Description**: Get organization details
- **Response**:
  ```json
  {
    "organizationId": "string",
    "name": "string",
    "type": "law_firm|corporate|individual",
    "address": "string",
    "phone": "string",
    "email": "string",
    "subscriptionStatus": "active|inactive",
    "subscriptionPlanId": "string",
    "billingCycleStart": "2023-04-01T00:00:00Z",
    "billingCycleEnd": "2023-05-01T00:00:00Z",
    "caseQuotaTotal": {
      "tier1": 20,
      "tier2": 10,
      "tier3": 5
    },
    "caseQuotaUsed": {
      "tier1": 10,
      "tier2": 5,
      "tier3": 2
    },
    "stripeCustomerId": "string",
    "stripeSubscriptionId": "string",
    "createdAt": "string",
    "updatedAt": "string",
    "createdBy": "string"
  }
  ```

#### Update Organization
- **Method**: PUT
- **Path**: `/v1/organizations/{organizationId}`
- **Description**: Update organization details (requires admin role)
- **Body**:
  ```json
  {
    "name": "string",
    "type": "law_firm|corporate|individual",
    "address": "string",
    "phone": "string",
    "email": "string"
  }
  ```
- **Response**: Same as Get Organization

#### Delete Organization
- **Method**: DELETE
- **Path**: `/v1/organizations/{organizationId}`
- **Description**: Delete an organization and all its related data. Only administrators can delete organizations, and the organization must not have an active subscription.
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "organizationId": "string"
  }
  ```
- **Response**:
  ```json
  {
    "message": "Organization deleted successfully"
  }
  ```
- **Error Responses**:
  - 400: Bad Request (e.g., organization has active subscription)
  - 401: Unauthorized (invalid token)
  - 403: Forbidden (not an administrator)
  - 404: Organization not found
  - 500: Server error

### Cases

#### Create Individual Case
- **Method**: POST
- **Path**: `/v1/cases`
- **Description**: Create a new case as an individual. The system first checks if the user has an active subscription with available quota. If quota is available, the case is created using the quota. If quota is exhausted or no active subscription exists, a `paymentIntentId` is required.
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "title": "string",
    "description": "string",
    "caseTier": 1, // 1, 2, or 3 - REQUIRED
    "paymentIntentId": "string", // OPTIONAL if user has subscription with quota
    "initialPartyIds": ["string"] // OPTIONAL array of party IDs to attach initially
  }
  ```
- **Response**:
  ```json
  {
    "caseId": "string",
    "title": "string",
    "status": "open",
    "createdAt": "string",
    "paymentStatus": "covered_by_quota", // or "paid_intent" if using payment
    "caseTier": 1,
    "casePrice": 900,
    "parties": [
      {
        "partyId": "string",
        "nameDisplay": "string" // Composite name based on party type
      }
    ]
  }
  ```
- **Errors**:
  - `402 Payment Required`: Returned when quota is exhausted and no payment intent is provided
  - `400 Bad Request`: Missing required fields or invalid data
  - `401 Unauthorized`: Authentication error

#### Create Organization Case
- **Method**: POST
- **Path**: `/v1/organizations/{organizationId}/cases`
- **Description**: Create a new case for an organization. The system first checks if the organization has an active subscription with available quota. If quota is available, the case is created using the quota. If quota is exhausted or no active subscription exists, a `paymentIntentId` is required.
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "title": "string",
    "description": "string",
    "caseTier": 1, // 1, 2, or 3 - REQUIRED
    "paymentIntentId": "string", // OPTIONAL if organization has subscription with quota
    "initialPartyIds": ["string"], // OPTIONAL array of party IDs to attach initially
    "assignedUserId": "string" // OPTIONAL staff user ID to assign the case to
  }
  ```
- **Response**:
  ```json
  {
    "caseId": "string",
    "title": "string",
    "status": "open",
    "createdAt": "string",
    "paymentStatus": "covered_by_quota", // or "paid_intent" if using payment
    "caseTier": 1,
    "casePrice": 900,
    "organizationId": "string",
    "assignedUserId": "string",
    "parties": [
      {
        "partyId": "string",
        "nameDisplay": "string" // Composite name based on party type
      }
    ]
  }
  ```
- **Errors**:
  - `402 Payment Required`: Returned when quota is exhausted and no payment intent is provided
  - `403 Forbidden`: User doesn't have permission to create cases for this organization
  - `400 Bad Request`: Missing required fields or invalid data
  - `401 Unauthorized`: Authentication error

#### List Individual Cases
- **Method**: GET
- **Path**: `/v1/users/me/cases`
- **Query Parameters**:
  - `status`: open|archived|deleted (default: open)
  - `limit`: number (default: 20)
  - `offset`: number (default: 0)
  - `labelIds`: Array of label IDs to filter by
- **Response**:
  ```json
  {
    "cases": [
      {
        "caseId": "string",
        "title": "string",
        "status": "string",
        "createdAt": "string",
        "paymentStatus": "covered_by_quota", // or "paid_intent"
        "caseTier": 1,
        "labels": [
          {
            "labelId": "string",
            "name": "string",
            "color": "string"
          }
        ],
        "parties": [
          {
            "partyId": "string",
            "nameDisplay": "string"
          }
        ]
      }
    ],
    "total": 25,
    "limit": 20,
    "offset": 0
  }
  ```

#### List Organization Cases
- **Method**: GET
- **Path**: `/v1/organizations/{organizationId}/cases`
- **Query Parameters**:
  - `status`: open|archived|deleted (default: open)
  - `limit`: number (default: 20)
  - `offset`: number (default: 0)
  - `labelIds`: Array of label IDs to filter by
  - `assignedUserId`: Filter by assigned staff member (admin only)
- **Response**:
  ```json
  {
    "cases": [
      {
        "caseId": "string",
        "title": "string",
        "status": "string",
        "createdAt": "string",
        "paymentStatus": "covered_by_quota", // or "paid_intent"
        "caseTier": 1,
        "assignedUserId": "string",
        "assignedUserName": "string",
        "labels": [
          {
            "labelId": "string",
            "name": "string",
            "color": "string"
          }
        ],
        "parties": [
          {
            "partyId": "string",
            "nameDisplay": "string"
          }
        ]
      }
    ],
    "total": 25,
    "limit": 20,
    "offset": 0
  }
  ```

#### Get Case
- **Method**: GET
- **Path**: `/v1/cases/{caseId}`
- **Description**: Get details of a specific case
- **Response**:
  ```json
  {
    "caseId": "string",
    "title": "string",
    "description": "string",
    "status": "open|archived|deleted",
    "createdAt": "string",
    "updatedAt": "string",
    "archivedAt": "string",
    "caseTier": 1,
    "paymentStatus": "covered_by_quota|paid_intent",
    "userId": "string",
    "organizationId": "string",
    "assignedUserId": "string",
    "assignedUserName": "string",
    "parties": [
      {
        "partyId": "string",
        "partyType": "individual|organization",
        "nameDetails": {
          // For individual parties
          "firstName": "string",
          "lastName": "string",
          
          // For organization parties
          "companyName": "string"
        },
        "contactInfo": {
          "address": "string",
          "email": "string",
          "phone": "string"
        }
      }
    ],
    "documents": [
      {
        "documentId": "string",
        "fileName": "string",
        "fileSize": 1024,
        "fileType": "string",
        "uploadedAt": "string",
        "uploadedBy": "string"
      }
    ],
    "labels": [
      {
        "labelId": "string",
        "name": "string",
        "color": "string"
      }
    ]
  }
  ```

#### Archive Case
- **Method**: POST
- **Path**: `/v1/cases/{caseId}/archive`
- **Description**: Archive a case (sets status to "archived")
- **Response**:
  ```json
  {
    "success": true,
    "message": "Case archived successfully",
    "caseId": "string",
    "status": "archived",
    "archivedAt": "string"
  }
  ```

#### Delete Case
- **Method**: DELETE
- **Path**: `/v1/cases/{caseId}`
- **Description**: Delete a case (soft delete - sets status to "deleted")
- **Response**:
  ```json
  {
    "success": true,
    "message": "Case deleted successfully"
  }
  ```

#### Assign Case
- **Method**: PUT
- **Path**: `/v1/cases/{caseId}/assign`
- **Description**: Assign a case to a staff member (organization admin only). This is a planned feature that is not yet implemented. Currently returns a 501 Not Implemented response. The function stub exists in the codebase as `relex_backend_assign_case`.
- **Body**:
  ```json
  {
    "assignedUserId": "string" // Staff user ID to assign case to, null to unassign
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Case assigned successfully",
    "caseId": "string",
    "assignedUserId": "string",
    "assignedUserName": "string"
  }
  ```

### Party Management

#### Create Party
- **Method**: POST
- **Path**: `/v1/parties`
- **Description**: Creates a new party with type-specific validation
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "partyType": "individual", // REQUIRED: "individual" or "organization"
    "nameDetails": {
      // For individual parties:
      "firstName": "John", // REQUIRED for individuals
      "lastName": "Doe",   // REQUIRED for individuals
      
      // For organization parties:
      "companyName": "Acme Inc" // REQUIRED for organizations
    },
    "identityCodes": {
      // For individual parties:
      "cnp": "1234567890123", // REQUIRED for individuals (13 digits)
      
      // For organization parties:
      "cui": "RO12345678", // REQUIRED for organizations 
      "regCom": "J12/345/2022" // REQUIRED for organizations
    },
    "contactInfo": {
      "address": "123 Main St", // REQUIRED for all party types
      "email": "contact@example.com", // Optional
      "phone": "+401234567" // Optional
    },
    "signatureData": { // Optional
      "storagePath": "signatures/party_signature.png"
    }
  }
  ```
- **Response**:
  ```json
  {
    "partyId": "string",
    "userId": "string",
    "partyType": "individual",
    "nameDetails": {
      "firstName": "John",
      "lastName": "Doe"
    },
    "identityCodes": {
      "cnp": "1234567890123"
    },
    "contactInfo": {
      "address": "123 Main St",
      "email": "contact@example.com",
      "phone": "+401234567"
    },
    "signatureData": {
      "storagePath": "signatures/party_signature.png",
      "capturedAt": "2023-10-20T14:30:00Z"
    },
    "createdAt": "2023-10-20T14:30:00Z",
    "updatedAt": "2023-10-20T14:30:00Z"
  }
  ```

#### Get Party
- **Method**: GET
- **Path**: `/v1/parties/{partyId}`
- **Description**: Retrieves a party by ID (requires ownership)
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Response**: Same as Create Party response

#### Update Party
- **Method**: PUT
- **Path**: `/v1/parties/{partyId}`
- **Description**: Updates a party with type-specific validation based on existing partyType (partyType itself cannot be changed)
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "nameDetails": {
      // For updating individual parties - cannot add companyName to individuals
      "firstName": "John",
      "lastName": "Smith"
      
      // For updating organization parties - cannot add firstName/lastName to organizations
      //"companyName": "Acme Corporation"
    },
    "identityCodes": {
      // Fields must match existing partyType
      "cnp": "1234567890123" // Only valid for individual parties
      //"cui": "RO87654321",  // Only valid for organization parties
      //"regCom": "J12/999/2022" // Only valid for organization parties
    },
    "contactInfo": {
      "address": "456 New St",
      "email": "new@example.com",
      "phone": "+40987654321"
    }
  }
  ```
- **Response**: Updated party object similar to Create Party response

#### Delete Party
- **Method**: DELETE
- **Path**: `/v1/parties/{partyId}`
- **Description**: Deletes a party (requires ownership, fails if party is attached to any cases)
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Response**: Status 204 No Content

#### List Parties
- **Method**: GET
- **Path**: `/v1/parties`
- **Query Parameters**:
  - `partyType`: Filter by party type (`individual` or `organization`)
- **Description**: Lists parties owned by the authenticated user
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Response**:
  ```json
  {
    "parties": [
      {
        "partyId": "string",
        "partyType": "individual",
        "nameDetails": { /* ... */ },
        "identityCodes": { /* ... */ },
        "contactInfo": { /* ... */ },
        "createdAt": "2023-10-20T14:30:00Z",
        "updatedAt": "2023-10-20T14:30:00Z"
      }
    ]
  }
  ```

#### Attach Party to Case
- **Method**: POST
- **Path**: `/v1/cases/{caseId}/parties`
- **Description**: Attaches an existing party to a case
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "partyId": "string" // REQUIRED
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Party successfully attached to case",
    "caseId": "string",
    "partyId": "string"
  }
  ```

#### Detach Party from Case
- **Method**: DELETE
- **Path**: `/v1/cases/{caseId}/parties/{partyId}`
- **Description**: Removes a party from a case
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Party successfully detached from case",
    "caseId": "string",
    "partyId": "string"
  }
  ```

### Files

#### Upload File
- **Method**: POST
- **Path**: `/v1/cases/{caseId}/files`
- **Body**: multipart/form-data
  - `file`: File
  - `fileName`: string
- **Description**: Uploads a file to a case. Limited to 10MB per file. Total storage per case is limited to 2GB.
- **Response**:
  ```json
  {
    "fileId": "string",
    "fileName": "string",
    "fileUrl": "string",
    "fileSize": 1024,
    "fileType": "string",
    "uploadedAt": "string"
  }
  ```
- **Errors**:
  - `400 Bad Request`: File too large or invalid format
  - `403 Forbidden`: Storage limit exceeded for the case
  - `401 Unauthorized`: Authentication error

#### Download File
- **Method**: GET
- **Path**: `/v1/files/{fileId}`
- **Response**: File content (application/octet-stream)

### Chat

#### Send Chat Message
- **Method**: POST
- **Path**: `/v1/cases/{caseId}/messages`
- **Description**: Send a message in the case chat
- **Body**:
  ```json
  {
    "content": "string",
    "messageType": "user|system"
  }
  ```
- **Response**:
  ```json
  {
    "messageId": "string",
    "content": "string",
    "timestamp": "string",
    "userId": "string",
    "messageType": "user|system"
  }
  ```

#### Get Chat History
- **Method**: GET
- **Path**: `/v1/cases/{caseId}/messages`
- **Query Parameters**:
  - `limit`: number (default: 50)
  - `before`: timestamp (for pagination)
- **Description**: Get the chat history for a case
- **Response**:
  ```json
  {
    "messages": [
      {
        "messageId": "string",
        "content": "string",
        "timestamp": "string",
        "userId": "string",
        "userName": "string",
        "messageType": "user|system"
      }
    ],
    "hasMore": true
  }
  ```

#### Enrich Prompt
- **Method**: POST
- **Path**: `/v1/cases/{caseId}/enrich-prompt`
- **Description**: Enrich a chat prompt with case context
- **Body**:
  ```json
  {
    "prompt": "string"
  }
  ```
- **Response**:
  ```json
  {
    "enrichedPrompt": "string"
  }
  ```

#### Send to Vertex AI
- **Method**: POST
- **Path**: `/v1/cases/{caseId}/send-to-vertex`
- **Description**: Send a prompt to Vertex AI and get a response
- **Body**:
  ```json
  {
    "prompt": "string",
    "enrichContext": true // whether to automatically enrich with case context
  }
  ```
- **Response**:
  ```json
  {
    "response": "string",
    "messageId": "string"
  }
  ```

### Payments

#### Create Payment Intent
- **Method**: POST
- **Path**: `/v1/payments/payment-intent`
- **Description**: Create a Stripe Payment Intent for a case payment (used when subscription quota is exhausted or no subscription exists)
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "caseTier": 1, // 1, 2, or 3
    "currency": "eur", // optional, defaults to "eur"
    "caseId": "string" // optional, to link the payment to a case
  }
  ```
- **Response**:
  ```json
  {
    "clientSecret": "string",
    "paymentIntentId": "string",
    "amount": 900, // in cents
    "currency": "eur",
    "message": "Payment intent created successfully"
  }
  ```

#### Create Checkout Session
- **Method**: POST
- **Path**: `/v1/payments/checkout-session`
- **Description**: Create a Stripe Checkout Session for a subscription with case quota or a one-time payment
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body** (for subscription):
  ```json
  {
    "planId": "personal_monthly|personal_yearly|org_basic_monthly|org_basic_yearly|org_pro_monthly|org_pro_yearly",
    "mode": "subscription", // default value
    "successUrl": "https://relex.ro/success", // optional
    "cancelUrl": "https://relex.ro/cancel", // optional
    "organizationId": "string" // optional, for business subscriptions
  }
  ```
- **Body** (for one-time payment):
  ```json
  {
    "amount": 2900, // in cents
    "mode": "payment", // required for one-time payment
    "currency": "eur", // optional, defaults to "eur"
    "productName": "Relex Legal Service", // optional
    "caseId": "string" // optional, to link the payment to a case
  }
  ```
- **Response**:
  ```json
  {
    "sessionId": "string",
    "url": "string",
    "message": "Checkout session created successfully"
  }
  ```

#### Cancel Subscription
- **Method**: DELETE
- **Path**: `/v1/subscriptions/{subscriptionId}`
- **Description**: Cancel a Stripe subscription at the end of the current billing period. The subscription will remain active until the end of the current billing cycle.
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Subscription has been scheduled for cancellation at the end of the current billing period"
  }
  ```

#### Redeem Voucher
- **Method**: POST
- **Path**: `/v1/vouchers/redeem`
- **Description**: Redeem a voucher code for the user or organization. This is a planned feature that is not yet implemented. Currently returns a 501 Not Implemented response. The function stub exists in the codebase as `relex_backend_redeem_voucher`.
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Body**:
  ```json
  {
    "voucherCode": "string",
    "organizationId": "string" // optional, to apply voucher to an organization instead of the user
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Voucher redeemed successfully",
    "voucherType": "free_case|subscription_discount|credit",
    "value": {
      "amount": 1000, // credit amount in cents, or discount percentage, or number of free cases
      "caseTier": 1 // only for free_case type
    },
    "expiresAt": "string"
  }
  ```

#### Handle Stripe Webhook
- **Method**: POST
- **Path**: `/v1/payments/webhook`
- **Description**: Process Stripe webhook events to update subscriptions and payments. Handles events such as `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `payment_intent.succeeded`, and more.
- **Headers**: 
  ```
  Stripe-Signature: <stripe_webhook_signature>
  ```
- **Body**: Stripe webhook event payload (raw)
- **Response**:
  ```json
  {
    "success": true,
    "message": "Webhook processed: event_type"
  }
  ```

## Subscription & Quota System

The platform uses a subscription model with case quotas:

1. **Subscription Plans**: Each plan includes a specific number of cases per tier per billing cycle (`caseQuotaTotal`)
2. **Quota Usage**: As cases are created, the quota is consumed (`caseQuotaUsed`)
3. **Quota Reset**: When a new billing cycle begins, the quota resets
4. **Exceeding Quota**: After exhausting quota, additional cases require individual payment

Case tiers with individual pricing:
- **Tier 1 (Basic)**: Simple cases (€9.00 each if purchased individually)
- **Tier 2 (Standard)**: Medium complexity (€29.00 each if purchased individually)
- **Tier 3 (Complex)**: High complexity (€99.00 each if purchased individually)

Subscription plans:
- **Individual**: €9/mo or €86.40/yr (20% discount)
- **Organisation Basic**: €200/mo or €1920/yr (20% discount)
- **Organisation Pro**: €500/mo or €4800/yr (20% discount)

Each plan includes different quota amounts for each tier, providing approximately 70% savings compared to buying cases individually.

## Error Responses

All endpoints use a consistent error format:
```json
{
  "error": "string",
  "message": "string"
}
```

Common error codes:
- `400 Bad Request`: Invalid request data or validation errors
  ```json
  {
    "error": "invalid_request",
    "message": "Detailed validation error message"
  }
  ```

- `401 Unauthorized`: Authentication required or invalid token
  ```json
  {
    "error": "unauthorized",
    "message": "Authentication required"
  }
  ```

- `402 Payment Required`: Subscription quota exhausted or no subscription
  ```json
  {
    "error": "payment_required",
    "message": "Case quota exhausted. Please purchase additional cases or upgrade your subscription."
  }
  ```

- `403 Forbidden`: Insufficient permissions for the requested action
  ```json
  {
    "error": "forbidden",
    "message": "You do not have permission to perform this action"
  }
  ```

- `404 Not Found`: Resource not found
  ```json
  {
    "error": "not_found",
    "message": "The requested resource was not found"
  }
  ```

- `409 Conflict`: Resource state conflict
  ```json
  {
    "error": "conflict",
    "message": "The requested operation conflicts with the current state"
  }
  ```

- `429 Too Many Requests`: Rate limit exceeded
  ```json
  {
    "error": "rate_limit_exceeded",
    "message": "Too many requests. Please try again later."
  }
  ```

- `500 Internal Server Error`: Server-side error
  ```json
  {
    "error": "internal_error",
    "message": "An unexpected error occurred"
  }
  ```

## Security

1. **Authentication**
   - All endpoints require Firebase Authentication
   - ID token must be included in Authorization header
   - Token validation includes:
     - Signature verification
     - Expiration check
     - Issuer verification
     - Audience verification

2. **Role-based Access Control**
   - Resource access based on user roles
   - Organization-specific roles (administrator, staff)
   - Individual resource ownership
   - Staff assignment validation for organization cases

3. **Input Validation**
   - Request data validation using Pydantic models
   - Field type checking
   - Required field validation
   - Format validation (e.g., CNP, CUI, RegCom formats)

4. **CORS**
   - Enabled for web clients
   - Configurable allowed origins
   - Supports preflight requests
   - Handles OPTIONS method

5. **Request Limits**
   - Files: 10MB per file, 2GB per case
   - JSON payloads: 1MB maximum size
   - Rate limiting on API endpoints
   - Concurrent request limits

## Monitoring

1. **Cloud Functions Logs**
   - Request/response logging
   - Error tracking
   - Performance metrics
   - Authentication events

2. **Error Reporting**
   - Automatic error capture
   - Stack trace collection
   - Error aggregation
   - Alert configuration

3. **Request Tracing**
   - Request ID tracking
   - Latency monitoring
   - Dependency tracking
   - Cross-service correlation

4. **Performance Monitoring**
   - Response time tracking
   - Error rate monitoring
   - Resource utilization
   - Quota usage tracking

## Development

1. **Local Testing**
   - Firebase Emulator Suite support
   - Local function deployment
   - Mock authentication
   - Test data population

2. **API Testing**
   - Postman collection available
   - Test environment configuration
   - Authentication helpers
   - Example requests

3. **OpenAPI Specification**
   - Full API documentation in `/terraform/openapi_spec.yaml`
   - Request/response schemas
   - Authentication requirements
   - Error definitions

4. **Environment Setup**
   - Development environment guide in `README.md`
   - Required dependencies
   - Configuration steps
   - Troubleshooting guide 