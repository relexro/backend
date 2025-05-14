# Architecture

## Overview

Relex is a cloud-native legal assistant platform built on Google Cloud Platform (GCP) that uses advanced language models to help users with Romanian legal matters. The system follows a serverless architecture model with event-driven processing and secure data management.

## System Components

```
┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Client App   │────▶│   API Gateway   │────▶│   Cloud Functions │
│  (Web/Mobile) │◀────│   (Cloud API)   │◀────│   (Serverless)   │
└───────────────┘     └─────────────────┘     └──────────────────┘
                                                       │
                                                       ▼
┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Cloud Storage│◀───▶│    Firestore    │◀───▶│   LLM Services   │
│  (Documents)  │     │   (Database)    │     │(Gemini/Grok/etc.)│
└───────────────┘     └─────────────────┘     └──────────────────┘
                                                       │
                                                       ▼
┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Secret Manager│     │    BigQuery     │     │  Cloud Scheduler │
│  (API Keys)   │     │ (Legal Research)│     │   (Background)   │
└───────────────┘     └─────────────────┘     └──────────────────┘
```

### Key Components:

1. **Client Applications**
   - Web application built with modern frontend frameworks
   - Mobile applications (future)
   - Authentication via Firebase Auth

2. **API Gateway (Google Cloud Endpoints)**
   - RESTful API interfaces with OpenAPI specification
   - Authentication and authorization checks
   - Rate limiting and quota management
   - Request routing to appropriate backend services
   - Accessed via the default Google-provided URL (found in `docs/terraform_outputs.log`)
   - Note: The custom domain `api-dev.relex.ro` is not currently the active endpoint

3. **Cloud Functions (Serverless Backend)**
   - Written in Python for backend logic
   - Function-specific responsibilities (user management, case handling, etc.)
   - Event-driven architecture
   - Secure integration with other GCP services

4. **Firestore (NoSQL Database)**
   - Document-oriented data storage
   - Real-time data synchronization
   - Scalable and serverless
   - Secure access control with Firestore Rules

5. **Cloud Storage**
   - Document storage for case files and generated documents
   - Secure access with signed URLs
   - Content-addressable storage for deduplicated references

6. **LangGraph Agent System**
   - Orchestrates multiple LLMs (Gemini and Grok)
   - State-machine-based workflow management
   - Specialized nodes for different agent tasks
   - Tool integration for external functionality

7. **LLM Services**
   - **Gemini**: Used for task handling, text generation, and tool usage
   - **Grok**: Used for legal reasoning and strategy
   - Custom prompt engineering for legal domain expertise
   - Context management techniques for efficient token usage

8. **BigQuery**
   - Legal research database
   - Query capability for Romanian legislation and case law
   - Analytics for system usage and performance

9. **Secret Manager**
   - Securely stores API keys and sensitive configuration
   - Integrated with Cloud Functions for secure access

10. **Firebase Authentication**
    - User identity management
    - Multi-provider authentication (Email, Google, etc.)
    - Custom claims for role-based access control

11. **Stripe Integration**
    - Payment processing for subscriptions and one-time purchases
    - Webhook handling for payment events
    - Secure customer data management

## Data Flow

1. **Authentication Flow**
   - User authenticates via Firebase Authentication
   - Firebase JWT token is generated and passed to API Gateway
   - API Gateway validates the Firebase JWT token
   - API Gateway then calls backend Cloud Run functions using a Google OIDC ID token it generates, acting as the `relex-functions-dev@relexro.iam.gserviceaccount.com` service account
   - Backend functions validate this Google OIDC ID token
   - Note: The `userId` available within the backend function context is the subject ID of the service account, not the original end-user's Firebase UID
   - Backend functions perform additional authorization checks

2. **Case Processing Flow**
   - User creates a case with initial description
   - Agent determines case complexity tier
   - System checks user/organization quota
   - If approved, agent begins analysis and document generation
   - Documents are stored in Cloud Storage and referenced in Firestore
   - User receives notifications and updates about case progress

3. **Payment Flow**
   - System determines payment requirement based on case tier and quota
   - Creates Stripe payment intent or checkout session
   - User completes payment through Stripe-hosted UI
   - Webhook notification confirms payment to backend
   - Backend updates user quota and continues case processing

4. **Document Generation Flow**
   - Agent identifies document requirements
   - Queries necessary information from case context
   - Generates document content using LLMs
   - Creates PDF with proper formatting and placeholders
   - Stores document in Cloud Storage
   - Updates Firestore with document reference

## Security Architecture

1. **Authentication**
   - Firebase Authentication with secure JWT handling
   - Short-lived tokens with proper expiration
   - Multi-factor authentication (future)

2. **Authorization**
   - Role-based access control (RBAC) system
   - Resource-level permissions (user, organization, case)
   - Firestore Security Rules as additional protection layer

3. **Data Protection**
   - Encryption at rest for all data stores
   - Encryption in transit with TLS
   - PII handling procedures to minimize exposure
   - Data minimization principles in LLM interactions

4. **API Security**
   - Input validation on all endpoints
   - Rate limiting to prevent abuse
   - CORS configuration for web security
   - Security headers in responses

5. **Infrastructure Security**
   - Least privilege principle for service accounts
   - VPC Service Controls (future enhancement)
   - Cloud Armor protection (future enhancement)
   - Regular security scanning and updates

## Deployment Architecture

The system is deployed and managed using Infrastructure as Code (IaC) with Terraform:

1. **Terraform Management**
   - All infrastructure defined in code
   - Version controlled configurations
   - Automated deployment pipeline
   - Environment consistency

2. **Deployment Process**
   - CI/CD integration for automated deployments
   - Staged rollouts (dev, staging, production)
   - Blue/green deployment strategy (future)
   - Automated testing before promotion

3. **Monitoring and Observability**
   - Cloud Logging for centralized logs
   - Error tracking and alerting
   - Performance monitoring
   - Usage analytics for business insights

## Technology Stack

1. **Backend**
   - Python 3.10+ for Cloud Functions
   - Firestore for database
   - Cloud Storage for document storage

2. **API Management**
   - OpenAPI 3.0 specification
   - Google Cloud Endpoints / API Gateway

3. **AI/ML**
   - Gemini LLM for assistant interactions
   - Grok LLM for legal reasoning
   - LangGraph for agent orchestration

4. **DevOps**
   - Terraform for infrastructure management
   - GitHub for version control
   - Cloud Build for CI/CD (future)

5. **Payment Processing**
   - Stripe for subscription and payment handling

## Scalability Considerations

1. **Horizontal Scaling**
   - Serverless architecture automatically scales with demand
   - No infrastructure provisioning required
   - Pay-per-use cost model

2. **Performance Optimization**
   - Efficient LLM context management
   - Caching strategies for frequent operations
   - Asynchronous processing for long-running tasks

3. **Cost Management**
   - Resource utilization monitoring
   - Quota and budget alerts
   - Optimization of expensive operations (LLM calls)

## Future Architectural Enhancements

1. **Enhanced Analytics**
   - Comprehensive usage analytics
   - Legal research pattern analysis
   - Performance optimization based on metrics

2. **Knowledge Distillation**
   - Building specialized models from accumulated legal knowledge
   - Case similarity matching for precedent reference
   - Fine-tuning of LLMs for Romanian legal domain

3. **Advanced Security**
   - VPC Service Controls implementation
   - Customer-managed encryption keys (CMEK)
   - Advanced threat protection

4. **Global Expansion**
   - Multi-region deployment
   - Localization framework for additional languages
   - Region-specific legal knowledge bases

## High-Level Interaction Flow (Agent Focus)

```