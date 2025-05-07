# Data Models

This document details the Firestore data models used in the Relex backend. All schemas are designed to work efficiently with the application's business logic and API endpoints.

## Users

Collection: `users`

Stores information about registered users.

```
users/{userId}
  |- displayName: string
  |- email: string
  |- photoURL: string (optional)
  |- createdAt: timestamp
  |- updatedAt: timestamp
  |- languagePreference: string (enum: 'en', 'ro')
  |- organizations: string[] (array of organization IDs the user belongs to)
  |- subscription: {
  |    subscription_id: string
  |    status: string (enum: 'active', 'canceled', 'past_due')
  |    plan: string
  |    current_period_end: timestamp
  |    cancel_at_period_end: boolean
  |    stripe_customer_id: string
  |  }
  |- quota: {
  |    tier_1: {
  |      remaining: number
  |      total: number
  |      reset_date: timestamp
  |    },
  |    tier_2: {
  |      remaining: number
  |      total: number
  |      reset_date: timestamp
  |    },
  |    tier_3: {
  |      remaining: number
  |      total: number
  |      reset_date: timestamp
  |    }
  |  }
```

## Organizations

Collection: `organizations`

Stores information about legal organizations (law firms, companies, etc.).

```
organizations/{organizationId}
  |- name: string
  |- type: string (enum: 'law_firm', 'company', 'ngo', 'government')
  |- address: string (optional)
  |- phone: string (optional)
  |- email: string (optional)
  |- createdAt: timestamp
  |- updatedAt: timestamp
  |- createdBy: string (user ID)
  |- subscription: {
  |    subscription_id: string
  |    status: string (enum: 'active', 'canceled', 'past_due')
  |    plan: string
  |    current_period_end: timestamp
  |    cancel_at_period_end: boolean
  |    stripe_customer_id: string
  |  }
  |- quota: {
  |    tier_1: {
  |      remaining: number
  |      total: number
  |      reset_date: timestamp
  |    },
  |    tier_2: {
  |      remaining: number
  |      total: number
  |      reset_date: timestamp
  |    },
  |    tier_3: {
  |      remaining: number
  |      total: number
  |      reset_date: timestamp
  |    }
  |  }
```

## Organization Memberships

Collection: `organization_memberships`

Represents the relationship between users and organizations.

```
organization_memberships/{membershipId}
  |- userId: string
  |- organizationId: string
  |- role: string (enum: 'administrator', 'staff')
  |- createdAt: timestamp
  |- updatedAt: timestamp
  |- invitedBy: string (user ID, optional)
  |- status: string (enum: 'active', 'pending', 'inactive')
```

## Cases

Collection: `cases`

Stores information about legal cases.

```
cases/{caseId}
  |- title: string
  |- description: string
  |- createdAt: timestamp
  |- updatedAt: timestamp
  |- status: string (enum: 'open', 'archived', 'deleted')
  |- tier: number (1, 2, or 3)
  |- owner: {
  |    type: string (enum: 'user', 'organization')
  |    user_id: string (if type is 'user')
  |    organization_id: string (if type is 'organization')
  |  }
  |- labels: string[] (array of label IDs)
  |- parties: {
  |    party_id: {
  |      id: string
  |      name: string
  |      type: string (enum: 'individual', 'company', 'organization', etc.)
  |      role: string (enum: 'plaintiff', 'defendant', 'third_party', 'witness', etc.)
  |      details: object (varies based on type)
  |    }
  |  }
  |- legal_analysis: {
  |    summary: string
  |    key_issues: string[]
  |    recommendations: string[]
  |    risk_assessment: string
  |  }
  |- timeline: [
  |    {
  |      date: timestamp
  |      event: string
  |      description: string
  |      documents: string[] (document IDs)
  |    }
  |  ]
  |- documents: [
  |    {
  |      id: string
  |      title: string
  |      type: string
  |      url: string
  |      createdAt: timestamp
  |      generatedBy: string (enum: 'user', 'ai')
  |    }
  |  ]
  |- notes: [
  |    {
  |      id: string
  |      content: string
  |      createdAt: timestamp
  |      createdBy: string (user ID)
  |    }
  |  ]
  |- case_processing_state: {
  |    current_phase: string
  |    current_step: string
  |    conversation_history: [
  |      {
  |        role: string (enum: 'user', 'assistant')
  |        content: string
  |        timestamp: timestamp
  |      }
  |    ]
  |    tools_history: [
  |      {
  |        tool: string
  |        inputs: object
  |        outputs: object
  |        timestamp: timestamp
  |        success: boolean
  |        error: string (optional)
  |      }
  |    ]
  |    drafts_in_progress: object
  |    last_updated: timestamp
  |  }
```

## Parties

Collection: `parties`

Stores information about parties involved in legal cases.

```
parties/{partyId}
  |- name: string
  |- type: string (enum: 'individual', 'company', 'organization', 'government')
  |- contactInfo: {
  |    email: string (optional)
  |    phone: string (optional)
  |    address: string (optional)
  |  }
  |- createdAt: timestamp
  |- updatedAt: timestamp
  |- createdBy: string (user ID)
  |- organizationId: string (optional, if created within an organization)
  |- details: {
  |    // For individuals:
  |    dateOfBirth: timestamp (optional)
  |    identification: string (optional)
  |    nationality: string (optional)
  |    
  |    // For companies/organizations:
  |    registrationNumber: string (optional)
  |    legalRepresentative: string (optional)
  |    industry: string (optional)
  |  }
```

## Labels

Collection: `labels`

Stores labels that can be applied to cases for organization.

```
labels/{labelId}
  |- name: string
  |- color: string (hex color code)
  |- createdAt: timestamp
  |- updatedAt: timestamp
  |- createdBy: string (user ID)
  |- organizationId: string (optional, if created within an organization)
```

## Case Processing State

The `case_processing_state` is a subdocument within the case document that tracks the AI agent's progress.

```
case_processing_state: {
  current_phase: string (enum: 'initialization', 'tier_determination', 'information_gathering', 'analysis', 'document_generation', 'conclusion')
  current_step: string (more detailed step within the current phase)
  conversation_history: [
    {
      role: string (enum: 'user', 'assistant')
      content: string
      timestamp: timestamp
    }
  ]
  tools_history: [
    {
      tool: string (name of the tool used)
      inputs: object (parameters passed to the tool)
      outputs: object (results returned by the tool)
      timestamp: timestamp
      success: boolean
      error: string (error message if tool execution failed)
    }
  ]
  drafts_in_progress: {
    document_type: {
      title: string
      content: string
      last_updated: timestamp
    }
  }
  last_updated: timestamp
  timeout_timestamp: timestamp (when the current state expires)
}
```

## Case Type Configurations

The system supports configuration for different case types, which affects agent behavior and available templates.

```
caseTypeConfigs/{configId}
  |- name: string
  |- description: string
  |- category: string (legal domain)
  |- applicablePartyRoles: string[] (roles that apply to this case type)
  |- requiredInformation: [
  |    {
  |      field: string
  |      description: string
  |      required: boolean
  |    }
  |  ]
  |- availableTemplates: string[] (IDs of templates applicable to this case type)
  |- defaultTier: number (suggested tier for this case type)
```

## Plans

The system tracks subscription plans in Firestore for reference, though the actual payment processing is handled by Stripe.

```
plans/{planId}
  |- name: string
  |- description: string
  |- price: number
  |- currency: string
  |- interval: string (enum: 'month', 'year')
  |- tierAccess: number[] (tiers accessible with this plan)
  |- quotaAllocations: {
  |    tier_1: number
  |    tier_2: number
  |    tier_3: number
  |  }
  |- features: string[]
  |- stripeProductId: string
  |- stripePriceId: string
  |- isActive: boolean
```

## Vouchers

Used for promotional codes and special access.

```
vouchers/{voucherId}
  |- code: string
  |- type: string (enum: 'discount', 'quota_increase', 'tier_access')
  |- value: number (amount of discount or quota increase)
  |- validFrom: timestamp
  |- validUntil: timestamp
  |- maxUses: number
  |- currentUses: number
  |- isActive: boolean
  |- createdBy: string (user ID)
  |- restrictions: {
  |    userIds: string[] (specific users, if restricted)
  |    organizationIds: string[] (specific organizations, if restricted)
  |    planIds: string[] (specific plans, if restricted)
  |  }
```

## Indexing Considerations

The following compound indexes are required for efficient querying:

1. Cases by owner and status:
   ```
   cases: owner.user_id, status
   cases: owner.organization_id, status
   ```

2. Organization memberships by user and organization:
   ```
   organization_memberships: userId, organizationId
   organization_memberships: organizationId, role
   ```

3. Labels by organization:
   ```
   labels: organizationId, name
   ```

4. Parties by organization:
   ```
   parties: organizationId, name
   ```
