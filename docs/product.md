## Relex Product Description (MVP)

### Overview

Relex is an AI-driven legal assistance platform designed to simplify legal case management through an intuitive chat interface. Built with a SvelteKit frontend and a Python-based Firebase backend deployed via Terraform, Relex provides case and "Parties" management, file attachments, and a subscription model that includes case quotas, with options for purchasing additional cases. The application supports Romanian and English from the MVP stage.

### Core Features (MVP Scope)

1.  **Authentication & Account Types**
    * **Login:** Exclusively Google Authentication via Firebase Authentication [cite: User Query Point 1].
    * **Account Types:**
        * **Individual (Personal) Account:** For individual users managing their own legal cases and associated "Parties" (profiles of people/entities involved) [cite: User Query Point 2].
        * **Organisation (Business) Account:** For companies managing multiple users and cases. Supports distinct roles [cite: User Query Point 2]:
            * **Administrator:** Manages all Organisation cases, "Parties," users, and subscription details; assigns cases to Staff members.
            * **Staff:** Can only access Organisation cases explicitly assigned to them by an Administrator.
    * **Account Switcher:** Located at the top of the left sidebar (desktop) or hamburger menu (mobile). Allows users who belong to an Organisation to seamlessly toggle between their Individual context and the Organisation context. Switching context alters *all* displayed data, including cases, "Parties," documents, and subscription/quota information, reflecting the selected account's scope.
    * **Role-Based Access Control (RBAC):** Enforced using Firebase Custom Claims (e.g., `role: "user" | "org_admin" | "staff"`, `orgId`) and corresponding Firebase Security Rules (Firestore & Storage) and backend function checks [cite: 246-250, backend_relex/context.md]. Individual accounts manage their own data; Organisation data is scoped by `orgId`, with Staff access restricted by case assignment.

2.  **Case Management**
    * **Actions:** Create, view, list (filterable by status), archive, delete cases [cite: 9, backend_relex/functions/src/cases.py].
    * **Case Structure:** Each case has essential fields: `title`, `description`, `status` ("open", "in_progress", "closed", "archived"), `creationDate`, `archiveDate` (optional), `parties` (array of attached `partyIds`), `documents` (array of document IDs), `labels` (array of label IDs), `userId` (creator), `orgId` (if Org case), `assignedUserId` (for Org staff assignments) [cite: 49, 135-148, 831, backend_relex/context.md].
    * **Case Tiers:** Each case includes a mandatory `tier` property (Enum: "Tier 1", "Tier 2", "Tier 3") assigned upon creation. This tier determines:
        * **Complexity/Type:** Reflects the nature of the case (e.g., Tier 1 for simple issues, Tier 3 for complex ones).
        * **Quota Usage:** Creating a case consumes one unit from the corresponding tier's quota within the active subscription plan.
        * **Price (for extra cases):** Tier 1: €9, Tier 2: €29, Tier 3: €99.
    * **Labels:** Cases can be tagged with predefined labels (fetched from backend) for organization.
    * **Frontend UI:**
        * List View: Displays cases relevant to the current context (Individual or Organisation). Organisation staff see only assigned cases. Filtering by status is available.
        * Detail View: Presents a chat interface along with menus/options to manage attached "Parties," view documents, and see case details/labels.
        * Creation: Form includes title, description, tier selection, and optionally attaching initial "Parties".

3.  **"Parties" (Părți) Management**
    * **Definition:** Manages profiles of individuals or organizations ("Parties") involved in cases, storing relevant legal identification and contact data [cite: 115, 119, 122-127].
    * **Party Types & Fields:**
        * **Individual Party:** `nameDetails` (firstName, lastName), `identityCodes` (cnp - Romanian Personal Numeric Code, required in MVP), `contactInfo` (address, email, phone), `signatureData` (captured digitally) [cite: 123-125, 1122].
        * **Organisation Party:** `nameDetails` (companyName), `identityCodes` (cui - Romanian Fiscal ID, regCom - Registration Number, both required), `contactInfo` (legalAddress, contactPerson details), `signatureData` (of legal representative) [cite: 126-128, 1122].
    * **Actions & UI:** The frontend provides UI (forms, lists, potentially within case details) for users to Create, Edit, and Delete "Parties" within their current account context (Individual or Organisation). Users can Attach/Detach these "Party" profiles to specific cases.
    * **Backend Status:** While the frontend requires these management capabilities, the corresponding backend API endpoints for creating, editing, deleting, attaching, and detaching Parties need implementation (as noted from `status.md`) [cite: backend_relex/status.md, 1045-1047, 1116]. The Firestore structure (`parties` collection) is defined [cite: 832, backend_relex/context.md].
    * **Storage:** Party data is stored in the `parties` Firestore collection, linked to cases via an array `attachedPartyIds` in the `cases` collection.

4.  **Subscription & Payment**
    * **Model:** Users subscribe to plans that include a monthly quota of cases across all three tiers (Tier 1, Tier 2, Tier 3). Extra cases needed beyond the included quota can be purchased individually at the standard per-tier rates (€9, €29, €99).
    * **Plans & Pricing:**
        * **Individual:** €9/mo or €86.40/yr (20% discount).
        * **Organisation Basic:** €200/mo or €1920/yr (20% discount).
        * **Organisation Pro:** €500/mo or €4800/yr (20% discount).
    * **Case Quotas (Included in Plans):**
        * Each plan includes a specific number of Tier 1, Tier 2, and Tier 3  ("Clasă 1", "Clasă 2", "Clasă 3".) cases per month/year. The exact numbers are configurable in the backend by an administrator but are structured to provide significantly more Tier 1 cases, fewer Tier 2, and even fewer Tier 3 cases, reflecting complexity and cost.
        * *(Example Quotas, numbers TBD in backend config):*
            * Individual: e.g., 5 Tier 1, 2 Tier 2, 1 Tier 3 cases per month.
            * Organisation Basic: e.g., 20 Tier 1, 10 Tier 2, 5 Tier 3 cases per month.
            * Organisation Pro: e.g., 50 Tier 1, 25 Tier 2, 10 Tier 3 cases per month.
        * This structure aims to offer ~70% savings compared to buying the equivalent cases individually over a year.
    * **Mechanics:**
        * Case creation attempts check the relevant tier's quota for the active subscription (Individual or Organisation). If quota is available, it's decremented.
        * If quota is exhausted, the backend returns an error, and the frontend prompts the user to purchase the case individually or upgrade their plan.
        * Stripe is used for all payment processing (Subscriptions and individual case purchases).
    * **Vouchers:** Users can redeem voucher codes for benefits like free cases or free subscription months. Frontend includes a redemption UI.

5.  **Chat Functionality**
    * **Interface:** A classic chat window is displayed within the Case Detail view.
    * **Features:** Users can send text messages and view the conversation history for the case. The frontend uses local session storage to persist user input in the chat box across page reloads.
    * **Backend:** The backend (Python Firebase Functions) provides API endpoints (`sendChatMessage`, `getChatHistory` - though exact endpoints TBD). It stores the full conversation history (user messages and AI responses) persistently in the `caseChatMessages` Firestore collection. AI integration details (enrichment, Vertex AI calls) are handled within the backend and abstracted from the frontend for the MVP.

6.  **File Handling**
    * **Support:** MVP supports uploading basic file types like images, PDFs, and documents.
    * **Storage:** Files are stored in Firebase Cloud Storage. Storage paths are organized based on the context (e.g., `users/{userId}/cases/{caseId}/...` or `organisations/{orgId}/cases/{caseId}/...` depending on ownership). Access is role-based.
    * **Limits & Enforcement:** A 2GB total storage limit exists per case. This limit is enforced by the backend during file upload attempts.
    * **Access Control:** Firebase Storage Security Rules, aligned with the RBAC model, restrict file access to authorized users (case owner, assigned staff, org admin) [cite: 104, 328-331].
    * **UI:** The frontend includes functionality to upload files (e.g., via a button in the chat or case details) and view/download attached documents.

7.  **UI/UX**
    * **Style:** "Dark Glassmorphism" aesthetic as per the initial style guide. Custom minimalist Svelte components will be built for most UI elements (cards, buttons, forms, etc.) to match this style. Flowbite components are used *only* for navigation and menu elements.
    * **Layout:**
        * **Desktop:** A left sidebar contains main navigation links (Cases, etc.), with the Account Switcher (Individual/Organisation selector) positioned at the top of this sidebar.
        * **Mobile:** A hamburger menu provides access to navigation and the account switcher.
    * **Languages:** Supports Romanian and English via `svelte-i18n`. A language toggle is available in the UI (likely navbar), and user preference is persisted.

8.  **Technical Details**
    * **Frontend:** SvelteKit, Tailwind CSS, Custom Svelte components, Flowbite (Nav/Menu only), Iconify, svelte-i18n. Deployed on Firebase Hosting.
    * **Backend:** Python Firebase Functions, Firestore (database), Cloud Storage (files), Stripe (payments). Deployed and managed via Terraform. `GOOGLE_APPLICATION_CREDENTIALS` used for authentication.
    * **Key Firestore Collections:** `users`, `organizations`, `organization_memberships`, `cases`, `parties`, `caseChatMessages`, `documents`, `labels`, `vouchers`, `plans` [cite: 826-834, backend -> context.md].

### Pending Items / Future Considerations (Post-MVP)

* **Signature Capture Library:** Research and selection of a suitable JavaScript library for capturing digital signatures in the frontend.
* **Backend Parties API:** Full implementation of Create, Read, Update, Delete, Attach/Detach endpoints for "Parties" [cite: backend_relex/status.md].
* **Advanced Security:** PII Scanning Layer, Immutable Audit Trails, detailed GDPR features (data retention enforcement, etc.), advanced encryption [cite: 760-766, 778].
* **Advanced Payments:** Chargeback handling, automated refunds, potentially more webhook events.
* **Performance Optimizations:** Caching, detailed indexing, cold start mitigation.
* **Full i18n:** Ensuring all content, including dynamic elements and potential Al outputs, is correctly localized.


---- UPDATE ----

# Product Description: Relex

## 1. Overview

Relex is an AI-driven platform designed to assist individuals and legal professionals in Romania with managing and navigating legal cases. It combines case management features with a sophisticated Lawyer AI Agent that provides guidance, performs legal research, and drafts relevant documents.

**Target Audience:** Individuals facing common legal issues in Romania, small law firms, paralegals, and potentially larger organizations needing streamlined case handling.

**Core Value Proposition:** Simplify legal processes through AI assistance, provide access to relevant legal information, improve case organization, and facilitate the creation of necessary legal documents.

## 2. Key Features

* **User Management:** Secure registration and login for individuals and organizations.
* **Organization Management:** Allows creation of organizations, inviting members (Admin, Staff roles), and managing organization-level subscriptions.
* **Case Management:**
    * Create, view, filter, and archive legal cases.
    * Attach/detach relevant parties (individuals, companies) to cases.
    * Upload and manage case-related documents (attachments).
    * **NEW:** View and manage agent-generated **Drafts** (PDF documents generated by the AI for court/official use).
* **Party Management:** Maintain a central repository of parties involved across cases (PII secured, access controlled).
* **Lawyer AI Agent Interaction:**
    * **NEW:** Interactive agent available within each case via a chat interface.
    * **NEW:** Automated case **Tier Determination** (Low, Standard, High complexity) by the agent based on initial user description.
    * **NEW:** Integrated **Quota Check and Payment:** Agent checks subscription quota against determined tier; prompts for per-case payment via Stripe if quota is unavailable, gating further interaction.
    * **NEW:** **AI-Powered Assistance:** Agent gathers case details, analyzes uploaded documents, performs legal research (Romanian legislation & case law via BigQuery), provides guidance (leveraging Gemini & Grok LLMs), and generates relevant draft documents (e.g., court filings, notifications).
    * **NEW:** Stores detailed, evolving case context (`case_details`) managed by the agent.
* **Subscription Management:** Tiered subscription plans (e.g., Free, Individual Pro, Organization Standard) offering varying quotas for cases based on complexity tiers. Secure payments handled by Stripe.
* **Document Handling:**
    * Secure storage for user-uploaded attachments (Cloud Storage).
    * **NEW:** Secure generation and versioned storage for AI-generated Drafts (PDFs in Cloud Storage, Markdown in Firestore).

## 3. Core User Flow (Illustrative - Simplified)

1.  **Registration/Login:** User signs up or logs in.
2.  **Case Creation:** User initiates case creation.
3.  **Agent Interaction Begins:** User lands in the case view; Lawyer AI Agent initiates conversation.
4.  **Tier Determination:** Agent asks questions, analyzes user description, determines case complexity Tier (1, 2, or 3).
5.  **Quota Check & Payment:** Agent checks quota via tool.
    * *If Quota OK:* Agent confirms and invites user to provide case details.
    * *If No Quota:* Agent prompts user to pay for the specific case via Stripe; interaction pauses until payment is confirmed.
6.  **Case Resolution (Agent Assistance):**
    * User provides details, uploads documents, attaches parties via UI.
    * Agent (Gemini) interacts, asks clarifying questions (guided by Grok), analyzes documents, updates `case_details`.
    * Agent performs legal research (BigQuery) as needed.
    * Agent consults Grok for strategy and planning.
    * Agent generates Draft documents (PDFs) based on Grok's guidance.
7.  **Draft Review:** User reviews generated Drafts in the UI, downloads PDFs.
8.  **Case Progression:** User continues interaction, potentially leading to revised drafts or case closure.
9.  **Archival:** User archives the case upon completion.

## 4. Technology Stack (Key Components)

* **Frontend:** SvelteKit
* **Backend:** Python on Google Cloud Functions
* **API:** RESTful API via Google Cloud API Gateway (OpenAPI spec)
* **Database:** Firestore (NoSQL)
* **Data Warehouse:** BigQuery (for legal data)
* **AI Orchestration:** LangGraph
* **LLMs:** Gemini Flash 2.5, Grok 3 Mini
* **File Storage:** Google Cloud Storage
* **Payments:** Stripe
* **Infrastructure:** Google Cloud Platform (managed via Terraform)

## 5. Monetization

* **Tiered Subscriptions:** Monthly/annual plans with quotas based on case complexity tiers (e.g., 5 Tier 1 cases, 2 Tier 2 cases per month).
* **Per-Case Purchase:** Option to purchase access for a single case if quota is exceeded or for non-subscribers (price may vary by tier).

*(Refer to `architecture.md`, `agent.md`, `data_models.md` for more technical details)*