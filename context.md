# Relex Backend Context

This document provides context for the Relex backend implementation, including design decisions, constraints, and implementation notes that aren't immediately obvious from the code.

## Technical Stack

The Relex backend uses the following technologies:

- **Firebase Cloud Functions**: Serverless functions that execute in response to events
- **Firestore**: NoSQL document database for storing application data
- **Firebase Authentication**: For user identity and authentication
- **Firebase Storage**: For storing document files and other assets
- **Terraform**: For infrastructure as code and resource provisioning
- **Python**: The primary programming language for all backend components
- **Flask**: Web framework used by Firebase Functions
- **Vertex AI**: Google's machine learning platform for AI capabilities

## Design Principles

The backend follows these key design principles:

1. **Serverless Architecture**: Using Google Cloud's serverless offerings to minimize operational overhead
2. **Stateless Functions**: Each function is designed to be stateless, handling a single responsibility
3. **Separation of Concerns**: Code is organized into modules by feature area
4. **RESTful API Design**: Following REST principles for API design
5. **Role-Based Access Control**: Permissions are based on organization roles and resource ownership

## Permission Model

The Relex backend implements a comprehensive role-based permission system that controls access to resources based on user roles within organizations. This model ensures that users can only access and modify resources they have appropriate permissions for.

### Organization Membership

All resources (cases, files) are associated with organizations, and permissions are determined by:

1. **Organization Membership**: A user must be a member of an organization to access its resources
2. **Role Within Organization**: The specific permissions a user has depends on their role

### User Roles

The system defines the following roles within organizations:

1. **Administrator**:
   - Has full access to all resources within the organization
   - Can manage organization settings and membership
   - Can create, read, update, delete, and archive cases
   - Can upload and download files

2. **Staff**:
   - Has limited access to organizational resources
   - Can create cases for the organization
   - Can read cases belonging to the organization
   - Can upload files to cases
   - Cannot archive or delete cases (unless they are the case owner)

3. **Case Owner**:
   - Special designation for the user who created a case
   - Has additional permissions for their own cases
   - Can archive or delete their own cases regardless of organization role

### Permission Implementation

The permission model is implemented through the `check_permissions` function in the `auth.py` module. This function:

1. Authenticates the user making the request
2. Determines the resource type (case, file, organization)
3. Identifies the organization that owns the resource 
4. Checks the user's role within that organization
5. Verifies if the action is permitted based on the role and resource

For all case and file management functions:
- The user is authenticated using the token in the Authorization header
- The function retrieves the organization ID associated with the resource
- The function checks if the user is a member of that organization and has appropriate permissions
- If authorized, the requested operation proceeds; if not, a 403 Forbidden error is returned

### Organization Resource Access

When a user performs an action on a case or file:
1. The system checks if the user is the resource owner (created the case)
2. If not, the system checks if the user is an administrator in the organization that owns the resource
3. If not, the system checks if the user is a staff member in the organization and if the action is permitted for staff
4. If none of these conditions are met, access is denied

## Implementation Patterns

### Organization-Based Access Control

All case and file management functions now follow this pattern:

```python
# Authenticate user
user = get_authenticated_user()
if not user:
    return {"error": "Unauthorized", "message": "Authentication required"}, 401

# Get organization ID (from request or from the resource)
organization_id = request.json.get("organizationId") or get_organization_id_from_resource()

# Check permissions
allowed = check_permissions(
    user["userId"], 
    resource_id=resource_id,
    organization_id=organization_id,
    action="action_name", 
    resource_type="resource_type"
)

if not allowed:
    return {"error": "Forbidden", "message": "You do not have permission..."}, 403

# Proceed with the function logic
```

### Error Handling

The backend implements consistent error handling with appropriate HTTP status codes:

- **400 Bad Request**: Invalid input parameters
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Authenticated but insufficient permissions
- **404 Not Found**: Resource does not exist
- **500 Internal Server Error**: Unexpected server-side errors

### Authentication Token Verification

Firebase Authentication tokens are verified in the `get_authenticated_user()` function. Authentication failures follow this pattern:

```python
def get_authenticated_user():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
        
    token = auth_header.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return {
            "userId": decoded_token["uid"],
            "email": decoded_token.get("email", "")
        }
    except Exception as e:
        return None
```

## Resource Collection Structure

### Organization Structure

The organization membership model has been updated to use a separate collection:

```
organization_memberships/{membershipId}
├── organizationId: string
├── userId: string
├── role: string ("administrator", "staff")
├── addedAt: timestamp
└── updatedAt: timestamp (optional)
```

This allows for efficient querying of:
- All organizations a user belongs to
- All members of an organization
- A user's role in a specific organization

### Case Structure

Cases now include organization ownership:

```
cases/{caseId}
├── title: string
├── description: string
├── userId: string (owner user ID)
├── organizationId: string (organization this case belongs to)
├── status: string ("open", "archived", "deleted")
├── creationDate: timestamp
├── archiveDate: timestamp (if archived)
└── deletionDate: timestamp (if deleted)
```

### Document Structure

File documents include back-references to both case and organization:

```
documents/{documentId}
├── caseId: string
├── organizationId: string
├── filename: string (generated unique filename)
├── originalFilename: string
├── fileType: string (MIME type)
├── fileSize: number
├── storagePath: string (path in Cloud Storage)
├── uploadDate: timestamp
└── uploadedBy: string (user ID)
```

## Common Implementation Notes

### Firestore Security Rules

When implementing the backend, note that security also needs to be implemented at the Firestore level. This is not yet in place, but will be implemented as part of the security hardening phase.

The rules will enforce the same permission model at the database level, providing an additional layer of security.

### Rate Limiting

Rate limiting is not yet implemented but is planned for a future update. For now, the functions rely on Google Cloud's built-in quotas.

### Logging and Monitoring

Functions should include appropriate logging for security-relevant events. This includes:
- Authentication failures
- Permission denials
- Resource creation, modification, or deletion

### Request Validation

All functions should perform strict validation of incoming parameters:
- Required fields must be present and non-empty
- Field types must match expected types
- Input length and content should be validated
- Organizations should be verified to exist before operations

## Authorization Flow

The authorization flow in case management functions follows this process:

1. Request contains JWT token in Authorization header
2. `get_authenticated_user()` verifies the token and returns user info
3. Function extracts organization ID from request or resource
4. `check_permissions()` checks if the user is:
   - The resource owner (created the case)
   - An administrator in the organization
   - A staff member with appropriate permissions
5. If authorized, the function proceeds; if not, it returns a 403 Forbidden error

For list operations, the function adds an organization filter to ensure users only see resources they're authorized to view:

```python
# Filter cases by organization
query = firestore_client.collection("cases").where("organizationId", "==", organization_id)
```

## Feature Requirements Context

### Case Management Features

Cases represent legal matters that users are working on. Key features include:

- **Creation**: Cases must be associated with an organization
- **Ownership**: The creator is recorded as the case owner
- **Status Management**: Cases can be open, archived, or deleted
- **Permission Control**: Access is based on organization membership and roles
- **File Attachment**: Files can be uploaded to and downloaded from cases

### Organization Management Features

Organizations represent law firms, legal departments, or other entities. Key features include:

- **Membership**: Users can be members of multiple organizations
- **Roles**: Users have roles within each organization
- **Access Control**: Organization membership determines access to resources
- **Hierarchical Permissions**: Administrators have more permissions than staff members

## Known Limitations

- **Invite System**: The system doesn't yet have an invite mechanism for organizations
- **Role Granularity**: Currently only two roles (administrator and staff)
- **Multi-organization Cases**: Cases can only belong to one organization
- **Rate Limiting**: No custom rate limiting implementation yet
- **File Size Limits**: File size limits are those imposed by Firebase (default 5MB)

## Future Improvements

- Add more granular roles and permissions
- Implement custom rate limiting
- Add an invite system for organizations
- Support for sharing cases across organizations
- Implement Firestore security rules
- Add comprehensive logging and monitoring