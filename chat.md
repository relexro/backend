# Chat Feature Implementation Guide (Main RAG Architecture)

## 1. Overview

This document outlines the implementation plan for the case-specific chat feature in the Relex backend. This feature allows users to interact with an AI assistant within the context of a legal case. The architecture utilizes a main Retrieval-Augmented Generation (RAG) system for legal knowledge (legislation/jurisprudence) and injects case-specific context (chat history, processed documents) directly into prompts for an external Large Language Model (LLM).

**Key principles:**

* **Main RAG:** A central Vertex AI Search index containing Romanian legislation and jurisprudence.
* **No Case RAG:** Case-specific documents (OCR'd text) and chat history are *not* indexed in separate RAGs.
* **Direct Context Injection:** Recent chat history and relevant processed document text are fetched directly from Cloud Storage and included in the LLM prompt when needed.
* **Dynamic Agent Behavior:** The agent's goal and instructions are fetched from Firestore based on the `caseTypeId`, tailoring its responses.
* **Single Chat Endpoint:** `POST /v1/cases/{caseId}/messages` handles receiving user messages, orchestrating context retrieval, RAG queries, LLM calls, and response storage.
* **Request/Response Model:** Interaction relies on standard HTTPS request/response. Function timeouts are increased to handle potentially long processing times.

## 2. Architecture

![Chat Architecture Diagram (Conceptual - Needs to be created)](placeholder_diagram.png)
*(Diagram should show: Frontend -> API Gateway -> POST /messages Function -> Auth Check -> GCS (Store User Msg) -> Firestore (Get CaseTypeConfig) -> GCS (Get History/Docs) -> Vertex AI Search (Main RAG Query) -> Prompt Construction -> External LLM API -> GCS (Store LLM Msg) -> Return Response)*

**Components:**

1.  **Firestore:**
    * `cases/{caseId}`: Stores case metadata, including the crucial `caseTypeId`.
    * `caseTypeConfigs/{caseTypeId}`: Stores dynamic agent goals and instructions per case type.
    * `documents/{documentId}`: Stores metadata about uploaded files, including OCR processing status (`processingStatus`, `processedStoragePath`).
2.  **Cloud Storage:**
    * `relex-files`: Stores original uploaded documents (`cases/{caseId}/documents/...`).
    * `relex-rag-processed`: Stores OCR output (`cases/{caseId}/processed/{documentId}.txt` or `.json`).
    * `relex-chat-data`: Stores chat history (`cases/{caseId}/chat_history.jsonl`).
    * `relex-rag-staging`: Stores pre-processed, merged JSONL files for Main RAG (`main/...`).
3.  **Cloud Vision API:** Used by the OCR function for `Document Text Detection`.
4.  **Vertex AI Search:**
    * Hosts the Main RAG DataStore (`relex-main-rag-datastore`) in `europe-west3`, indexed with pre-processed legislation/jurisprudence JSONL data.
    * Uses an embedding model (e.g., `textembedding-gecko@latest`).
    * Queried by the Chat Agent function.
5.  **Cloud Functions (Python):**
    * `relex-backend-process-document`: Triggered by uploads to `relex-files`; performs OCR, saves processed text to `relex-rag-processed`, updates Firestore.
    * `relex-backend-get-chat-history`: Handles `GET /v1/cases/{caseId}/messages`; reads and returns chat history from `relex-chat-data`.
    * `relex-backend-send-chat-message`: Handles `POST /v1/cases/{caseId}/messages`; orchestrates the main chat logic (auth, context fetching, RAG query, LLM call, storage). Configured with increased timeout (e.g., 300s).
6.  **External LLM API:** The designated external LLM endpoint (e.g., Claude), called by the chat agent function. API Key managed via Secret Manager.
7.  **API Gateway:** Exposes the `/v1/cases/{caseId}/messages` (POST and GET) endpoints.
8.  **Terraform:** Manages deployment of Functions, API Gateway config, Vertex AI Search resources (DataStore, App/Engine), IAM permissions, and GCS buckets.

## 3. Data Flow (User Sends Message)

1.  Frontend sends `POST /v1/cases/{caseId}/messages` with `{ "content": "..." }`.
2.  `relex-backend-send-chat-message` function triggers.
3.  **Auth:** User authenticated & authorized for the case.
4.  **Store User Msg:** Message appended to `gs://relex-chat-data/cases/{caseId}/chat_history.jsonl`.
5.  **Fetch Case Type Config:** Read `caseTypeId` from `cases/{caseId}`, fetch config from `caseTypeConfigs/{caseTypeId}`.
6.  **Fetch Case Context:** Read recent history from `chat_history.jsonl`. Conditionally read relevant processed docs from `relex-rag-processed`.
7.  **Query Main RAG:** Query Vertex AI Search DataStore (`relex-main-rag-datastore` in `europe-west3`) using user message content (potentially filtered using hints from case type config).
8.  **Construct Prompt:** Combine dynamic goal/instructions, case context (history/docs), Main RAG results, and user query.
9.  **Call External LLM:** Send constructed prompt; get response.
10. **Store LLM Msg:** Append LLM response to `chat_history.jsonl`.
11. **Return Response:** Send LLM response back to frontend via HTTP response.

## 4. Main RAG Data Preparation

* **Requirement:** The ~550k source TXT files **must** be pre-processed due to Vertex AI Search ingestion limits (max ~5000 files per batch directory).
* **Process:**
    * Run the dedicated Python script (`scripts/preprocess_main_rag.py` - to be created).
    * Input: Source GCS folders (`legislatie`, `jurisprudenta`).
    * Output: Merged, structured JSONL files (fewer than 5000 files total if possible, each < 1GB) uploaded directly to `gs://relex-rag-staging/main/`.
    * JSONL Schema: `{ "id": "...", "content": "...", "metadata": { "source_type": "...", ... } }`. Define useful metadata fields.
* **Ingestion:** After Terraform creates the DataStore, manually trigger the batch import via Console/gcloud pointing to `gs://relex-rag-staging/main/`.

## 5. Terraform Configuration

* Define `google_discovery_engine_data_store` and `google_discovery_engine_search_engine` (or App equivalent) resources in `europe-west3`.
* Configure the `relex-backend-send-chat-message` function resource with `timeout_seconds = 300` (or higher).
* Grant necessary IAM permissions to function service accounts (Storage R/W, Firestore R/W, Vertex AI Search User, Vision User, Secret Manager Accessor).

## 6. API Changes

* Ensure `openapi_spec.yaml` reflects the primary endpoints:
    * `POST /v1/cases/{caseId}/messages` -> `relex-backend-send-chat-message`
    * `GET /v1/cases/{caseId}/messages` -> `relex-backend-get-chat-history`
* Remove defunct endpoints (`/enrich-prompt`, `/send-to-vertex`).
* Update `api.md` and other relevant documentation.

## 7. Potential Issues & Mitigations

* **RAG Ingestion:** Pre-processing script is critical. Monitor batch import jobs carefully.
* **Timeouts:** Start with increased function timeout (300s). If issues persist, consider refactoring to an asynchronous Pub/Sub pattern.
* **OCR Quality:** Use Vision `Document Text Detection`. Accept potential inaccuracies in RAG results based on source quality.
* **Prompt Engineering:** Iteratively refine the prompt structure for the external LLM to correctly use dynamic goals and combine diverse context sources.
* **Cost:** Monitor Vertex AI Search, Vision, and external LLM costs. Implement cleanup for archived/deleted case data if needed.
* **Security:** Implement Firestore/Storage security rules. Ensure strict authorization checks in all functions. Vet external LLM privacy policy.