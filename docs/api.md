# Relex API Documentation

## Base URL
The API is accessed via the default Google Cloud API Gateway URL. This URL is generated upon deployment and can be found in `docs/terraform_outputs.log` under the `api_gateway_url` key (e.g., `relex-api-gateway-dev-mvef5dk.ew.gateway.dev`).

All endpoints are deployed under the `/v1` path prefix.

> **Important Note:** The custom domain `api-dev.relex.ro` is not currently the active endpoint for the API Gateway.

## Authentication
All endpoints require Firebase Authentication. Include the ID token in the Authorization header:
```
Authorization: Bearer <firebase_id_token>
```

### Authentication Flow
When a client makes a request to the API:

1. The client includes the Firebase JWT token in the Authorization header
2. The API Gateway validates this token
3. The API Gateway then calls the backend Cloud Run functions using a Google OIDC ID token it generates, acting as the `relex-functions-dev@relexro.iam.gserviceaccount.com` service account
4. The backend validates this Google OIDC ID token

## API Endpoints

### Authentication

#### GET /auth/validate-user
Validates a user's authentication token and creates a user record if it doesn't exist.

**Headers:**
- `Authorization` (string, required): Firebase Authentication token (Bearer format)

**Responses:**
- `200 OK`: User validation successful
  ```json
  {
    "userId": "string",
    "email": "string",
    "displayName": "string",
    "isNewUser": "boolean",
    "validationTimestamp": "string"
  }
  ```
- `401 Unauthorized`: Unauthorized (invalid token)
- `500 Internal Server Error`: Internal server error

#### POST /auth/check-permissions
Checks if a user has specific permissions for a resource.

**Headers:**
- `Authorization` (string, required): Firebase Authentication token (Bearer format)

**Request Body:**
```json
{
  "resourceType": "case|organization|party|document",
  "resourceId": "string",
  "permission": "read|write|delete|admin"
}
```

**Responses:**
- `200 OK`: Permission check result
  ```json
  {
    "userId": "string",
    "resourceType": "string",
    "resourceId": "string",
    "permission": "string",
    "hasPermission": "boolean",
    "reason": "string"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized (invalid token)
- `500 Internal Server Error`: Internal server error

#### GET /auth/user-role
Gets a user's role in a specific organization.

**Query Parameters:**
- `organizationId` (string, required): ID of the organization
- `userId` (string, optional): Optional user ID (if not provided, uses the authenticated user)

**Responses:**
- `200 OK`: User role information
  ```json
  {
    "userId": "string",
    "organizationId": "string",
    "role": "string",
    "isMember": "boolean"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `404 Not Found`: Organization not found
- `500 Internal Server Error`: Internal server error

### Agent Interaction

#### POST /cases/{caseId}/agent/messages
Interact with the Lawyer AI Agent for a specific case.

**Path Parameters:**
- `caseId` (string, required): ID of the case for the agent interaction

**Request Body:**
```json
{
  "message": "string"  // The user's text message or input data
}
```

**Responses:**
- `200 OK`: Successful agent response or status update
  ```json
  {
    "status": "string",
    "message": "string",
    "response": {
      "content": "string",
      "recommendations": ["string"],
      "next_steps": ["string"],
      "draft_documents": [
        {
          "id": "string",
          "title": "string",
          "url": "string"
        }
      ],
      "research_summary": "string"
    },
    "completed_steps": ["string"],
    "errors": [
      {
        "node": "string",
        "error": "string",
        "timestamp": "string"
      }
    ],
    "timestamp": "string"
  }
  ```
- `400 Bad Request`: Bad request (e.g., invalid input format)
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (e.g., user doesn't have access to the case)
- `404 Not Found`: Case not found
- `500 Internal Server Error`: Internal server error (Agent handler failure)

### User Management

#### GET /users/me
Retrieves the profile of the authenticated user.

**Responses:**
- `200 OK`: User profile
  ```json
  {
    "userId": "string",
    "email": "string",
    "displayName": "string",
    "photoURL": "string",
    "languagePreference": "en|ro"
  }
  ```
- `401 Unauthorized`: Unauthorized
- `404 Not Found`: Not found
- `500 Internal Server Error`: Internal server error

#### PUT /users/me
Updates the profile of the authenticated user.

**Request Body:**
```json
{
  "displayName": "string",
  "photoURL": "string",
  "languagePreference": "en|ro"
}
```

**Responses:**
- `200 OK`: User profile updated
  ```json
  {
    "userId": "string",
    "email": "string",
    "displayName": "string",
    "photoURL": "string",
    "languagePreference": "en|ro"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `404 Not Found`: Not found
- `500 Internal Server Error`: Internal server error

#### GET /users/me/organizations
Lists all organizations the authenticated user is a member of.

**Responses:**
- `200 OK`: List of organizations
  ```json
  {
    "organizations": [
      {
        "organizationId": "string",
        "name": "string",
        "description": "string",
        "role": "string",
        "joinedAt": "string"
      }
    ]
  }
  ```
- `401 Unauthorized`: Unauthorized
- `500 Internal Server Error`: Internal server error

#### GET /users/me/cases
Lists all cases owned by the authenticated user.

**Query Parameters:**
- `limit` (integer, optional): Maximum number of cases to return (default 20, max 100)
- `offset` (integer, optional): Offset for pagination (default 0)
- `status` (string, optional): Filter by case status (open, archived, deleted)

**Responses:**
- `200 OK`: List of cases
  ```json
  {
    "cases": [
      {
        "caseId": "string",
        "title": "string",
        "description": "string",
        "status": "string",
        "createdAt": "string",
        "updatedAt": "string"
      }
    ],
    "total": "integer",
    "limit": "integer",
    "offset": "integer"
  }
  ```
- `401 Unauthorized`: Unauthorized
- `500 Internal Server Error`: Internal server error

### Organization Management

#### POST /organizations
Creates a new organization with the authenticated user as administrator.

**Request Body:**
```json
{
  "name": "string",
  "type": "string",
  "description": "string",
  "address": "string",
  "phone": "string",
  "email": "string"
}
```

**Responses:**
- `201 Created`: Organization created successfully
  ```json
  {
    "organizationId": "string",
    "name": "string",
    "type": "string",
    "description": "string",
    "address": "string",
    "phone": "string",
    "email": "string",
    "createdAt": "string",
    "createdBy": "string"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `500 Internal Server Error`: Internal server error

#### GET /organizations/{organizationId}
Retrieves detailed information about a specific organization. Accessible by organization members.

**Path Parameters:**
- `organizationId` (string, required): ID of the organization to retrieve

**Responses:**
- `200 OK`: Organization details
  ```json
  {
    "organizationId": "string",
    "name": "string",
    "type": "string",
    "description": "string",
    "address": "string",
    "phone": "string",
    "email": "string",
    "createdAt": "string",
    "updatedAt": "string",
    "memberCount": "integer",
    "subscription": {
      "status": "string",
      "plan": "string",
      "currentPeriodEnd": "string",
      "caseQuota": "integer",
      "casesUsed": "integer"
    }
  }
  ```
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (not a member of the organization)
- `404 Not Found`: Organization not found
- `500 Internal Server Error`: Internal server error

#### PUT /organizations/{organizationId}
Updates information for an existing organization. Accessible by organization administrators.

**Path Parameters:**
- `organizationId` (string, required): ID of the organization to update

**Request Body:**
```json
{
  "name": "string",
  "description": "string",
  "address": "string",
  "phone": "string",
  "email": "string"
}
```

**Responses:**
- `200 OK`: Organization updated successfully
  ```json
  {
    "organizationId": "string",
    "name": "string",
    "type": "string",
    "description": "string",
    "address": "string",
    "phone": "string",
    "email": "string",
    "updatedAt": "string"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (caller is not an administrator)
- `404 Not Found`: Organization not found
- `500 Internal Server Error`: Internal server error

#### DELETE /organizations/{organizationId}
Deletes an organization. Only possible if there's no active subscription and caller is an administrator.

**Path Parameters:**
- `organizationId` (string, required): ID of the organization to delete

**Responses:**
- `200 OK`: Organization deleted successfully
  ```json
  {
    "success": "boolean",
    "organizationId": "string"
  }
  ```
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (caller is not an administrator or organization has active subscription)
- `404 Not Found`: Organization not found
- `500 Internal Server Error`: Internal server error

## Organization Membership API (v1)

All endpoints now use only body or query parameters. Path parameters are no longer supported for organization membership operations.

### POST /organizations/members
- Adds the authenticated user (end_user_id) to the specified organization with the given role.
- **Body:** `{ "organizationId": string, "userId": string (ignored), "role": "administrator" | "staff" }`
- **Behavior:** The backend always adds the authenticated user, not the userId in the body.
- **Response:** 201 with member data, or 409 if already a member.

### DELETE /organizations/members
- Removes the authenticated user from the specified organization.
- **Body:** `{ "organizationId": string, "userId": string (ignored) }`
- **Behavior:** The backend always removes the authenticated user.
- **Response:** 200 on success, 404 if not a member, 400 if last admin.

### GET /organizations/members
- Lists all members of the specified organization.
- **Query:** `organizationId=...`
- **Response:** 200 with member list.

### PUT /organizations/members
- Updates the role of the authenticated user in the organization.
- **Body:** `{ "organizationId": string, "userId": string (ignored), "newRole": "administrator" | "staff" }`
- **Response:** 200 on success, 400 if last admin.

### GET /organizations/members/role
- Gets the role of the authenticated user in the organization.
- **Query:** `organizationId=...`
- **Response:** `{ "role": string, "isMember": bool }`

#### Migration Notes
- All path-parameter endpoints for organization membership have been removed.
- All tests now use in-memory Firestore mocks with full support for chained .where() and .limit() calls.
- The backend always uses the authenticated user for add/remove/role operations, regardless of userId in the body.

### Case Management

#### POST /cases
Creates a new individual case for the authenticated user or an organization case if organizationId is provided.

**Request Body:**
```json
{
  "title": "string",
  "description": "string",
  "caseTier": "integer",
  "caseTypeId": "string",
  "organizationId": "string",
  "paymentIntentId": "string",
  "initialPartyIds": ["string"]
}
```

**Responses:**
- `201 Created`: Case created successfully
  ```json
  {
    "caseId": "string",
    "status": "string"
  }
  ```
- `400 Bad Request`: Bad request (e.g., invalid input format)
- `401 Unauthorized`: Unauthorized
- `402 Payment Required`: Payment Required
- `403 Forbidden`: Forbidden (e.g., insufficient permissions)
- `500 Internal Server Error`: Internal server error

#### GET /cases/{caseId}
Retrieves detailed information about a specific case.

**Path Parameters:**
- `caseId` (string, required): ID of the case to retrieve

**Responses:**
- `200 OK`: Case details retrieved successfully
  ```json
  {
    "caseId": "string",
    "title": "string",
    "description": "string",
    "status": "open|archived|deleted",
    "caseTier": "integer",
    "caseTypeId": "string",
    "createdAt": "string",
    "updatedAt": "string",
    "createdBy": "string",
    "organizationId": "string",
    "assignedTo": "string",
    "parties": [
      {
        "partyId": "string",
        "role": "string",
        "addedAt": "string",
        "notes": "string"
      }
    ],
    "labels": [
      {
        "labelId": "string",
        "name": "string",
        "color": "string"
      }
    ],
    "files": [
      {
        "fileId": "string",
        "filename": "string",
        "contentType": "string",
        "size": "integer",
        "uploadedAt": "string",
        "downloadUrl": "string"
      }
    ],
    "agentProgress": {
      "isActive": "boolean",
      "lastInteraction": "string",
      "completedSteps": ["string"],
      "recommendations": ["string"]
    }
  }
  ```
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (e.g., user doesn't have access to the case)
- `404 Not Found`: Case not found
- `500 Internal Server Error`: Internal server error

#### DELETE /cases/{caseId}
Marks a case as deleted. Changes a case status to "deleted". Deleted cases are only shown when specifically requested.

**Path Parameters:**
- `caseId` (string, required): ID of the case to mark as deleted

**Responses:**
- `200 OK`: Case marked as deleted successfully
  ```json
  {
    "success": "boolean",
    "caseId": "string",
    "status": "string"
  }
  ```
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (e.g., user doesn't have access to the case)
- `404 Not Found`: Case not found
- `500 Internal Server Error`: Internal server error

#### PUT /cases/{caseId}/archive
Archives a case. Changes a case status to "archived". Archived cases are not shown in the default case listing.

**Path Parameters:**
- `caseId` (string, required): ID of the case to archive

**Responses:**
- `200 OK`: Case archived successfully
  ```json
  {
    "success": "boolean",
    "caseId": "string",
    "status": "string"
  }
  ```
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (e.g., user doesn't have access to the case)
- `404 Not Found`: Case not found
- `500 Internal Server Error`: Internal server error

#### POST /cases/{caseId}/assign
Assigns a case to a user. Assigns an organization case to a specific user. Only available for organization administrators.

**Path Parameters:**
- `caseId` (string, required): ID of the case to assign

**Request Body:**
```json
{
  "userId": "string",
  "notes": "string"
}
```

**Responses:**
- `200 OK`: Case assigned successfully
  ```json
  {
    "success": "boolean",
    "caseId": "string",
    "userId": "string",
    "assignedAt": "string",
    "notes": "string"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (not an administrator of the organization)
- `404 Not Found`: Case or user not found
- `500 Internal Server Error`: Internal server error

#### POST /organizations/{organizationId}/cases
Creates a new case for a specific organization.

**Path Parameters:**
- `organizationId` (string, required): The unique identifier of the organization

**Request Body:**
```json
{
  "title": "string",
  "description": "string",
  "caseTier": "integer",
  "caseTypeId": "string",
  "paymentIntentId": "string",
  "initialPartyIds": ["string"],
  "assignedUserId": "string"
}
```

**Responses:**
- `201 Created`: Case created successfully
  ```json
  {
    "caseId": "string",
    "status": "string"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `402 Payment Required`: Payment Required
- `403 Forbidden`: Forbidden
- `404 Not Found`: Organization not found
- `500 Internal Server Error`: Internal server error

#### GET /organizations/{organizationId}/cases
Lists cases associated with the specified organization.

**Path Parameters:**
- `organizationId` (string, required): ID of the organization

**Query Parameters:**
- `limit` (integer, optional): Maximum number of cases to return (default 20, max 100)
- `offset` (integer, optional): Offset for pagination (default 0)
- `status` (string, optional): Filter by case status (open, archived, deleted)

**Responses:**
- `200 OK`: List of cases
  ```json
  {
    "cases": [
      {
        "caseId": "string",
        "title": "string",
        "description": "string",
        "status": "string",
        "createdAt": "string",
        "updatedAt": "string"
      }
    ],
    "total": "integer",
    "limit": "integer",
    "offset": "integer"
  }
  ```
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden
- `404 Not Found`: Organization not found
- `500 Internal Server Error`: Internal server error

### File Management

#### POST /cases/{caseId}/files
Uploads a file and attaches it to a specific case.

**Path Parameters:**
- `caseId` (string, required): ID of the case to attach the file to

**Content-Type:** `application/octet-stream`, `image/jpeg`, `image/png`, `application/pdf`, `text/plain`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/msword`

**Responses:**
- `200 OK`: File uploaded successfully
  ```json
  {
    "fileId": "string",
    "caseId": "string",
    "filename": "string",
    "contentType": "string",
    "size": "integer",
    "downloadUrl": "string",
    "uploadedAt": "string",
    "metadata": {
      "fileType": "string",
      "description": "string"
    }
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden
- `404 Not Found`: Case not found
- `500 Internal Server Error`: Internal server error

#### GET /cases/{caseId}/files/{fileId}
Downloads a file attached to a specific case.

**Path Parameters:**
- `caseId` (string, required): ID of the case the file is attached to
- `fileId` (string, required): ID of the file to download

**Responses:**
- `200 OK`: File download metadata
  ```json
  {
    "downloadUrl": "string",
    "filename": "string",
    "documentId": "string"
  }
  ```
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden
- `404 Not Found`: File or case not found
- `500 Internal Server Error`: Internal server error

### Party Management

#### POST /parties
Creates a new party record in the system.

**Request Body:**
```json
{
  "partyType": "individual|organization",
  "nameDetails": {
    "firstName": "string",
    "lastName": "string",
    "middleName": "string",
    "companyName": "string"
  },
  "identityCodes": {
    "ssn": "string",
    "cnp": "string",
    "taxId": "string",
    "registrationNumber": "string"
  },
  "contactInfo": {
    "email": "string",
    "phone": "string",
    "address": {
      "street": "string",
      "city": "string",
      "state": "string",
      "postalCode": "string",
      "country": "string"
    }
  },
  "signatureData": {}
}
```

**Responses:**
- `201 Created`: Party created successfully
  ```json
  {
    "partyId": "string",
    "status": "success"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `500 Internal Server Error`: Internal server error

#### GET /parties
Lists parties created by the authenticated user.

**Query Parameters:**
- `limit` (integer, optional): Maximum number of results to return
- `offset` (integer, optional): Number of results to skip (for pagination)
- `partyType` (string, optional): Filter by party type (individual, company, etc.)

**Responses:**
- `200 OK`: List of parties
  ```json
  {
    "parties": [
      {
        "partyId": "string",
        "partyType": "individual|company|government|other",
        "nameDetails": {
          "firstName": "string",
          "lastName": "string",
          "middleName": "string",
          "companyName": "string"
        },
        "identityCodes": {
          "ssn": "string",
          "cnp": "string",
          "taxId": "string",
          "registrationNumber": "string"
        },
        "contactInfo": {
          "email": "string",
          "phone": "string",
          "address": {
            "street": "string",
            "city": "string",
            "state": "string",
            "postalCode": "string",
            "country": "string"
          }
        },
        "createdAt": "string",
        "updatedAt": "string",
        "createdBy": "string"
      }
    ],
    "total": "integer",
    "limit": "integer",
    "offset": "integer"
  }
  ```
- `401 Unauthorized`: Unauthorized
- `500 Internal Server Error`: Internal server error

#### GET /parties/{partyId}
Retrieves detailed information about a specific party.

**Path Parameters:**
- `partyId` (string, required): ID of the party to retrieve

**Responses:**
- `200 OK`: Party details retrieved successfully
  ```json
  {
    "partyId": "string",
    "partyType": "individual|company|government|other",
    "nameDetails": {
      "firstName": "string",
      "lastName": "string",
      "middleName": "string",
      "companyName": "string"
    },
    "identityCodes": {
      "ssn": "string",
      "cnp": "string",
      "taxId": "string",
      "registrationNumber": "string"
    },
    "contactInfo": {
      "email": "string",
      "phone": "string",
      "address": {
        "street": "string",
        "city": "string",
        "state": "string",
        "postalCode": "string",
        "country": "string"
      }
    },
    "createdAt": "string",
    "updatedAt": "string",
    "createdBy": "string"
  }
  ```
- `401 Unauthorized`: Unauthorized
- `404 Not Found`: Party not found
- `500 Internal Server Error`: Internal server error

#### PUT /parties/{partyId}
Updates an existing party's information.

**Path Parameters:**
- `partyId` (string, required): ID of the party to update

**Request Body:**
```json
{
  "partyType": "individual|company|government|other",
  "nameDetails": {
    "firstName": "string",
    "lastName": "string",
    "middleName": "string",
    "companyName": "string"
  },
  "identityCodes": {
    "ssn": "string",
    "cnp": "string",
    "taxId": "string",
    "registrationNumber": "string"
  },
  "contactInfo": {
    "email": "string",
    "phone": "string",
    "address": {
      "street": "string",
      "city": "string",
      "state": "string",
      "postalCode": "string",
      "country": "string"
    }
  }
}
```

**Responses:**
- `200 OK`: Party updated successfully
  ```json
  {
    "partyId": "string",
    "status": "success"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `404 Not Found`: Party not found
- `500 Internal Server Error`: Internal server error

#### DELETE /parties/{partyId}
Deletes a party. This operation may be restricted if the party is associated with cases.

**Path Parameters:**
- `partyId` (string, required): ID of the party to delete

**Responses:**
- `204 No Content`: Party deleted successfully
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (e.g., party is associated with cases)
- `404 Not Found`: Party not found
- `500 Internal Server Error`: Internal server error

#### POST /cases/{caseId}/parties
Associates an existing party with a case.

**Path Parameters:**
- `caseId` (string, required): ID of the case

**Request Body:**
```json
{
  "userId": "string",
  "notes": "string"
}
```

**Responses:**
- `200 OK`: Case assigned successfully
  ```json
  {
    "success": "boolean",
    "caseId": "string",
    "userId": "string",
    "assignedAt": "string",
    "notes": "string"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (not an administrator of the organization)
- `404 Not Found`: Case or user not found
- `500 Internal Server Error`: Internal server error

### Payment Management

#### POST /payments/intent
Creates a Stripe payment intent for purchasing a specific case tier.

**Request Body:**
```json
{
  "amount": "integer",
  "currency": "string",
  "caseTier": "integer",
  "organizationId": "string",
  "metadata": {}
}
```

**Responses:**
- `200 OK`: Payment intent created successfully
  ```json
  {
    "clientSecret": "string",
    "paymentIntentId": "string",
    "amount": "integer",
    "currency": "string"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden
- `500 Internal Server Error`: Internal server error

#### POST /payments/checkout
Creates a Stripe checkout session for subscription plans.

**Request Body:**
```json
{
  "priceId": "string",
  "organizationId": "string",
  "successUrl": "string",
  "cancelUrl": "string"
}
```

**Responses:**
- `200 OK`: Checkout session created successfully
  ```json
  {
    "sessionId": "string",
    "url": "string"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden
- `500 Internal Server Error`: Internal server error

#### POST /webhooks/stripe
Processes webhook events from Stripe for payment and subscription management.

**Headers:**
- `Stripe-Signature` (string, required): Stripe signature for validating the webhook event

**Request Body:**
```json
{}
```

**Responses:**
- `200 OK`: Webhook processed successfully
  ```json
  {
    "received": "boolean",
    "event": "string"
  }
  ```
- `400 Bad Request`: Bad request (invalid webhook payload)
- `500 Internal Server Error`: Internal server error

#### POST /subscriptions/{subscriptionId}/cancel
Cancels an active subscription. The subscription will remain active until the end of the current billing period.

**Path Parameters:**
- `subscriptionId` (string, required): ID of the subscription to cancel

**Responses:**
- `200 OK`: Subscription canceled successfully
  ```json
  {
    "success": "boolean",
    "subscriptionId": "string",
    "status": "string",
    "cancelAt": "string"
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (not authorized to cancel this subscription)
- `404 Not Found`: Subscription not found
- `500 Internal Server Error`: Internal server error

#### POST /vouchers/redeem
Redeems a voucher code to add case credits or activate a subscription.

**Request Body:**
```json
{
  "code": "string",
  "organizationId": "string"
}
```

**Responses:**
- `200 OK`: Voucher redeemed successfully
  ```json
  {
    "success": "boolean",
    "voucherId": "string",
    "type": "string",
    "value": "integer",
    "expiresAt": "string"
  }
  ```
- `400 Bad Request`: Bad request (invalid or expired voucher)
- `401 Unauthorized`: Unauthorized
- `404 Not Found`: Voucher not found
- `409 Conflict`: Conflict (voucher already redeemed)
- `500 Internal Server Error`: Internal server error

#### GET /products
Retrieves the list of available products, subscription plans, and pricing information.

**Responses:**
- `200 OK`: List of products and pricing
  ```json
  {
    "casePricing": [
      {
        "tier": "integer",
        "amount": "integer",
        "currency": "string",
        "description": "string"
      }
    ],
    "subscriptionPlans": [
      {
        "id": "string",
        "name": "string",
        "description": "string",
        "priceId": "string",
        "amount": "integer",
        "currency": "string",
        "interval": "string",
        "caseQuota": "integer",
        "features": ["string"]
      }
    ]
  }
  ```
- `401 Unauthorized`: Unauthorized
- `500 Internal Server Error`: Internal server error

# API Readiness Checklist (July 2024)

- [x] All major endpoints implemented
- [x] Local tests passing
- [x] Deployed to GCP and validated via API Gateway
- [ ] End-to-end tested with frontend and real tokens
- [ ] All endpoints marked as production-ready or not
- `OpenAPI spec finalized and validated

> Note: The API is fully deployed to GCP and all integration tests are run against the live API Gateway endpoints. Some endpoints may require further testing or are not yet production-ready. See endpoint notes below.
