# Relex API Documentation

> **Important Note**: This API documentation reflects the actual implementation in the codebase (`functions/src/*.py`), which serves as the primary source of truth. Developer Notes have been added to endpoints where discrepancies with the OpenAPI specification (`terraform/openapi_spec.yaml`) were identified. See the [Summary of API Documentation Updates and Identified Discrepancies](#summary-of-api-documentation-updates-and-identified-discrepancies) section at the end of this document for a comprehensive list of all identified inconsistencies.

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

* **Operation ID:** `relex_backend_create_case`
* **Security:** Requires Firebase Authentication

---

### Request Body

| Field            | Type    | Required | Description                                       |
| :--------------- | :------ | :------- | :------------------------------------------------ |
| `title`          | string  | Yes      | Title of the case.                                |
| `description`    | string  | Yes      | Description of the case.                          |
| `caseTier`       | integer | Yes      | Case tier level determining the price (1=€9.00, 2=€29.00, 3=€99.00). |
| `caseTypeId`     | string  | Yes      | The ID of the case type for this case.            |
| `organizationId` | string  | No       | Organization ID if creating a case for an organization. If omitted, creates an individual case. |
| `paymentIntentId`| string  | No       | Stripe payment intent ID (optional if user/organization has an active subscription with available quota). |
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

| Field           | Type    | Description                               |
| :-------------- | :------ | :---------------------------------------- |
| `caseId`        | string  | Unique identifier for the case.           |
| `status`        | string  | Status of the case (initially "open").    |

**Example:**

```json
{
  "caseId": "case_123456",
  "status": "open"
}
```

#### `400 Bad Request`

Invalid request format or data.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "Valid title is required"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission for this action.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to create cases"
}
```

#### `404 Not Found`

User or organization not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Organization not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Failed to create case: [error details]"
}
```

**Developer Note:** The code implementation doesn't explicitly check for or return a `402 Payment Required` status code when the quota is exhausted, though this is defined in the OpenAPI spec. Also, the response structure in the code returns a simplified object with just `caseId` and `status`, not the full case object as described in the spec.

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
  "message": "Case quota exhausted. Please provide payment or upgrade your subscription."
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

* **Operation ID:** `relex_backend_get_case`
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

| Field           | Type    | Description                               |
| :-------------- | :------ | :---------------------------------------- |
| All case fields | various | All fields stored in the case document, plus `caseId`. |

**Example:**

```json
{
  "userId": "user_abc123",
  "title": "Divorce Settlement",
  "description": "Seeking assistance with divorce proceedings and property division.",
  "status": "open",
  "caseTier": 2,
  "caseTypeId": "divorce_settlement",
  "casePrice": 2900,
  "paymentStatus": "paid",
  "creationDate": "2023-04-01T12:00:00Z",
  "organizationId": null,
  "caseId": "case_123456"
}
```

#### `400 Bad Request`

Case ID is missing from the URL path.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "Case ID missing in URL path"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to access this case.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to access this case"
}
```

#### `404 Not Found`

Case not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Case not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Failed to retrieve case"
}
```

**Developer Note:** The code implementation returns all fields from the Firestore document as-is, with the addition of a `caseId` field. This differs from the OpenAPI specification which defines a more structured response schema with specific fields. The actual response fields will depend on what's stored in the Firestore document.

## GET /users/me/cases

Returns a list of cases that belong to the current authenticated user.

* **Operation ID:** `relex_backend_list_cases`
* **Security:** Requires Firebase Authentication

---

### Query Parameters

| Parameter  | Type    | Required | Description                                  |
| :--------- | :------ | :------- | :------------------------------------------- |
| `status`   | string  | No       | Filter by case status (open, closed, archived). Default: excludes deleted cases |
| `limit`    | integer | No       | Maximum number of cases to return. Default: 50, Max: 100 |
| `offset`   | integer | No       | Number of cases to skip. Default: 0         |

---

### Responses

#### `200 OK`

Successfully retrieved the list of user cases.

* Content-Type: `application/json`

| Field         | Type    | Description                               |
| :------------ | :------ | :---------------------------------------- |
| `cases`       | array   | Array of case objects with all their fields. |
| `pagination`  | object  | Pagination details.                       |
| `pagination.total` | integer | Total number of cases matching the query. |
| `pagination.limit` | integer | Limit used for the query.            |
| `pagination.offset` | integer | Offset used for the query.          |
| `pagination.hasMore` | boolean | Indicates if there are more cases available. |
| `organizationId` | string | Organization ID if requested (null for individual cases). |

**Example:**

```json
{
  "cases": [
    {
      "userId": "user_abc123",
      "title": "Divorce Settlement",
      "description": "Seeking assistance with divorce proceedings and property division.",
      "status": "open",
      "caseTier": 2,
      "caseTypeId": "divorce_settlement",
      "casePrice": 2900,
      "paymentStatus": "paid",
      "creationDate": "2023-04-01T12:00:00Z",
      "caseId": "case_123456"
    },
    {
      "userId": "user_abc123",
      "title": "Will Creation",
      "description": "Creating a last will and testament.",
      "status": "open",
      "caseTier": 1,
      "caseTypeId": "will_creation",
      "casePrice": 900,
      "paymentStatus": "paid",
      "creationDate": "2023-03-15T10:30:00Z",
      "caseId": "case_789012"
    }
  ],
  "pagination": {
    "total": 5,
    "limit": 50,
    "offset": 0,
    "hasMore": false
  },
  "organizationId": null
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Failed to list cases"
}
```

**Developer Note:** The code implementation differs from the OpenAPI spec as it supports different valid statuses ("open", "closed", "archived") and has a different response structure with pagination information. The OpenAPI spec also includes optional `labelIds` as a query parameter, which is not implemented in the code.

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

Archives a case, making it inaccessible to normal case listings but still retrievable.

* **Operation ID:** `relex_backend_archive_case`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |

---

### Responses

#### `200 OK`

Case successfully archived.

* Content-Type: `application/json`

| Field     | Type   | Description                 |
| :-------- | :----- | :-------------------------- |
| `message` | string | Success message.            |

**Example:**

```json
{
  "message": "Case archived successfully"
}
```

#### `400 Bad Request`

Case ID is missing from the URL path.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "Case ID missing in URL path"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to archive this case.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to archive this case"
}
```

#### `404 Not Found`

Case not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Case not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Failed to archive case"
}
```

**Developer Note:** The code implementation returns a simple 200 OK response with a message rather than returning a full case object as might be expected in a RESTful API. It also adds timestamps for the archiving action in the database but does not return these in the response.

## DELETE /cases/{caseId}

Marks a case as deleted (soft delete). The case will not appear in regular listings but remains in the database.

* **Operation ID:** `relex_backend_delete_case`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |

---

### Responses

#### `200 OK`

Case successfully marked as deleted.

* Content-Type: `application/json`

| Field     | Type   | Description                 |
| :-------- | :----- | :-------------------------- |
| `message` | string | Success message.            |

**Example:**

```json
{
  "message": "Case marked as deleted successfully"
}
```

#### `400 Bad Request`

Case ID is missing from the URL path.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "Case ID missing in URL path"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to delete this case.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to delete this case"
}
```

#### `404 Not Found`

Case not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Case not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Failed to delete case"
}
```

**Developer Note:** This is a soft delete operation that changes the case status to "deleted" rather than actually removing it from the database. The code implementation returns a simple success message rather than the deleted case data as might be expected in a RESTful API.

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

## POST /organizations

Creates a new organization and adds the authenticated user as an administrator.

* **Operation ID:** `relex_backend_create_organization`
* **Security:** Requires Firebase Authentication

---

### Request Body

| Field         | Type   | Required | Description                                  |
| :------------ | :----- | :------- | :------------------------------------------- |
| `name`        | string | Yes      | Name of the organization.                    |
| `description` | string | No       | Description of the organization.             |
| `address`     | object | No       | Physical address of the organization.        |
| `contactInfo` | object | No       | Contact information for the organization.    |

**Example:**

```json
{
  "name": "Acme Corporation",
  "description": "Legal services company",
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zipCode": "10001",
    "country": "USA"
  },
  "contactInfo": {
    "email": "contact@acmecorp.com",
    "phone": "+1234567890",
    "website": "https://acmecorp.com"
  }
}
```

---

### Responses

#### `201 Created`

Organization successfully created.

* Content-Type: `application/json`

| Field               | Type    | Description                                      |
| :------------------ | :------ | :----------------------------------------------- |
| `id`                | string  | Unique identifier of the organization.           |
| `name`              | string  | Name of the organization.                        |
| `description`       | string  | Description of the organization.                 |
| `address`           | object  | Physical address of the organization.            |
| `contactInfo`       | object  | Contact information for the organization.        |
| `createdBy`         | string  | User ID of the creator.                          |
| `createdAt`         | string  | Timestamp when the organization was created.     |
| `updatedAt`         | string  | Timestamp when the organization was last updated.|
| `subscriptionStatus`| string  | Current subscription status (initially null).    |
| `stripeCustomerId`  | string  | Stripe customer ID (initially null).             |
| `stripeSubscriptionId`| string| Stripe subscription ID (initially null).         |
| `subscriptionPlanId`| string  | Subscription plan ID (initially null).           |
| `caseQuotaTotal`    | integer | Total case quota (initially 0).                  |
| `caseQuotaUsed`     | integer | Used case quota (initially 0).                   |
| `billingCycleStart` | string  | Start of billing cycle (initially null).         |
| `billingCycleEnd`   | string  | End of billing cycle (initially null).           |

**Example:**

```json
{
  "id": "org_12345abcde",
  "name": "Acme Corporation",
  "description": "Legal services company",
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zipCode": "10001",
    "country": "USA"
  },
  "contactInfo": {
    "email": "contact@acmecorp.com",
    "phone": "+1234567890",
    "website": "https://acmecorp.com"
  },
  "createdBy": "user_abc123",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z",
  "subscriptionStatus": null,
  "stripeCustomerId": null,
  "stripeSubscriptionId": null,
  "subscriptionPlanId": null,
  "caseQuotaTotal": 0,
  "caseQuotaUsed": 0,
  "billingCycleStart": null,
  "billingCycleEnd": null
}
```

#### `400 Bad Request`

Invalid request format or missing required fields.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "Valid organization name is required"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error creating organization"
}
```

## GET /organizations/{organizationId}

Retrieves information about a specific organization.

* **Operation ID:** `relex_backend_get_organization`
* **Security:** Requires Firebase Authentication

---

### Query Parameters

| Parameter        | Type   | Required | Description                              |
| :--------------- | :----- | :------- | :--------------------------------------- |
| `organizationId` | string | Yes      | The unique identifier of the organization. |

---

### Responses

#### `200 OK`

Successfully retrieved organization information.

* Content-Type: `application/json`

| Field               | Type    | Description                                      |
| :------------------ | :------ | :----------------------------------------------- |
| `id`                | string  | Unique identifier of the organization.           |
| `name`              | string  | Name of the organization.                        |
| `description`       | string  | Description of the organization.                 |
| `address`           | object  | Physical address of the organization.            |
| `contactInfo`       | object  | Contact information for the organization.        |
| `createdBy`         | string  | User ID of the creator.                          |
| `createdAt`         | string  | Timestamp when the organization was created.     |
| `updatedAt`         | string  | Timestamp when the organization was last updated.|
| `subscriptionStatus`| string  | Current subscription status.                     |
| `stripeCustomerId`  | string  | Stripe customer ID.                              |
| `stripeSubscriptionId`| string| Stripe subscription ID.                          |
| `subscriptionPlanId`| string  | Subscription plan ID.                            |
| `caseQuotaTotal`    | integer | Total case quota.                                |
| `caseQuotaUsed`     | integer | Used case quota.                                 |
| `billingCycleStart` | string  | Start of billing cycle.                          |
| `billingCycleEnd`   | string  | End of billing cycle.                            |

**Example:**

```json
{
  "id": "org_12345abcde",
  "name": "Acme Corporation",
  "description": "Legal services company",
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zipCode": "10001",
    "country": "USA"
  },
  "contactInfo": {
    "email": "contact@acmecorp.com",
    "phone": "+1234567890",
    "website": "https://acmecorp.com"
  },
  "createdBy": "user_abc123",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z",
  "subscriptionStatus": "active",
  "stripeCustomerId": "cus_12345abcde",
  "stripeSubscriptionId": "sub_12345abcde",
  "subscriptionPlanId": "plan_standard",
  "caseQuotaTotal": 10,
  "caseQuotaUsed": 3,
  "billingCycleStart": "2023-04-01T00:00:00Z",
  "billingCycleEnd": "2023-05-01T00:00:00Z"
}
```

#### `400 Bad Request`

Missing organization ID parameter.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "Organization ID query parameter is required"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to access this organization.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to access this organization"
}
```

#### `404 Not Found`

Organization not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Organization not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error retrieving organization"
}
```

## PUT /organizations/{organizationId}

Updates an existing organization.

* **Operation ID:** `relex_backend_update_organization`
* **Security:** Requires Firebase Authentication with administrator permission on the organization

---

### Request Body

| Field         | Type   | Required | Description                                  |
| :------------ | :----- | :------- | :------------------------------------------- |
| `organizationId` | string | Yes      | The unique identifier of the organization.  |
| `name`        | string | No       | Name of the organization.                    |
| `description` | string | No       | Description of the organization.             |
| `address`     | object | No       | Physical address of the organization.        |
| `contactInfo` | object | No       | Contact information for the organization.    |

**Example:**

```json
{
  "organizationId": "org_12345abcde",
  "name": "Acme Corporation Updated",
  "description": "Legal and consulting services company",
  "address": {
    "street": "456 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zipCode": "94105",
    "country": "USA"
  },
  "contactInfo": {
    "email": "new-contact@acmecorp.com",
    "phone": "+1987654321",
    "website": "https://acmecorp-updated.com"
  }
}
```

---

### Responses

#### `200 OK`

Organization successfully updated.

* Content-Type: `application/json`

| Field               | Type    | Description                                      |
| :------------------ | :------ | :----------------------------------------------- |
| All organization fields | various | All the updated fields of the organization.  |

**Example:**

```json
{
  "id": "org_12345abcde",
  "name": "Acme Corporation Updated",
  "description": "Legal and consulting services company",
  "address": {
    "street": "456 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zipCode": "94105",
    "country": "USA"
  },
  "contactInfo": {
    "email": "new-contact@acmecorp.com",
    "phone": "+1987654321",
    "website": "https://acmecorp-updated.com"
  },
  "createdBy": "user_abc123",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-15T14:30:00Z",
  "updatedBy": "user_abc123",
  "subscriptionStatus": "active",
  "stripeCustomerId": "cus_12345abcde",
  "stripeSubscriptionId": "sub_12345abcde",
  "subscriptionPlanId": "plan_standard",
  "caseQuotaTotal": 10,
  "caseQuotaUsed": 3,
  "billingCycleStart": "2023-04-01T00:00:00Z",
  "billingCycleEnd": "2023-05-01T00:00:00Z"
}
```

#### `400 Bad Request`

Invalid request format or data.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "Organization ID is required in request body"
}
```

Or:

```json
{
  "error": "Bad Request",
  "message": "Organization name cannot be empty"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to update this organization.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to update this organization"
}
```

#### `404 Not Found`

Organization not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Organization not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error updating organization"
}
```

Or:

```json
{
  "error": "Database Error",
  "message": "Failed to update organization: [error details]"
}
```

## DELETE /organizations/{organizationId}

Deletes an organization and related data (memberships, marks cases as deleted).

* **Operation ID:** `relex_backend_delete_organization`
* **Security:** Requires Firebase Authentication with administrator permission on the organization

---

### Request Body

| Field           | Type   | Required | Description                                  |
| :-------------- | :----- | :------- | :------------------------------------------- |
| `organizationId`| string | Yes      | The unique identifier of the organization.   |

**Example:**

```json
{
  "organizationId": "org_12345abcde"
}
```

---

### Responses

#### `200 OK`

Organization successfully deleted.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `message` | string | Success message.     |

**Example:**

```json
{
  "message": "Organization deleted successfully"
}
```

#### `400 Bad Request`

Invalid request format or data.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "Organization ID is required"
}
```

Or:

```json
{
  "error": "Bad Request",
  "message": "Cannot delete organization with active subscription. Please cancel the subscription first."
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to delete this organization.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to delete this organization"
}
```

#### `404 Not Found`

Organization not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Organization not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error deleting organization"
}
```

Or:

```json
{
  "error": "Database Error",
  "message": "Failed to delete organization: [error details]"
}
```

## GET /users/me

Retrieves the profile of the authenticated user.

* **Operation ID:** `relex_backend_get_user_profile`
* **Security:** Requires Firebase Authentication

---

### Responses

#### `200 OK`

Successfully retrieved user profile.

* Content-Type: `application/json`

| Field               | Type   | Description                                      |
| :------------------ | :----- | :----------------------------------------------- |
| `userId`            | string | The unique identifier of the authenticated user. |
| `email`             | string | Email address of the user.                       |
| `displayName`       | string | Display name of the user.                        |
| `photoURL`          | string | URL to the user's profile photo.                 |
| `role`              | string | User's role in the system.                       |
| `subscriptionStatus`| string | Status of the user's subscription.               |
| `languagePreference`| string | User's preferred language.                       |
| `createdAt`         | string | Timestamp when the user profile was created.     |
| `updatedAt`         | string | Timestamp when the user profile was last updated.|

**Example:**

```json
{
  "userId": "user_abc123",
  "email": "user@example.com",
  "displayName": "John Doe",
  "photoURL": "https://example.com/profile.jpg",
  "role": "user",
  "subscriptionStatus": null,
  "languagePreference": "en",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "User authentication context missing"
}
```

#### `404 Not Found`

User profile not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "User profile not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Failed to retrieve user profile"
}
```

## PUT /users/me

Updates the profile of the authenticated user.

* **Operation ID:** `relex_backend_update_user_profile`
* **Security:** Requires Firebase Authentication

---

### Request Body

| Field               | Type   | Required | Description                                 |
| :------------------ | :----- | :------- | :------------------------------------------ |
| `displayName`       | string | No       | New display name for the user.              |
| `photoURL`          | string | No       | New URL to the user's profile photo.        |
| `languagePreference`| string | No       | New preferred language (en, ro, fr, de, es).|

**Example:**

```json
{
  "displayName": "John Smith",
  "photoURL": "https://example.com/new-profile.jpg",
  "languagePreference": "fr"
}
```

---

### Responses

#### `200 OK`

User profile successfully updated.

* Content-Type: `application/json`

| Field               | Type   | Description                                      |
| :------------------ | :----- | :----------------------------------------------- |
| `userId`            | string | The unique identifier of the authenticated user. |
| `email`             | string | Email address of the user.                       |
| `displayName`       | string | Updated display name of the user.                |
| `photoURL`          | string | Updated URL to the user's profile photo.         |
| `role`              | string | User's role in the system.                       |
| `subscriptionStatus`| string | Status of the user's subscription.               |
| `languagePreference`| string | Updated preferred language.                      |
| `createdAt`         | string | Timestamp when the user profile was created.     |
| `updatedAt`         | string | Timestamp when the user profile was last updated.|

**Example:**

```json
{
  "userId": "user_abc123",
  "email": "user@example.com",
  "displayName": "John Smith",
  "photoURL": "https://example.com/new-profile.jpg",
  "role": "user",
  "subscriptionStatus": null,
  "languagePreference": "fr",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-15T14:30:00Z"
}
```

#### `400 Bad Request`

Invalid request format or data.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "No JSON data provided"
}
```

Or:

```json
{
  "error": "Bad Request",
  "message": "Language preference must be one of: en, ro, fr, de, es"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "User authentication context missing"
}
```

#### `404 Not Found`

User profile not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "User profile not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Failed to update user profile"
}
```

## POST /parties

Creates a new party (individual or organization) associated with the authenticated user.

* **Operation ID:** `relex_backend_create_party`
* **Security:** Requires Firebase Authentication

---

### Request Body

| Field           | Type   | Required | Description                                  |
| :-------------- | :----- | :------- | :------------------------------------------- |
| `partyType`     | string | Yes      | Type of party ("individual" or "organization"). |
| `nameDetails`   | object | Yes      | Name details appropriate for the party type. |
| `identityCodes` | object | Yes      | Identification codes for the party.          |
| `contactInfo`   | object | Yes      | Contact information for the party.           |
| `signatureData` | object | No       | Optional signature data for the party.       |

For `nameDetails`, when `partyType` is "individual":
| Field        | Type   | Required | Description         |
| :----------- | :----- | :------- | :------------------ |
| `firstName`  | string | Yes      | First name.         |
| `lastName`   | string | Yes      | Last name.          |

For `nameDetails`, when `partyType` is "organization":
| Field         | Type   | Required | Description         |
| :------------ | :----- | :------- | :------------------ |
| `companyName` | string | Yes      | Company name.       |

For `identityCodes`, when `partyType` is "individual":
| Field | Type   | Required | Description                            |
| :---- | :----- | :------- | :------------------------------------- |
| `cnp` | string | Yes      | CNP (Romanian personal numeric code, must be 13 digits). |

For `identityCodes`, when `partyType` is "organization":
| Field    | Type   | Required | Description                        |
| :------- | :----- | :------- | :--------------------------------- |
| `cui`    | string | Yes      | CUI (fiscal identification code).  |
| `regCom` | string | Yes      | Registration number.               |

For `contactInfo`:
| Field     | Type   | Required | Description                        |
| :-------- | :----- | :------- | :--------------------------------- |
| `address` | object | Yes      | Address information.               |
| `email`   | string | No       | Email address.                     |
| `phone`   | string | No       | Phone number.                      |

**Example (Individual):**

```json
{
  "partyType": "individual",
  "nameDetails": {
    "firstName": "John",
    "lastName": "Doe"
  },
  "identityCodes": {
    "cnp": "1234567890123"
  },
  "contactInfo": {
    "address": "123 Main St, Bucharest",
    "email": "john.doe@example.com",
    "phone": "+40721234567"
  }
}
```

**Example (Organization):**

```json
{
  "partyType": "organization",
  "nameDetails": {
    "companyName": "Acme Corporation"
  },
  "identityCodes": {
    "cui": "RO12345678",
    "regCom": "J12/345/2020"
  },
  "contactInfo": {
    "address": "456 Business Ave, Cluj-Napoca",
    "email": "contact@acme.com",
    "phone": "+40212345678"
  }
}
```

---

### Responses

#### `201 Created`

Party created successfully.

* Content-Type: `application/json`

| Field           | Type   | Description                                |
| :-------------- | :----- | :----------------------------------------- |
| `partyId`       | string | Unique identifier for the created party.   |
| `partyType`     | string | Type of party.                             |
| `nameDetails`   | object | Name details for the party.                |
| `identityCodes` | object | Identification codes for the party.        |
| `contactInfo`   | object | Contact information for the party.         |
| `signatureData` | object | Signature data if provided.                |
| `userId`        | string | ID of the user who created the party.      |
| `createdAt`     | string | ISO 8601 timestamp of creation.            |
| `updatedAt`     | string | ISO 8601 timestamp of last update.         |

**Example:**

```json
{
  "partyId": "party_123456",
  "partyType": "individual",
  "nameDetails": {
    "firstName": "John",
    "lastName": "Doe"
  },
  "identityCodes": {
    "cnp": "1234567890123"
  },
  "contactInfo": {
    "address": "123 Main St, Bucharest",
    "email": "john.doe@example.com",
    "phone": "+40721234567"
  },
  "userId": "user_abc123",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z"
}
```

#### `400 Bad Request`

Invalid request format or missing required fields.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "partyType must be 'individual' or 'organization'"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error creating party: [error details]"
}
```

**Developer Note:** The OpenAPI spec in terraform/openapi_spec.yaml defines a different request structure with `name`, `type`, and `contact` fields, whereas the actual code implementation uses a more detailed structure with `partyType`, `nameDetails`, `identityCodes`, and `contactInfo`.

## GET /parties/{partyId}

Retrieves information about a specific party.

* **Operation ID:** `relex_backend_get_party`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `partyId` | string | Yes      | The unique identifier of the party. |

---

### Responses

#### `200 OK`

Successfully retrieved party information.

* Content-Type: `application/json`

| Field           | Type   | Description                                |
| :-------------- | :----- | :----------------------------------------- |
| `partyId`       | string | Unique identifier for the party.           |
| `partyType`     | string | Type of party (individual or organization).|
| `nameDetails`   | object | Name details for the party.                |
| `identityCodes` | object | Identification codes for the party.        |
| `contactInfo`   | object | Contact information for the party.         |
| `signatureData` | object | Signature data if available.               |
| `userId`        | string | ID of the user who created the party.      |
| `createdAt`     | string | ISO 8601 timestamp of creation.            |
| `updatedAt`     | string | ISO 8601 timestamp of last update.         |

**Example:**

```json
{
  "partyId": "party_123456",
  "partyType": "individual",
  "nameDetails": {
    "firstName": "John",
    "lastName": "Doe"
  },
  "identityCodes": {
    "cnp": "1234567890123"
  },
  "contactInfo": {
    "address": "123 Main St, Bucharest",
    "email": "john.doe@example.com",
    "phone": "+40721234567"
  },
  "userId": "user_abc123",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-01T12:00:00Z"
}
```

#### `400 Bad Request`

Missing party ID.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "partyId is required in query parameters or URL path"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to view this party.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to access this party"
}
```

#### `404 Not Found`

Party not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Party not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error getting party: [error details]"
}
```

**Developer Note:** The code implementation in party.py accepts the partyId as either a query parameter or as part of the URL path, trying both approaches. However, the OpenAPI spec in terraform/openapi_spec.yaml only defines it as a path parameter in the URL.

## PUT /parties/{partyId}

Updates an existing party.

* **Operation ID:** `relex_backend_update_party`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `partyId` | string | Yes      | The unique identifier of the party. |

---

### Request Body

| Field           | Type   | Required | Description                                  |
| :-------------- | :----- | :------- | :------------------------------------------- |
| `partyId`       | string | Yes      | The unique identifier of the party to update.|
| `nameDetails`   | object | No       | Updated name details appropriate for the party type. |
| `identityCodes` | object | No       | Updated identification codes for the party.  |
| `contactInfo`   | object | No       | Updated contact information for the party.   |
| `signatureData` | object | No       | Updated signature data for the party. Set to null to remove. |

The specific fields allowed in `nameDetails`, `identityCodes`, and `contactInfo` depend on the party type (individual or organization) and follow the same structure as in the POST /parties endpoint.

**Example (Individual):**

```json
{
  "partyId": "party_123456",
  "nameDetails": {
    "firstName": "John",
    "lastName": "Smith"
  },
  "contactInfo": {
    "address": "456 New Address St, Bucharest",
    "email": "john.smith@example.com"
  }
}
```

**Example (Organization):**

```json
{
  "partyId": "party_789012",
  "nameDetails": {
    "companyName": "Acme Corporation Updated"
  },
  "contactInfo": {
    "address": "789 Business Park, Cluj-Napoca",
    "phone": "+40212345679"
  }
}
```

---

### Responses

#### `200 OK`

Party successfully updated.

* Content-Type: `application/json`

| Field           | Type   | Description                                |
| :-------------- | :----- | :----------------------------------------- |
| `partyId`       | string | Unique identifier for the party.           |
| `partyType`     | string | Type of party (individual or organization).|
| `nameDetails`   | object | Updated name details for the party.        |
| `identityCodes` | object | Updated identification codes for the party.|
| `contactInfo`   | object | Updated contact information for the party. |
| `signatureData` | object | Updated signature data if available.       |
| `userId`        | string | ID of the user who created the party.      |
| `createdAt`     | string | ISO 8601 timestamp of creation.            |
| `updatedAt`     | string | ISO 8601 timestamp of last update.         |

**Example:**

```json
{
  "partyId": "party_123456",
  "partyType": "individual",
  "nameDetails": {
    "firstName": "John",
    "lastName": "Smith"
  },
  "identityCodes": {
    "cnp": "1234567890123"
  },
  "contactInfo": {
    "address": "456 New Address St, Bucharest",
    "email": "john.smith@example.com",
    "phone": "+40721234567"
  },
  "userId": "user_abc123",
  "createdAt": "2023-04-01T12:00:00Z",
  "updatedAt": "2023-04-15T14:30:00Z"
}
```

#### `400 Bad Request`

Invalid request format, missing required fields, or no valid fields provided for update.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "partyId is required in request body"
}
```

Or:

```json
{
  "error": "Bad Request",
  "message": "No valid fields provided for update"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to update this party.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to update this party"
}
```

#### `404 Not Found`

Party not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Party not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error updating party: [error details]"
}
```

**Developer Note:** The OpenAPI spec in terraform/openapi_spec.yaml defines a simpler `PartyUpdateInput` schema with fewer fields and different structure compared to the actual code implementation. The code requires `partyId` in the request body, even though it's also expected in the URL path.

## DELETE /parties/{partyId}

Deletes a party.

* **Operation ID:** `relex_backend_delete_party`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `partyId` | string | Yes      | The unique identifier of the party. |

---

### Responses

#### `204 No Content`

Party successfully deleted.

* No content in response body

#### `400 Bad Request`

Missing party ID.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "partyId is required in query parameters or URL path"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to delete this party.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to delete this party"
}
```

#### `404 Not Found`

Party not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Party not found"
}
```

#### `409 Conflict`

Party cannot be deleted (e.g., it is attached to cases).

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Conflict",
  "message": "Party cannot be deleted as it is attached to one or more cases"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error deleting party: [error details]"
}
```

**Developer Note:** The OpenAPI spec in terraform/openapi_spec.yaml correctly defines the 204 No Content response, but the actual code implementation may not consistently return this status code. Also, the code supports obtaining the partyId from either the URL path or query parameters, while the spec only defines it as a path parameter.

## GET /products

Retrieves active products and their prices from Stripe.

* **Operation ID:** `relex_backend_get_products`
* **Security:** No authentication required

---

### Responses

#### `200 OK`

Successfully retrieved products information.

* Content-Type: `application/json`

| Field          | Type  | Description                             |
| :------------- | :---- | :-------------------------------------- |
| `subscriptions`| array | List of subscription products.          |
| `cases`        | array | List of case tier products.             |

Each subscription product in the `subscriptions` array has the following structure:

| Field         | Type   | Description                            |
| :------------ | :----- | :------------------------------------- |
| `id`          | string | Stripe product ID.                     |
| `name`        | string | Product name.                          |
| `description` | string | Product description.                   |
| `plan_type`   | string | Type of plan (individual, org_basic, etc.). |
| `price`       | object | Price information.                     |

Each case product in the `cases` array has the following structure:

| Field         | Type    | Description                           |
| :------------ | :------ | :------------------------------------ |
| `id`          | string  | Stripe product ID.                    |
| `name`        | string  | Product name.                         |
| `description` | string  | Product description.                  |
| `tier`        | integer | Case tier level (1, 2, or 3).         |
| `price`       | object  | Price information.                    |

The `price` object has the following structure:

| Field      | Type   | Description                                |
| :--------- | :----- | :----------------------------------------- |
| `id`       | string | Stripe price ID.                           |
| `amount`   | integer| Price amount in smallest currency unit (e.g., cents). |
| `currency` | string | Three-letter ISO currency code (e.g., "eur"). |
| `type`     | string | Price type ("recurring" or "one_time").    |
| `recurring`| object | Present only for subscription products.    |

The `recurring` object (for subscription products) has the following structure:

| Field           | Type    | Description                           |
| :-------------- | :------ | :------------------------------------ |
| `interval`      | string  | Billing interval ("month" or "year"). |
| `interval_count`| integer | Number of intervals between billings. |

**Example:**

```json
{
  "subscriptions": [
    {
      "id": "prod_ABC123",
      "name": "Basic Subscription",
      "description": "Monthly subscription with 5 cases per month",
      "plan_type": "individual",
      "price": {
        "id": "price_XYZ789",
        "amount": 2900,
        "currency": "eur",
        "type": "recurring",
        "recurring": {
          "interval": "month",
          "interval_count": 1
        }
      }
    }
  ],
  "cases": [
    {
      "id": "prod_DEF456",
      "name": "Basic Case",
      "description": "Basic legal advice",
      "tier": 1,
      "price": {
        "id": "price_UVW123",
        "amount": 900,
        "currency": "eur",
        "type": "one_time"
      }
    },
    {
      "id": "prod_GHI789",
      "name": "Standard Case",
      "description": "Comprehensive legal advice",
      "tier": 2,
      "price": {
        "id": "price_RST456",
        "amount": 2900,
        "currency": "eur",
        "type": "one_time"
      }
    },
    {
      "id": "prod_JKL012",
      "name": "Premium Case",
      "description": "Complete legal solution",
      "tier": 3,
      "price": {
        "id": "price_OPQ789",
        "amount": 9900,
        "currency": "eur",
        "type": "one_time"
      }
    }
  ]
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Stripe Error",
  "message": "Failed to retrieve products from Stripe: [error details]"
}
```

Or:

```json
{
  "error": "Configuration Error",
  "message": "Stripe API key not configured"
}
```

**Developer Note:** The OpenAPI spec in terraform/openapi_spec.yaml has a similar structure but with some differences in field naming and nesting. The actual implementation uses a Firestore cache to improve performance, but this is an implementation detail that doesn't affect the API interface.

## POST /cases/{caseId}/agent/messages

Interact with the Lawyer AI Agent for a specific case.

* **Operation ID:** `relex_backend_agent_handler`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |

---

### Request Body

| Field        | Type   | Required | Description                                   |
| :----------- | :----- | :------- | :-------------------------------------------- |
| `message`    | string | Yes      | The user's message or query to the agent.     |

**Example:**

```json
{
  "message": "What legal options do I have in my divorce case?"
}
```

---

### Responses

#### `200 OK`

Successfully processed the agent request.

* Content-Type: `application/json`

| Field           | Type    | Description                                |
| :-------------- | :------ | :----------------------------------------- |
| `status`        | string  | Status of the operation ('success' or 'error'). |
| `message`       | string  | The agent's response message.              |
| `timestamp`     | string  | ISO 8601 timestamp of when the response was generated. |
| `metadata`      | object  | Optional metadata about the response.      |

The `metadata` object may contain:

| Field              | Type    | Description                                |
| :----------------- | :------ | :----------------------------------------- |
| `confidence_score` | number  | Agent's confidence in the response (0-1).  |
| `execution_time`   | number  | Time taken to process the request in seconds. |
| `risks`            | array   | Potential risks identified by the agent.   |

**Example:**

```json
{
  "status": "success",
  "message": "Based on the information you've provided about your divorce case, you have several legal options. First, you could pursue mediation, which is often less expensive and less adversarial than going to court. Second, you could negotiate a settlement through your attorneys. If these approaches don't work, litigation is always an option, though it should typically be considered a last resort due to costs and emotional toll. Given that children are involved, the court will prioritize their best interests when determining custody arrangements. I recommend documenting all assets and financial information thoroughly as this will be crucial for property division discussions.",
  "timestamp": "2023-07-15T14:30:00Z",
  "metadata": {
    "confidence_score": 0.92,
    "execution_time": 2.34,
    "risks": []
  }
}
```

#### `400 Bad Request`

Invalid request format or missing required fields.

* Content-Type: `application/json`

| Field        | Type   | Description                                |
| :----------- | :----- | :----------------------------------------- |
| `status`     | string | Error status.                              |
| `message`    | string | Error message details.                     |
| `timestamp`  | string | ISO 8601 timestamp of the error.           |

**Example:**

```json
{
  "status": "error",
  "message": "No JSON data provided",
  "timestamp": "2023-07-15T14:31:00Z"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field        | Type   | Description                                |
| :----------- | :----- | :----------------------------------------- |
| `status`     | string | Error status.                              |
| `message`    | string | Error message details.                     |
| `timestamp`  | string | ISO 8601 timestamp of the error.           |

**Example:**

```json
{
  "status": "error",
  "message": "Authentication required",
  "timestamp": "2023-07-15T14:32:00Z"
}
```

#### `403 Forbidden`

User does not have permission to access this case.

* Content-Type: `application/json`

| Field        | Type   | Description                                |
| :----------- | :----- | :----------------------------------------- |
| `status`     | string | Error status.                              |
| `message`    | string | Error message details.                     |
| `timestamp`  | string | ISO 8601 timestamp of the error.           |

**Example:**

```json
{
  "status": "error",
  "message": "You do not have permission to access this case",
  "timestamp": "2023-07-15T14:33:00Z"
}
```

#### `404 Not Found`

Case not found.

* Content-Type: `application/json`

| Field        | Type   | Description                                |
| :----------- | :----- | :----------------------------------------- |
| `status`     | string | Error status.                              |
| `message`    | string | Error message details.                     |
| `timestamp`  | string | ISO 8601 timestamp of the error.           |

**Example:**

```json
{
  "status": "error",
  "message": "Case 123456 not found",
  "timestamp": "2023-07-15T14:34:00Z"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field           | Type   | Description                                |
| :-------------- | :----- | :----------------------------------------- |
| `status`        | string | Error status.                              |
| `message`       | string | Error message details.                     |
| `error_details` | string | Optional detailed error information.       |
| `timestamp`     | string | ISO 8601 timestamp of the error.           |

**Example:**

```json
{
  "status": "error",
  "message": "Error processing agent request: LLM service unavailable",
  "error_details": "[Stack trace details]",
  "timestamp": "2023-07-15T14:35:00Z"
}
```

**Developer Note:** The OpenAPI spec in terraform/openapi_spec.yaml defines a more complex request body with additional fields like `type`, `input`, `user_id`, `case_id`, and `user_info`, while the actual code implementation primarily uses the `message` field. The response structure also differs, with the spec defining a more complex structure than what the actual implementation returns.

## POST /webhooks/stripe

Handles incoming Stripe webhook events.

* **Operation ID:** `relex_backend_handle_stripe_webhook`
* **Security:** No authentication required, but validates the Stripe signature

---

### Request Body

The request body should be the raw payload sent by Stripe, with the `Stripe-Signature` header included.

---

### Responses

#### `200 OK`

Successfully processed the webhook event.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `received`| boolean| Indicates the event was received. |
| `type`    | string | The type of event that was processed. |

**Example:**

```json
{
  "received": true,
  "type": "checkout.session.completed"
}
```

#### `400 Bad Request`

Invalid request format or missing required information.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "No POST data provided"
}
```

Or:

```json
{
  "error": "Bad Request",
  "message": "Stripe signature verification failed"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error processing Stripe webhook: [error details]"
}
```

**Developer Note:** This endpoint is not fully defined in the OpenAPI spec. The implementation handles various Stripe events such as `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, and `customer.subscription.updated`, updating user and organization subscription statuses and quotas accordingly.

## POST /cases/{caseId}/files

Uploads a file to a specific case.

* **Operation ID:** `relex_backend_upload_file`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |

---

### Request Body

The request body should be a `multipart/form-data` containing:

| Field | Type   | Required | Description              |
| :---- | :----- | :------- | :----------------------- |
| `file`| binary | Yes      | The file to be uploaded. |

---

### Responses

#### `201 Created`

File successfully uploaded.

* Content-Type: `application/json`

| Field        | Type   | Description                               |
| :----------- | :----- | :---------------------------------------- |
| `fileId`     | string | Unique identifier for the uploaded file.  |
| `fileName`   | string | Name of the uploaded file.                |
| `contentType`| string | MIME type of the file.                    |
| `size`       | integer| Size of the file in bytes.                |
| `caseId`     | string | ID of the case the file is attached to.   |
| `uploadedBy` | string | User ID of the uploader.                  |
| `uploadedAt` | string | ISO 8601 timestamp of the upload time.    |
| `downloadUrl`| string | URL to download the file (time-limited).  |

**Example:**

```json
{
  "fileId": "file_abc123",
  "fileName": "divorce_agreement.pdf",
  "contentType": "application/pdf",
  "size": 1048576,
  "caseId": "case_123456",
  "uploadedBy": "user_abc123",
  "uploadedAt": "2023-04-01T12:00:00Z",
  "downloadUrl": "https://storage.googleapis.com/relex-case-files/..."
}
```

#### `400 Bad Request`

Invalid request format or missing required file.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "No file provided"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to upload files to this case.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to upload files to this case"
}
```

#### `404 Not Found`

Case not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Case not found"
}
```

#### `413 Payload Too Large`

File exceeds the maximum size limit.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Payload Too Large",
  "message": "File exceeds the maximum size limit of 10MB"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error uploading file: [error details]"
}
```

**Developer Note:** The OpenAPI spec and the code implementation use different field names in the response object. The spec uses fields like `url` while the code uses `downloadUrl`. Also, the spec defines a `FileResponse` schema that doesn't exactly match what the code returns.

## GET /cases/{caseId}/files/{fileId}

Downloads a file associated with a specific case.

* **Operation ID:** `relex_backend_download_file`
* **Security:** Requires Firebase Authentication

---

### Path Parameters

| Parameter | Type   | Required | Description                    |
| :-------- | :----- | :------- | :----------------------------- |
| `caseId`  | string | Yes      | The unique identifier of the case. |
| `fileId`  | string | Yes      | The unique identifier of the file. |

---

### Responses

#### `200 OK`

Successfully fetched the file.

* Content-Type: Matches the file's content type
* Binary file data in the response body

Headers include:
* `Content-Disposition: attachment; filename=<original filename>`
* `Content-Type: <file MIME type>`
* `Content-Length: <file size in bytes>`

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to download this file.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to access this file"
}
```

#### `404 Not Found`

File or case not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "File not found"
}
```

Or:

```json
{
  "error": "Not Found",
  "message": "Case not found"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error downloading file: [error details]"
}
```

**Developer Note:** The OpenAPI spec in terraform/openapi_spec.yaml defines a `FileResponse` schema for the response, but the actual implementation returns the file binary data directly with appropriate headers rather than a JSON response.

## POST /organizations/{organizationId}/members

Adds a user to an organization.

* **Operation ID:** `relex_backend_add_organization_member`
* **Security:** Requires Firebase Authentication with administrator permission on the organization

---

### Path Parameters

| Parameter        | Type   | Required | Description                              |
| :--------------- | :----- | :------- | :--------------------------------------- |
| `organizationId` | string | Yes      | The unique identifier of the organization. |

---

### Request Body

| Field           | Type   | Required | Description                                  |
| :-------------- | :----- | :------- | :------------------------------------------- |
| `organizationId`| string | Yes      | The unique identifier of the organization.   |
| `userId`        | string | Yes      | The unique identifier of the user to add.    |
| `role`          | string | No       | The user's role in the organization (administrator or staff). Default: staff |

**Example:**

```json
{
  "organizationId": "org_12345abcde",
  "userId": "user_98765zyxw",
  "role": "staff"
}
```

---

### Responses

#### `201 Created`

User successfully added to the organization.

* Content-Type: `application/json`

| Field           | Type   | Description                                |
| :-------------- | :----- | :----------------------------------------- |
| `id`            | string | Unique identifier for the membership.      |
| `organizationId`| string | ID of the organization.                    |
| `userId`        | string | ID of the user added to the organization.  |
| `role`          | string | Role of the user in the organization.      |
| `addedBy`       | string | ID of the user who added this member.      |
| `joinedAt`      | string | ISO 8601 timestamp when the user joined.   |

**Example:**

```json
{
  "id": "member_abc123",
  "organizationId": "org_12345abcde",
  "userId": "user_98765zyxw",
  "role": "staff",
  "addedBy": "user_admin123",
  "joinedAt": "2023-04-01T12:00:00Z"
}
```

#### `400 Bad Request`

Invalid request format or missing required fields.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Bad Request",
  "message": "Organization ID is required"
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `403 Forbidden`

User does not have permission to add members to this organization.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to add members to this organization"
}
```

#### `404 Not Found`

Organization or target user not found.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Not Found",
  "message": "Organization org_12345abcde not found"
}
```

Or:

```json
{
  "error": "Not Found",
  "message": "Target user user_98765zyxw not found"
}
```

#### `409 Conflict`

User is already a member of the organization.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Conflict",
  "message": "User is already a member"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error adding member: [error details]"
}
```

**Developer Note:** The OpenAPI spec in terraform/openapi_spec.yaml uses a different collection name ('organizationMembers') than the actual implementation ('organization_memberships'), and the response structure doesn't match exactly.

## GET /users/me/organizations

Lists all organizations the authenticated user is a member of.

* **Operation ID:** `relex_backend_list_user_organizations`
* **Security:** Requires Firebase Authentication

---

### Responses

#### `200 OK`

Successfully retrieved the list of organizations.

* Content-Type: `application/json`

| Field           | Type  | Description                              |
| :-------------- | :---- | :--------------------------------------- |
| `organizations` | array | List of organizations the user belongs to.|

Each organization in the `organizations` array has the following structure:

| Field            | Type   | Description                                |
| :--------------- | :----- | :----------------------------------------- |
| `organizationId` | string | The unique identifier of the organization. |
| `name`           | string | Name of the organization.                  |
| `description`    | string | Description of the organization.           |
| `role`           | string | User's role in the organization (administrator or staff). |
| `joinedAt`       | string | ISO 8601 timestamp when the user joined.   |

**Example:**

```json
{
  "organizations": [
    {
      "organizationId": "org_12345abcde",
      "name": "Acme Corporation",
      "description": "Leading provider of cloud services",
      "role": "administrator",
      "joinedAt": "2023-03-15T10:30:00Z"
    },
    {
      "organizationId": "org_67890fghij",
      "name": "XYZ Consulting",
      "description": "Legal consulting services",
      "role": "staff",
      "joinedAt": "2023-04-01T14:45:00Z"
    }
  ]
}
```

#### `401 Unauthorized`

Authentication token is missing or invalid.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Unauthorized",
  "message": "Authentication data missing"
}
```

#### `500 Internal Server Error`

Server encountered an unexpected error.

* Content-Type: `application/json`

| Field     | Type   | Description          |
| :-------- | :----- | :------------------- |
| `error`   | string | Error code.          |
| `message` | string | Error message details.|

**Example:**

```json
{
  "error": "Internal Server Error",
  "message": "Error listing user organizations: [error details]"
}
```

**Developer Note:** The OpenAPI spec in terraform/openapi_spec.yaml defines a `MembershipResponse` schema that differs from the actual implementation's response structure, particularly in field naming and data organization.

## Summary of API Documentation Updates and Identified Discrepancies

This section provides a summary of all identified discrepancies between the actual code implementation in `functions/src/` and the OpenAPI specification in `terraform/openapi_spec.yaml`.

### Documentation Structure

- The API documentation has been updated to follow the preferred markdown style as specified in the requirements.
- All endpoints have been documented based on the actual code implementation, with "Developer Notes" added where discrepancies with the OpenAPI spec were found.

### General Discrepancies

1. **Endpoint Names and Operation IDs**:
   - The OpenAPI spec and code implementation sometimes use different operation IDs for the same functionality.
   - Some endpoints in the code are missing from the OpenAPI spec entirely.

2. **Path Parameters**:
   - Several endpoints in the code (e.g., party.py) accept parameters from either query parameters or URL path, while the OpenAPI spec typically only defines one approach.

3. **Request/Response Structures**:
   - Field naming differences: The OpenAPI spec often uses different field names than what's implemented in the code (e.g., `url` vs `downloadUrl`).
   - Data structure differences: The actual implementation often returns more detailed or differently structured responses than what's defined in the OpenAPI spec.

4. **Collection Names**:
   - The code implementation sometimes uses different Firestore collection names than what's implied in the OpenAPI spec (e.g., 'organization_memberships' vs 'organizationMembers').

### Endpoint-Specific Discrepancies

1. **POST /cases**:
   - The OpenAPI spec defines separate operations for individual and organization cases, while the code uses a single function with an optional organizationId parameter.

2. **POST /parties**:
   - The OpenAPI spec defines a simpler request structure with `name`, `type`, and `contact` fields, while the code implementation uses a more detailed structure with `partyType`, `nameDetails`, `identityCodes`, and `contactInfo`.

3. **PUT /parties/{partyId}**:
   - The code requires `partyId` in the request body, even though it's also expected in the URL path.
   - The OpenAPI spec defines a simpler `PartyUpdateInput` schema with fewer fields.

4. **GET /parties/{partyId}**:
   - The code accepts the partyId as either a query parameter or as part of the URL path, while the OpenAPI spec only defines it as a path parameter.

5. **DELETE /parties/{partyId}**:
   - The OpenAPI spec correctly defines the 204 No Content response, but the actual code implementation may not consistently return this status code.

6. **GET /products**:
   - The OpenAPI spec has a similar structure but with differences in field naming and nesting compared to the code implementation.

7. **POST /cases/{caseId}/agent/messages**:
   - The OpenAPI spec defines a more complex request body with additional fields like `type`, `input`, `user_id`, `case_id`, and `user_info`, while the actual code primarily uses just the `message` field.
   - The response structure also differs significantly.

8. **POST /webhooks/stripe**:
   - This endpoint is not fully defined in the OpenAPI spec, despite having significant functionality in the code.

9. **POST /cases/{caseId}/files**:
   - The OpenAPI spec and the code implementation use different field names in the response object.
   - The spec defines a `FileResponse` schema that doesn't match what the code returns.

10. **GET /cases/{caseId}/files/{fileId}**:
    - The OpenAPI spec defines a `FileResponse` schema for the response, but the actual implementation returns the file binary data directly with appropriate headers.

11. **POST /organizations/{organizationId}/members**:
    - The OpenAPI spec uses a different collection name ('organizationMembers') than the actual implementation ('organization_memberships').
    - The response structure doesn't match exactly between the spec and code.

12. **GET /users/me/organizations**:
    - The OpenAPI spec defines a `MembershipResponse` schema that differs from the actual implementation's response structure, particularly in field naming and data organization.

### Recommendations

1. Update the OpenAPI spec to match the actual code implementation, particularly focusing on:
   - Endpoint paths and operation IDs
   - Request and response structures
   - Missing endpoints
   - Parameter handling (path vs. query)
   - Response codes and payload formats

2. Consider standardizing naming conventions across both the code and OpenAPI spec for consistency.