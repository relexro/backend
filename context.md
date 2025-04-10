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
- **Stripe**: Payment processing for individual cases
- **Cloudflare**: DNS management for custom domain (direct CNAME, unproxied)

## Design Principles

The backend follows these key design principles:

1. **Serverless Architecture**: Using Google Cloud's serverless offerings to minimize operational overhead
2. **Stateless Functions**: Each function is designed to be stateless, handling a single responsibility
3. **Separation of Concerns**: Code is organized into modules by feature area
4. **RESTful API Design**: Following REST principles for API design
5. **Dual Case Ownership**: Supporting both individual and organization-owned cases
6. **Role-Based Access Control**: Permissions based on organization roles and resource ownership

## Permission Model

The Relex backend implements a comprehensive permission system that supports both individual case ownership and organization-based role permissions. This model ensures appropriate access control for all resources.

### Case Ownership Model

The system supports two types of case ownership:

1. **Individual Cases**:
   - Created by individual users
   - Require per-case payment (handled through Stripe)
   - Owner has full control over the case
   - Not associated with any organization

2. **Organization Cases**:
   - Created within an organization context
   - Require per-case payment (handled through Stripe)
   - Access controlled by organization roles
   - Associated with a specific organization

### Organization Membership

For organization-owned resources:

1. **Organization Membership**: A user must be a member of an organization to access its resources
2. **Role Within Organization**: The specific permissions a user has depends on their role

### User Roles

The system defines the following roles:

1. **Administrator**:
   - Has full access to all organization resources
   - Can manage organization settings and membership
   - Can create, read, update, delete, and archive organization cases
   - Can upload and download files to organization cases

2. **Staff**:
   - Has limited access to organizational resources
   - Can create cases for the organization
   - Can read cases belonging to the organization
   - Can upload files to organization cases
   - Cannot archive or delete organization cases (unless they are the case owner)

3. **Individual User**:
   - Can create individual cases (with payment)
   - Has full control over their individual cases
   - Can be a member of organizations with specific roles

4. **Case Owner**:
   - Special designation for the user who created a case
   - Has full control over their individual cases
   - Has additional permissions for organization cases they created

### Permission Implementation

The permission model is implemented through the `check_permissions` function in the `auth.py` module. This function:

1. Authenticates the user making the request
2. Determines the resource type (case, file, organization, party, document)
3. For organization resources:
   - Identifies the organization
   - Checks the user's role within that organization
   - Verifies if the action is permitted based on the role
4. For individual cases:
   - Verifies case ownership
   - Checks payment status if required

### Resource Access Patterns

When a user performs an action on a case or file:

1. The system determines if it's an individual or organization case
2. For individual cases:
   - Verifies the user is the owner
   - Checks payment status if required
3. For organization cases:
   - Checks if the user is the case owner
   - If not, checks administrator role
   - If not, checks staff permissions
4. Access is granted or denied based on these checks

## Implementation Patterns

### Dual Ownership Access Control

All case and file management functions follow this pattern:

```python
# Authenticate user
user = get_authenticated_user()
if not user:
    return {"error": "Unauthorized", "message": "Authentication required"}, 401

# Get case data
case = get_case(case_id)
if not case:
    return {"error": "Not Found", "message": "Case not found"}, 404

# For individual cases
if not case.get("organizationId"):
    # Check ownership
    if case["userId"] != user["userId"]:
        return {"error": "Forbidden", "message": "Not the case owner"}, 403
    # Check payment status if required
    if action_requires_payment and case["paymentStatus"] != "paid":
        return {"error": "Payment Required", "message": "Case payment pending"}, 402

# For organization cases
else:
    allowed = check_permissions(
        user["userId"],
        resource_id=case_id,
        organization_id=case["organizationId"],
        action="action_name"
    )
    if not allowed:
        return {"error": "Forbidden", "message": "Insufficient permissions"}, 403

    # Check payment status if required
    if action_requires_payment and case["paymentStatus"] != "paid":
        return {"error": "Payment Required", "message": "Case payment pending"}, 402

# Proceed with the function logic
```

## Resource Collection Structure

### User Profile Structure

Created by Auth trigger on user creation:

```
users/{userId}
├── email: string
├── displayName: string
├── photoURL: string
├── role: string ("user", "admin")
├── stripeCustomerId: string (optional, links user to Stripe customer)
├── subscriptionPlanId: string (optional, e.g., 'personal_monthly', 'personal_yearly')
├── stripeSubscriptionId: string (optional, for active personal subscriptions)
├── subscriptionStatus: string ("active", "canceled", "past_due", "inactive", null)
├── caseQuotaTotal: number (integer, max cases included per cycle for current plan)
├── caseQuotaUsed: number (integer, default: 0, cases used in current cycle)
├── billingCycleStart: timestamp (optional, start date of current billing cycle)
├── billingCycleEnd: timestamp (optional, end date of current billing cycle)
├── languagePreference: string ("en", "ro")
├── createdAt: timestamp
└── updatedAt: timestamp
```

### Subscription Plans Schema

The `plans` collection in Firestore stores internal configuration data for subscription plans offered by the platform:

```
plans/{planId}
├── planId: string (matches Document ID, e.g., 'personal_monthly', 'business_pro_yearly')
├── name: string (user-friendly name, e.g., "Personal Monthly")
├── stripePriceId: string (corresponding Stripe Price ID, e.g., 'price_123abc')
├── caseQuotaTotal: number (integer, number of cases included per billing cycle)
├── isActive: boolean (whether the plan is currently offered)
├── type: string ('personal' or 'business')
├── billingCycle: string ('monthly' or 'yearly')
└── updatedAt: timestamp (when plan configuration was last modified)
```

### Organization Structure

```
organizations/{organizationId}
├── name: string
├── type: string
├── address: string (optional)
├── phone: string (optional)
├── email: string (optional)
├── ownerId: string
├── stripeCustomerId: string (optional, links organization to Stripe customer)
├── subscriptionPlanId: string (optional, e.g., 'business_standard_monthly', 'business_pro_yearly')
├── stripeSubscriptionId: string (optional, for active organization subscriptions)
├── subscriptionStatus: string ("active", "canceled", "past_due", "inactive", null)
├── caseQuotaTotal: number (integer, max cases included per cycle for current plan)
├── caseQuotaUsed: number (integer, default: 0, cases used in current cycle)
├── billingCycleStart: timestamp (optional, start date of current billing cycle)
├── billingCycleEnd: timestamp (optional, end date of current billing cycle)
└── createdAt: timestamp
```

### Organization Membership Structure

```
organization_memberships/{membershipId}
├── organizationId: string
├── userId: string
├── role: string ("administrator", "staff")
├── addedAt: timestamp
├── addedBy: string (userId of the user who added this member)
└── updatedAt: timestamp (optional)
```

### Case Structure

Supports both individual and organization cases:

```
cases/{caseId}
├── title: string
├── description: string
├── userId: string (**Creator/Owner User ID**)
├── organizationId: string (**Optional** - ID of the organization this case belongs to, null if individual case)
├── assignedUserId: string (**Optional** - ID of the staff user this case is assigned to, only for org cases)
├── status: string ("open", "archived", "deleted")
├── caseTier: number (e.g., 1, 2, 3 - indicates complexity tier)
├── caseTypeId: string (**Required** - Type of legal case, e.g., "divorce", "commercial_dispute")
├── casePrice: number (e.g., 900, 2900, 9900 - price in cents based on tier)
├── paymentStatus: string ("paid_intent", "paid_checkout", "pending", "failed", "covered_by_quota")
├── paymentIntentId: string (**Optional** - Links to Stripe Payment Intent for this case's fee)
├── attachedPartyIds: array of strings (**Optional** - List of party IDs linked to this case)
├── createdAt: timestamp
├── updatedAt: timestamp
├── archivedAt: timestamp (optional)
└── deletedAt: timestamp (optional)
```

### Case Type Configuration Structure

Defines behavior for the chat agent based on case type:

```
caseTypeConfigs/{caseTypeId}
├── caseTypeId: string (matches Document ID, e.g., 'divorce', 'commercial_dispute')
├── agentGoal: string (primary goal for the chat agent for this case type)
├── agentInstructions: array of strings (specific instructions for the agent)
└── relevantSources: array of strings (optional, sources to prioritize for this case type)
```

### Party Structure

Supports both individual (person) and organization parties:

```
parties/{partyId}
├── userId: string (**Creator/Owner User ID**)
├── partyType: string ("individual", "organization") (**Required** - Type of entity)
├── nameDetails: object (**Required**)
│   ├── firstName: string (**Required if partyType='individual'**)
│   ├── lastName: string (**Required if partyType='individual'**)
│   └── companyName: string (**Required if partyType='organization'**)
├── identityCodes: object (**Required**)
│   ├── cnp: string (**Required if partyType='individual'** - Romanian Personal Numeric Code)
│   ├── cui: string (**Required if partyType='organization'** - Romanian Org Fiscal Code)
│   └── regCom: string (**Required if partyType='organization'** - Romanian Org Registration Number)
├── contactInfo: object (**Required**)
│   ├── address: string
│   ├── email: string (optional)
│   └── phone: string (optional)
├── signatureData: object (optional)
│   ├── storagePath: string
│   └── capturedAt: timestamp
├── createdAt: timestamp
└── updatedAt: timestamp
```

### Document Structure

```
documents/{documentId}
├── documentId: string
├── caseId: string
├── filename: string
├── originalFilename: string
├── fileType: string
├── fileSize: number
├── storagePath: string
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
- **Deletion Control**: Organizations can only be deleted by administrators and must not have active subscriptions
- **Data Cleanup**: Organization deletion includes proper cleanup of all related data:
  - Organization memberships are removed
  - Organization cases are marked as deleted
  - Organization document is removed
  - All operations are performed in a transaction for data consistency

## Case Ownership Model

Cases in Relex can be owned in two ways:

1. **Individual Cases**:
   - Created by any authenticated user without associating an organization
   - Linked directly to the creator's `userId`
   - `organizationId` field in the case document is `null` or absent
   - Requires per-case payment (managed via Stripe Payment Intents)
   - Only the owner (`userId`) has access, besides system administrators

2. **Organization Cases**:
   - Created by a member (administrator or staff) of an organization
   - Linked to both the creator's `userId` and the `organizationId`
   - Access permissions are governed by the user's role within the organization
   - Requires per-case payment (managed via Stripe Payment Intents)

## Pricing and Subscription Model

The Relex platform implements a subscription model with included case quotas (Model B):

### Subscription Plans

1. **Personal Plans**:
   - Available directly to individual users
   - Provides access to basic platform features
   - Types: 'personal_monthly', 'personal_yearly'
   - Includes a predefined number of cases per billing cycle

2. **Business Plans**:
   - Available to organizations
   - Provides access to organization features and collaboration tools
   - Types: 'business_standard_monthly', 'business_standard_yearly', 'business_pro_monthly', 'business_pro_yearly'
   - Includes a predefined number of cases per billing cycle

### Case Tiers and Pricing

Cases are categorized by complexity tier:

1. **Tier 1 (Basic)**: Simple cases (€9.00 / 900 cents if purchased individually)
2. **Tier 2 (Standard)**: Medium complexity (€29.00 / 2900 cents if purchased individually)
3. **Tier 3 (Complex)**: High complexity (€99.00 / 9900 cents if purchased individually)

### Plans Configuration

The system uses an internal `plans` collection to define subscription plans:
- Each plan document defines the `caseQuotaTotal`
- Plans specify whether they are 'personal' or 'business' type
- Plans include the corresponding Stripe Price ID for billing
- Admin can modify plans or add new ones through this collection

### Quota Management

Quota usage is tracked in the user or organization document:
- `caseQuotaTotal`: Max number of cases included in the subscription
- `caseQuotaUsed`: Number of cases already created in the current billing cycle
- `billingCycleStart` and `billingCycleEnd`: Define the current quota period
- Quotas reset automatically at the end of each billing cycle

### Case Creation Flow

When creating a case:

1. Backend checks if the user/organization has an active subscription
2. If active, it compares `caseQuotaUsed` against `caseQuotaTotal`
3. If quota is available, case is created with `paymentStatus: "covered_by_quota"`
4. If quota is exceeded, user has two options:
   - Purchase an individual case via Stripe Payment Intent
   - Upgrade to a plan with a higher quota

For individual case purchases:
1. Frontend creates a Payment Intent for the desired case tier
2. User completes payment using Stripe Elements integration
3. After successful payment, case is created with `paymentStatus: "paid_intent"`
4. This case doesn't count against the subscription quota

### Stripe Integration

The platform integrates with Stripe for both subscription management and individual case payments:

1. **Stripe Customer ID**:
   - Each user/organization has a `stripeCustomerId`
   - This ID persists across multiple subscriptions or one-time payments

2. **Stripe Subscription ID**:
   - The `stripeSubscriptionId` links to an active subscription
   - Updated when subscriptions are created, changed, or canceled

3. **Payment Intent ID**:
   - Only present for individually purchased cases
   - Links to the Stripe payment for that specific case

4. **Webhook Handler**:
   - Processes various Stripe events to update Firestore data
   - Handles subscription lifecycle events
   - Updates quota reset on new billing cycles
   - Ensures data consistency between Stripe and Firestore

### Payment Status Tracking

Both subscriptions and individual case payments have status tracking:

1. **Subscription Status** (`subscriptionStatus`):
   - "active": Subscription is current and in good standing
   - "past_due": Payment failed but subscription still active
   - "canceled": Subscription has been canceled but not yet expired
   - "inactive": No active subscription

2. **Case Payment Status** (`paymentStatus`):
   - "covered_by_quota": Case was created using subscription quota
   - "paid_intent": Case was paid for individually via Payment Intent
   - "paid_checkout": Case was paid for via Checkout Session
   - "pending": Individual payment initiated but not completed
   - "failed": Individual payment attempt failed

## Chat Functionality

The Relex platform includes chat functionality that integrates with AI services:

### Messages Collection

Chat messages are stored in a subcollection `conversations` under each case. Each message includes:
- `promptId`: Unique ID for the message
- `prompt`: Original user prompt
- `response`: AI response
- `timestamp`: When the message was sent
- `userId`: Who sent the message

### Permission Control

- Messages can only be read or created by users with access to the parent case
- The permission check in `store_conversation` ensures proper authorization

### Enrichment Process

- The `enrich_prompt` function adds relevant case context to user prompts
- This enrichment improves AI understanding of the legal context

### AI Integration

- The backend connects to Vertex AI for response generation
- `send_to_vertex_ai` handles the interaction with the AI service

## Known Limitations

- **Invite System**: The system doesn't yet have an invite mechanism for organizations
- **Role Granularity**: Currently only two roles (administrator and staff)
- **Multi-organization Cases**: Cases can only belong to one organization
- **Rate Limiting**: No custom rate limiting implementation yet
- **File Size Limits**: File size limits are those imposed by Firebase (default 5MB)

## Future Improvements

1. Add more granular roles and permissions
2. Implement custom rate limiting
3. Add an invite system for organizations
4. Support for sharing cases across organizations
5. Implement Firestore security rules
6. Add comprehensive logging and monitoring