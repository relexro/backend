# Relex Backend - TODO List (Revised - Focus: API Stability & Testing)

**Overall Goal:** Ensure all API endpoints are fully functional, robustly tested (unit and integration), and any identified issues are systematically resolved via executor prompts. The immediate priority is to address why the API might not be working as expected, starting with authentication and core user/organization endpoints.

## Phase 1: Urgent - Establish Baseline API Functionality & Core Testing

### 1.0. Implement Agent Language Configuration
    * **Objective:** Configure the legal agent's language capabilities as per requirements, ensuring users can interact in multiple languages while internal operations and UI maintain specified language standards.
    * **Sub-Tasks:**
        * 1.0.1. **Document Supported User Languages & Configure Agent Constants:**
            * Action: Document the 30 user-facing languages in `docs/product_overview.md`. Create Python constants for supported user languages, UI languages, and the internal operational language in `functions/src/agent_config.py`.
            * **Status:** DONE.
        * 1.0.2. **Ensure Internal Operations & Prompts are Exclusively in Romanian:**
            * Action: Ensure all system prompts, predefined responses, and LLM-to-LLM communications use only Romanian. Inspect `functions/src/response_templates.py` and `functions/src/draft_templates.py` for hardcoded strings.
            * **Status:** DONE.
            * **Sub-bullets:**
                * [DONE] Core agent prompts in `functions/src/agent-config/` (`agent_loop.txt`, `modules.txt`) updated by Operator to new strategy; Romanian language confirmed. Obsolete `prompt.txt` in `functions/src/agent-config/` confirmed deleted. (Iterative refinement of `agent_loop.txt` content deferred by Operator).
                * [DONE] Review `functions/src/response_templates.py` for hardcoded strings and ensure Romanian language or prepare for i18n. (No code changes needed per language policy)
                * [DONE] Review `functions/src/draft_templates.py` for hardcoded strings and ensure Romanian language or prepare for i18n. (No code changes needed per language policy)
        * 1.0.3. **Implement UI Language Preference (EN/RO) in User Profile:**
            * Action: Modify user profile model (`functions/src/user.py` and Firestore structure) and API endpoints to store and manage a `languagePreference` field ('en' or 'ro'). Implement logic in `functions/src/auth.py` or `functions/src/user.py` to auto-set this preference from Google OAuth `locale` data on initial user creation. Ensure `GET /v1/users/me` returns this preference. Add relevant unit tests in `tests/unit/test_user.py`.
            * **Status:** DONE.
        * 1.0.4. **(Future Task) Translation Layer for User Input/Output:**
            * Action: Plan for integrating a translation service.
            * **Status:** Deferred.
        * 1.0.5. **(Future Task) UI Elements Translation:**
            * Action: Note requirement for UI text element translation (frontend).
            * **Status:** Deferred.

### 1.2. Core Unit Testing Implementation
    * **Objective:** Establish foundational unit tests for critical business logic, ensuring functions behave as expected in isolation within the `tests/unit` directory.
    * **Sub-Tasks:**
        * 1.2.1. **Unit Tests for `functions/src/auth.py`:**
            * Focus: JWT validation (valid, invalid, expired tokens), user extraction from token, core permission logic, HTTP endpoints. Mock Firebase Admin SDK and other external calls.
            * **Status:** Substantially Complete (67% coverage achieved).
            * **Sub-bullets:**
                * [DONE] Unit tests for `validate_firebase_id_token` and `validate_gateway_sa_token` covering various token states.
                * [DONE] Unit tests for `get_authenticated_user` covering different auth paths and locale extraction.
                * [DONE] Unit tests for `PermissionCheckRequest` model validation.
                * [DONE] Unit tests for `requires_auth` decorator (basic coverage).
                * [DONE] Unit tests for core permission checking logic helpers (`_check_organization_permissions`, `_check_case_permissions`, `_check_party_permissions`, `_check_document_permissions`), including cross-organization security scenarios.
                * [DONE] Unit tests for `add_cors_headers` decorator.
                * [DEFERRED] Comprehensive unit tests for HTTP endpoint functions in `auth.py` (`validate_user`, `get_user_profile`, `check_permissions` (HTTP wrapper), `get_user_role` logic function using `jsonify`). These unit tests were problematic due to Flask app context requirements and are deferred in favor of integration tests (Phase 1.3) as per Operator directive. (Relevant unit test classes in `tests/unit/test_auth.py` have been commented out).
            * **Original Executor Prompt (Reference for initial scope):** "Create comprehensive unit tests for all functions in `functions/src/auth.py`. Ensure `_verify_firebase_jwt` (or equivalent) is tested with various token states. Mock external calls (e.g., `firebase_admin.auth.verify_id_token`). Store tests in `tests/unit/test_auth.py`. Report test execution results."
        * 1.2.2. **Unit Tests for `functions/src/user.py` (Core Functions):**
            * Focus: User profile creation (if applicable), retrieval, update logic. Mock Firestore calls.
            * **Executor Prompt:** "Create unit tests for `get_user_profile_logic` and `update_user_profile_logic` (or equivalent functions) in `functions/src/user.py`. Mock Firestore client interactions (`db.collection(...).document(...).get()`, etc.). Store tests in `tests/unit/test_user.py`. Report test execution results."
        * 1.2.3. **Unit Tests for Auth Permission Helpers:**
            * **Status:** In Progress (Partially implemented in Task 1.2.1)
            * **Sub-bullets:**
                * [PARTIAL] Create dedicated unit tests for `_check_organization_permissions` and `_check_case_permissions` (for org cases) in `functions/src/auth.py`, mocking Firestore calls to isolate permission logic.
                * [PARTIAL] Test all permission scenarios for organization admins, staff, and non-members.
                * [ ] Test cross-organization security (users from one org cannot affect another org's resources).
                * [ ] Add tests for `_check_party_permissions` and `_check_document_permissions` helpers.
                * [ ] Enhance existing tests with more complex scenarios (e.g., multiple calls with different arguments).
        * 1.2.4. **Run All New Unit Tests:**
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
            * **Executor Prompt:** "Execute integration tests: `test_user.py` and `test_organization.py` from `tests/integration/` against the deployed dev environment. Ensure `RELEX_API_BASE_URL` (e.g., `https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev/v1/`) and the appropriate authentication tokens (`RELEX_TEST_JWT`, `RELEX_ORG_ADMIN_TEST_JWT`, and `RELEX_ORG_USER_TEST_JWT`) are set as environment variables for the test execution environment. Report failures with request/response details."

## Phase 2: Expanding Test Coverage & API Functionality

### 2.1. Comprehensive Unit Testing
    * **Objective:** Achieve >80% unit test coverage for all modules in `functions/src/`, with tests residing in `tests/unit/`.
    * **Sub-Tasks:** (For each `.py` file in `functions/src/` not yet covered)
        * 2.1.1. **Module: `functions/src/organization.py`**
            * [ ] Create comprehensive unit tests for all functions in `organization.py`, mocking Firestore and `check_permission`.
            * [ ] Test `create_organization` with valid and invalid inputs, verifying transaction logic.
            * [ ] Test `get_organization` with various permission scenarios.
            * [ ] Test `update_organization` with valid and invalid inputs, verifying field validation.
            * [ ] Test `delete_organization` including subscription checks and transaction logic for deletion.
        * 2.1.2. **Module: `functions/src/organization_membership.py`**
            * [ ] Create comprehensive unit tests for all functions in `organization_membership.py`, mocking Firestore and `check_permission`.
            * [ ] Test `add_organization_member` with valid and invalid inputs.
            * [ ] Test `set_organization_member_role` with various role transitions.
            * [ ] Test `list_organization_members` with different permission scenarios.
            * [ ] Test `remove_organization_member` including last admin checks.
            * [ ] Test `get_user_organization_role` with various user/org combinations.
            * [ ] Test `list_user_organizations` with users belonging to multiple organizations.
        * 2.1.3. **Module: `[module_name.py]`**
            * **Executor Prompt:** "Analyze `functions/src/[module_name.py]`. Identify all functions and classes. Create comprehensive unit tests covering main logic paths, edge cases, and error handling. Mock all external dependencies (Firestore, other GCP services, external APIs). Store tests in `tests/unit/test_[module_name].py`. Report execution results and estimated coverage."
            * Modules to cover: `cases.py`, `payments.py`, `party.py`, `agent_orchestrator.py`, `agent_nodes.py`, `llm_integration.py`, etc.

### 2.2. Comprehensive Integration Testing
    * **Objective:** Ensure all API endpoints defined in `terraform/openapi_spec.yaml` are covered by integration tests located in `tests/integration/`.
    * **Sub-Tasks:** (For each endpoint/flow not yet covered)
        * 2.2.1. **Organization Management Integration Tests**
            * [ ] **Organization Update (`PUT /organizations/{organizationId}`):** Verify org admin can update, staff cannot, non-member cannot.
            * [ ] **Organization Deletion (`DELETE /organizations/{organizationId}`):** Verify org admin can delete (and cannot with active subscription), staff cannot, non-member cannot.
        * 2.2.2. **Organization Membership Integration Tests**
            * [ ] Enhance existing tests to verify role-based access control for all membership operations.
            * [ ] Test that staff members cannot add/remove/change roles of other members.
            * [ ] Test that the last administrator cannot be removed or downgraded.
        * 2.2.3. **Case Management in Organization Context**
            * [ ] **Create Case (`POST /organizations/{organizationId}/cases`):** Test for admin (can create), staff (can create), non-member (cannot).
            * [ ] **Assign Case (`POST /cases/{caseId}/assign`):** Test for admin (can assign), staff (cannot), non-member (cannot); test invalid assignments.
            * [ ] **List Organization Cases (`GET /organizations/{organizationId}/cases`):** Test for admin, staff, and non-member.
        * 2.2.4. **File & Party Management for Organization Cases**
            * [ ] Test file upload/download for organization cases using `org_admin_api_client` and `org_user_api_client`.
            * [ ] Test party creation/update/deletion for organization cases using `org_admin_api_client` and `org_user_api_client`.
            * [ ] Verify non-members cannot access files or parties for organization cases.
        * 2.2.5. **Cross-Organization Security Tests**
            * [ ] Test that users from one organization cannot access resources from another organization.
            * [ ] Test that organization admins cannot modify members of other organizations.
            * [ ] Test that organization cases are properly isolated between organizations.
        * 2.2.6. **Endpoint/Flow: `[HTTP Method] [path]` (e.g., `POST /cases/{caseId}/parties`)**
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
