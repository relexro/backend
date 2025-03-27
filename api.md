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
- `POST /v1/payments/cancel-subscription` (cancel subscription)
- `POST /v1/webhook/stripe` (handle Stripe webhooks)

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
    "resourceType": "case|organization",
    "resourceId": "string",
    "organizationId": "string",
    "action": "read|update|delete|upload_file|manage_access|create_case"
  }
  ```
- **Response**:
  ```json
  {
    "allowed": true,
    "role": "string"
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
    "createdAt": "string"
  }
  ```

### Cases

#### Create Individual Case
- **Method**: POST
- **Path**: `/v1/cases`
- **Body**:
  ```json
  {
    "title": "string",
    "description": "string",
    "paymentIntentId": "string",
    "caseTier": 1 // 1, 2, or 3
  }
  ```
- **Response**:
  ```json
  {
    "caseId": "string",
    "title": "string",
    "status": "open",
    "createdAt": "string",
    "paymentStatus": "paid",
    "caseTier": 1,
    "casePrice": 900
  }
  ```

#### Create Organization Case
- **Method**: POST
- **Path**: `/v1/organizations/{organizationId}/cases`
- **Body**:
  ```json
  {
    "title": "string",
    "description": "string",
    "paymentIntentId": "string",
    "caseTier": 1 // 1, 2, or 3
  }
  ```
- **Response**:
  ```json
  {
    "caseId": "string",
    "title": "string",
    "status": "open",
    "createdAt": "string",
    "paymentStatus": "paid",
    "caseTier": 1,
    "casePrice": 900
  }
  ```

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
        "paymentStatus": "string"
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
        "createdAt": "string"
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
- **Description**: Create a Stripe Payment Intent for a case payment
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
- **Description**: Create a Stripe Checkout Session for a subscription or one-time payment
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
- **Description**: Cancel a Stripe subscription at the end of the current billing period
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
- **Description**: Process Stripe webhook events to update subscriptions and payments
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
- `forbidden`: 403
- `not_found`: 404
- `internal_error`: 500

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