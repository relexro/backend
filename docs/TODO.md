# Relex Backend - TODO List

This document tracks outstanding tasks, issues, and planned work for the Relex Backend system. Items are organized by priority and status.

## Critical Issues

### API Gateway Logging
- **Status**: RESOLVED_WORKAROUND_IDENTIFIED
- **Symptom**: API Gateway logs were not appearing in Cloud Logging when filtering for `resource.type=api_gateway`. Investigation revealed that logs are present but under `resource.type=api` with a `logName` containing `apigateway` (e.g., `projects/relexro/logs/relex-api-dev-1zpirx0ouzrnu.apigateway.relexro.cloud.goog%2Fendpoints_log`).
- **Impact**: Monitoring and debugging of the API Gateway is now possible using the correct query.
- **Next Steps**:
  1. Created a dedicated log view `api-gateway-logs` for easier access (Actioned on 2025-05-17).
  2. Verify log generation by making test requests to the API Gateway (`relex-api-gateway-dev-mvef5dk.ew.gateway.dev`) and checking the `api-gateway-logs` view or using the query: `resource.type=api AND logName:apigateway` in Cloud Logging for project `relexro`.
  3. Update any internal developer documentation or runbooks to reflect the correct method for querying API Gateway logs.
  4. Consider creating a custom monitoring dashboard in Cloud Monitoring for API Gateway metrics and these logs for improved long-term visibility.
  5. If detailed transactional or payload logging from the API Gateway itself is still required beyond what is available in `resource.type=api` logs, investigate enabling this at the API Config level or through backend function logging enhancements.

### Custom Domain for API Gateway
- **Status**: DEFERRED
- **Current State**: The API is accessed via the default Google-provided URL (found in `docs/terraform_outputs.log` as `api_gateway_url`), not the custom domain `api-dev.relex.ro`.
- **Next Steps**:
  1. If reactivated, implement using Cloud Load Balancer with SSL certificate
  2. Update DNS records in Cloudflare
  3. Configure proper health checks
  4. Update documentation to reflect the new endpoint

### End-User Identity Propagation
- **Status**: PARTIALLY IMPLEMENTED
- **Current State**: The backend function's `auth.py` (`get_authenticated_user`) now extracts the original end-user's Firebase UID and email from the `X-Endpoint-API-Userinfo` header.
- **Next Steps**:
  1. Verify this implementation works for all endpoints
  2. Add comprehensive tests for the authentication flow
  3. Update documentation to reflect the current implementation

## High Priority Tasks

### Comprehensive API Endpoint Testing
- **Status**: INCOMPLETE
- **Current State**: Only `/v1/users/me` has been partially tested for routing, authentication, and end-user identity propagation.
- **Next Steps**:
  1. Create a test plan for all ~37 endpoints
  2. Implement automated tests for each endpoint
  3. Verify routing, authentication, authorization, and business logic
  4. Test health check mechanism for all endpoints
  5. Document test results and any issues found

### JWT Audience Configuration Review
- **Status**: PENDING
- **Current State**: The `jwt_audience` in `openapi_spec.yaml` is not currently explicitly set, relying on defaults.
- **Next Steps**:
  1. Review current configuration and behavior
  2. Consider adding explicit configuration for clarity
  3. Test with different audience values to ensure proper validation

### Implement Rate Limiting
- **Status**: NOT STARTED
- **Next Steps**:
  1. Design rate limiting strategy (per user, per IP, per endpoint)
  2. Implement in API Gateway configuration
  3. Add monitoring for rate limit events
  4. Document rate limits in API documentation

### Security Headers Configuration
- **Status**: NOT STARTED
- **Next Steps**:
  1. Define required security headers (CORS, Content-Security-Policy, etc.)
  2. Implement in API Gateway or backend functions
  3. Verify with security scanning tools

## Medium Priority Tasks

### Optimize Permission Checks
- **Status**: PLANNED
- **Current State**: Permission checks require Firestore reads for each check.
- **Next Steps**:
  1. Implement Firebase Custom Claims for frequently used permissions
  2. Update `auth.py` to use claims when available
  3. Benchmark performance improvements

### Implement Voucher System
- **Status**: PLANNED
- **Next Steps**:
  1. Design database schema for vouchers
  2. Implement voucher creation and validation endpoints
  3. Integrate with payment system
  4. Add admin interface for voucher management

### Add File Versioning
- **Status**: PLANNED
- **Next Steps**:
  1. Design versioning system for documents
  2. Update storage operations to maintain versions
  3. Implement version history API
  4. Update UI to display and manage versions

### Improve Agent Error Handling
- **Status**: PLANNED
- **Next Steps**:
  1. Implement more robust error recovery for the Lawyer AI Agent
  2. Add retry mechanisms for LLM API calls
  3. Improve error messages and logging
  4. Implement session recovery for interrupted agent conversations

## Low Priority Tasks

### API Versioning
- **Status**: PLANNED
- **Next Steps**:
  1. Design versioning strategy
  2. Update OpenAPI specification
  3. Implement version routing in API Gateway
  4. Document versioning policy

### Advanced Search Implementation
- **Status**: PLANNED
- **Next Steps**:
  1. Evaluate search technologies (Firestore native, Algolia, etc.)
  2. Design search API
  3. Implement indexing and search functionality
  4. Add to API documentation

### Contribution Guidelines
- **Status**: PLANNED
- **Next Steps**:
  1. Create `CONTRIBUTING.md` with development workflow
  2. Document code style and review process
  3. Add issue and PR templates

### Architecture Diagrams
- **Status**: PLANNED
- **Next Steps**:
  1. Create detailed system architecture diagrams
  2. Add sequence diagrams for key flows
  3. Update `docs/architecture.md`

## Completed Tasks

### API Gateway Path Translation
- **Status**: COMPLETED
- **Resolution**: Configured with `path_translation: CONSTANT_ADDRESS` for all backends
- **Date**: May 2025

### Cloud Function Health Checks
- **Status**: COMPLETED
- **Resolution**: Standardized to respond to `X-Google-Health-Check: true` header
- **Date**: May 2025
