# Relex Backend - TODO List

**Overall Goal:** Ensure all API endpoints are fully functional, robustly tested (unit and integration), and any identified issues are systematically resolved. The immediate priority is to address the API Gateway logging issues and LLM integration test failures.

## Current Tasks

### 1. Fix API Gateway Logging Issues
- [ ] Set up proper logging configuration for API Gateway
- [ ] Implement log aggregation and analysis tools
- [ ] Create alerts for critical API Gateway events
- [ ] Document logging best practices for API Gateway

### 2. Fix LLM Integration Tests
- [ ] Review and fix `pytest` patches and mocks in `tests/integration/test_llm_integration.py`
- [ ] Ensure mocks provide correctly formatted `list` of `BaseMessage` objects
- [ ] Verify all 18 tests pass after fixes
- [ ] Document the correct mocking approach for future reference

### 3. Complete Organization Management Integration Tests
- [ ] Organization Update (`PUT /organizations/{organizationId}`)
  - [ ] Verify org admin can update
  - [ ] Verify staff cannot update
  - [ ] Verify non-member cannot update
- [ ] Organization Deletion (`DELETE /organizations/{organizationId}`)
  - [ ] Verify org admin can delete (and cannot with active subscription)
  - [ ] Verify staff cannot delete
  - [ ] Verify non-member cannot delete

### 4. Complete Stripe Integration Tests
- [ ] Promotion code/coupon handling for both payment intents and checkout sessions
- [ ] Webhook event handling for all relevant Stripe events
- [ ] Quota management based on subscription purchases and one-time payments
- [ ] Organization-specific subscription and payment handling

### 5. API Documentation Updates
- [ ] Audit and update OpenAPI spec to match implemented behavior
- [ ] Update API documentation with latest changes
- [ ] Document authentication flow and requirements
- [ ] Add examples for all endpoints

### 6. Monitoring & Alerting
- [ ] Review existing monitoring and logging setup
- [ ] Set up alerts for critical errors
- [ ] Implement performance monitoring
- [ ] Create dashboard for system health

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
