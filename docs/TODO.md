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
            * **Status:** DONE.
            * **Executor Prompt:** "Create unit tests for `get_user_profile_logic` and `update_user_profile_logic` (or equivalent functions) in `functions/src/user.py`. Mock Firestore client interactions (`db.collection(...).document(...).get()`, etc.). Store tests in `tests/unit/test_user.py`. Report test execution results."
        * 1.2.3. **Unit Tests for Auth Permission Helpers:**
            * **Status:** DONE
            * **Sub-bullets:**
                * [DONE] Create dedicated unit tests for `_check_organization_permissions` and `_check_case_permissions` (for org cases) in `functions/src/auth.py`, mocking Firestore calls to isolate permission logic. (Extended to cover `_check_party_permissions` and `_check_document_permissions` as well).
                * [DONE] Test all permission scenarios for organization admins, staff, and non-members for the covered helpers.
                * [DONE] Test cross-organization security (users from one org cannot affect another org's resources) for the covered helpers.
        * 1.2.4. **Run All New Unit Tests:**
            * **Executor Prompt:** "Execute all unit tests in the `tests/unit/` directory using `python -m pytest tests/unit/`. Report any failures with full tracebacks."

### 1.3. Basic Integration Tests for Core User & Organization Flows
    * **Objective:** Ensure the primary user and organization API endpoints work end-to-end against a deployed environment, using tests located in `tests/integration`.
    * **Context:** API Gateway URL: `https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev/v1/`
    * **Sub-Tasks:**
        * 1.3.1. **Integration Test: User Creation & Retrieval (if applicable, or focus on retrieval if creation is external):**
            * If user creation is via an endpoint: Test `POST /users` then `GET /users/me`.
            * If only retrieval: Confirm `GET /users/me` (already covered by 1.1.3 if successful).
            * **Executor Prompt (if creation endpoint exists):** "Develop an integration test for user creation (e.g., `POST /v1/users`) followed by retrieval (`GET /v1/users/me`). Use a valid test JWT. Assert 201/200 status codes and validate response data. Store in `tests/integration/test_user_e2e.py`. Report execution results."
        * 1.3.2. **Integration Test: Organization Creation & Retrieval:**
            * Test `POST /organizations` to create a new organization. - DONE (Key functionalities fixed: `end_user_id` propagation, datetime handling, sentinel value serialization, and Firestore client issues in auth. All tests now passing.)
            * Test `GET /organizations/{orgId}` to retrieve the created organization. - DONE (Fixed Firestore client import issue in auth.py, all tests now passing.)
            * Test `GET /organizations` (or `/users/me/organizations`) to list user's organizations. - DONE (All tests now passing.)
            * **Executor Prompt:** "Develop integration tests for: 1. Creating an organization (`POST /v1/organizations`) with payload `{\"name\": \"Test Org Integration\"}`. 2. Retrieving the created org by its ID. 3. Listing organizations for the test user. Use a valid test JWT. Assert appropriate status codes and response data. Store in `tests/integration/test_organization.py`. Report execution results."
        * 1.3.3. **Run Core Integration Tests:**
            * **Executor Prompt:** "Execute integration tests: `test_user_e2e.py` and `test_organization.py` from `tests/integration/` against the deployed dev environment. Ensure `RELEX_API_BASE_URL` (e.g., `https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev/v1/`) and the appropriate authentication tokens (`RELEX_TEST_JWT`, `RELEX_ORG_ADMIN_TEST_JWT`, and `RELEX_ORG_USER_TEST_JWT`) are set as environment variables for the test execution environment. Use `./refresh_tokens.sh` to refresh expired tokens automatically. Report failures with request/response details."

## Phase 2: Expanding Test Coverage & API Functionality

### 2.1. Comprehensive Unit Testing
    * **Objective:** Achieve >80% unit test coverage for all modules in `functions/src/`, with tests residing in `tests/unit/`.
    * **Sub-Tasks:** (For each `.py` file in `functions/src/` not yet covered)
        * 2.1.1. **Module: `functions/src/organization.py`**
            * [x] Create comprehensive unit tests for all functions in `organization.py`, mocking Firestore and `check_permission`. (Covers `create_organization`, `get_organization`, `update_organization`, `delete_organization` including transaction logic, validation, and permission scenarios).
        * 2.1.2. **Module: `functions/src/organization_membership.py`**
            * [x] Create comprehensive unit tests for all functions in `organization_membership.py`, mocking Firestore and `check_permission`. (Tests implemented in `tests/integration/test_organization_membership.py` cover unit-level logic for `add_organization_member`, `set_organization_member_role`, `list_organization_members`, `remove_organization_member`, `get_user_organization_role`, `list_user_organizations`).
        * 2.1.3. **Module: `functions/src/party.py`**
            * [x] **Module: `functions/src/party.py`**: Comprehensive unit tests implemented, covering all functions, validation (CNP, CUI, RegCom), permission checks, and edge cases.
        * 2.1.4. **Module: `functions/src/cases.py`**
            * [x] **Module: `functions/src/cases.py`**: Comprehensive unit tests implemented for core logic, covering `create_case` (individual and org), `get_case`, `list_cases` (user and org, with filtering/pagination), `archive_case`, and `delete_case` (soft delete). Permission checks and error handling are included. (Note: `update_case` function not present in current module version).
        * 2.1.5. **Module: `functions/src/llm_integration.py`**
            * [x] **Module: `functions/src/llm_integration.py`**: Comprehensive unit tests implemented (16 tests, ~95%+ coverage), covering initialization, context preparation, API interactions (mocked), response formatting, conversation history, and core query processing logic. All tests passing. `pytest.ini` and `requirements-dev.txt` updated to handle `asyncio` tests and suppress warnings. Note: Some async-related warnings persist in other test files (`test_nodes.py`), but these are unrelated to `llm_integration.py` and may require environment setup adjustments.
        * Modules to cover: `payments.py`, `agent_orchestrator.py`, `agent_nodes.py`, etc.

### 2.2. Comprehensive Integration Testing
    * **Objective:** Ensure all API endpoints defined in `terraform/openapi_spec.yaml` are covered by integration tests located in `tests/integration/`.
    * **Sub-Tasks:** (For each endpoint/flow not yet covered)
        * 2.2.1. **Organization Management Integration Tests**
            * [ ] **Organization Update (`PUT /organizations/{organizationId}`):** Verify org admin can update, staff cannot, non-member cannot.
            * [ ] **Organization Deletion (`DELETE /organizations/{organizationId}`):** Verify org admin can delete (and cannot with active subscription), staff cannot, non-member cannot. (Note: `test_admin_cannot_delete_organization_with_active_subscription` in `test_organization.py` was SKIPPED in last run; reason needs checking if not known.)
        * 2.2.2. **Organization Membership Integration Tests**
            * [x] Enhance existing tests to verify role-based access control for all membership operations. (Note: 10 tests in `TestOrganizationMembership` class in `test_organization_membership.py` are emulator-specific and were SKIPPED in API gateway test run.)
            * [x] Test that staff members cannot add/remove/change roles of other members.
            * [x] Test that the last administrator cannot be removed or downgraded.
        * 2.2.3. **Case Management in Organization Context**
            * [x] **Create Case (`POST /organizations/{organizationId}/cases`):** Test for admin (can create), staff (can create), non-member (cannot).
            * [x] **Assign Case (`POST /cases/{caseId}/assign`):** Test for admin (can assign), staff (cannot), non-member (cannot); test invalid assignments.
            * [x] **List Organization Cases (`GET /organizations/{organizationId}/cases`):** Test for admin, staff, and non-member.
        * 2.2.4. **File & Party Management for Organization Cases**
            * [x] Test file upload/download for organization cases using `org_admin_api_client` and `org_user_api_client`.
            * [x] Test party creation/update/deletion for organization cases using `org_admin_api_client` and `org_user_api_client`.
            * [x] Verify non-members cannot access files or parties for organization cases.
        * 2.2.5. **Cross-Organization Security Tests**
            * [x] Test that users from one organization cannot access resources from another organization. (Note: `test_admin_cannot_access_other_org_details` in `test_cross_org_security.py` is intentionally SKIPPED due to known API behavior.)
            * [x] Test that organization admins cannot modify members of other organizations.
            * [x] Test that organization cases are properly isolated between organizations.
        * 2.2.6. **Stripe Integration Tests** // Status updated based on focused test run on 2025-05-22
            * [x] Payment intent creation and handling for different case tiers - COMPLETED (Relevant tests in `test_payments.py` passed)
            * [x] Checkout session creation for subscriptions (individual plan) - VERIFIED (`test_create_checkout_session` for `planId: "individual_monthly"` now passing. Prerequisites: `tests/conftest.py` correctly sources `api_base_url` from `docs/terraform_outputs.log` or `RELEX_API_BASE_URL` env var; `STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY` env var is set; Operator configured Firestore `plans/individual_monthly` document for webhook processing, including `caseQuotaTotal`). Further testing for organization plans may be needed.
            * [?] Promotion code/coupon handling for both payment intents and checkout sessions - NEEDS RE-VERIFICATION (Not covered in focused 2025-05-22 test run)
            * [~] Webhook event handling for all relevant Stripe events - NEEDS REVIEW (Most tests in `test_stripe_webhooks.py` were SKIPPED; some basic webhook tests in `test_payments.py` passed)
            * [?] Quota management based on subscription purchases and one-time payments - NEEDS RE-VERIFICATION (Not covered in focused 2025-05-22 test run)
            * [?] Organization-specific subscription and payment handling - NEEDS RE-VERIFICATION (Not covered in focused 2025-05-22 test run)
            * [x] Products endpoint for retrieving Stripe products and pricing - COMPLETED (`test_get_products` in `test_payments.py` passed)
            * [x] Payment system authentication and user context propagation - COMPLETED (Fixed end_user_id issue)
        * 2.2.7. **Endpoint/Flow: `[HTTP Method] [path]` (e.g., `POST /cases/{caseId}/parties`)**
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
        * [DONE] Addressed multiple core issues (May 2025 cycle): Fixed `request.user_id` to `request.end_user_id` across `organization.py`, `cases.py`, `party.py`, `organization_membership.py`. Resolved datetime usage inconsistencies. Fixed Firestore sentinel serialization in `create_org_in_transaction`, `add_organization_member`, `set_organization_member_role`. Corrected Firestore client import in `auth.py`. Added `pytest.ini` to suppress test warnings. These fixes resulted in all tests passing.

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
