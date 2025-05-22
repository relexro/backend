# Authentication and Authorization

## Overview

Relex implements a comprehensive authentication and authorization system based on Firebase Authentication and a custom Role-Based Access Control (RBAC) model. This system ensures that users can only access resources they are authorized to use, while providing flexible permission management.

## Authentication Flow

### Firebase Authentication

The system uses Firebase Authentication for user identity management:

1. **Client-Side Authentication**:
   - The frontend application integrates Firebase Auth SDK
   - Users can authenticate using various providers:
     - Email/Password
     - Google OAuth
     - (Future) Apple, Microsoft, etc.

2. **Token Generation**:
   - Upon successful authentication, Firebase issues a JWT token
   - The token contains user identity information (UID, email)
   - The token may include custom claims for authorization

3. **API Authentication**:
   - All protected API endpoints require a valid Firebase Auth token
   - The token is passed in the HTTP Authorization header
   - The API Gateway validates the token using Firebase's JWK endpoint
   - The API Gateway then calls backend Cloud Run functions using a Google OIDC ID token it generates, acting as the `relex-functions-dev@relexro.iam.gserviceaccount.com` service account
   - The backend `auth.py` script validates this Google OIDC ID token (verifying against the function's own URL as audience)
   - The `userId` available within the backend function context after this authentication step is the subject ID of the `relex-functions-dev@...` service account, **not** the original end-user's Firebase UID

### End-User Identity Propagation

Currently, the original end-user's Firebase UID is not automatically propagated from the API Gateway to the backend functions. This has important implications:

1. **Identity in Backend Functions**: The `userId` available in the backend function context corresponds to the `relex-functions-dev@...` service account, not the original end-user's Firebase UID.

2. **User-Specific Operations**: If backend logic needs to be performed on behalf of the original end-user, their identity must be explicitly passed from the API Gateway to the backend function (e.g., as a custom header or in the request payload).

3. **Future Enhancement**: A mechanism for automatically propagating the original end-user's identity from the API Gateway to the backend functions is planned but not currently implemented.

### Testing Authentication

For testing purposes, you can obtain Firebase JWT tokens using either the automated refresh script (recommended) or the manual browser utility. The system uses three different token types for different test scenarios:

1. **Regular User Token (`RELEX_TEST_JWT`)**: For testing endpoints as a regular user without organization membership
2. **Organization Admin Token (`RELEX_ORG_ADMIN_TEST_JWT`)**: For testing endpoints as an organization administrator
3. **Organization User Token (`RELEX_ORG_USER_TEST_JWT`)**: For testing endpoints as an organization staff member

#### Automated Token Refresh (Recommended)

The easiest way to manage these tokens is using the automated refresh script:

```bash
# Quick setup (one-time)
pip install firebase-admin requests
python scripts/setup_token_automation.py

# Refresh all 3 tokens anytime
./refresh_tokens.sh
```

This automatically:
- Generates fresh tokens for all 3 test users
- Updates your `~/.zshenv` file with the new tokens
- Eliminates manual browser token copying
- Can be set up to run automatically every 45 minutes

See [Token Automation Documentation](../token_automation.md) for detailed setup instructions.

#### Manual Token Generation (Alternative)

If you prefer manual token generation, follow these steps:

1. Navigate to the `tests/` directory
2. Start a local web server: `python3 -m http.server 8080`
3. Open `http://localhost:8080/test-auth.html` in your browser
4. For each token type:
   - Sign in with the appropriate user account
   - After successful authentication, click "Show/Hide Token" to reveal the JWT token
   - Copy the entire token and set the corresponding environment variable:

```bash
# For regular user tests
export RELEX_TEST_JWT="your_regular_user_token_here"

# For organization admin tests
export RELEX_ORG_ADMIN_TEST_JWT="your_org_admin_token_here"

# For organization user tests
export RELEX_ORG_USER_TEST_JWT="your_org_user_token_here"
```

#### Token Expiration

Firebase JWT tokens expire after 1 hour. When tokens expire, you'll see authentication errors in your tests. Simply refresh the tokens using:

```bash
# Automated refresh (if set up)
./refresh_tokens.sh

# Or manual refresh via browser
# Follow the manual steps above
```

### Token Format

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjFmODhiODE0MjljYzQ1MWEzMzVjMmY1Y2RiM2RmYjM0ZWIzYmJjN2YiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vcmVsZXhybyIsImF1ZCI6InJlbGV4cm8iLCJhdXRoX3RpbWUiOjE2MTIzNDU2NzgsInVzZXJfaWQiOiJnUEdYblpDUWFkU2doVldwY3pYeWdnWlpNMjgzIiwic3ViIjoiZ1BHWG5aQ1FhZFNnaFZXcGN6WHlnZ1paTTI4MyIsImlhdCI6MTYxMjM0NTY3OCwiZXhwIjoxNjEyMzQ5Mjc4LCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJ1c2VyQGV4YW1wbGUuY29tIl19LCJzaWduX2luX3Byb3ZpZGVyIjoicGFzc3dvcmQifX0.SIGNATURE
```

## Authorization Model

### Role-Based Access Control (RBAC)

The system implements a custom RBAC model defined in `functions/src/auth.py`:

1. **Roles**:
   - **Individual User**: Default role for all authenticated users
   - **Organization Administrator**: Manages organization settings and members
   - **Organization Staff**: Regular organization member
   - **System Administrator**: Special role for system management (internal use)

2. **Resources**:
   - **Cases**: Legal cases managed in the system
   - **Organizations**: Company/law firm profiles
   - **Organization Memberships**: User associations with organizations
   - **Parties**: Individuals or entities involved in cases
   - **Documents**: Legal documents related to cases

3. **Permissions**:
   - **View**: Read access to a resource
   - **Create**: Ability to create new resources
   - **Update**: Ability to modify existing resources
   - **Delete**: Ability to remove resources
   - **Manage**: Administrative control (combines all permissions)

### Permission Mappings

The system defines permission mappings in the `PERMISSIONS` dictionary in `auth.py`:

```python
PERMISSIONS = {
    # Individual user permissions
    "user": {
        "case": ["view", "create", "update", "delete"],
        "party": ["view", "create", "update", "delete"],
        "document": ["view", "create", "update", "delete"],
        "organization": ["view", "create"],
        "organization_membership": ["view"],
    },
    # Organization administrator permissions
    "organization_administrator": {
        "case": ["view", "create", "update", "delete"],
        "party": ["view", "create", "update", "delete"],
        "document": ["view", "create", "update", "delete"],
        "organization": ["view", "update"],
        "organization_membership": ["view", "create", "update", "delete"],
    },
    # Organization staff permissions
    "organization_staff": {
        "case": ["view", "create", "update"],
        "party": ["view", "create", "update"],
        "document": ["view", "create", "update"],
        "organization": ["view"],
        "organization_membership": ["view"],
    },
    # System administrator permissions
    "system_administrator": {
        "case": ["view", "create", "update", "delete", "manage"],
        "party": ["view", "create", "update", "delete", "manage"],
        "document": ["view", "create", "update", "delete", "manage"],
        "organization": ["view", "create", "update", "delete", "manage"],
        "organization_membership": ["view", "create", "update", "delete", "manage"],
    },
}
```

### Resource-Specific Authorization

The authorization system performs resource-specific checks to determine if a user has permission to access a particular resource:

1. **Case Access**:
   - Users can access their own individual cases
   - Organization members can access cases owned by their organization
   - System administrators can access all cases

2. **Organization Access**:
   - Users can view organizations they are members of
   - Users can create new organizations
   - Organization administrators can manage their own organization
   - System administrators can manage all organizations

3. **Organization Membership Access**:
   - Users can view their own memberships
   - Organization administrators can manage memberships in their organization
   - System administrators can manage all memberships

4. **Document Access**:
   - Access is determined by the parent case ownership
   - Users can access documents in cases they can access

## Implementation

### Authentication Functions

The authentication and authorization logic is centralized in `functions/src/auth.py` with these key functions:

1. **`_authenticate_and_call`**: A decorator that validates Firebase Auth tokens and extracts user information before calling the wrapped function.

2. **`get_user_id_from_token`**: Extracts the user ID from a Firebase Auth token.

3. **`has_permission`**: Checks if a user has a specific permission on a resource type.

4. **`can_access_resource`**: Checks if a user can access a specific resource instance.

5. **`get_user_roles`**: Retrieves all roles assigned to a user, including organization roles.

### Custom Claims (Future Implementation)

The system is designed to utilize Firebase Custom Claims for enhanced authorization:

1. **Role Assignment**:
   - System administrator roles will be assigned via custom claims
   - Claims will be set using the Firebase Admin SDK
   - Claims are limited to 1KB in size

2. **Claim Format**:
   ```json
   {
     "roles": {
       "system": ["system_administrator"],
       "organizations": {
         "org_id_1": ["organization_administrator"],
         "org_id_2": ["organization_staff"]
       }
     }
   }
   ```

3. **Claim Verification**:
   - Custom claims will be verified during API calls
   - The verification logic will be implemented in `auth.py`

## Firestore Security Rules

While the primary authorization is handled in the backend functions, Firestore Security Rules provide an additional layer of protection:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow authenticated users to read their own user document
    match /users/{userId} {
      allow read: if request.auth != null && request.auth.uid == userId;
    }

    // Allow authenticated users to read/write their own cases
    match /cases/{caseId} {
      allow read: if request.auth != null &&
        (resource.data.owner.user_id == request.auth.uid ||
         resource.data.owner.organization_id in get(/databases/$(database)/documents/users/$(request.auth.uid)).data.organizations);
    }

    // Restrict all other access to backend functions
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

## API Gateway Configuration

### API Gateway URL

The API is accessed via the default Google Cloud API Gateway URL, not the custom domain. To find this URL:

1. Check the `docs/terraform_outputs.log` file after deployment
2. Look for the `api_gateway_url` key (e.g., `relex-api-gateway-dev-mvef5dk.ew.gateway.dev`)
3. Use this URL as the base for all API requests

Note: The custom domain `api-dev.relex.ro` is not currently the active endpoint for the API Gateway.

### Known Issues

- **API Gateway Logs**: API Gateway logs are available in Cloud Logging under `resource.type=api` (not `resource.type=api_gateway`) with a `logName` containing `apigateway`. Use the dedicated log view `api-gateway-logs` or the query `resource.type=api AND logName:apigateway` to access these logs.
- **End-User Identity**: As mentioned above, the original end-user's Firebase UID is not automatically propagated to backend functions.

## Future Enhancements

1. **Implementation of Custom Claims**: To optimize authorization performance and reduce Firestore reads.

2. **Invitation System**: For seamless organization membership management.

3. **Fine-Grained Permissions**: Additional permission types for more granular access control.

4. **Audit Logging**: Comprehensive logging of authentication and authorization events.

5. **Multi-Factor Authentication**: Enhanced security for sensitive operations.

6. **End-User Identity Propagation**: Implement a mechanism to automatically propagate the original end-user's identity from the API Gateway to the backend functions.