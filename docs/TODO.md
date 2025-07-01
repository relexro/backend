# Relex Backend - TODO List

**Overall Goal:** Ensure all API endpoints are fully functional, robustly tested (unit and integration), and any identified issues are systematically resolved. The immediate priority is to address the LLM integration test failures.

## Current Tasks

### 1. Fix LLM Integration Tests
- [ ] Review and fix `pytest` patches and mocks in `tests/integration/test_llm_integration.py`
- [ ] Ensure mocks provide correctly formatted `list` of `BaseMessage` objects
- [ ] Verify all 18 tests pass after fixes
- [ ] Document the correct mocking approach for future reference

### 2. Complete Organization Management Integration Tests
- [ ] Organization Update (`PUT /organizations/{organizationId}`)
  - [ ] Verify org admin can update
  - [ ] Verify staff cannot update
  - [ ] Verify non-member cannot update
- [ ] Organization Deletion (`DELETE /organizations/{organizationId}`)
  - [ ] Verify org admin can delete (and cannot with active subscription)
  - [ ] Verify staff cannot delete
  - [ ] Verify non-member cannot delete

### 3. Complete Stripe Integration Tests
- [ ] Promotion code/coupon handling for both payment intents and checkout sessions
- [ ] Webhook event handling for all relevant Stripe events
- [ ] Quota management based on subscription purchases and one-time payments
- [ ] Organization-specific subscription and payment handling

## Development Environment

### Required Tools
- Python 3.10 (required for Cloud Functions runtime)
- Node.js 18+ (required for Firebase CLI and Emulator Suite)
- Terraform 1.0+
- Firebase CLI
- Google Cloud SDK

### Local Setup
1. Firebase Emulator Suite (for local auth testing)
2. Local development server
3. Test environment
4. Development database

## High Priority

- [ ] **Comprehensive API Testing:** Test all API endpoints for correct behavior, error handling, and edge cases.
- [ ] **Integration Testing for Exa Tools:** Write and run integration tests specifically targeting the new `find_legislation` and `find_case_law` tools to validate their outputs.
- [ ] **End-to-End (E2E) Workflow Test:** Perform a full E2E test by running a complex query through the deployed agent to ensure the entire workflow from input to response generation functions correctly with the new Exa research node.

## Medium Priority

- [ ] **Performance Benchmarking:** Measure the latency of the new `_research_node` and compare it to the legacy BigQuery implementation (now replaced by Exa).
- [ ] **Error Handling Validation:** Test the agent's ability to gracefully handle potential errors from the Exa API (e.g., API key errors, empty results).

## Low Priority

- [ ] **Explore Exa Highlights Feature:** Investigate using the "highlights" feature in the Exa `get_contents` endpoint to potentially improve summary generation in downstream nodes.

## Done

- [x] **Exa Secret Manager Integration & Deployment Fix.**
- [x] **Refactor Research Backend from BigQuery to Exa API.**
- [x] **Add `exa-py` dependency and update Terraform for `EXA_API_KEY` secret.**
- [x] **Initial project setup and CI/CD pipeline.**

# TODO for API Readiness

- [ ] Ensure all secrets (Gemini, Grok, Exa, Stripe) are set and accessible in Secret Manager
- [ ] Deploy latest backend to GCP using terraform/deploy.sh
- [ ] Validate all endpoints via API Gateway (see terraform_outputs.log for URL)
- [ ] Implement/verify all required authentication and authorization flows (Firebase JWT, OIDC, etc.)
- [ ] End-to-end test all endpoints with real tokens from the frontend
- [ ] Document any missing or unstable endpoints in docs/api.md
- [ ] Finalize OpenAPI spec (terraform/openapi_spec.yaml) and validate with Redocly
- [ ] Update docs/status.md with deployment and test results
- [ ] Confirm frontend integration readiness with API
- [ ] Clean up obsolete/legacy code and tests
- [ ] Mark any endpoints that are not yet production-ready
- [ ] Add any additional tasks discovered during deployment/testing
