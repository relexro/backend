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
    "status": "string",  // The status of the agent's operation (e.g., 'success' or 'error')
    "message": "string",  // The agent's textual response to the user
    "timestamp": "string",  // ISO 8601 timestamp of when the response was generated
    "metadata": {           // Optional metadata including confidence scores and execution time
      // ...
    }
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
  "displayName": "string",  // User's display name
  "photoURL": "string",  // URL to the user's profile photo
  "languagePreference": "en|ro"  // User's preferred language
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
        "organizationId": "string",  // The unique identifier of the organization
        "name": "string",  // Name of the organization
        "description": "string",  // Description of the organization
        "role": "string",  // User's role in the organization (administrator or staff)
        "joinedAt": "string"  // ISO 8601 timestamp when the user joined
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
    "total": "integer",  // Total number of cases that match the filter
    "limit": "integer",  // Maximum number of cases returned
    "offset": "integer"  // Offset for pagination
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
  "name": "string",  // Name of the organization
  "type": "string",  // Type of organization (e.g., law_firm)
  "description": "string",  // Description of the organization
  "address": "string",  // Address of the organization
  "phone": "string",  // Phone number of the organization
  "email": "string"  // Email of the organization
}
```

**Responses:**
- `201 Created`: Organization created successfully
  ```json
  {
    "organizationId": "string",  // Unique identifier for the organization
    "name": "string",  // Name of the organization
    "type": "string",  // Type of the organization
    "description": "string",  // Description of the organization
    "address": "string",  // Address of the organization
    "phone": "string",  // Phone number of the organization
    "email": "string",  // Email of the organization
    "createdAt": "string",  // Creation timestamp (ISO 8601)
    "createdBy": "string"  // ID of the user who created the organization
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
    "organizationId": "string",  // Unique identifier for the organization
    "name": "string",  // Name of the organization
    "type": "string",  // Type of the organization
    "description": "string",  // Description of the organization
    "address": "string",  // Address of the organization
    "phone": "string",  // Phone number of the organization
    "email": "string",  // Email of the organization
    "createdAt": "string",  // Creation timestamp (ISO 8601)
    "updatedAt": "string",  // Last update timestamp (ISO 8601)
    "memberCount": "integer",  // Number of members in the organization
    "subscription": {
      "status": "string",  // Subscription status
      "plan": "string",  // Current subscription plan
      "currentPeriodEnd": "string",  // End of the current billing period (ISO 8601)
      "caseQuota": "integer",  // Number of cases allowed under current plan
      "casesUsed": "integer"  // Number of cases created under current plan
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
  "name": "string",  // Name of the organization
  "description": "string",  // Description of the organization
  "address": "string",  // Address of the organization
  "phone": "string",  // Phone number of the organization
  "email": "string"  // Email of the organization
}
```

**Responses:**
- `200 OK`: Organization updated successfully
  ```json
  {
    "organizationId": "string",  // Unique identifier for the organization
    "name": "string",  // Name of the organization
    "type": "string",  // Type of the organization
    "description": "string",  // Description of the organization
    "address": "string",  // Address of the organization
    "phone": "string",  // Phone number of the organization
    "email": "string",  // Email of the organization
    "updatedAt": "string"  // Update timestamp (ISO 8601)
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
    "success": "boolean",  // Indicates successful operation
    "organizationId": "string"  // ID of the deleted organization
  }
  ```
- `401 Unauthorized`: Unauthorized
- `403 Forbidden`: Forbidden (caller is not an administrator or organization has active subscription)
- `404 Not Found`: Organization not found
- `500 Internal Server Error`: Internal server error

### Case Management

#### POST /cases
Creates a new individual case for the authenticated user or an organization case if organizationId is provided.

**Request Body:**
```json
{
  "title": "string",  // Title of the case
  "description": "string",  // Description of the case
  "caseTier": "integer",  // Case tier level
  "caseTypeId": "string",  // The ID of the case type for this case
  "organizationId": "string",  // Organization ID for organization cases
  "paymentIntentId": "string",  // Stripe payment intent ID
  "initialPartyIds": ["string"]  // Optional array of party IDs to attach initially
}
```

**Responses:**
- `201 Created`: Case created successfully
  ```json
  {
    "caseId": "string",  // Unique identifier for the case
    "status": "string"  // Status of the case (initially "open")
  }
  ```
- `400 Bad Request`: Bad request (e.g., invalid input format)
- `401 Unauthorized`: Unauthorized
- `402 Payment Required`: Payment Required
- `403 Forbidden`: Forbidden (e.g., insufficient permissions)
- `500 Internal Server Error`: Internal server error

#### POST /organizations/{organizationId}/cases
Creates a new case for a specific organization.

**Path Parameters:**
- `organizationId` (string, required): The unique identifier of the organization

**Request Body:**
```json
{
  "title": "string",  // Title of the case
  "description": "string",  // Description of the case
  "caseTier": "integer",  // Case tier level
  "caseTypeId": "string",  // The ID of the case type for this case
  "paymentIntentId": "string",  // Stripe payment intent ID
  "initialPartyIds": ["string"],  // Optional array of party IDs to attach initially
  "assignedUserId": "string"  // Optional staff user ID to assign the case to
}
```

**Responses:**
- `201 Created`: Case created successfully
  ```json
  {
    "caseId": "string",  // Unique identifier for the case
    "status": "string"  // Status of the case (initially "open")
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `402 Payment Required`: Payment Required
- `403 Forbidden`: Forbidden
- `404 Not Found`: Organization not found
- `500 Internal Server Error`: Internal server error

### File Management

#### GET /cases/{caseId}/files/{fileId}
Download a file attached to a specific case.

**Path Parameters:**
- `caseId` (string, required): ID of the case the file is attached to
- `fileId` (string, required): ID of the file to download

**Responses:**
- `200 OK`: Returns a JSON object containing a time-limited, signed URL to download the file, the original filename, and the document's metadata ID.
  ```json
  {
    "downloadUrl": "string",  // A time-limited, signed URL to download the file directly from cloud storage
    "filename": "string",     // The original filename of the document
    "documentId": "string"    // The unique identifier for the document's metadata record
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
  "partyType": "individual", // or "organization"
  "nameDetails": {
    // For individual: firstName, lastName, etc.
    // For organization: companyName
  },
  "identityCodes": {
    // For individual: cnp, etc.
    // For organization: cui, regCom, etc.
  },
  "contactInfo": {
    // Contact information fields
  },
  "signatureData": {
    // Optional signature data
  }
}
```

**Responses:**
- `201 Created`: Party created successfully
  ```json
  {
    "partyId": "string",  // ID of the created party
    "status": "success"   // Status of the operation
  }
  ```
- `400 Bad Request`: Bad request
- `401 Unauthorized`: Unauthorized
- `500 Internal Server Error`: Internal server error
