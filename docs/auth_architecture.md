# Authentication Architecture and Flow

## High-Level Flow

```
+-------------------+        +-------------------+        +-------------------+        +-------------------+
|   Client (User)   |        |   API Gateway     |        | Cloud Function    |        |   Backend Logic   |
|-------------------|        |-------------------|        |-------------------|        |-------------------|
| 1. Sends request  |  --->  | 2. Validates JWT  |  --->  | 3. Receives       |  --->  | 4. Handles        |
|   with            |        |    (Firebase)     |        |    request with   |        |    business logic |
|   Authorization   |        |                   |        |    headers        |        |                   |
|   header          |        |                   |        |                   |        |                   |
+-------------------+        +-------------------+        +-------------------+        +-------------------+
```

## Detailed Flow

1. **Client** authenticates with Firebase and receives a JWT.
2. **Client** sends API request to API Gateway with:
   - `Authorization: Bearer <firebase_jwt>`
3. **API Gateway**:
   - Validates the JWT using Firebase public keys.
   - If valid, forwards the request to the Cloud Function (backend) using IAM (service account).
   - Forwards the original user's claims as a base64-encoded JSON in the `X-Endpoint-API-Userinfo` or `X-Apigateway-Api-Userinfo` header.
   - Forwards the original `Authorization` header as `X-Forwarded-Authorization`.
4. **Cloud Function (Backend)**:
   - Receives the request with all headers.
   - The backend's `get_authenticated_user` function:
     - Checks for `X-Endpoint-API-Userinfo` or `X-Apigateway-Api-Userinfo` header and decodes it to extract user info (UID, email, etc).
     - If not present, falls back to validating the `Authorization` header as a Firebase JWT.
     - If neither is valid, returns 401 Unauthorized.
   - All endpoint handlers use a decorator (`inject_user_context`) to ensure authentication and inject user info into the request object.
   - Business logic functions (e.g., `get_user_profile`) expect the user context to be present on the request.

## OpenAPI Spec and Header Forwarding
- The OpenAPI spec (`terraform/openapi_spec.yaml`) is configured to forward all necessary headers from API Gateway to the backend, including:
  - `X-Endpoint-API-Userinfo`
  - `X-Apigateway-Api-Userinfo`
  - `X-Forwarded-Authorization`
  - `Authorization` (if needed)
- This ensures the backend always receives the required headers for authentication.

## Backend Header Expectations
- The backend expects:
  - `X-Endpoint-API-Userinfo` or `X-Apigateway-Api-Userinfo`: base64-encoded JSON with Firebase claims
  - `X-Forwarded-Authorization`: original JWT
  - `Authorization`: may be present, but not always trusted (depends on call path)

## How Backend Functions Call Auth
- All HTTP handlers are decorated with `@inject_user_context` (in `main.py`).
- This decorator calls `get_authenticated_user(request)` before any business logic runs.
- If authentication fails, the request is rejected with 401.
- If successful, user info is injected as attributes on the request (e.g., `request.end_user_id`).
- All business logic functions (e.g., `get_user_profile`, `update_user_profile`) expect these attributes to be present and use them for authorization and data access.

## Common Pitfalls
- If the OpenAPI spec does not forward the correct headers, authentication will fail.
- If the backend does not check the correct header, user identity will not be established.
- Always ensure the API Gateway and backend are in sync regarding header names and expectations. 