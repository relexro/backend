# Relex Backend Blueprint

This document outlines the architecture, design decisions, and roadmap for the Relex backend.

## Architecture Overview

The Relex backend is built as a set of serverless Firebase Cloud Functions. Each function corresponds to a specific API endpoint and performs a discrete task.

### Core Components

1. **Authentication System**
   - Firebase Authentication for user identity
   - Custom role-based permission system
   - Organization membership management

2. **Case Management**
   - Individual and organization case management
   - Create, read, update, delete (CRUD) operations
   - File upload and management
   - Case status tracking (open, archived, deleted)
   - Dual ownership model (individual/organization)

3. **Organization Management**
   - Organization creation and configuration
   - User role management within organizations
   - Member invitation and management

4. **Infrastructure**
   - Terraform-managed Google Cloud resources
   - Firebase Firestore for data storage
   - Firebase Storage for file storage
   - Serverless architecture for scalability
   - Cloudflare DNS for custom domain (direct CNAME, unproxied)
   - API Gateway with custom domain (api.relex.ro)

## Development and Testing Workflow

### Project Structure and Workflow

The project follows a specific structure for development and deployment:

1. **Terraform Folder**: Contains all infrastructure configuration
   - The `/terraform` folder is the ONLY place for deployment configuration
   - All infrastructure changes must be defined here
   - ALWAYS use this folder for deploying any backend functions

2. **Tests Folder**: Contains all test scripts and configurations
   - The `/tests` folder is the ONLY place for test code
   - All new features must have corresponding tests
   - ALWAYS write tests for new functionality before deployment

3. **Development Workflow**:
   - Develop new features in the source code
   - Write tests in the tests folder
   - Run tests locally to validate
   - Use Terraform to deploy to the cloud environment
   - NEVER create ad-hoc or standalone deployment scripts

IMPORTANT: This workflow must be strictly adhered to for all development. Custom deployment scripts, manual deployments, or testing approaches outside this structure are NOT permitted. This ensures consistency, reliability, and maintainability of the codebase.

## Permission Model

The Relex backend implements a comprehensive role-based permission system that controls access to resources based on user roles within organizations, while also supporting individual case ownership.

### Core Principles

1. **Dual Ownership Model**: Cases can belong to either individuals or organizations
2. **Role-Based Access Control**: Organization access is determined by user roles
3. **Least Privilege**: Users are granted only the permissions necessary for their role
4. **Individual Ownership**: Users have full control over their individual cases
5. **Resource-Specific Permissions**: Each resource type has dedicated permission logic

### User Roles

The system defines the following roles within organizations:

1. **Administrator**
   - Can manage organization settings
   - Can manage all organization cases and documents
   - Can add and remove members from the organization
   - Can assign roles to members
   - Has full permissions for all organization actions

2. **Staff**
   - Can create cases for the organization
   - Can view cases they're explicitly assigned to
   - Can update and upload files to assigned cases
   - Cannot archive or delete organization cases (unless they are the case owner)
   - Cannot manage organization settings or members

3. **Case Owner**
   - Special designation for the user who created a case
   - Has full control over their individual cases
   - Has additional permissions for organization cases they created
   - Can archive or delete their own cases regardless of organization role

### Centralized Permission Definitions

The permission model uses a centralized permissions map that defines allowed actions for each role and resource type:

```python
PERMISSIONS = {
    "case": {
        "administrator": {"read", "update", "delete", "archive", "upload_file", 
                         "download_file", "attach_party", "detach_party", "assign_case"},
        "staff": {"read", "update", "upload_file", "download_file", 
                 "attach_party", "detach_party"},
        "owner": {"read", "update", "delete", "archive", "upload_file", 
                 "download_file", "attach_party", "detach_party"}
    },
    "organization": {
        "administrator": {"read", "update", "delete", "manage_members", 
                         "create_case", "list_cases", "assign_case"},
        "staff": {"read", "create_case", "list_cases"}
    },
    "party": {
        "owner": {"read", "update", "delete"}
    },
    "document": {
        "administrator": {"read", "delete"},
        "staff": {"read"},
        "owner": {"read", "delete"}
    }
}
```

### Resource-Specific Permission Checkers

The system implements modular, resource-specific permission checkers:

1. **Case Permissions**:
   - Checks for individual case ownership
   - For organization cases, checks membership role
   - For staff members, verifies case assignment
   - Owners have full permissions on their own cases

2. **Organization Permissions**:
   - Checks user membership and role
   - Administrators have full permissions
   - Staff have limited read/create permissions

3. **Party Permissions**:
   - Only the creator/owner can manage their parties
   - Strict ownership model

4. **Document Permissions**:
   - Maps document actions to parent case permissions
   - Access to documents is controlled through case access

### Permission Implementation

The permission model is implemented through the `check_permissions` function in the `auth.py` module. This function verifies that the authenticated user has the necessary permissions to perform the requested action.

The permission checks follow this process:

1. Authenticate the user making the request
2. Validate the request data using Pydantic
3. Determine the resource type (case, organization, party, document)
4. Dispatch to the appropriate resource-specific checker
5. The resource checker performs relevant database lookups
6. Allow or deny the request based on role, ownership, and assignment (for staff)

For cases and files, the following permissions apply:

| Action | Administrator | Staff (Assigned) | Staff (Unassigned) | Case Owner | Individual Owner |
|--------|---------------|------------------|-------------------|------------|------------------|
| Create Case | ✅ | ✅ | ✅ | N/A | ✅ |
| Read Case | ✅ | ✅ | ❌ | ✅ | ✅ |
| Update Case | ✅ | ✅ | ❌ | ✅ | ✅ |
| Archive Case | ✅ | ❌ | ❌ | ✅ | ✅ |
| Delete Case | ✅ | ❌ | ❌ | ✅ | ✅ |
| Upload File | ✅ | ✅ | ❌ | ✅ | ✅ |
| Download File | ✅ | ✅ | ❌ | ✅ | ✅ |
| List Cases | ✅ | ✅ (Only assigned) | ✅ (Only assigned) | ✅ | ✅ |

## Data Model

### Collections

1. **users**
   - User profile information
   - Authentication details
   - Language preferences
   - Subscription status

2. **organizations**
   - Organization details (name, type)
   - Contact information
   - Creation timestamp
   - Owner reference

3. **organization_memberships**
   - Maps users to organizations
   - Stores user roles within organizations
   - Manages access control
   - Timestamps for member actions

4. **cases**
   - Case metadata (title, description)
   - Created by user reference
   - Optional organization reference
   - Optional assignedUserId (for staff assignment)
   - Case tier and price information
   - Status (open, archived, deleted)
   - Payment status and payment intent ID
   - Creation and modification timestamps

5. **documents**
   - Document metadata
   - File storage references
   - Case reference
   - Upload information and timestamps

## API Design

The API is designed around RESTful principles, with each endpoint corresponding to a specific function:

### Authentication Endpoints

- `validate_user`: Validates the user's authentication token and returns user information
- `check_permissions`: Checks if a user has permission to perform a specific action on a resource

### User Management Endpoints

- `get_user_profile`: Retrieves the authenticated user's profile
- `update_user_profile`: Updates user profile information
- `list_user_organizations`: Lists organizations the user is a member of
- `list_user_cases`: Lists individual cases owned by the user

### Organization Management Endpoints

- `create_organization`: Creates a new organization
- `get_organization`: Retrieves organization details
- `update_organization`: Updates organization details
- `add_organization_member`: Adds a member to an organization with a specific role
- `remove_organization_member`: Removes a member from an organization
- `set_organization_member_role`: Updates a member's role within an organization
- `list_organization_members`: Lists all members of an organization

### Case Management Endpoints

- `create_case`: Creates a new case (individual or organization)
- `get_case`: Retrieves case details
- `list_cases`: Lists cases with filtering options
- `archive_case`: Archives a case
- `delete_case`: Marks a case as deleted

### File Management Endpoints

- `upload_file`: Uploads a file to a case
- `download_file`: Generates a download URL for a file

### Payment Processing Endpoints

- `create_payment_intent`: Creates a Stripe payment intent for case payments
- `create_checkout_session`: Creates a Stripe checkout session for subscriptions
- `cancel_subscription`: Cancels an active subscription
- `handle_stripe_webhook`: Processes Stripe webhook events to update database records

## Development Roadmap

### Phase 1: Core Infrastructure (Completed)

- Set up Firebase project and Firestore database
- Configure Firebase Authentication
- Create Terraform configuration for resource management
- Implement basic user management

### Phase 2: Case Management (Completed)

- Implement case CRUD operations
- Develop file upload and storage functionality
- Create case status management

### Phase 3: Organization Management (Completed)

- Implement organization creation and management
- Develop user role management within organizations
- Create organization membership functionality

### Phase 4: Permission System (Completed)

- Implement role-based access control
- Develop the `check_permissions` function
- Update all case and file functions to use permission checks
- Ensure proper organization ownership of resources

### Phase 5: Payment System (Completed)

- Implement Stripe integration for payments and subscriptions
- Create webhook handler for payment event processing
- Develop subscription management functionality
- Add case-tier based pricing model
- Implement payment verification during case creation
- Set up secure secrets management with Google Secret Manager

### Phase 6: AI Integration (Current Phase)

- Integrate with Vertex AI
- Implement conversation management
- Develop document analysis capabilities

### Phase 7: Advanced Features (Future)

- Develop analytics and reporting
- Create notification system
- Implement document versioning
- Add advanced security features

## Testing Strategy

The testing strategy includes:

1. **Unit Tests**: Testing individual functions for correct behavior
2. **Integration Tests**: Testing interactions between functions and external systems
3. **Permission Tests**: Verifying that the permission system correctly enforces access control
4. **End-to-End Tests**: Testing complete user workflows

### Testing Methods

- Automated tests using pytest in the `/tests` folder
- Manual testing with curl and Postman
- Log analysis for verification
- Firestore document inspection

## Deployment Process

The deployment process is automated using Terraform and follows these steps:

1. Code changes are committed to the repository
2. Terraform scripts in the `/terraform` folder are executed to provision or update resources
3. Firebase Functions are deployed with the new code
4. Verification tests are run to ensure correct deployment

## Security Considerations

The system implements several security measures:

1. **Authentication**: All API endpoints require valid authentication
2. **Authorization**: Role-based access control for all operations
3. **Data Validation**: Input validation for all API calls with Pydantic
4. **Secure Storage**: Encrypted storage for files and sensitive data
5. **Logging**: Comprehensive logging for security audits
6. **Staff Assignment Checks**: Verification that staff only access assigned cases

## Conclusion

This blueprint serves as a guide for the development and maintenance of the Relex backend. It will be updated as the system evolves and new features are implemented.