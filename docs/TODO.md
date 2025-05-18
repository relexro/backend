# Relex Backend - TODO List (Revised - Focus: API Stability & Testing)

**Overall Goal:** Ensure all API endpoints are fully functional, robustly tested (unit and integration), and any identified issues are systematically resolved via executor prompts. The immediate priority is to address why the API might not be working as expected, starting with authentication and core user/organization endpoints.

## Phase 1: Urgent - Establish Baseline API Functionality & Core Testing

### 1.2. Core Unit Testing Implementation
    * **Objective:** Establish foundational unit tests for critical business logic, ensuring functions behave as expected in isolation within the `tests/unit` directory.
    * **Sub-Tasks:**
        * 1.2.1. **Unit Tests for `functions/src/auth.py`:**
            * Focus: JWT validation (valid, invalid, expired tokens), user extraction from token. Mock Firebase Admin SDK.
            * **Executor Prompt:** "Create comprehensive unit tests for all functions in `functions/src/auth.py`. Ensure `_verify_firebase_jwt` (or equivalent) is tested with various token states. Mock external calls (e.g., `firebase_admin.auth.verify_id_token`). Store tests in `tests/unit/test_auth.py`. Report test execution results."
        * 1.2.2. **Unit Tests for `functions/src/user.py` (Core Functions):**
            * Focus: User profile creation (if applicable), retrieval, update logic. Mock Firestore calls.
            * **Executor Prompt:** "Create unit tests for `get_user_profile_logic` and `update_user_profile_logic` (or equivalent functions) in `functions/src/user.py`. Mock Firestore client interactions (`db.collection(...).document(...).get()`, etc.). Store tests in `tests/unit/test_user.py`. Report test execution results."
        * 1.2.3. **Run All New Unit Tests:**
            * **Executor Prompt:** "Execute all unit tests in the `tests/unit/` directory using `python -m pytest tests/unit/`. Report any failures with full tracebacks."

### 1.3. Basic Integration Tests for Core User & Organization Flows
    * **Objective:** Ensure the primary user and organization API endpoints work end-to-end against a deployed environment, using tests located in `tests/integration`.
    * **Context:** API Gateway URL: `https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev/v1/`
    * **Sub-Tasks:**
        * 1.3.1. **Integration Test: User Creation & Retrieval (if applicable, or focus on retrieval if creation is external):**
            * If user creation is via an endpoint: Test `POST /users` then `GET /users/me`.
            * If only retrieval: Confirm `GET /users/me` (already covered by 1.1.3 if successful).
            * **Executor Prompt (if creation endpoint exists):** "Develop an integration test for user creation (e.g., `POST /v1/users`) followed by retrieval (`GET /v1/users/me`). Use a valid test JWT. Assert 201/200 status codes and validate response data. Store in `tests/integration/test_user.py`. Report execution results."
        * 1.3.2. **Integration Test: Organization Creation & Retrieval:**
            * Test `POST /organizations` to create a new organization.
            * Test `GET /organizations/{orgId}` to retrieve the created organization.
            * Test `GET /organizations` (or `/users/me/organizations`) to list user's organizations.
            * **Executor Prompt:** "Develop integration tests for: 1. Creating an organization (`POST /v1/organizations`) with payload `{\"name\": \"Test Org Integration\"}`. 2. Retrieving the created org by its ID. 3. Listing organizations for the test user. Use a valid test JWT. Assert appropriate status codes and response data. Store in `tests/integration/test_organization.py`. Report execution results."
        * 1.3.3. **Run Core Integration Tests:**
            * **Executor Prompt:** "Execute integration tests: `test_user.py` and `test_organization.py` from `tests/integration/` against the deployed dev environment. Ensure `RELEX_API_BASE_URL` (e.g., `https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev/v1/`) and `RELEX_TEST_JWT` are set as environment variables for the test execution environment. Report failures with request/response details."

## Phase 2: Expanding Test Coverage & API Functionality

### 2.1. Comprehensive Unit Testing
    * **Objective:** Achieve >80% unit test coverage for all modules in `functions/src/`, with tests residing in `tests/unit/`.
    * **Sub-Tasks:** (For each `.py` file in `functions/src/` not yet covered)
        * 2.1.1. **Module: `[module_name.py]`**
            * **Executor Prompt:** "Analyze `functions/src/[module_name.py]`. Identify all functions and classes. Create comprehensive unit tests covering main logic paths, edge cases, and error handling. Mock all external dependencies (Firestore, other GCP services, external APIs). Store tests in `tests/unit/test_[module_name].py`. Report execution results and estimated coverage."
            * Modules to cover: `cases.py`, `payments.py`, `organization_membership.py`, `party.py`, `agent_orchestrator.py`, `agent_nodes.py`, `llm_integration.py`, etc.

### 2.2. Comprehensive Integration Testing
    * **Objective:** Ensure all API endpoints defined in `terraform/openapi_spec.yaml` are covered by integration tests located in `tests/integration/`.
    * **Sub-Tasks:** (For each endpoint/flow not yet covered)
        * 2.2.1. **Endpoint/Flow: `[HTTP Method] [path]` (e.g., `POST /cases/{caseId}/parties`)**
            * **Executor Prompt:** "Develop integration tests for the `[HTTP Method] [path]` endpoint. Cover successful scenarios, common error conditions (invalid input, unauthorized, not found), and data validation. Store tests in `tests/integration/test_[resource_name].py`. Report execution results."
            * Endpoints/Flows to cover: All CRUD operations for Cases, Parties, Organization Memberships, Payments (including webhook simulation if possible), Agent invocations.

### 2.3. Debugging and Fixing Issues from Expanded Testing
    * **Objective:** Systematically address any failures identified during comprehensive testing.
    * **Process:** For each failing test:
        * 1. **Isolate Failure:** Confirm if it's a test issue or an API issue.
        * 2. **Investigate API Issue (if applicable):** Use prompts similar to 1.1.1 (log analysis, code review).
            * **Executor Prompt (Investigation):** "The integration test `[test_function_name]` for `[HTTP Method] [path]` is failing with `[error/status]`. Analyze relevant Cloud Function logs for `[cloud_function_name]`, API Gateway logs, and review the handler code in `functions/src/[handler_file.py]`. Summarize findings and potential root cause."
        * 3. **Implement Fix:**
            * **Executor Prompt (Code Modification):** "Based on the investigation for the failing `[HTTP Method] [path]` test, modify `functions/src/[file_to_fix.py]`. Replace/update the code at `[specific function/line numbers]` with the following: `[complete new code snippet]`.
        * 4. **Re-test:**
            * **Executor Prompt:** "After applying the fix for `[HTTP Method] [path]`, re-run the specific failing test `[test_function_name]` and then the entire `tests/integration/test_[resource_name].py` suite. Report results."

## Phase 3: Refinement, Documentation & Ongoing Maintenance

### 3.1. API Documentation Accuracy
    * **Objective:** Ensure `terraform/openapi_spec.yaml` accurately reflects the working API.
    * **Sub-Tasks:**
        * 3.1.1. **Audit and Update OpenAPI Spec:**
            * **Executor Prompt:** "Compare the implemented API behavior (verified by integration tests) against `terraform/openapi_spec.yaml`. Identify and list all discrepancies in paths, methods, parameters, request/response schemas. For each discrepancy, provide the corrective YAML snippet for `openapi_spec.yaml`."

### 3.2. Developer Documentation Updates
    * **Objective:** Update all relevant markdown documents in `docs/` (e.g., `api.md`, `architecture.md`, `concepts/*`).
    * **Sub-Tasks:**
        * 3.2.1. **Sync Documentation with Code/API Reality:**
            * **Executor Prompt:** "Review `docs/api.md` and `docs/architecture.md`. Update these documents to reflect any changes or clarifications that arose from the intensive testing and debugging phases (e.g., corrected endpoint behavior, refined authentication flow). Provide the modified sections."

### 3.3. Monitoring & Alerting
    * **Objective:** Proactively identify API issues in production.
    * **Sub-Tasks:**
        * 3.3.1. **Review existing monitoring and logging (as per `docs/monitoring_and_logging.md`).**
        * 3.3.2. **Set up alerts for critical errors** (e.g., >X% 5xx errors on API Gateway, high Cloud Function error rates).
            * **Executor Prompt:** "Based on `docs/monitoring_and_logging.md` and the project's GCP setup, outline the steps or provide a gcloud command to create an alert policy in Google Cloud Monitoring that triggers if the API Gateway (identified by its name, e.g., `relex-api-gateway-dev` or similar, check `docs/terraform_outputs.log` if unsure) experiences a 5xx error rate above 1% over a 5-minute window."

---

**Notes for Lead Planner:**
* This TODO list is a living document. Update it as new issues are found or priorities shift.
* Break down tasks into the smallest actionable steps suitable for an Executor.
* Always reference the `docs/PLANNER_GUIDE.md` and `docs/guardrail.md` when creating prompts.
* Executor prompts should be generated one at a time as you progress through these tasks.
