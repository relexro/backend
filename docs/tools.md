# Function Tool Specifications

This document defines the specifications for the function tools used by the Lawyer AI Agent (orchestrated by LangGraph and primarily invoked by Gemini based on its reasoning or Grok's guidance). These tools interact with backend services, databases, and external APIs.

**Note:** All tool implementations must handle potential errors gracefully and return informative error messages to the agent. Input validation is crucial. The agent (Gemini) is responsible for formatting inputs correctly based on these specifications. All natural language strings within parameters or returned data should support UTF-8 (Romanian).

## 1. `query_bigquery`

* **Description:** Executes a SQL query against the specified Romanian legal BigQuery table (`legislatie` or `jurisprudenta`). Used for legal research. Supports two implicit modes based on query structure: returning summaries or full text.
* **Implementation:** Backend function authorized to access `relexro.romanian_legal_data`.
* **Parameters:**
    * `query_string`: (string, required) The SQL query designed by Gemini (based on Grok's guidance). This query might select specific fields for summaries or use `doc_id` for full text retrieval.
    * `table_name`: (string, required) The target table name. Must be either `"legislatie"` or `"jurisprudenta"`.
* **Returns:**
    * **On Success:** `{"status": "success", "results": [...]}` where `results` is a list of dictionaries, each representing a row returned by the query (e.g., `{"doc_id": "...", "summary": "..."}` or `{"doc_id": "...", "full_text": "..."}`).
    * **On Failure:** `{"status": "error", "error_message": "string"}` (e.g., "Invalid table name", "Query execution failed: [BQ Error]", "Unauthorized access").
* **Usage Notes:** Gemini first formulates queries to get summaries/titles/doc\_ids. After Grok reviews the summaries, Gemini formulates a new query using specific `doc_id`s to fetch the full text.

## 2. `get_party_id_by_name`

* **Description:** Looks up the internal `partyId` associated with a first name mentioned by the user within the context of the current case. This maps user references (e.g., "John Doe") to internal IDs (e.g., "party0", "party1") used in placeholders.
* **Implementation:** Backend function that queries the `case_details.parties_involved_context` within the current `/cases/{caseId}` document.
* **Parameters:**
    * `case_id`: (string, required) The ID of the current case.
    * `mentioned_name`: (string, required) The first name or alias the user used to refer to the party (e.g., "John", "Alice", "the company").
* **Returns:**
    * **On Success (Match Found):** `{"status": "success", "partyId": "string"}` (e.g., `"party0"`).
    * **On Success (No Match):** `{"status": "not_found", "message": "Party reference not found in case context."}`
    * **On Failure:** `{"status": "error", "error_message": "string"}` (e.g., "Case ID not found", "Error accessing case details").
* **Usage Notes:** Gemini calls this when it needs to insert a party placeholder into a draft based on user natural language references.

## 3. `generate_draft_pdf`

* **Description:** Takes Markdown content (with placeholders like `{{party0.firstName}}`), substitutes the placeholders with actual PII fetched securely from the `/parties/` collection, converts the result to PDF (UTF-8), and stores it in Cloud Storage under the specified case and revision. Updates the draft status in `case_details`.
* **Implementation:** Secure backend function. **Crucially, this function is the ONLY component besides the Party Management UI that accesses raw PII from the `/parties` collection.** It uses a secure method to fetch data based on `partyId`s present as placeholders in the markdown *after* confirming they are attached to the `case_id`. Uses a Markdown-to-PDF library (e.g., `WeasyPrint`, `markdown-pdf`) ensuring UTF-8 support.
* **Parameters:**
    * `case_id`: (string, required) The ID of the current case.
    * `markdown_content`: (string, required) The draft content in Markdown format, containing placeholders like `{{party0.lastName}}`, `{{party1.cui}}`.
    * `draft_name`: (string, required) The base name for the document (e.g., "Cerere_chemare_judecata").
    * `revision`: (integer, required) The revision number for this version of the draft.
* **Returns:**
    * **On Success:** `{"status": "success", "pdf_gcs_path": "string", "draft_firestore_id": "string"}` (The path where the PDF was saved in GCS and the ID of the corresponding entry in `case_details.draft_status`).
    * **On Failure:** `{"status": "error", "error_message": "string"}` (e.g., "Placeholder substitution failed: Party ID {partyId} not found or not attached to case", "PDF conversion failed", "Cloud Storage upload failed", "Firestore update failed").
* **Usage Notes:** Called by Gemini (via LangGraph) after Grok approves a draft plan and Gemini generates the Markdown.

## 4. `check_quota`

* **Description:** Checks if the user or their organization has available quota for the specified case tier based on their active subscription.
* **Implementation:** Backend function that reads user/organization subscription data from Firestore.
* **Parameters:**
    * `user_id`: (string, required) The ID of the user initiating the check.
    * `organization_id`: (string | null) The ID of the organization, if the case is under an organization.
    * `tier`: (integer, required) The case tier (1, 2, or 3) determined by the agent.
* **Returns:**
    * **On Success:** `{"status": "success", "has_quota": "boolean"}`.
    * **On Failure:** `{"status": "error", "error_message": "string"}` (e.g., "User not found", "Subscription not found", "Invalid tier").
* **Usage Notes:** Called by the agent immediately after determining the case tier in Phase 1.

## 5. `get_case_details`

* **Description:** Retrieves the entire `case_details` object from the specified case document in Firestore.
* **Implementation:** Backend function performing a Firestore read.
* **Parameters:**
    * `case_id`: (string, required) The ID of the case to retrieve details for.
* **Returns:**
    * **On Success:** `{"status": "success", "case_details": {...}}` (The full `case_details` object as defined in `data_models.md`).
    * **On Failure:** `{"status": "error", "error_message": "string"}` (e.g., "Case ID not found").
* **Usage Notes:** Called frequently by Gemini at the start of processing loops or when needing the full current context.

## 6. `update_case_details`

* **Description:** Updates specific fields within the `case_details` object in the specified case document in Firestore. Uses dot notation for targeted updates if possible, otherwise replaces specified sub-objects. Also updates the main `case.updatedAt` timestamp and potentially the `case_details.last_updated` timestamp.
* **Implementation:** Backend function performing a Firestore write/update. Needs robust handling of concurrent updates if necessary (though agent interactions are likely sequential per case).
* **Parameters:**
    * `case_id`: (string, required) The ID of the case to update.
    * `updates`: (dict, required) A dictionary containing the fields and values to update within `case_details`. Example: `{"summary.current": "New summary text", "facts": [{"timestamp": ..., "fact": ...}]}` (would append to facts array), or `{"legal_research.legislation": [...]}` (would replace the legislation list).
* **Returns:**
    * **On Success:** `{"status": "success"}`.
    * **On Failure:** `{"status": "error", "error_message": "string"}` (e.g., "Case ID not found", "Update failed due to invalid field", "Firestore write error").
* **Usage Notes:** Called frequently by Gemini after processing new information, analyzing documents, receiving LLM guidance, or completing actions, to persist changes to the case context.

## 7. `create_support_ticket`

* **Description:** Creates a support ticket in an external system (e.g., Zendesk, Jira, or even a simple Firestore collection `/support_tickets`) when the agent encounters an unrecoverable error. Also updates the case status to `paused_support`.
* **Implementation:** Backend function integrating with the support system API or writing to a dedicated Firestore collection.
* **Parameters:**
    * `case_id`: (string, required) The ID of the case experiencing the issue.
    * `issue_description`: (string, required) A detailed description of the problem encountered by the agent (generated by Gemini).
    * `agent_state_snapshot`: (dict, optional) A snapshot of relevant parts of `case_details` or `case_processing_state` at the time of failure.
* **Returns:**
    * **On Success:** `{"status": "success", "ticket_id": "string"}` (The ID of the created support ticket).
    * **On Failure:** `{"status": "error", "error_message": "string"}` (e.g., "Failed to connect to support system", "Error creating ticket").
* **Usage Notes:** Called by Gemini as the last resort in the error handling flow.

## (Potential) `consult_grok`

* **Description:** Wraps the direct API call to Grok. Might be useful for standardizing input/output, adding specific preprocessing or error handling around the Grok call. If direct API calls from LangGraph are robust, this tool might be optional.
* **Implementation:** Backend function making the API call to Grok, potentially managing session context if needed beyond what LangGraph handles.
* **Parameters:**
    * `case_id`: (string, required) For context/session lookup.
    * `context_summary`: (string, required) Synthesized context prepared by Gemini.
    * `specific_question`: (string, required) The specific guidance requested from Grok by Gemini.
* **Returns:**
    * **On Success:** `{"status": "success", "response": "string"}` (Grok's natural language response).
    * **On Failure:** `{"status": "error", "error_message": "string"}` (e.g., "Grok API error", "Timeout").
* **Usage Notes:** Used whenever Gemini needs guidance from the expert reasoner (Grok).

---

**`prompts.md`**

```markdown
# Prompt Strategy and Placeholders

This document outlines the core strategies and provides placeholders for the prompts used by the Lawyer AI Agent, particularly for guiding Gemini and facilitating its interaction with Grok and the function tools.

**Core Principles:**

1.  **Language:** All prompts directed to LLMs (Gemini, Grok) and user-facing messages generated by the agent **must be in Romanian**. (English used here for specification clarity).
2.  **Roles:** Prompts must strictly enforce the roles:
    * **Gemini:** The diligent, user-facing **Assistant**. Gathers information, summarizes, uses tools based on instructions, asks Grok for guidance, writes drafts based on Grok's plan. Polite but concise with the user.
    * **Grok:** The expert **Lawyer/Reasoner**. Provides legal strategy, identifies information gaps, requests specific actions from Gemini, validates findings, outlines draft structure/content. Uses formal, expert language.
3.  **Efficiency:** Prompts should guide LLMs to be concise and avoid unnecessary conversational filler or overly verbose explanations, especially in internal steps, to minimize token usage and latency. Instructions should be direct.
4.  **Tool Usage:** Prompts must clearly instruct Gemini *when* and *how* to use specific function tools, including formatting parameters correctly based on `tools.md`.
5.  **Context Management:** Gemini must be prompted to utilize `get_case_details` to fetch the latest context and `update_case_details` to persist new findings, ensuring the `case_details` object remains the central source of truth. Session IDs (`gemini_session_id`, `grok_session_id`) should be managed appropriately.
6.  **Error Handling:** Prompts must include instructions for Gemini on how to handle tool errors according to the defined escalation path (retry -> consult Grok -> ask user -> create ticket).
7.  **Focus:** During specific phases (like tier determination), prompts must instruct Gemini to stay focused on the current objective and reject irrelevant user digressions.

## Key Prompt Placeholders (Conceptual - To be developed in Romanian)

### 1. Gemini System Prompt

* **Purpose:** Define Gemini's overall role, capabilities, limitations, and interaction style.
* **Content Outline:**
    * "You are an AI Legal Assistant for the Relex platform. Your primary language is Romanian."
    * "Your role is to assist users with their legal cases by gathering information, interacting with them politely and efficiently, and utilizing available tools."
    * "You work under the guidance of an expert legal reasoning model, Grok. You must consult Grok for strategic decisions, legal analysis confirmation, and planning."
    * "Your tasks include: understanding user requests, determining case tier, managing case details via tools (`get_case_details`, `update_case_details`), parsing documents, querying legal databases via `query_bigquery`, identifying parties via `get_party_id_by_name`, generating draft documents in Markdown (with placeholders) based on Grok's instructions using `generate_draft_pdf`, and handling payments/quotas via `check_quota`."
    * "Maintain the `case_details` object accurately using the provided tools."
    * "When interacting with the user, be clear, concise, and helpful. Ask clarifying questions when needed."
    * "When consulting Grok, provide a concise summary of the current context from `case_details` and ask specific questions for guidance."
    * "Follow the error handling protocol: Retry tool -> Consult Grok -> Ask User -> Create Support Ticket (`create_support_ticket`)."
    * "Strictly adhere to privacy guidelines: Never request or handle raw PII. Use placeholders for party data in drafts."
    * "Manage interactions within the allowed time limits, saving state if necessary before timeout."
    * "Use Romanian for all user interactions and consultations with Grok."

### 2. Initial Greeting & Tiering Prompt (User Facing)

* **Purpose:** First message from Gemini upon case creation.
* **Content:** *"Bun venit la Relex! Pentru a vă putea ajuta cât mai bine, trebuie să înțeleg mai întâi tipul problemei juridice și complexitatea acesteia (nivelul de caz). Vă rog să descrieți pe scurt situația dvs."* (Welcome to Relex! To best assist you, I first need to understand the type and complexity (case tier) of your legal matter. Please briefly describe your situation.)

### 3. Tier Determination Prompt (Internal for Gemini)

* **Purpose:** Guide Gemini to analyze the user's initial description and classify the case tier.
* **Input Context:** User's first message, Tier Definitions (`tiers_ro.md` content).
* **Content Outline:**
    * "Analyze the user's description of their legal situation provided below."
    * "[Insert User's Initial Message Here]"
    * "Based on the user's description and the following Case Tier definitions, determine the most appropriate tier (1, 2, or 3)."
    * "[Insert Content of `tiers_ro.md` Here]"
    * "Consider the keywords, case type examples, and complexity described for each tier."
    * "Respond *only* with the determined tier number (1, 2, or 3) and a brief justification based *strictly* on the definitions and the user's input. Do not engage in further conversation yet."
    * "If the description is too vague to determine the tier, ask the user one specific clarifying question strictly focused on tier determination (e.g., 'Does this involve a court case already?', 'What is the approximate value involved?')."

### 4. Quota Check / Payment Prompt (User Facing)

* **Purpose:** Inform user about quota status and prompt for payment if needed.
* **Input Context:** Result from `check_quota` tool.
* **Content Outline (Quota OK):** *"Am verificat abonamentul dvs. și aveți credit disponibil pentru acest tip de caz (Nivel {tier}). Putem continua. Vă rog să îmi oferiți mai multe detalii despre caz."* (I have checked your subscription and you have available credit for this case type (Tier {tier}). We can proceed. Please provide me with more details about the case.)
* **Content Outline (No Quota):** *"Am determinat că acest caz se încadrează la Nivelul {tier} de complexitate. Abonamentul dvs. curent nu mai are credit disponibil pentru acest nivel. Pentru a continua, este necesară achiziționarea accesului pentru acest caz specific. Vă rugăm să utilizați butonul 'Plătește Cazul' pentru a finaliza plata. Interfața va fi limitată până la confirmarea plății."* (I have determined this case falls under Tier {tier} complexity. Your current subscription does not have available credit for this tier. To proceed, purchasing access for this specific case is required. Please use the 'Pay for Case' button to complete the payment. The interface will be limited until payment is confirmed.)

### 5. Context Synthesis & Grok Consultation Prompt (Internal for Gemini)

* **Purpose:** Instruct Gemini to prepare context and ask Grok for guidance.
* **Input Context:** Current `case_details`, latest user messages/document analysis.
* **Content Outline:**
    * "The current case state requires guidance from the expert legal reasoner, Grok."
    * "First, retrieve the latest full context using `get_case_details`."
    * "Based on the retrieved `case_details` (summary, facts, objectives, documents, previous interactions, etc.) and any very recent user messages, synthesize a concise update for Grok."
    * "Formulate a specific question for Grok based on the current situation. Examples:"
        * "What specific information is still missing to form a strategy?"
        * "Based on these facts, what legal avenues should we explore first?"
        * "Please review the summaries from `query_bigquery` results in `case_details.legal_research` and advise which full texts are most relevant to fetch."
        * "Do we have enough information to start planning a draft document for {objective}?"
        * "How should I respond to the user's latest query about {topic}?"
    * "Call Grok directly with the synthesized context and your specific question. Ensure the communication is in Romanian."
    * "After receiving Grok's response, update `case_details` using `update_case_details` with Grok's guidance (e.g., in `internal_notes` or `agent_interactions.log`) and proceed with the instructed action (e.g., ask user, call tool, generate draft)."

### 6. BigQuery Query Generation Prompt (Internal for Gemini)

* **Purpose:** Instruct Gemini to formulate a BigQuery SQL query based on Grok's request.
* **Input Context:** Grok's instruction (e.g., "Find case law related to...") and current `case_details`.
* **Content Outline:**
    * "Grok has requested legal research on '{Grok's Topic}'."
    * "Formulate an efficient SQL query for the BigQuery `query_bigquery` tool to find relevant entries in the `{table_name}` table (`legislatie` or `jurisprudenta`)."
    * "Initially, focus the query on retrieving summaries, titles, and `doc_id`s, not the full text. Use relevant keywords derived from Grok's topic and the `case_details`."
    * "Keywords to consider: [{Keywords from Grok/case_details}]."
    * "Example Query Structure (adjust fields as needed): `SELECT doc_id, title, summary FROM \`relexro.romanian_legal_data.{table_name}\` WHERE LOWER(full_text) LIKE '%keyword1%' AND LOWER(full_text) LIKE '%keyword2%' LIMIT 10`"
    * "Call the `query_bigquery` tool with the generated query string and table name."
    * "After execution, update `case_details.legal_research` with the results using `update_case_details`."
    * "Then, synthesize these results and consult Grok again to determine which specific `doc_id`s require full-text retrieval."

### 7. Draft Generation Prompt (Internal for Gemini)

* **Purpose:** Instruct Gemini to write a draft in Markdown based on Grok's plan.
* **Input Context:** Grok's instructions/plan, current `case_details`.
* **Content Outline:**
    * "Grok has provided instructions to draft the document: '{Draft Name}'."
    * "Grok's key points/structure: [{Grok's detailed guidance}]"
    * "Retrieve the latest context using `get_case_details`."
    * "Write the full draft document in Markdown format (Romanian, UTF-8)."
    * "Incorporate relevant facts, objectives, and legal findings from `case_details` as guided by Grok."
    * **"Crucially:** Where personal data of parties is required (names, addresses, CNP, CUI, etc.), use **only** placeholders based on `partyId` resolved via `get_party_id_by_name`. Format: `{{partyId.fieldName}}` (e.g., `{{party0.lastName}}`, `{{party1.cui}}`). Do NOT include actual PII."
    * "Ensure the tone and formatting are appropriate for an official legal document (simple, clear, formal)."
    * "Once the Markdown is complete, prepare the parameters for the `generate_draft_pdf` tool: `case_id`, the full `markdown_content`, `draft_name`, and the correct `revision` number (incrementing from previous versions if any, found in `case_details.draft_status`)."
    * "Call the `generate_draft_pdf` tool."
    * "After successful execution, update `case_details` with the PDF path and metadata using `update_case_details`."
    * "Finally, notify the user that the draft is ready."

### 8. Error Handling Prompts (Internal for Gemini)

* **Purpose:** Guide Gemini through the error recovery flow.
* **Input Context:** Tool error message, current context.
* **Content Outline (Retry):** "The tool call `{tool_name}` failed with error: '{error_message}'. Analyze the error and the parameters used. Attempt to call the tool again up to 2 times, potentially correcting parameters if the error suggests an input issue. Log the attempt in `case_details`."
* **Content Outline (Consult Grok):** "Retrying tool `{tool_name}` failed after 2 attempts. Synthesize the situation (original goal, tool called, parameters, error messages) and consult Grok for advice on how to proceed or alternative approaches. Log the consultation."
* **Content Outline (Ask User):** "Grok's suggested alternative for the failed tool `{tool_name}` also failed / Grok advised asking the user. Formulate a clear question for the user explaining the obstacle (without technical jargon) and requesting specific information or action needed to proceed (e.g., 'I'm having trouble locating the document you mentioned. Could you please re-upload it or confirm the filename?', 'To proceed, I need to correctly identify 'John Doe'. Is he listed in the attached parties?')."
* **Content Outline (Create Ticket):** "User clarification did not resolve the issue with `{tool_name}` / The issue is deemed unrecoverable by the agent. Generate a concise summary of the problem, the steps taken, and why the agent cannot proceed. Call the `create_support_ticket` tool with this description and the `case_id`. Notify the user that a support ticket has been created and the case is paused until the issue is resolved by the support team."

---

**`agent.md`**

```markdown
# Lawyer AI Agent

This document describes the Lawyer AI Agent, its architecture within the Relex platform, its core workflow, components, and operational principles.

## 1. Overview and Purpose

The Lawyer AI Agent is a sophisticated AI system designed to assist users with Romanian legal cases directly within the Relex platform. It replaces the previous basic chat functionality with an interactive, multi-step process involving advanced AI models and specialized tools.

**Key Goals:**

* Guide users through case initiation, including complexity tier determination and payment processing.
* Gather comprehensive case details through conversation and document analysis.
* Perform legal research using a dedicated BigQuery database of Romanian legislation and case law.
* Provide strategic guidance based on expert legal reasoning.
* Generate draft legal documents (e.g., applications, motions) ready for user review and submission.
* Maintain privacy and security, especially regarding Personal Identifiable Information (PII).

## 2. Architecture & Components

The agent operates as part of the backend system, orchestrated by **LangGraph** and leveraging several key components:

* **Orchestrator:** LangGraph manages the agent's state machine, executing nodes representing different steps in the workflow and handling transitions based on results.
* **LLMs:**
    * **Gemini Flash 2.5 (Assistant):** User-facing communication, data gathering, initial analysis, tool invocation formatting, draft writing (following Grok's plan), tier determination. Uses Romanian.
    * **Grok 3 Mini (Reasoner):** Expert legal analysis, strategic guidance, information gap identification, validation of legal research, planning draft structure/content. Uses Romanian.
* **Function Tools:** Python functions providing specific capabilities (See `tools.md` for details):
    * BigQuery Access (`query_bigquery`)
    * Quota/Payment Check (`check_quota`)
    * Case Context Management (`get_case_details`, `update_case_details`)
    * Party ID Lookup (`get_party_id_by_name`)
    * Secure PDF Draft Generation (`generate_draft_pdf`)
    * Support Ticket Creation (`create_support_ticket`)
* **State Management:** Primarily via the `/cases/{caseId}` document in Firestore, especially the `case_details` object and `case_processing_state` for timeout recovery.
* **Knowledge Base:** BigQuery tables (`legislatie`, `jurisprudenta`).
* **Interaction Channel:** Via specific backend Cloud Function(s) handling `/cases/{caseId}/agent/message` endpoints (RESTful, long timeout for MVP).

*(Refer to `architecture.md` for a visual diagram and `data_models.md` for Firestore structures.)*

## 3. Core Workflow (LangGraph States)

The agent operates in distinct phases managed by the LangGraph state machine:

```mermaid
graph TD
    A[Start Case/New Message] --> B{Load Context / State};
    B --> C{Check Phase};

    subgraph Phase 1: Tiering & Payment
        C -- Needs Tier --> D[Determine Tier (Gemini)];
        D -- Tier --> E[Check Quota (Tool)];
        E -- No Quota --> F[Request Payment (User Interaction)];
        F -- Payment OK --> G[Transition to Active];
        E -- Quota OK --> G;
    end

    subgraph Phase 2: Active Case Resolution
        C -- Active --> H[Process User Input / Plan Next Step (Gemini)];
        H --> I{Decide Action};
        I -- Need Info from User --> J[Ask User (Gemini)];
        I -- Need Legal Research --> K[Query BigQuery (Tool via Gemini)];
        I -- Need Guidance --> L[Consult Grok (LLM Call via Gemini)];
        I -- Need Draft --> M[Generate Draft (Tool via Gemini)];
        I -- Tool Error --> N[Handle Error Flow];
        I -- Task Complete / Waiting --> P[Wait for User / Timeout];

        J --> O{Update Context};
        K --> O;
        L --> O;
        M --> O;
        N --> P;
        O --> H;  // Loop back to process next step based on updated context

    end

     G --> H; // Transition from Phase 1 to Phase 2
     P --> A; // Wait state loops back on new message/event

    style G fill:#D5E8D4,stroke:#82B366