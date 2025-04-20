Key Phases & Steps:

Initialization: On new message, load current case_details and case_processing_state. Determine current phase (Tiering or Active Resolution). Recover state if resuming after timeout.
Phase 1: Tier Determination & Payment:
Determine Tier: Gemini analyzes initial user input against definitions (tiers_ro.md).
Check Quota: check_quota tool verifies subscription status.
Request Payment: If no quota, inform user and pause until payment confirmed (via Stripe webhook updating case status).
Transition: Once tier is set and payment/quota confirmed, update case status to active and move to Phase 2. case_details is updated with initial info.
Phase 2: Active Case Resolution (Loop):
Process Input/Plan: Gemini analyzes the latest user message, current case_details, and potentially pending actions. Decides the immediate next step (ask user, research, consult Grok, draft).
Ask User: Gemini formulates and sends clarifying questions.
Query BigQuery: Gemini formulates SQL (based on Grok's needs), calls query_bigquery, processes results, updates case_details, potentially consults Grok on summaries.
Consult Grok: Gemini synthesizes context, asks specific questions, receives guidance, updates case_details.
Generate Draft: Gemini writes Markdown (with placeholders) based on Grok's plan, calls generate_draft_pdf, updates case_details.
Handle Error: Follows defined flow: Retry -> Consult Grok -> Ask User -> Ticket.
Update Context: After most actions, Gemini calls update_case_details to persist changes.
Wait: If no immediate action, or after sending a message, agent waits for next user input or timeout. State saved before timeout.
4. Key Operational Principles
Romanian Language: All LLM interactions and user-facing communication are in Romanian.
Assistant-Reasoner Roles: Gemini executes and interacts, Grok strategizes and guides. Prompts enforce this separation (see prompts.md).
Context is King: case_details in Firestore is the central, evolving source of truth, managed via get/update tools.
Tool Reliance: Agent relies heavily on specialized tools for external actions and data manipulation (see tools.md).
Privacy First: PII is strictly isolated in /parties and only accessed by the authorized generate_draft_pdf tool during placeholder substitution. LLMs never see raw PII.
Error Handling: A defined escalation path ensures resilience.
State Recovery: Mechanisms are in place (case_processing_state) to recover from timeouts during long operations (MVP).
Efficiency: Prompting aims for conciseness to manage latency and cost.
5. Interaction Model (MVP)
Users interact via the case-specific chat interface.
Backend uses standard HTTPS requests with a long timeout (e.g., 5 minutes).
Agent processes potentially multiple internal steps before returning a single response.
Frontend handles potential delays and provides a mechanism (e.g., reload button) to trigger state recovery if a timeout occurs.
Streaming responses (WebSockets) are deferred post-MVP.
This agent represents a significant enhancement to Relex, providing powerful AI-driven assistance for legal case management.

