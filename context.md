# Relex Backend Context

**Project Name:** Relex Backend (Firebase Functions)

**Application Description:** Backend for Relex, an AI-powered legal chat application. This backend is built using Firebase Functions in Python and integrates with Firestore, Cloud Storage, and Vertex AI Conversational Agents.

**Technology Stack:**

*   **Serverless Functions:** Firebase Functions (Python runtime)
*   **Database:** Firebase Firestore (NoSQL document database)
*   **Object Storage:** Firebase Cloud Storage (for file storage)
*   **AI Conversational Agent:** Vertex AI Conversational Agents (Generative Agent with Vertex AI Search integration planned)
*   **Payment Processing:** Stripe (for one-time case payments and business subscriptions)
*   **Infrastructure as Code:** Terraform (for deployment and infrastructure management)
*   **Authentication:** Firebase Authentication (user management and security)
*   **Programming Language:** Python 3.x

**Key Modules/Functions (Organized by Feature Area):**

*   `cases.py`: Functions for case management (create, get, list, archive, delete, file upload/download).
*   `chat.py`: Functions for AI Chat interactions (receive prompt, enrich prompt, send to Vertex AI, store conversation).
*   `auth.py`: Functions for authentication and authorization (future advanced auth logic).
*   `payments.py`: Functions for payment processing (Stripe Payment Intents, Checkout Sessions, voucher redemption, subscription status).
*   `business.py`: Functions for business account management (create, get, update business accounts).

**Data Storage (Firestore Collections):**

*   `users`: User profiles (personal and business admins).
*   `businesses`: Business accounts.
*   `cases`: Legal cases.
*   `parties`: "Parties" (legal identities).
*   `caseChatMessages`: Chat messages within cases.
*   `documents`: Document metadata.
*   `labels`: Case labels/tags.
*   `vouchers`: Voucher codes.

**Security Considerations:**

*   Firebase Authentication for user authentication.
*   Firebase Security Rules for Firestore and Cloud Storage access control.
*   Input validation and sanitization in Firebase Functions to prevent injection attacks.
*   PII Scanning Layer (to be implemented) before sending prompts to Vertex AI.
*   Immutable Audit Trail (to be implemented) for sensitive data access.
*   Encryption at rest (Firebase default) and encryption in transit (HTTPS).
*   Rate limiting (if needed) for Firebase Functions.
*   Role-based access control (RBAC) for organization resources:
    *   Case owners have full access to their cases.
    *   Organization administrators have full access to all cases within their organization.
    *   Organization staff members have limited permissions based on their role.
    *   Permissions are verified through the `check_permissions` function.
    *   Fine-grained control over actions like reading, updating, deleting, and uploading files.

**Deployment:**

*   Terraform for infrastructure provisioning and deployment of Firebase Functions, Firestore, Cloud Storage, and IAM roles.
*   `GOOGLE_APPLICATION_CREDENTIALS` for authentication in Terraform and Firebase Functions.

**Context for LLM Prompts:**

*   When generating backend code, focus on modular Python functions within each module (`cases.py`, `chat.py`, etc.).
*   Use Firebase Admin SDK to interact with Firestore, Cloud Storage, and Firebase Authentication.
*   Integrate with Stripe Python library for payment processing.
*   Interact with Vertex AI Conversational Agents using Google Cloud Python client libraries.
*   Implement robust error handling and logging.
*   Ensure secure coding practices and data validation.
*   Consider performance and scalability when designing functions.
*   Code should be well-organized, readable, and maintainable.
*   Terraform configurations should be well-structured and idempotent.