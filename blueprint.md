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
   - Create, read, update, delete (CRUD) operations for legal cases
   - File upload and management
   - Case status tracking (open, archived, deleted)
   - Organization-based access control

3. **AI Integration**
   - Integration with Vertex AI for legal analysis
   - Conversation history management
   - Document analysis capabilities

4. **Organization Management**
   - Organization creation and configuration
   - User role management within organizations
   - Billing and subscription management

5. **Infrastructure**
   - Terraform-managed Google Cloud resources
   - Firebase Firestore for data storage
   - Firebase Storage for file storage
   - Serverless architecture for scalability

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

The Relex backend implements a comprehensive role-based permission system that controls access to resources based on user roles within organizations.

### Core Principles

1. **Organization Ownership**: All cases and documents belong to organizations, not individual users
2. **Role-Based Access Control**: Access to resources is determined by a user's role within an organization
3. **Least Privilege**: Users are granted only the permissions necessary for their role
4. **Hierarchical Permissions**: Higher-level roles inherit permissions from lower-level roles

### User Roles

The system defines the following roles within organizations:

1. **Administrator**
   - Can manage organization settings
   - Can manage all cases and documents within the organization
   - Can add and remove users from the organization
   - Can assign roles to users
   - Has full permissions for all actions

2. **Staff**
   - Can create cases for the organization
   - Can view all cases within the organization
   - Can upload files to cases
   - Cannot archive or delete cases (unless they are the case owner)
   - Cannot manage organization settings or users

3. **Case Owner**
   - Special designation for the user who created a case
   - Has additional permissions for their own cases
   - Can archive or delete their own cases regardless of their organization role

### Permission Implementation

The permission model is implemented through the `check_permissions` function in the `auth.py` module. This function is called by all case and file management functions to verify that the authenticated user has the necessary permissions to perform the requested action.

The permission checks follow this process:

1. Authenticate the user making the request
2. Determine the resource type (case, file, organization)
3. Identify the organization that owns the resource
4. Check the user's role within that organization
5. Verify if the action is permitted based on the role and resource
6. Allow or deny the request accordingly

For cases and files, the following permissions apply:

| Action | Administrator | Staff | Case Owner | Non-Member |
|--------|---------------|-------|------------|------------|
| Create case | ✅ | ✅ | N/A | ❌ |
| View case | ✅ | ✅ | ✅ | ❌ |
| Archive case | ✅ | ❌ | ✅ | ❌ |
| Delete case | ✅ | ❌ | ✅ | ❌ |
| Upload file | ✅ | ✅ | ✅ | ❌ |
| Download file | ✅ | ✅ | ✅ | ❌ |
| List cases | ✅ | ✅ | ✅ | ❌ |

## Data Model

### Collections

1. **users**
   - User profile information
   - Authentication details
   - Preferences

2. **organizations**
   - Organization details (name, type, etc.)
   - Billing information
   - Configuration settings

3. **organization_memberships**
   - Maps users to organizations
   - Stores user roles within organizations
   - Manages access control

4. **cases**
   - Case metadata (title, description, status)
   - Created by user reference
   - Organization reference
   - Creation and modification timestamps
   - Status tracking (open, archived, deleted)

5. **documents**
   - Document metadata
   - File storage references
   - Case and organization references
   - Upload information

6. **conversations**
   - AI conversation history
   - Prompts and responses
   - User and case references

7. **messages**
   - Individual messages within conversations
   - Timestamps and metadata
   - References to AI model used

## API Design

The API is designed around RESTful principles, with each endpoint corresponding to a specific function:

### Authentication Endpoints

- `validate_user`: Validates the user's authentication token and returns user information
- `check_permissions`: Checks if a user has permission to perform a specific action on a resource

### Case Management Endpoints

- `create_case`: Creates a new case, requiring organization ID and checking permissions
- `get_case`: Retrieves a case by ID, checking if the user has access to the case's organization
- `list_cases`: Lists cases, filtered by organization ID with permission checks
- `archive_case`: Archives a case, requiring administrator or case owner permissions
- `delete_case`: Marks a case as deleted, requiring administrator or case owner permissions

### File Management Endpoints

- `upload_file`: Uploads a file to a case, checking if the user has access to the case's organization
- `download_file`: Generates a download URL for a file, checking if the user has access to the case's organization

### Organization Management Endpoints

- `create_organization`: Creates a new organization
- `get_organization`: Retrieves organization details
- `update_organization`: Updates organization details
- `add_organization_member`: Adds a user to an organization with a specific role
- `remove_organization_member`: Removes a user from an organization
- `set_organization_member_role`: Updates a user's role within an organization
- `list_organization_members`: Lists all members of an organization
- `list_user_organizations`: Lists all organizations a user belongs to

### AI Integration Endpoints

- `receive_prompt`: Receives a user prompt for AI processing
- `send_to_vertex_ai`: Sends a prepared prompt to Vertex AI and returns the response
- `store_conversation`: Stores conversation history for future reference

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

### Phase 4: Permission System (Current Phase)

- Implement role-based access control
- Develop the `check_permissions` function
- Update all case and file functions to use permission checks
- Ensure proper organization ownership of resources

### Phase 5: AI Integration (Planned)

- Integrate with Vertex AI
- Implement conversation management
- Develop document analysis capabilities

### Phase 6: Advanced Features (Future)

- Implement billing and subscription management
- Develop analytics and reporting
- Create notification system
- Implement document versioning

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
3. **Data Validation**: Input validation for all API calls
4. **Secure Storage**: Encrypted storage for files and sensitive data
5. **Logging**: Comprehensive logging for security audits

## Conclusion

This blueprint serves as a guide for the development and maintenance of the Relex backend. It will be updated as the system evolves and new features are implemented.