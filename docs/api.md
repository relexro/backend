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
- `POST /v1/organizations/{organizationId}/members`
- `GET /v1/organizations/{organizationId}/members`
- `PUT /v1/organizations/{organizationId}/members/{userId}`
- `DELETE /v1/organizations/{organizationId}/members/{userId}`

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

### Case Management

## POST /cases

Creates a new individual case for the authenticated user.

* **Operation ID:** `createIndividualCase`
* **Security:** Requires Firebase Authentication

---

### Request Body

| Field            | Type    | Required | Description                                       |
| :--------------- | :------ | :------- | :------------------------------------------------ |
| `title`          | string  | Yes      | Title of the case.                                |
| `description`    | string  | Yes      | Description of the case.                          |
| `caseTier`       | integer | Yes      | Case tier level determining the price (1=€9.00, 2=€29.00, 3=€99.00). |
| `caseTypeId`     | string  | Yes      | The ID of the case type for this case.            |
| `paymentIntentId`| string  | No       | Stripe payment intent ID (optional if user has an active subscription with available quota). |
| `initialPartyIds`| array   | No       | Optional array of party IDs to attach initially.  |

**Example:**

```json
{
  "title": "Divorce Settlement",
  "description": "Seeking assistance with divorce proceedings and property division.",
  "caseTier": 2,
  "caseTypeId": "divorce_settlement",
  "paymentIntentId": "pi_3NpKs8JHR4975g4B0QU4XKw9",
  "initialPartyIds": ["party_123456", "party_789012"]
}
```

---

### Responses

#### `201 Created`

Case created successfully.

* Content-Type: `application/json`
* Schema: `#/definitions/Case`

| Field           | Type    | Required | Description                               |
| :-------------- | :------ | :------- | :---------------------------------------- |
| `id`            | string  | Yes      | Unique identifier for the case.           |
| `title`         | string  | Yes      | Title of the case.                        |
| `description`   | string  | No       | Description of the case.                  |
| `status`        | string  | Yes      | Status of the case.                       |
| `organizationId`| string  | Yes      | Organization ID the case belongs to.      |
| `createdAt`     | string  | No       | Timestamp when the case was created.      |
| `updatedAt`     | string  | No       | Timestamp when the case was last updated. |
| `createdBy`     | string  | No       | User ID of the creator.                   |
| `assignedUserId`| string  | No       | User ID of the assigned user.             |
| `assignedUserName`| string| No       | Name of the assigned user.                |
| `parties`       | array   | No       | Parties associated with the case.         |

**Example:**

```json
{
  "id": "case_123456",
  "title": "Divorce Settlement",
  "description": "Seeking assistance with divorce proceedings and property division.",
  "status": "active",
  "organizationId": "user_abc123",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z",
  "createdBy": "user_abc123",
  "parties": [
    {
      "id": "party_123456",
      "name": "John Doe",
      "type": "individual"
    },
    {
      "id": "party_789012",
      "name": "Jane Doe",
      "type": "individual"
    }
  ]
}
```

#### `400 Bad Request`

Invalid request format or data.

* Content-Type: `application/json`
* Schema: `#/definitions/BadRequest`

| Field     | Type   | Enum          | Description          |
| :-------- | :----- | :------------ | :------------------- |
| `error`   | string | `bad_request` | Error code.          |
| `message` | string |               | Error message details.|

**Example:**

```json
{
  "error": "bad_request",
  "message": "Missing required field: title"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `402 Payment Required`

Quota exhausted or no active subscription, and paymentIntentId not provided.

* Content-Type: `application/json`
* Schema: `#/definitions/PaymentRequired`

| Field     | Type   | Enum             | Description          |
| :-------- | :----- | :--------------- | :------------------- |
| `error`   | string | `payment_required` | Error code.        |
| `message` | string |                  | Error message details.|

**Example:**

```json
{
  "error": "payment_required",
  "message": "Case quota exhausted. Please provide payment or upgrade your subscription."
}
```

#### `403 Forbidden`

User does not have permission for this action.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "You do not have permission to create cases"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

## POST /organizations/{organizationId}/cases

Creates a new case for a specific organization.

* **Operation ID:** `createOrganizationCase`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter        | Type   | Required | Description                              |
| :--------------- | :----- | :------- | :--------------------------------------- |
| `organizationId` | string | Yes      | The unique identifier of the organization. |

---

### Request Body

| Field            | Type    | Required | Description                                       |
| :--------------- | :------ | :------- | :------------------------------------------------ |
| `title`          | string  | Yes      | Title of the case.                                |
| `description`    | string  | Yes      | Description of the case.                          |
| `caseTier`       | integer | Yes      | Case tier level determining the price (1=€9.00, 2=€29.00, 3=€99.00). |
| `caseTypeId`     | string  | Yes      | The ID of the case type for this case.            |
| `paymentIntentId`| string  | No       | Stripe payment intent ID (optional if organization has an active subscription with available quota). |
| `initialPartyIds`| array   | No       | Optional array of party IDs to attach initially.  |
| `assignedUserId` | string  | No       | Optional staff user ID to assign the case to.     |

**Example:**

```json
{
  "title": "Corporate Contract Review",
  "description": "Review of the new supplier agreements for legal compliance.",
  "caseTier": 2,
  "caseTypeId": "contract_review",
  "paymentIntentId": "pi_3NpKs8JHR4975g4B0QU4XKw9",
  "initialPartyIds": ["party_123456", "party_789012"],
  "assignedUserId": "user_def456"
}
```

---

### Responses

#### `201 Created`

Case created successfully.

* Content-Type: `application/json`
* Schema: `#/definitions/Case`

| Field           | Type    | Required | Description                               |
| :-------------- | :------ | :------- | :---------------------------------------- |
| `id`            | string  | Yes      | Unique identifier for the case.           |
| `title`         | string  | Yes      | Title of the case.                        |
| `description`   | string  | No       | Description of the case.                  |
| `status`        | string  | Yes      | Status of the case.                       |
| `organizationId`| string  | Yes      | Organization ID the case belongs to.      |
| `createdAt`     | string  | No       | Timestamp when the case was created.      |
| `updatedAt`     | string  | No       | Timestamp when the case was last updated. |
| `createdBy`     | string  | No       | User ID of the creator.                   |
| `assignedUserId`| string  | No       | User ID of the assigned user.             |
| `assignedUserName`| string| No       | Name of the assigned user.                |
| `parties`       | array   | No       | Parties associated with the case.         |

**Example:**

```json
{
  "id": "case_123456",
  "title": "Corporate Contract Review",
  "description": "Review of the new supplier agreements for legal compliance.",
  "status": "active",
  "organizationId": "org_12345abcde",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z",
  "createdBy": "user_abc123",
  "assignedUserId": "user_def456",
  "assignedUserName": "Jane Smith",
  "parties": [
    {
      "id": "party_123456",
      "name": "Acme Corporation",
      "type": "organization"
    },
    {
      "id": "party_789012",
      "name": "Supplier Inc.",
      "type": "organization"
    }
  ]
}
```

#### `400 Bad Request`

Invalid request format or data.

* Content-Type: `application/json`
* Schema: `#/definitions/BadRequest`

| Field     | Type   | Enum          | Description          |
| :-------- | :----- | :------------ | :------------------- |
| `error`   | string | `bad_request` | Error code.          |
| `message` | string |               | Error message details.|

**Example:**

```json
{
  "error": "bad_request",
  "message": "Missing required field: title"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `402 Payment Required`

Quota exhausted or no active subscription, and paymentIntentId not provided.

* Content-Type: `application/json`
* Schema: `#/definitions/PaymentRequired`

| Field     | Type   | Enum             | Description          |
| :-------- | :----- | :--------------- | :------------------- |
| `error`   | string | `payment_required` | Error code.        |
| `message` | string |                  | Error message details.|

**Example:**

```json
{
  "error": "payment_required",
  "message": "Organization case quota exhausted. Please provide payment or upgrade your subscription."
}
```

#### `403 Forbidden`

User does not have permission to create cases for this organization.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "You do not have permission to create cases for this organization"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

## GET /cases/{caseId}

Retrieves detailed information about a specific case.

* **Operation ID:** `getCase`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                   |
| :-------- | :----- | :------- | :---------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |

---

### Responses

#### `200 OK`

Successfully retrieved the case details.

* Content-Type: `application/json`
* Schema: `#/definitions/Case`

| Field           | Type    | Required | Description                               |
| :-------------- | :------ | :------- | :---------------------------------------- |
| `id`            | string  | Yes      | Unique identifier for the case.           |
| `title`         | string  | Yes      | Title of the case.                        |
| `description`   | string  | No       | Description of the case.                  |
| `status`        | string  | Yes      | Status of the case.                       |
| `organizationId`| string  | Yes      | Organization ID the case belongs to.      |
| `createdAt`     | string  | No       | Timestamp when the case was created.      |
| `updatedAt`     | string  | No       | Timestamp when the case was last updated. |
| `createdBy`     | string  | No       | User ID of the creator.                   |
| `assignedUserId`| string  | No       | User ID of the assigned user.             |
| `assignedUserName`| string| No       | Name of the assigned user.                |
| `caseTypeId`    | string  | Yes      | Type of the case.                         |
| `caseTier`      | integer | Yes      | Tier level of the case.                   |
| `parties`       | array   | No       | Parties associated with the case.         |
| `files`         | array   | No       | Files attached to the case.               |
| `messages`      | array   | No       | Messages in the case conversation.        |

**Example:**

```json
{
  "id": "case_123456",
  "title": "Divorce Settlement",
  "description": "Seeking assistance with divorce proceedings and property division.",
  "status": "active",
  "organizationId": "user_abc123",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-05T14:30:00Z",
  "createdBy": "user_abc123",
  "caseTypeId": "divorce_settlement",
  "caseTier": 2,
  "parties": [
    {
      "id": "party_123456",
      "name": "John Doe",
      "type": "individual",
      "role": "client"
    },
    {
      "id": "party_789012",
      "name": "Jane Doe",
      "type": "individual",
      "role": "opposing_party"
    }
  ],
  "files": [
    {
      "id": "file_123456",
      "name": "marriage_certificate.pdf",
      "contentType": "application/pdf",
      "size": 245789,
      "uploadedAt": "2023-04-02T10:15:00Z",
      "uploadedBy": "user_abc123"
    }
  ],
  "messages": [
    {
      "id": "msg_123456",
      "content": "Hello, I need help with my divorce case.",
      "sender": "user",
      "timestamp": "2023-04-01T12:30:00Z"
    },
    {
      "id": "msg_789012",
      "content": "I understand your situation. Let me help you with the legal aspects of your divorce.",
      "sender": "agent",
      "timestamp": "2023-04-01T12:32:00Z"
    }
  ]
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `403 Forbidden`

User does not have permission to access this case.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "You do not have permission to access this case"
}
```

#### `404 Not Found`

Case not found.

* Content-Type: `application/json`
* Schema: `#/definitions/NotFound`

| Field     | Type   | Enum       | Description          |
| :-------- | :----- | :--------- | :------------------- |
| `error`   | string | `not_found`| Error code.          |
| `message` | string |            | Error message details.|

**Example:**

```json
{
  "error": "not_found",
  "message": "Case not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

## GET /users/me/cases

Returns a list of cases that belong to the current authenticated user.

* **Operation ID:** `listMyCases`
* **Security:** Requires Firebase Authentication

---

### Query Parameters

| Parameter  | Type    | Required | Description                                  |
| :--------- | :------ | :------- | :------------------------------------------- |
| `status`   | string  | No       | Filter by case status (open, archived, deleted). Default: open |
| `limit`    | integer | No       | Maximum number of cases to return. Default: 20 |
| `offset`   | integer | No       | Number of cases to skip. Default: 0         |
| `labelIds` | array   | No       | Filter by label IDs                          |

---

### Responses

#### `200 OK`

Successfully retrieved the list of cases.

* Content-Type: `application/json`

| Field    | Type    | Required | Description                                 |
| :------- | :------ | :------- | :------------------------------------------ |
| `cases`  | array   | Yes      | List of case objects.                       |
| `total`  | integer | Yes      | Total number of cases matching the criteria. |
| `limit`  | integer | Yes      | Maximum number of cases returned.           |
| `offset` | integer | Yes      | Number of cases skipped.                    |

Each case in the array has the following structure:

| Field           | Type    | Required | Description                            |
| :-------------- | :------ | :------- | :------------------------------------- |
| `id`            | string  | Yes      | Unique identifier for the case.        |
| `title`         | string  | Yes      | Title of the case.                     |
| `status`        | string  | Yes      | Status of the case.                    |
| `createdAt`     | string  | Yes      | Creation timestamp.                    |
| `paymentStatus` | string  | No       | Payment status.                        |
| `caseTier`      | integer | No       | Case tier level (1, 2, or 3).          |
| `labels`        | array   | No       | Array of label objects.                |
| `parties`       | array   | No       | Array of party summary objects.        |

**Example:**

```json
{
  "cases": [
    {
      "id": "case_123456",
      "title": "Divorce Settlement",
      "status": "open",
      "createdAt": "2023-04-01T12:00:00Z",
      "paymentStatus": "covered_by_quota",
      "caseTier": 2,
      "labels": [
        {
          "labelId": "label_123",
          "name": "Urgent",
          "color": "#FF0000"
        }
      ],
      "parties": [
        {
          "partyId": "party_456",
          "nameDisplay": "John Doe"
        }
      ]
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

## GET /organizations/{organizationId}/cases

Returns a list of cases that belong to the specified organization.

* **Operation ID:** `listOrganizationCases`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter        | Type   | Required | Description                              |
| :--------------- | :----- | :------- | :--------------------------------------- |
| `organizationId` | string | Yes      | The unique identifier of the organization. |

---

### Query Parameters

| Parameter       | Type    | Required | Description                                  |
| :-------------- | :------ | :------- | :------------------------------------------- |
| `status`        | string  | No       | Filter by case status (open, archived, deleted). Default: open |
| `limit`         | integer | No       | Maximum number of cases to return. Default: 20 |
| `offset`        | integer | No       | Number of cases to skip. Default: 0         |
| `labelIds`      | array   | No       | Filter by label IDs                          |
| `assignedUserId`| string  | No       | Filter by assigned staff member (admin only) |

---

### Responses

#### `200 OK`

Successfully retrieved the list of cases.

* Content-Type: `application/json`

| Field    | Type    | Required | Description                                 |
| :------- | :------ | :------- | :------------------------------------------ |
| `cases`  | array   | Yes      | List of case objects.                       |
| `total`  | integer | Yes      | Total number of cases matching the criteria. |
| `limit`  | integer | Yes      | Maximum number of cases returned.           |
| `offset` | integer | Yes      | Number of cases skipped.                    |

Each case in the array has the following structure:

| Field           | Type    | Required | Description                            |
| :-------------- | :------ | :------- | :------------------------------------- |
| `id`            | string  | Yes      | Unique identifier for the case.        |
| `title`         | string  | Yes      | Title of the case.                     |
| `status`        | string  | Yes      | Status of the case.                    |
| `createdAt`     | string  | Yes      | Creation timestamp.                    |
| `organizationId`| string  | Yes      | Organization ID.                       |
| `assignedUserId`| string  | No       | User ID of assigned staff member.      |
| `assignedUserName`| string| No       | Name of assigned staff member.         |
| `labels`        | array   | No       | Array of label objects.                |
| `parties`       | array   | No       | Array of party summary objects.        |

**Example:**

```json
{
  "cases": [
    {
      "id": "case_123456",
      "title": "Corporate Contract Review",
      "status": "open",
      "createdAt": "2023-04-01T12:00:00Z",
      "organizationId": "org_12345abcde",
      "assignedUserId": "user_def456",
      "assignedUserName": "Jane Smith",
      "labels": [
        {
          "labelId": "label_123",
          "name": "Urgent",
          "color": "#FF0000"
        }
      ],
      "parties": [
        {
          "partyId": "party_456",
          "nameDisplay": "Acme Corporation"
        }
      ]
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

#### `400 Bad Request`

Invalid request format or parameters.

* Content-Type: `application/json`
* Schema: `#/definitions/BadRequest`

| Field     | Type   | Enum          | Description          |
| :-------- | :----- | :------------ | :------------------- |
| `error`   | string | `bad_request` | Error code.          |
| `message` | string |               | Error message details.|

**Example:**

```json
{
  "error": "bad_request",
  "message": "Invalid status parameter"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `403 Forbidden`

User does not have permission to view cases for this organization.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "You do not have permission to view cases for this organization"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

## POST /cases/{caseId}/archive

Archives a specific case.

* **Operation ID:** `archiveCase`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                   |
| :-------- | :----- | :------- | :---------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |

---

### Responses

#### `200 OK`

Case successfully archived.

* Content-Type: `application/json`

| Field     | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `success` | boolean| Yes      | Indicates successful operation.|
| `caseId`  | string | Yes      | ID of the archived case.       |

**Example:**

```json
{
  "success": true,
  "caseId": "case_123456"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `403 Forbidden`

User does not have permission to archive this case.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "You do not have permission to archive this case"
}
```

#### `404 Not Found`

Case not found.

* Content-Type: `application/json`
* Schema: `#/definitions/NotFound`

| Field     | Type   | Enum       | Description          |
| :-------- | :----- | :--------- | :------------------- |
| `error`   | string | `not_found`| Error code.          |
| `message` | string |            | Error message details.|

**Example:**

```json
{
  "error": "not_found",
  "message": "Case not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

## DELETE /cases/{caseId}

Deletes a specific case.

* **Operation ID:** `deleteCase`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                   |
| :-------- | :----- | :------- | :---------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |

---

### Responses

#### `200 OK`

Case successfully deleted.

* Content-Type: `application/json`

| Field     | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `success` | boolean| Yes      | Indicates successful operation.|
| `caseId`  | string | Yes      | ID of the deleted case.        |

**Example:**

```json
{
  "success": true,
  "caseId": "case_123456"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `403 Forbidden`

User does not have permission to delete this case.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "You do not have permission to delete this case"
}
```

#### `404 Not Found`

Case not found.

* Content-Type: `application/json`
* Schema: `#/definitions/NotFound`

| Field     | Type   | Enum       | Description          |
| :-------- | :----- | :--------- | :------------------- |
| `error`   | string | `not_found`| Error code.          |
| `message` | string |            | Error message details.|

**Example:**

```json
{
  "error": "not_found",
  "message": "Case not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

## PUT /cases/{caseId}/assign

Assigns a case to a staff member (for organization administrators only).

* **Operation ID:** `assignCase`
* **Security:** Requires Firebase Authentication with administrator role

---

### Path Parameters

| Parameter | Type   | Required | Description                   |
| :-------- | :----- | :------- | :---------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |

---

### Request Body

| Field           | Type   | Required | Description                            |
| :-------------- | :----- | :------- | :------------------------------------- |
| `assignedUserId`| string | Yes      | User ID of the staff member to assign. |

**Example:**

```json
{
  "assignedUserId": "user_def456"
}
```

---

### Responses

#### `200 OK`

Case successfully assigned.

* Content-Type: `application/json`

| Field            | Type   | Required | Description                             |
| :--------------- | :----- | :------- | :-------------------------------------- |
| `success`        | boolean| Yes      | Indicates successful operation.         |
| `caseId`         | string | Yes      | ID of the case.                         |
| `assignedUserId` | string | Yes      | User ID of the assigned staff member.   |
| `assignedUserName`| string| No       | Name of the assigned staff member.      |

**Example:**

```json
{
  "success": true,
  "caseId": "case_123456",
  "assignedUserId": "user_def456",
  "assignedUserName": "Jane Smith"
}
```

#### `400 Bad Request`

Invalid request format or missing required fields.

* Content-Type: `application/json`
* Schema: `#/definitions/BadRequest`

| Field     | Type   | Enum          | Description          |
| :-------- | :----- | :------------ | :------------------- |
| `error`   | string | `bad_request` | Error code.          |
| `message` | string |               | Error message details.|

**Example:**

```json
{
  "error": "bad_request",
  "message": "Missing required field: assignedUserId"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `403 Forbidden`

User does not have administrator permissions.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "Only organization administrators can assign cases"
}
```

#### `404 Not Found`

Case or user not found.

* Content-Type: `application/json`
* Schema: `#/definitions/NotFound`

| Field     | Type   | Enum       | Description          |
| :-------- | :----- | :--------- | :------------------- |
| `error`   | string | `not_found`| Error code.          |
| `message` | string |            | Error message details.|

**Example:**

```json
{
  "error": "not_found",
  "message": "Case or assigned user not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

### Party Management

## POST /cases/{caseId}/parties

Attaches a party to a case.

* **Operation ID:** `attachPartyToCase`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |

---

### Request Body

| Field     | Type   | Required | Description                               |
| :-------- | :----- | :------- | :---------------------------------------- |
| `partyId` | string | Yes      | ID of the party to attach to the case.    |
| `role`    | string | Yes      | Role of the party in the case (client, opposing_party, witness, etc.). |

**Example:**

```json
{
  "partyId": "party_123456",
  "role": "client"
}
```

---

### Responses

#### `200 OK`

Party successfully attached to the case.

* Content-Type: `application/json`

| Field     | Type    | Required | Description                       |
| :-------- | :------ | :------- | :-------------------------------- |
| `success` | boolean | Yes      | Indicates successful operation.   |
| `caseId`  | string  | Yes      | ID of the case.                   |
| `partyId` | string  | Yes      | ID of the attached party.         |
| `role`    | string  | Yes      | Role of the party in the case.    |

**Example:**

```json
{
  "success": true,
  "caseId": "case_123456",
  "partyId": "party_123456",
  "role": "client"
}
```

#### `400 Bad Request`

Invalid request format or missing required fields.

* Content-Type: `application/json`
* Schema: `#/definitions/BadRequest`

| Field     | Type   | Enum          | Description          |
| :-------- | :----- | :------------ | :------------------- |
| `error`   | string | `bad_request` | Error code.          |
| `message` | string |               | Error message details.|

**Example:**

```json
{
  "error": "bad_request",
  "message": "Missing required field: partyId"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `403 Forbidden`

User does not have permission to attach parties to this case.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "You do not have permission to attach parties to this case"
}
```

#### `404 Not Found`

Case or party not found.

* Content-Type: `application/json`
* Schema: `#/definitions/NotFound`

| Field     | Type   | Enum       | Description          |
| :-------- | :----- | :--------- | :------------------- |
| `error`   | string | `not_found`| Error code.          |
| `message` | string |            | Error message details.|

**Example:**

```json
{
  "error": "not_found",
  "message": "Case or party not found"
}
```

#### `409 Conflict`

Party is already attached to the case.

* Content-Type: `application/json`
* Schema: `#/definitions/Conflict`

| Field     | Type   | Enum       | Description          |
| :-------- | :----- | :--------- | :------------------- |
| `error`   | string | `conflict` | Error code.          |
| `message` | string |            | Error message details.|

**Example:**

```json
{
  "error": "conflict",
  "message": "Party is already attached to this case"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

## DELETE /cases/{caseId}/parties/{partyId}

Detaches a party from a case.

* **Operation ID:** `detachPartyFromCase`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |
| `partyId` | string | Yes      | The unique identifier of the party to detach. |

---

### Responses

#### `200 OK`

Party successfully detached from the case.

* Content-Type: `application/json`

| Field     | Type    | Required | Description                       |
| :-------- | :------ | :------- | :-------------------------------- |
| `success` | boolean | Yes      | Indicates successful operation.   |
| `caseId`  | string  | Yes      | ID of the case.                   |
| `partyId` | string  | Yes      | ID of the detached party.         |

**Example:**

```json
{
  "success": true,
  "caseId": "case_123456",
  "partyId": "party_123456"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `403 Forbidden`

User does not have permission to detach parties from this case.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "You do not have permission to detach parties from this case"
}
```

#### `404 Not Found`

Case, party, or relationship not found.

* Content-Type: `application/json`
* Schema: `#/definitions/NotFound`

| Field     | Type   | Enum       | Description          |
| :-------- | :----- | :--------- | :------------------- |
| `error`   | string | `not_found`| Error code.          |
| `message` | string |            | Error message details.|

**Example:**

```json
{
  "error": "not_found",
  "message": "Party is not attached to this case"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

### Files Management

## POST /cases/{caseId}/files

Uploads a file to a case.

* **Operation ID:** `uploadFile`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |

---

### Request Body

This endpoint expects a multipart/form-data request with the following parameters:

| Field        | Type   | Required | Description                         |
| :----------- | :----- | :------- | :---------------------------------- |
| `file`       | file   | Yes      | The file to upload.                 |
| `title`      | string | No       | Custom title for the file.          |
| `description`| string | No       | Description of the file.            |

---

### Responses

#### `200 OK`

File successfully uploaded.

* Content-Type: `application/json`

| Field          | Type   | Required | Description                               |
| :------------- | :----- | :------- | :---------------------------------------- |
| `fileId`       | string | Yes      | Unique identifier for the uploaded file.  |
| `fileName`     | string | Yes      | Original name of the file.                |
| `title`        | string | No       | Custom title for the file.                |
| `description`  | string | No       | Description of the file.                  |
| `size`         | integer| Yes      | Size of the file in bytes.                |
| `contentType`  | string | Yes      | MIME type of the file.                    |
| `uploadedAt`   | string | Yes      | Timestamp when the file was uploaded.     |
| `uploadedBy`   | string | Yes      | User ID of the uploader.                  |
| `downloadUrl`  | string | Yes      | Temporary URL to download the file.       |

**Example:**

```json
{
  "fileId": "file_123456",
  "fileName": "marriage_certificate.pdf",
  "title": "Marriage Certificate",
  "description": "Original marriage certificate document",
  "size": 245789,
  "contentType": "application/pdf",
  "uploadedAt": "2023-04-02T10:15:00Z",
  "uploadedBy": "user_abc123",
  "downloadUrl": "https://api.relex.ro/v1/files/file_123456"
}
```

#### `400 Bad Request`

Invalid request format or file type not allowed.

* Content-Type: `application/json`
* Schema: `#/definitions/BadRequest`

| Field     | Type   | Enum          | Description          |
| :-------- | :----- | :------------ | :------------------- |
| `error`   | string | `bad_request` | Error code.          |
| `message` | string |               | Error message details.|

**Example:**

```json
{
  "error": "bad_request",
  "message": "File type not allowed"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `403 Forbidden`

User does not have permission to upload files to this case.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "You do not have permission to upload files to this case"
}
```

#### `404 Not Found`

Case not found.

* Content-Type: `application/json`
* Schema: `#/definitions/NotFound`

| Field     | Type   | Enum       | Description          |
| :-------- | :----- | :--------- | :------------------- |
| `error`   | string | `not_found`| Error code.          |
| `message` | string |            | Error message details.|

**Example:**

```json
{
  "error": "not_found",
  "message": "Case not found"
}
```

#### `413 Payload Too Large`

File size exceeds allowed limit.

* Content-Type: `application/json`
* Schema: `#/definitions/PayloadTooLarge`

| Field     | Type   | Enum                | Description          |
| :-------- | :----- | :------------------ | :------------------- |
| `error`   | string | `payload_too_large` | Error code.          |
| `message` | string |                     | Error message details.|

**Example:**

```json
{
  "error": "payload_too_large",
  "message": "File size exceeds the maximum allowed limit of 10MB"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

## GET /files/{fileId}

Downloads a file.

* **Operation ID:** `downloadFile`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                     |
| :-------- | :----- | :------- | :------------------------------ |
| `fileId`  | string | Yes      | The unique identifier of the file. |

---

### Responses

#### `200 OK`

File successfully retrieved.

* Content-Type: The MIME type of the file
* Headers:
  - `Content-Disposition`: attachment; filename="filename.ext"
  - `Content-Length`: Size of the file in bytes
  - `Content-Type`: MIME type of the file

The response body contains the binary content of the file.

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`
* Schema: `#/definitions/Unauthorized`

| Field     | Type   | Enum           | Description          |
| :-------- | :----- | :------------- | :------------------- |
| `error`   | string | `unauthorized` | Error code.          |
| `message` | string |                | Error message details.|

**Example:**

```json
{
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

#### `403 Forbidden`

User does not have permission to download this file.

* Content-Type: `application/json`
* Schema: `#/definitions/Forbidden`

| Field     | Type   | Enum        | Description          |
| :-------- | :----- | :---------- | :------------------- |
| `error`   | string | `forbidden` | Error code.          |
| `message` | string |             | Error message details.|

**Example:**

```json
{
  "error": "forbidden",
  "message": "You do not have permission to download this file"
}
```

#### `404 Not Found`

File not found.

* Content-Type: `application/json`
* Schema: `#/definitions/NotFound`

| Field     | Type   | Enum       | Description          |
| :-------- | :----- | :--------- | :------------------- |
| `error`   | string | `not_found`| Error code.          |
| `message` | string |            | Error message details.|

**Example:**

```json
{
  "error": "not_found",
  "message": "File not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`
* Schema: `#/definitions/InternalServerError`

| Field     | Type   | Enum                  | Description          |
| :-------- | :----- | :-------------------- | :------------------- |
| `error`   | string | `internal_server_error` | Error code.        |
| `message` | string |                       | Error message details.|

**Example:**

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```
