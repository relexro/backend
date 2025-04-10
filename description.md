## Relex Backend Implementation Documentation (MVP)

### 1. Overview & Architecture

The Relex backend is a serverless application built using Python Firebase Functions, managed and deployed via Terraform [cite: 6, README.md, blueprint.md]. It utilizes Firebase services (Firestore, Authentication, Cloud Storage) and integrates with Stripe for payments [cite: context.md]. The architecture focuses on modular functions triggered via HTTPS requests, typically routed through Google Cloud API Gateway with a custom domain (`api.relex.ro`) [cite: api.md, README.md].

* **Implemented:** Basic Terraform setup for functions, API Gateway, Storage, Firestore; Python function structure [cite: status.md, README.md].
* **To Do:** Refine Terraform IAM roles for least privilege, implement Firestore security rules, finalize API Gateway configuration (OpenAPI spec exists but needs alignment with final function signatures) [cite: status.md, context.md].

### 2. Authentication & Authorization

* **Implemented:**
    * Firebase Authentication integration (Google provider only as requested) [cite: README.md].
    * Enhanced permission checking with modular, resource-specific checkers in `auth.py`.
    * Centralized permissions map defining allowed actions by role and resource type.
    * Pydantic validation for permission request data.
    * Staff assignment validation for organization cases.
    * Document permission logic that respects parent case access.
    * Role checking within Org Admin functions (`organization_membership.py`).
    * User profile creation trigger (`create_user_profile`).
    * Permission checking for chat conversations, ensuring users can only access conversations for cases they have permission to view.
* **To Do:**
    * **Firebase Custom Claims:** Implement setting custom claims (`role`, `orgId`) on user tokens to optimize permission checks.
    * **Firestore Security Rules:** Write and deploy comprehensive rules mirroring RBAC logic [cite: 248, context.md].
    * **Cloud Storage Security Rules:** Write and deploy rules based on case ownership and organization roles.

### 3. API Structure

* **Implemented:** `openapi_spec.yaml`, `api.md` define many endpoints [cite: terraform/openapi_spec.yaml, api.md]. `main.py` exports corresponding functions [cite: functions/src/main.py].
* **To Do:**
    * **Consistency Check:** Ensure implemented functions match `openapi_spec.yaml`.
    * **Quota Error Response:** Define HTTP 402 error response for quota exhaustion.
    * **Voucher Endpoint:** Define and implement voucher redemption endpoint.
    * **Case Assignment Endpoint:** Define and implement endpoint for Org Admins to assign cases (`assignedUserId`) to Staff.

### 4. Firestore Schema

* **Implemented:** Core collections (`users`, `organizations`, `organization_memberships`, `cases`, `documents`, `payments`, `checkoutSessions`, `plans`, `parties`, `caseTypeConfigs`) defined in `context.md` [cite: context.md]. Collection name consistency fixed.
* **To Do:**
    * **Labels Collection:** Implement `labels` collection (predefined).
    * **Vouchers Collection:** Implement `vouchers` collection.
    * **Case Schema:** Add `assignedUserId`. Refine `paymentStatus` Update `create_case`. Added `caseTypeId` field for dynamic chat agent configuration.
    * **User/Org Schema:** Ensure schemas include all required subscription/quota fields (`caseQuotaTotal`, `caseQuotaUsed`, `billingCycleStart`, `billingCycleEnd`, `voucherBalance` etc.) [cite: context.md].
    * **Indexing:** Define and configure necessary Firestore indexes.

### 5. Cloud Storage Structure

* **Implemented:** Single bucket (`relex-files`) usage [cite: functions/src/cases.py]. Path structure `cases/{caseId}/documents/{filename}` used [cite: functions/src/cases.py].
* **To Do:**
    * **Finalize Path Strategy:** Standardize path for Organisation cases (e.g., `organizations/{orgId}/cases/{caseId}/...`).
    * **Implement ACLs:** Deploy Storage Security Rules reflecting RBAC.
    * **Implement 1GB Limit Check:** Add logic in `upload_file`.

### 6. Function Modules Status

* **`auth.py` [cite: functions/src/auth.py]:**
    * Implemented:
        * Enhanced `check_permissions` with resource-specific checkers (case, organization, party, document)
        * Centralized permissions map with predefined actions per role
        * Pydantic validation for request schemas
        * Staff assignment validation for organization cases
        * Document permissions derived from parent case access
        * `validate_user` and `get_user_role` with improved error handling
    * To Do: Implement Firebase custom claims for optimization.

* **`user.py` [cite: functions/src/user.py]:**
    * Implemented: `get_user_profile`, `update_user_profile`, `create_user_profile`.
    * To Do: Ensure schema includes `voucherBalance`.

* **`organization.py` [cite: functions/src/organization.py]:**
    * Implemented:
        * `create_organization` (fixed collection name to `organization_memberships`)
        * `get_organization`
        * `update_organization` (improved error handling)
        * `delete_organization` (with transaction-based cleanup)
    * Fixed: Collection name inconsistency resolved across all functions.
    * To Do: Ensure schema includes subscription/quota fields. Align/deprecate superseded functions.

* **`organization_membership.py` [cite: functions/src/organization_membership.py]:**
    * Implemented: Core membership management functions with corrected collection name (`organization_memberships`).
    * Fixed: Collection name inconsistency resolved across all functions.
    * To Do: Enhance error handling for edge cases.

* **`cases.py` [cite: functions/src/cases.py]:**
    * Implemented: `create_case` (lacks quota check), `get_case`, `list_cases` (basic filtering), `archive_case`, `delete_case`, `upload_file`, `download_file`, `attach_party_to_case`, `detach_party_from_case`.
    * To Do: **Implement Quota Check in `create_case`**, implement case assignment (`assignedUserId`), add label filtering, integrate enhanced `check_permissions`. Implement 1GB limit check.

* **`payments.py` [cite: functions/src/payments.py]:**
    * Implemented: `create_payment_intent`, `create_checkout_session`, `handle_stripe_webhook` (various events with improved error handling and nested data access), `cancel_subscription`.
    * Fixed: Added more robust error handling for Stripe API calls and safer nested data access.
    * To Do: **Implement Voucher Redemption Logic**, ensure webhook correctly updates quotas/billing cycle. Configure Stripe Price IDs. Add tests.

* **`chat.py` [cite: functions/src/chat.py]:**
    * Implemented: Basic endpoints with enhanced permission checking in `store_conversation` to verify parent case permissions.
    * Fixed: Added proper permission check to `store_conversation`.
    * To Do: Implement functional `sendChatMessage` and `getChatHistory` endpoints using `conversations` subcollection. Defer actual AI integration.

* **`party.py` [cite: functions/src/party.py]:**
    * Implemented: Full CRUD operations (`create_party`, `get_party`, `update_party`, `delete_party`, `list_parties`), attach/detach functions via `cases.py`.
    * To Do: Enhance search and filtering capabilities.

### 7. Payment System Implementation Status

* **Implemented:**
    * Stripe setup, Payment Intent/Checkout Session creation, webhook handler for subscription events, cancellation [cite: functions/src/payments.py].
    * Subscription fields in `users`/`organizations` schemas [cite: context.md].
    * `plans` collection defined [cite: context.md].
    * Product/price listing endpoint (`GET /v1/products`) with Firestore caching to minimize Stripe API calls.
* **To Do:**
    * **Quota Logic:** Implement quota checking/decrementing in `create_case`. Handle "quota exhausted" error.
    * **Quota Reset:** Ensure `invoice.paid` webhook resets `caseQuotaUsed` and updates billing cycle dates.
    * **Backend Quota Configuration:** Implement admin mechanism to define quotas per plan/tier (likely via `plans` collection).
    * **Voucher Backend:** Implement `redeem_voucher` logic.

### 8. Deployment

* **Implemented:** Terraform scripts (`main.tf`, etc.) for deployment [cite: README.md]. `deploy.sh` script [cite: terraform/deploy.sh]. Uses `GOOGLE_APPLICATION_CREDENTIALS`. GCS backend for state [cite: terraform/deploy.sh].
* **To Do:** Configure necessary IAM permissions. Securely manage environment variables (Stripe keys etc.) during deployment.

### 9. Summary of Missing MVP Backend Components

* ✅ **Party Management API:** Full CRUD operations and Attach/Detach functionality now implemented.
* ✅ **RBAC Enforcement:** Enhanced modular permission system with resource-specific checkers and staff assignment validation implemented.
* ✅ **Conversation Storage:** Added permission checks to ensure secure conversation storage.
* **Quota System:** Full logic in `create_case` & webhook reset.
* **Voucher Redemption API & Logic.**
* **Firestore/Storage Security Rules.**
* **Case Assignment API & Logic.**
* **Chat API:** Functional `sendChatMessage` / `getChatHistory`.
* **File Size Limit Enforcement.**
* **(Post-MVP Ideal):** Admin interface/function to configure plan quotas.