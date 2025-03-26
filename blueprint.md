# Relex Backend Blueprint

## System Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│                        CLIENT APPLICATIONS                        │
│    (Web, Mobile - React/React Native/Flutter Applications)        │
│                                                                   │
└───────────────────────┬───────────────────────┬──────────────────┘
                        │                       │
                        ▼                       ▼
┌───────────────────────────────┐   ┌─────────────────────────────┐
│                               │   │                             │
│  FIREBASE AUTHENTICATION      │   │  CLOUD STORAGE              │
│  - User Sign-up/Sign-in       │   │  - Document Storage         │
│  - JWT Token Generation       │   │  - File Upload/Download     │
│  - User Management            │   │                             │
│                               │   │                             │
└─────────────┬─────────────────┘   └───────────────┬─────────────┘
              │                                     │
              ▼                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    GOOGLE CLOUD FUNCTIONS                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐  ┌────────────────┐  ┌───────────────────┐  │
│  │               │  │                │  │                   │  │
│  │  Auth Module  │  │  Organization  │  │  Cases Module     │  │
│  │               │  │  Module        │  │                   │  │
│  └───────────────┘  └────────────────┘  └───────────────────┘  │
│                                                                 │
│  ┌───────────────┐  ┌────────────────┐  ┌───────────────────┐  │
│  │               │  │                │  │                   │  │
│  │  Chat Module  │  │  Payments      │  │  Files Module     │  │
│  │               │  │  Module        │  │                   │  │
│  └───────────────┘  └────────────────┘  └───────────────────┘  │
│                                                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                      FIRESTORE DATABASE                         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐  ┌────────────────┐  ┌───────────────────┐  │
│  │ organizations │  │     cases      │  │    documents      │  │
│  │ collection    │  │   collection   │  │    collection     │  │
│  └───────┬───────┘  └────────┬───────┘  └────────┬──────────┘  │
│          │                   │                    │             │
│          ▼                   ▼                    ▼             │
│  ┌───────────────┐  ┌────────────────┐  ┌───────────────────┐  │
│  │ users         │  │  conversations │  │  payments         │  │
│  │ subcollection │  │  subcollection │  │  collection       │  │
│  └───────────────┘  └────────────────┘  └───────────────────┘  │
│                                                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                          VERTEX AI                              │
│                   (For AI Chat Capabilities)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component Interactions

### Authentication Flow

1. Client application initiates authentication with Firebase Auth
2. Firebase Auth issues JWT token to authenticated user
3. Client includes token in Authorization header for API requests
4. Cloud Functions verify token and extract user information
5. Permission checks are performed based on user roles stored in Firestore

### Organization Management Flow

1. Admin user creates an organization via `create_organization` endpoint
2. Organization details stored in `organizations` collection in Firestore
3. Admin is automatically added to organization's users subcollection with admin role
4. Admin can add additional users via `add_organization_user` endpoint
5. User roles can be modified using `set_user_role` endpoint
6. Organization info can be updated via `update_organization` endpoint

### Case Management Flow

1. User creates a case via `create_case` endpoint, optionally linked to an organization
2. Case details stored in `cases` collection in Firestore
3. Users can view cases they own or cases belonging to organizations they're members of
4. Case status can be updated via `archive_case` or `delete_case` endpoints

### Document Management Flow

1. User uploads files to a case via `upload_file` endpoint
2. Files stored in Cloud Storage with unique filenames
3. Metadata stored in `documents` collection in Firestore
4. Files can be downloaded via `download_file` endpoint which generates signed URLs

### Chat Interaction Flow

1. User sends a prompt via `receive_prompt` endpoint
2. Prompt is enriched with case context via `enrich_prompt` endpoint
3. Enriched prompt is sent to Vertex AI via `send_to_vertex_ai` endpoint
4. Response is received from Vertex AI and returned to client
5. Conversation is stored in Firestore via `store_conversation` endpoint

### Payment Processing Flow

1. User initiates payment via `create_payment_intent` or `create_checkout_session` endpoint
2. Stripe payment intent or checkout session is created
3. Client secret or checkout URL is returned to client
4. Client completes payment on frontend using Stripe.js or Checkout
5. Payment status is updated via webhook (not yet implemented)

## Data Models

### Organization Collection (formerly Business)

```
organizations/{organizationId}
├── name: string
├── type: string
├── address: string
├── phone: string
├── email: string
├── ownerId: string (user ID of organization owner)
├── createdAt: timestamp
├── updatedAt: timestamp (optional)
├── status: string ("active", "inactive", "suspended")
└── users/{userId} (subcollection)
    ├── role: string ("admin", "member") 
    ├── addedDate: timestamp
    └── updatedAt: timestamp (optional)
```

### Cases Collection

```
cases/{caseId}
├── title: string
├── description: string
├── userId: string (owner user ID)
├── organizationId: string (optional, if associated with an organization)
├── status: string ("open", "closed", "archived", "deleted")
├── creationDate: timestamp
├── archiveDate: timestamp (if archived)
└── deletionDate: timestamp (if deleted)
```

### Documents Collection

```
documents/{documentId}
├── caseId: string
├── filename: string (generated unique filename)
├── originalFilename: string
├── fileType: string (MIME type)
├── fileSize: number
├── storagePath: string (path in Cloud Storage)
├── uploadDate: timestamp
└── uploadedBy: string (user ID)
```

### Conversations Collection

```
conversations/{conversationId}
├── userId: string
├── caseId: string (optional)
└── messages/{messageId} (subcollection)
    ├── prompt: string
    ├── response: string
    ├── timestamp: timestamp
    └── enrichedContext: string (optional)
```

## Deployment Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│                  TERRAFORM CONFIGURATION                       │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐ │
│  │                     │  │                                 │ │
│  │  Google Project     │  │  Firebase Project               │ │
│  │  Configuration      │  │  Configuration                  │ │
│  │                     │  │                                 │ │
│  └─────────────────────┘  └─────────────────────────────────┘ │
│                                                                │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐ │
│  │                     │  │                                 │ │
│  │  Cloud Functions    │  │  Storage Bucket                 │ │
│  │  Configuration      │  │  Configuration                  │ │
│  │                     │  │                                 │ │
│  └─────────────────────┘  └─────────────────────────────────┘ │
│                                                                │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐ │
│  │                     │  │                                 │ │
│  │  IAM Permissions    │  │  API Enablement                 │ │
│  │  Configuration      │  │  Configuration                  │ │
│  │                     │  │                                 │ │
│  └─────────────────────┘  └─────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

All cloud infrastructure is managed through Terraform, including:
1. Google Cloud Project setup
2. Firebase project configuration
3. Cloud Functions deployment
4. Storage bucket creation
5. IAM permissions
6. API enablement

## API Endpoints Map

### Authentication Endpoints
- `validate_user`: Validates JWT token and returns user info
- `check_permissions`: Checks if user has permission for a specific action
- `get_user_role`: Gets a user's role in an organization

### Organization Endpoints (formerly Business)
- `create_organization`: Creates a new organization account
- `get_organization`: Retrieves organization details by ID
- `add_organization_user`: Adds a user to an organization
- `set_user_role`: Sets a user's role in an organization
- `update_organization`: Updates organization details
- `list_organization_users`: Lists users in an organization
- `remove_organization_user`: Removes a user from an organization

### Case Management Endpoints
- `create_case`: Creates a new case
- `get_case`: Retrieves case details by ID
- `list_cases`: Lists cases with optional filters
- `archive_case`: Archives a case
- `delete_case`: Marks a case as deleted

### File Management Endpoints
- `upload_file`: Uploads a file to a case
- `download_file`: Generates a signed URL for downloading a file

### Chat Endpoints
- `receive_prompt`: Receives a prompt from a user
- `send_to_vertex_ai`: Sends a prompt to Vertex AI
- `store_conversation`: Stores a conversation
- `enrich_prompt`: Enriches a prompt with case context

### Payment Endpoints
- `create_payment_intent`: Creates a Stripe Payment Intent
- `create_checkout_session`: Creates a Stripe Checkout Session