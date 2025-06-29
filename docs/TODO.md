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
