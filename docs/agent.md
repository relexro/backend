# Lawyer AI Agent Implementation Guide

## 1. Overview and Purpose

This document provides a comprehensive guide to the Lawyer AI Agent feature within the Relex platform. This agent replaces the previous chat functionality (described in the original `chat.md` [cite: 1]) and represents a significant evolution from a Retrieval-Augmented Generation (RAG) approach with direct context injection to a sophisticated, multi-step agent architecture.

The Lawyer AI Agent is designed to assist users interactively with Romanian legal cases. Its core purpose is to guide users through the entire lifecycle of a case within the platform, from initial assessment and onboarding to performing legal research, providing strategic insights, and generating relevant legal documents.

**Key Goals & Responsibilities:**

* **Interactive Case Assistance:** Engage users via the chat interface to understand their situation.
* **Automated Case Assessment:** Determine case complexity (Tier 1, 2, or 3) based on user descriptions and predefined criteria (see `tiers_ro.md`).
* **Access Management:** Check user subscription quotas against the determined tier and facilitate per-case payments via Stripe integration when necessary[cite: 1].
* **Contextual Understanding:** Build and maintain a rich, evolving understanding of the case (`case_details` object in Firestore) by processing user input, analyzing attached documents, and tracking interactions[cite: 1].
* **Legal Research:** Perform targeted queries against a specialized BigQuery database containing Romanian legislation (`legislatie`) and case law (`jurisprudenta`). This replaces the previous main RAG system based on Vertex AI Search[cite: 1].
* **Expert Reasoning & Strategy:** Leverage a dedicated reasoning LLM (Grok) to analyze case context, identify legal strategies, and guide the research and drafting process.
* **Document Drafting:** Generate draft legal documents (e.g., court applications, notifications) in Markdown format with placeholders for sensitive data, and facilitate their conversion to secure PDFs.
* **Tool Utilization:** Effectively use a suite of specialized function tools for interacting with backend services, databases, and APIs (defined in `tools.md`).
* **State Management & Error Handling:** Manage its operational state across potentially long-running interactions and handle errors gracefully following a defined protocol.
* **Privacy & Security:** Adhere to strict privacy protocols, ensuring PII is handled securely and never directly accessed by LLMs.

*(For a high-level system view, refer to `architecture.md`)*.

## 2. Architecture & Core Components

The agent utilizes a modern agent architecture orchestrated using **LangGraph**, running within the backend Google Cloud Functions environment (specifically, the `agent_handler.py` function, replacing the old `chat.py` [cite: 1]).

**Key Components:**

1.  **LangGraph Orchestrator:** Manages the agent's state machine, controlling the flow between different processing steps (nodes) based on defined logic and results.
2.  **LLMs:**
    * **Gemini Flash 2.5 (Assistant):** The primary LLM responsible for user interaction (Romanian), prompt analysis, data extraction, context summarization, calling function tools, writing Markdown drafts based on Grok's guidance, and initial tier determination. Operates under instructions defined in `prompts.md`.
    * **Grok 3 Mini (Reasoner):** The expert legal LLM providing strategic oversight, legal reasoning, guidance on information needs, validation of research findings, and planning for document drafting. Interacts with Gemini in Romanian, guided by prompts in `prompts.md`.
3.  **Function Tools:** A suite of specialized Python functions callable by the agent (primarily Gemini) to perform specific actions. These bridge the gap between the LLMs and the application's backend/external services. *(See `tools.md` for detailed specifications)*.
4.  **Firestore Database:** The primary datastore for application state. Crucially holds:
    * `/cases/{caseId}`: Core case data, including the vital `case_details` object which serves as the agent's dynamic memory, and `case_processing_state` for recovery. *(See `data_models.md` for schema)*.
    * `/parties/{partyId}`: Secure storage for PII.
5.  **BigQuery Knowledge Base:** Contains structured Romanian legal texts (`relexro.romanian_legal_data.legislatie`, `relexro.romanian_legal_data.jurisprudenta`), queried via the `query_bigquery` tool.
6.  **Cloud Storage:** Stores user-uploaded documents (`relex-files` bucket, path `cases/{caseId}/attachments/`) and agent-generated PDF drafts (`relex-files` bucket, path `cases/{caseId}/drafts/`). This replaces the multiple buckets mentioned in `chat.md` (`relex-rag-processed`, `relex-chat-data`)[cite: 1].
7.  **Agent Interaction Handler (`agent_handler.py`):** The Cloud Function triggered by `POST /cases/{caseId}/agent/message`[cite: 1]. It authenticates requests, loads context, invokes the LangGraph agent, manages the execution loop (respecting timeouts), saves state, and returns the final response. Configured with an increased timeout (e.g., 300-600 seconds) for MVP[cite: 1].

## 3. Core Workflow (LangGraph State Machine)

The agent's operation is modeled as a state machine within LangGraph, progressing through distinct phases and steps.

```mermaid
graph TD
    A[Start: New User Message / Resume] --> B{Load Context / State};
    B --> C{Determine Phase};

    subgraph Phase 1: Tiering & Payment
        C -- Phase: Tiering --> D[Determine Tier];
        D -- Tier Result --> E{Invoke Tool: check_quota};
        E -- Quota Result --> F{Process Quota};
        F -- No Quota --> G[Inform User & Request Payment];
        F -- Quota OK --> H[Update Status & Transition to Active];
        G --> I[Wait for Payment Webhook / Pause];
    end

    subgraph Phase 2: Active Case Resolution
        C -- Phase: Active --> J[Process Input & Plan (Gemini)];
        J --> K{Select Action};
        K -- Action: Ask User --> L[Formulate Question (Gemini)];
        K -- Action: Research --> M[Generate BQ Query (Gemini)];
        M --> N{Invoke Tool: query_bigquery};
        K -- Action: Consult --> O[Synthesize & Ask Grok (Gemini)];
        O --> P{Invoke Grok API};
        K -- Action: Draft --> Q[Generate Markdown (Gemini)];
        Q --> R{Invoke Tool: generate_draft_pdf};
        K -- Action: Update --> S{Invoke Tool: update_case_details};
        K -- Action: Error --> T[Initiate Error Handling Flow];
        K -- Action: Wait --> U[Save State & Wait];

        L --> V[Send Response to User];
        N -- BQ Results --> W[Process Results (Gemini)];
        P -- Grok Guidance --> W;
        R -- PDF Path --> W;
        S --> W;  // After updating, decide next step
        T --> U; // After initiating error handling, wait or respond

        W --> J; // Loop back to plan next step based on new info/guidance
    end

     H --> J; // Transition from Phase 1 to Phase 2
     I --> V; // Wait for payment confirmation (external event)
     U --> A; // Loop back when new message arrives or resumed
     V --> A; // Loop back after sending message to user

    style H fill:#D5E8D4,stroke:#82B366

    Workflow Explanation:

Load Context/State (Node B): When the agent handler function is invoked, it first loads the current /cases/{caseId} document, specifically the case_details and case_processing_state, using the get_case_details tool internally or direct Firestore access. If resuming after a timeout, case_processing_state dictates the starting point.
Determine Phase (Node C): Checks the case status (e.g., tier_pending, payment_pending, active). Directs flow to Phase 1 or Phase 2.
Phase 1: Tiering & Payment (Nodes D-I, H):
(Node D) Gemini determines the tier using user input and definitions (tiers_ro.md), guided by prompts from prompts.md.
(Node E) The check_quota tool is called.
(Node F) Based on the tool result:
If no quota, (Node G) Gemini formulates a message asking the user to pay, the case status is updated to payment_pending, and the agent pauses (Node I). Payment completion (via Stripe webhook updating the case status) acts as the trigger to resume and transition.
If quota is OK, (Node H) the case status is updated to active, case_details is updated with the tier and initial info, and the flow transitions to Phase 2.
Phase 2: Active Case Resolution (Nodes J-W): This is the main operational loop.
(Node J) Gemini analyzes the current situation (new user input, case_details, results from previous step) and decides the next logical action, guided by its system prompt and potentially recent Grok guidance.
(Node K) Based on Gemini's decision, the flow branches:
Ask User (Node L): Gemini crafts a question, the response is sent to the user (Node V), and the agent waits (Node U -> A).
Research (Node M, N): Gemini formulates a BigQuery query, calls query_bigquery (Node N), processes results (Node W), updates case_details (via tool call within W or next step), and loops back to plan (Node J).
Consult Grok (Node O, P): Gemini prepares context, calls Grok API (Node P), receives guidance (Node W), updates case_details, and loops back (Node J).
Draft (Node Q, R): Gemini generates Markdown, calls generate_draft_pdf (Node R), processes success/failure (Node W), updates case_details, potentially notifies user (Node L -> V), and loops back (Node J).
Update Context (Node S): Explicit step if only an update is needed, calls update_case_details, processes result (Node W), loops back (Node J).
Error (Node T): If a tool fails irrecoverably according to the protocol (Retry -> Grok -> User -> Ticket), this node triggers the error handling logic (e.g., calling create_support_ticket), updates status, potentially notifies user, and enters wait state (Node U).
(Node W) This logical step processes the results from tool calls or LLM responses, critically involving Gemini calling update_case_details to persist new information before deciding the next step via Node J.
(Node U) Represents the agent entering a wait state, saving its progress via case_processing_state if nearing timeout.
4. State Management and Recovery
Given the potential length of agent operations and the stateless nature of Cloud Functions, robust state management is crucial.

Primary State: The case_details object within the /cases/{caseId} Firestore document serves as the agent's persistent memory. It is read at the beginning of an interaction and updated frequently via the update_case_details tool after significant actions or information processing.
Volatile State: LangGraph inherently manages the current step within the defined graph during a single function invocation.
Timeout Recovery: To handle function timeouts (MVP approach, max 5-10 mins):
The agent_handler.py function should monitor execution time.
If approaching the timeout limit during an agent step (e.g., waiting for LLM or tool), the agent should be interrupted.
A snapshot of the current state (e.g., the last successful node, pending action details) is saved to the case_processing_state field in Firestore.
The function returns an error or specific code indicating a timeout requiring user action.
The frontend displays a message and potentially a "Reload/Resume" button.
When the user reloads/resumes, the agent_handler.py reads case_processing_state and instructs LangGraph to restart the flow from the saved point.
5. Error Handling Protocol
Tool failures or unexpected LLM responses are handled systematically:

Automatic Retry (Gemini): For transient tool errors, Gemini attempts to retry the tool call (up to 2 times), potentially adjusting parameters based on the error message.
Consult Grok (Gemini): If retries fail, Gemini synthesizes the context and the error, then consults Grok for alternative strategies or advice.
Ask User (Gemini): If Grok advises or if the error clearly requires user input (e.g., ambiguous party name, missing document), Gemini formulates a clear, non-technical question for the user.
Create Support Ticket (Gemini -> Tool): If the issue remains unresolved after user interaction, or if it's a fundamental platform issue, Gemini generates a summary and calls the create_support_ticket tool. The case status is set to paused_support, and the user is notified.
6. Privacy and Security
PII Isolation: Sensitive party data (CNP, full address, etc.) is stored only in the /parties/{partyId} collection in Firestore. Access must be strictly controlled via Firestore Security Rules and IAM permissions.
LLM Data Handling: Gemini and Grok never receive raw PII. Gemini works with partyIds (e.g., party0) resolved via get_party_id_by_name.
Secure PDF Generation: The generate_draft_pdf tool is the designated component responsible for fetching PII from /parties (using the partyId provided in placeholders like {{party0.cnp}}) only for parties attached to the specific case_id and substituting it just before PDF generation. This tool requires elevated, carefully audited permissions.
Authentication & Authorization: All API endpoints, especially the agent interaction endpoint, enforce strict authentication and authorization checks to ensure users only access their own cases or cases within their authorized organization.
(Refer also to api.md security considerations).

This detailed architecture and workflow provide the foundation for a powerful, context-aware, and secure Lawyer AI Agent within the Relex platform.