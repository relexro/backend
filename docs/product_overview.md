# Relex Product Overview

## Overview

Relex is an AI-driven legal assistance platform designed to simplify legal case management for individuals and legal professionals in Romania. It combines traditional case management features with a sophisticated Lawyer AI Agent that provides guidance, performs legal research, and drafts relevant legal documents. The platform operates in Romanian and English, offering a comprehensive solution to navigate the complexities of the Romanian legal system.

## Target Audience

- **Individuals:** People facing common legal issues in Romania who need guidance and document preparation
- **Small Law Firms:** Legal practices seeking to streamline their workflow and enhance productivity
- **Paralegals:** Professionals who assist lawyers with case preparation and document drafting
- **Organizations:** Companies with legal departments that need centralized case management

## Core Value Proposition

- **Simplify Legal Processes:** AI assistance guides users through complex legal procedures
- **On-Demand Legal Information:** Access to relevant Romanian legislation and case law
- **Improved Case Organization:** Structured approach to managing legal cases
- **Efficient Document Creation:** AI-generated draft documents ready for official use
- **Accessibility:** Making legal assistance more available and affordable

## Key Features

### User Management

- Secure registration and login via Firebase Authentication
- User profile management with customizable settings
- Language preference selection (Romanian/English)
- Subscription and quota tracking

### Organization Management

- Organization creation with multiple configurations (law firm, corporate, individual)
- Member invitations with role-based access control (Administrator, Staff)
- Organization-level subscription management
- Case assignment to specific staff members
- Centralized oversight for administrators

### Case Management

- Create, view, filter, and archive legal cases
- Three-tier case complexity system (Basic, Standard, Complex)
- Document attachment and management
- Timeline tracking of case events
- Legal analysis and recommendations
- Labeling and organization features

### Party Management

- Centralized repository of individuals and organizations involved in cases
- Detailed information storage with proper validation:
  - Individuals: Name, CNP (Romanian Personal Numeric Code), contact information
  - Organizations: Company name, CUI (Fiscal ID), Registration Number, contact details
- Secure storage of personal identification information
- Easy attachment/detachment of parties to cases

### Lawyer AI Agent

- Interactive chat interface within each case
- Automated case tier determination based on complexity
- Integration with subscription quota system
- Legal research using Romanian legislation and case law
- Document analysis and understanding
- Strategic guidance and recommendations
- Draft document generation (court filings, notifications, etc.)
- Follow-up and case progression assistance

### Subscription System

- Tiered subscription plans:
  - Individual: €9/month or €86.40/year (20% discount)
  - Organization Basic: €200/month or €1920/year (20% discount)
  - Organization Pro: €500/month or €4800/year (20% discount)
- Case quota system based on complexity tiers:
  - Tier 1 (Basic): Simple cases
  - Tier 2 (Standard): Medium complexity
  - Tier 3 (Complex): High complexity
- Ability to purchase individual cases when quota is exhausted
- Secure payment processing through Stripe
- Voucher system for promotions and discounts

### Document Handling

- Secure storage for user-uploaded attachments
- AI-generated draft documents in PDF format
- Document versioning and history
- Easy download and sharing

## User Flow Example

1. User logs in and creates a new case
2. The Lawyer AI Agent initiates conversation and determines case complexity tier
3. System checks available quota for the determined tier
4. User provides case details, uploads documents, and attaches relevant parties
5. AI Agent analyzes information, performs legal research, and provides guidance
6. Agent generates draft documents based on case requirements
7. User reviews and downloads the draft documents
8. User continues interaction with the Agent for refinements or additional assistance
9. Case is archived upon completion

## Technology Stack

- Frontend: SvelteKit with responsive design
- Backend: Python on Google Cloud Functions
- Database: Firestore (NoSQL)
- Legal Data: Exa API
- AI Orchestration: LangGraph with Gemini and Grok LLMs
- File Storage: Google Cloud Storage
- Authentication: Firebase Authentication
- Payments: Stripe
- Infrastructure: Google Cloud Platform (managed via Terraform)

## Security and Privacy

- Role-based access control for all resources
- Secure handling of personally identifiable information
- Encryption for data at rest and in transit
- Compliance with GDPR and Romanian data protection regulations
- Strict permission checking for all operations

## Supported User Interaction Languages

The Relex legal agent is designed to allow users to interact in a wide range of languages to ensure accessibility. These languages include:
* Romanian
* English
* French
* German
* Italian
* Spanish
* Swedish
* Norwegian
* Danish
* Ukrainian
* Polish
* Hungarian
* Greek
* Turkish
* Hebrew
* Arabic
* Portuguese
* Dutch
* Estonian
* Finnish
* Czech
* Slovak
* Lithuanian
* Icelandic
* Latvian
* Bulgarian
* Serbian
* Macedonian
* Albanian

While user interaction is supported in these languages (requiring translation to/from Romanian internally for core processing), the User Interface (UI) itself will be available in English and Romanian. The core internal processing, system prompts, and communication between AI components (Gemini and Grok) will be conducted exclusively in Romanian.