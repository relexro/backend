# Data Models

This document outlines the primary data structures stored in Firestore, focusing on those relevant to cases, parties, and the Lawyer AI Agent.

## Firestore Collections

* `/users/{userId}`: Stores individual user profile information, authentication details, and subscription status (if individual).
* `/organizations/{organizationId}`: Stores organization details, subscription status, and member lists.
* `/parties/{partyId}`: Stores information about individuals or entities involved in cases. **Crucially, Personally Identifiable Information (PII) is stored here and accessed only via specific, authorized tools (e.g., PDF generator) – never directly by LLMs.**
* `/cases/{caseId}`: Stores the core information about each legal case, including metadata, status, attached entities, and the detailed agent context.

## `/cases/{caseId}` Document Structure

This document is central to the agent's operation.

```json
{
  "caseId": "string", // Unique ID for the case
  "title": "string", // User-defined title or auto-generated
  "userId": "string", // ID of the user who created the case
  "organizationId": "string | null", // ID of the organization the case belongs to, if any
  "createdAt": "timestamp",
  "updatedAt": "timestamp",
  "status": "string", // e.g., "tier_pending", "payment_pending", "active", "paused_support", "archived", "closed"
  "caseTier": "integer | null", // 1, 2, or 3 - Determined by agent
  "caseTypeId": "string | null", // Specific type identifier if needed, post-tiering (e.g., "traffic_fine_challenge", "divorce_uncontested")
  "attachedPartyIds": ["string"], // List of partyIds from the /parties collection relevant to this case
  "attachedDocumentIds": ["string"], // List of document metadata IDs stored likely in case_details or a subcollection, linking to Cloud Storage
  "subscriptionInfo": { // Denormalized snapshot at time of check/payment
    "checkedAt": "timestamp",
    "tierChecked": "integer",
    "quotaAvailable": "boolean",
    "paymentRequired": "boolean",
    "paymentCompleted": "boolean",
    "stripeSessionId": "string | null"
  },
  "gemini_session_id": "string | null", // Session ID for Gemini API context/billing per case
  "grok_session_id": "string | null",   // Session ID for Grok API context/billing per case
  "case_processing_state": { // State for recovery after timeout/reload
      "last_successful_step": "string", // Identifier of the last completed LangGraph node/step
      "pending_action": "string | null", // Description of the action that timed out
      "state_saved_at": "timestamp"
  },
  "case_details": { // Rich, evolving context managed by the agent (See detailed structure below)
    // ... Structure defined below ...
  }
}