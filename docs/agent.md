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