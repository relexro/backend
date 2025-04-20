# Architecture Overview

This document provides a high-level overview of the Relex application architecture, incorporating the Lawyer AI Agent feature.

## Components

The system comprises several key components interacting to deliver the legal case management and AI assistance functionality:

1.  **Frontend (SvelteKit):** The user interface where users (Individuals, Organization Admins/Staff) interact with the application, manage cases, parties, documents, and communicate with the Lawyer AI Agent.
2.  **API Gateway (Google Cloud):** Exposes the backend functionality via a RESTful API defined in `openapi_spec.yaml`. Handles request routing, authentication, and potentially rate limiting.
3.  **Backend Cloud Functions (Google Cloud):** Stateless Python functions handling the core business logic:
    * Authentication (`auth.py`)
    * User Management (`user.py`)
    * Organization Management (`organization.py`, `organization_membership.py`)
    * Case Management (`cases.py`)
    * Party Management (`party.py`)
    * Payment Processing (`payments.py` via Stripe)
    * **Agent Interaction Handler:** A new or significantly modified function (previously `chat.py`) responsible for receiving user messages for the agent, invoking the LangGraph agent, managing state, and returning responses.
4.  **Lawyer AI Agent (LangGraph):** The core AI engine orchestrated using LangGraph. It resides within or is invoked by the Agent Interaction Handler function. Key internal components:
    * **LangGraph Orchestrator:** Manages the agent's state machine and flow execution.
    * **Gemini Flash 2.5 (LLM):** Acts as the primary assistant LLM - handles user interaction, data gathering, document parsing, tool formatting, draft writing based on Grok's guidance, and tier determination.
    * **Grok 3 Mini (LLM):** Acts as the expert legal reasoner - provides strategic guidance, requests specific information, validates legal findings, and outlines draft requirements.
    * **Function Tools:** Specific Python functions callable by the agent (defined in `tools.md`, implemented likely within backend functions) for actions like querying BigQuery, checking quotas, managing `case_details`, generating PDFs, looking up party IDs, and creating support tickets.
5.  **Firestore (Google Cloud):** NoSQL database used for storing application data:
    * User profiles, organization details, subscriptions.
    * Case metadata (including `case_details`, `case_processing_state`, `gemini_session_id`, `grok_session_id`, draft Markdown content & metadata).
    * Party information (PII stored separately and securely).
    * Agent message history (potentially).
6.  **Cloud Storage (Google Cloud):** Stores binary files:
    * User-uploaded case documents (`case_id/attachments/`).
    * Agent-generated PDF drafts (`case_id/drafts/`).
7.  **BigQuery (Google Cloud):** Data warehouse storing Romanian legal data:
    * `relexro.romanian_legal_data.legislatie` (Legislation)
    * `relexro.romanian_legal_data.jurisprudenta` (Case Law)
8.  **Stripe:** External service for handling subscription and individual case payments.

## High-Level Interaction Flow (Agent Focus)

```mermaid
sequenceDiagram
    participant User (Frontend)
    participant API Gateway
    participant Backend Function (Agent Handler)
    participant Lawyer Agent (LangGraph)
    participant Gemini (LLM)
    participant Grok (LLM)
    participant Function Tools
    participant Firestore
    participant Cloud Storage
    participant BigQuery
    participant Stripe

    User->>API Gateway: Send Message (POST /cases/{id}/agent/message)
    API Gateway->>Backend Function (Agent Handler): Forward Request
    Backend Function (Agent Handler)->>Firestore: Load case_details, state, history
    Backend Function (Agent Handler)->>Lawyer Agent (LangGraph): Invoke Agent(state, message)

    Note over Lawyer Agent (LangGraph): Agent Loop Starts (Tiering/Payment or Resolution)

    Lawyer Agent (LangGraph)->>Gemini (LLM): Process message / Determine next step
    Gemini (LLM)->>Lawyer Agent (LangGraph): Analysis / Tool Call Request

    alt Tier Determination
        Lawyer Agent (LangGraph)->>Gemini (LLM): Ask to determine tier (with definitions)
        Gemini (LLM)->>Lawyer Agent (LangGraph): Determined Tier
        Lawyer Agent (LangGraph)->>Function Tools: check_quota(tier)
        Function Tools->>Firestore: Read subscription/quota
        Function Tools-->>Lawyer Agent (LangGraph): Quota OK/Not OK
        alt No Quota
             Lawyer Agent (LangGraph)->>Backend Function (Agent Handler): Signal Need Payment
             Backend Function (Agent Handler)-->>User (Frontend): Prompt for Payment
             User->>Stripe: Perform Payment
             Stripe-->>Backend Function (Agent Handler): Payment Webhook
             Backend Function (Agent Handler)->>Firestore: Update Case Status
             User->>API Gateway: Resume Interaction / Send Message
             Note over User (Frontend): Flow continues after payment
        end
    end

    alt Case Resolution
        Lawyer Agent (LangGraph)->>Gemini (LLM): Gather info / Query BQ / Consult Grok / Generate Draft
        Gemini (LLM)->>Lawyer Agent (LangGraph): Request Tool (e.g., query_bigquery, get_party_id, consult_grok, update_case_details)

        Lawyer Agent (LangGraph)->>Function Tools: Execute Tool Call (e.g., query_bigquery)
        Function Tools->>BigQuery: Execute Query
        BigQuery-->>Function Tools: Results
        Function Tools-->>Lawyer Agent (LangGraph): Tool Result

        Lawyer Agent (LangGraph)->>Gemini (LLM): Provide Tool Result / Ask Grok Guidance

        Gemini (LLM)->>Grok (LLM): Present context, ask guidance
        Grok (LLM)-->>Gemini (LLM): Reasoning / Next Steps / Plan

        Gemini (LLM)->>Lawyer Agent (LangGraph): Plan / Draft Instructions / User Query

        alt Generate Draft
            Lawyer Agent (LangGraph)->>Gemini (LLM): Write Draft Markdown (with placeholders)
            Gemini (LLM)-->>Lawyer Agent (LangGraph): Markdown Content
            Lawyer Agent (LangGraph)->>Function Tools: generate_draft_pdf(...)
            Function Tools->>Firestore: Get Party PII
            Function Tools->>Cloud Storage: Store PDF Draft
            Function Tools->>Firestore: Store Draft Metadata
            Function Tools-->>Lawyer Agent (LangGraph): Success / Draft Path
        end
    end


    Lawyer Agent (LangGraph)->>Backend Function (Agent Handler): Final Response / State Update
    Backend Function (Agent Handler)->>Firestore: Save case_details, state, history
    Backend Function (Agent Handler)-->>User (Frontend): Send Agent Reply (within timeout)