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
// Example with email/password
await firebase.auth().signInWithEmailAndPassword(email, password);

// Example with Google
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

### User Management
- `GET /v1/users/me`
- `PUT /v1/users/me`
- `GET /v1/users/me/organizations`
- `GET /v1/users/me/cases`

### Organization Management
- `POST /v1/organizations`
- `GET /v1/organizations/{organizationId}`
- `PUT /v1/organizations/{organizationId}`

### Organization Membership
- `POST /v1/organizations/{organizationId}/members`
- `GET /v1/organizations/{organizationId}/members`
- `PUT /v1/organizations/{organizationId}/members/{userId}`
- `DELETE /v1/organizations/{organizationId}/members/{userId}`

### Cases
- `POST /v1/cases` (individual cases)
- `POST /v1/organizations/{organizationId}/cases` (organization cases)
- `GET /v1/cases/{caseId}`
- `GET /v1/users/me/cases` (list individual cases)
- `GET /v1/organizations/{organizationId}/cases` (list organization cases)
- `POST /v1/cases/{caseId}/archive`
- `DELETE /v1/cases/{caseId}`

### Files
- `POST /v1/cases/{caseId}/files`
- `GET /v1/files/{fileId}`

### Payments
- `POST /v1/payments/payment-intent` (create payment intent)
- `POST /v1/payments/checkout-session` (create checkout session)
- `DELETE /v1/subscriptions/{subscriptionId}` (cancel subscription)
- `POST /v1/payments/webhook` (handle Stripe webhooks)

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
    "caseQuotaTotal": 10,
    "caseQuotaUsed": 5,
    "stripeCustomerId": "string",
    "stripeSubscriptionId": "string",
    "languagePreference": "en|ro",
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
        "type": "string",
        "role": "string"
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

### Cases

#### Create Individual Case
- **Method**: POST
- **Path**: `/v1/cases`
- **Description**: Create a new case as an individual. The system first checks if the user has an active subscription with available quota. If quota is available, the case is created using the quota. If quota is exhausted or no active subscription exists, a `paymentIntentId` is required.
- **Body**:
  ```json
  {
    "title": "string",
    "description": "string",
    "caseTier": 1, // 1, 2, or 3 - REQUIRED
    "paymentIntentId": "string" // OPTIONAL if user has subscription with quota
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
    "casePrice": 900
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
- **Body**:
  ```json
  {
    "title": "string",
    "description": "string",
    "caseTier": 1, // 1, 2, or 3 - REQUIRED
    "paymentIntentId": "string" // OPTIONAL if organization has subscription with quota
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
    "casePrice": 900
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
  - `status`: open|archived|deleted
  - `limit`: number
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
        "caseTier": 1
      }
    ]
  }
  ```

#### List Organization Cases
- **Method**: GET
- **Path**: `/v1/organizations/{organizationId}/cases`
- **Query Parameters**:
  - `status`: open|archived|deleted
  - `limit`: number
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
        "caseTier": 1
      }
    ]
  }
  ```

### Files

#### Upload File
- **Method**: POST
- **Path**: `/v1/cases/{caseId}/files`
- **Body**: multipart/form-data
  - `file`: File
  - `fileName`: string
- **Response**:
  ```json
  {
    "fileId": "string",
    "fileName": "string",
    "fileUrl": "string",
    "uploadedAt": "string"
  }
  ```

#### Download File
- **Method**: GET
- **Path**: `/v1/files/{fileId}`
- **Response**: File content (application/octet-stream)

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
    "planId": "personal_monthly", // or other plan IDs
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

## Error Responses

All endpoints use a consistent error format:
```json
{
  "error": "string",
  "message": "string"
}
```

Common error codes:
- `invalid_request`: 400
- `unauthorized`: 401
- `payment_required`: 402 - Subscription quota exhausted or no subscription
- `forbidden`: 403
- `not_found`: 404
- `internal_error`: 500

## Party Management

The Relex API supports management of parties (individuals or organizations) that can be attached to cases as plaintiffs, defendants, or other stakeholders.

### Party Types and Conditional Fields

A key feature of the Party system is the `partyType` field, which determines what other fields are required:

1. **Individual Parties** (`partyType: "individual"`):
   - **Required in nameDetails**: `firstName`, `lastName`
   - **Required in identityCodes**: `cnp` (Romanian Personal Numeric Code, 13 digits)
   - Cannot have organization-specific fields (companyName, cui, regCom)

2. **Organization Parties** (`partyType: "organization"`):
   - **Required in nameDetails**: `companyName`
   - **Required in identityCodes**: `cui` (Romanian Fiscal Code), `regCom` (Romanian Registration Number)
   - Cannot have individual-specific fields (firstName, lastName, cnp)

All party types require `contactInfo.address` (email and phone are optional).

### Create Party
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

### Example: Creating an Organization Party
```json
{
  "partyType": "organization",
  "nameDetails": {
    "companyName": "ABC Company SRL"
  },
  "identityCodes": {
    "cui": "RO12345678",
    "regCom": "J40/123/2020"
  },
  "contactInfo": {
    "address": "123 Business Ave, Bucharest",
    "email": "contact@abccompany.ro",
    "phone": "+40721234567"
  }
}
```

### Get Party
- **Method**: GET
- **Path**: `/v1/parties/{partyId}`
- **Description**: Retrieves a party by ID (requires ownership)
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Response**: Same as Create Party response

### Update Party
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
    "partyId": "string", // REQUIRED
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

### Delete Party
- **Method**: DELETE
- **Path**: `/v1/parties/{partyId}`
- **Description**: Deletes a party (requires ownership, fails if party is attached to any cases)
- **Headers**: 
  ```
  Authorization: Bearer <firebase_id_token>
  ```
- **Response**: Status 204 No Content

### List Parties
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
        "nameDetails": { ... },
        "identityCodes": { ... },
        "contactInfo": { ... },
        "createdAt": "2023-10-20T14:30:00Z",
        "updatedAt": "2023-10-20T14:30:00Z"
      }
    ]
  }
  ```

### Attach Party to Case
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

### Detach Party from Case
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

## Subscription & Quota System

The platform uses a subscription model with case quotas:

1. **Subscription Plans**: Each plan includes a specific number of cases per billing cycle (caseQuotaTotal)
2. **Quota Usage**: As cases are created, the quota is consumed (caseQuotaUsed)
3. **Quota Reset**: When a new billing cycle begins, the quota resets
4. **Exceeding Quota**: After exhausting quota, additional cases require individual payment

Case tiers:
- **Tier 1 (Basic)**: Simple cases (€9.00 each if purchased individually)
- **Tier 2 (Standard)**: Medium complexity (€29.00 each if purchased individually)
- **Tier 3 (Complex)**: High complexity (€99.00 each if purchased individually)

## Security

1. All endpoints require Firebase Authentication
2. Role-based access control
3. Input validation and sanitization
4. CORS enabled for web clients
5. Request size limits:
   - Files: 10MB
   - JSON payloads: 1MB

## Monitoring

1. Cloud Functions logs
2. Error reporting
3. Request tracing
4. Performance monitoring

## Development

1. Local testing with Firebase Emulator
2. Postman collection available
3. OpenAPI spec in `/terraform/openapi_spec.yaml`
4. Environment setup in `README.md` 