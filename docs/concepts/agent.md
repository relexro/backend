# Relex AI Agent

## Overview

The Relex AI Agent is an advanced legal assistant designed to help users with Romanian legal cases within the Relex platform. It operates through a sophisticated LangGraph workflow system, leveraging multiple specialized Large Language Models (LLMs) to provide comprehensive legal services.

## Core Architecture

The agent implementation follows a clean separation of concerns across several layers:

1. **HTTP Layer (`main.py`)**
   - Handles HTTP requests and authentication
   - Delegates to the agent handler function

2. **Agent Handler (`agent.py::handle_agent_request`)**
   - Parses request data
   - Extracts case ID and user message
   - Uses authenticated user information (user_id, user_email) from the request
   - Performs explicit authorization check to ensure the user has read access to the requested case
   - Returns appropriate error responses (403, 404) if authorization fails
   - Delegates to the Agent class only if authorization succeeds

3. **Agent Core (`agent.py::Agent`)**
   - Manages agent state
   - Executes the agent workflow graph
   - Interacts with Firestore for persistence
   - Returns structured responses

4. **Agent Graph (`agent_orchestrator.py`, `agent_nodes.py`)**
   - Defines the agent's workflow as a LangGraph state machine
   - Implements specialized nodes for different agent tasks

5. **Configuration Management (`agent_config.py`)**
   - Loads runtime configurations from the `functions/src/agent-config/` directory
   - Parses and processes prompt templates, tool definitions, and other configuration files
   - Provides functions to access and assemble prompts and tool definitions

## Runtime Configuration

The agent relies on several critical runtime configuration files stored in the `functions/src/agent-config/` directory:

1. **`prompt.txt`**
   - Contains system prompts and templates for different LLM interactions
   - Parsed into sections by `agent_config.py::load_prompts()`

2. **`modules.txt`**
   - Contains modular components that can be assembled into complete prompts
   - Parsed by `agent_config.py::load_modules()`

3. **`tools.json`**
   - Defines the schema, parameters, and descriptions for all available tools
   - Uses OpenAI function calling JSON schema format
   - Loaded by `agent_config.py::load_tools()`

4. **`agent_loop.txt`**
   - Describes the agent's operational flow
   - Loaded by `agent_config.py::load_agent_loop()`

These configuration files are critical for the agent's operation and must be deployed with the functions code.

## LLM Collaboration

The agent operates using two core LLMs with distinct roles:

- **Gemini (Assistant)**: Handles user interaction, data gathering, document analysis, tool usage, and drafting based on instructions.
- **Grok (Reasoner)**: Provides expert legal reasoning, strategic guidance, validation, and planning.

This dual-LLM approach enables:
- Task specialization based on each model's strengths
- Critical validation and verification of legal reasoning
- Enhanced reliability through cross-checking

## Language and Localization

The agent's working language is **Romanian**. All thinking, user communication, and internal LLM communication (Gemini <-> Grok) is conducted in Romanian. The system ensures all generated Markdown and PDFs properly support Romanian characters (UTF-8).

## State Management

The agent maintains two primary state objects in Firestore:

1. **`case_details`**: Stores persistent case information, including:
   - Case metadata (title, description, creation date)
   - Parties involved
   - Legal analysis
   - Research findings
   - Generated documents
   - Timeline of events

2. **`case_processing_state`**: Stores the agent's internal workflow state, including:
   - Current phase and step
   - Conversation history
   - In-progress drafts
   - Tool usage history
   - Timeout management

The `update_case_details` and `get_case_details` tools provide access to these state objects.

## Agent Workflow

The agent operates in an iterative loop with distinct phases:

### Phase 1: Tier Determination & Payment

1. **Greet User & Request Initial Description**
2. **Analyze Description**: Understand the user's situation to determine the case complexity tier (1, 2, or 3) using internal definitions. Uses Gemini for this.
3. **Check Quota**: Use the `check_quota` tool to verify if the user/organization has quota for the determined tier.
4. **Handle Payment (if needed)**: If quota is insufficient, notify the user and pause interaction until payment is confirmed via backend updates.
5. **Update Case Details**: Persist the determined tier and payment status using `update_case_details`.

### Phase 2: Active Case Resolution (Iterative Loop)

6. **Analyze Events/User Input**: Understand the latest user messages and the current state stored in `case_details` (fetched via `get_case_details`). Uses Gemini.
7. **Consult Reasoner (Grok)**: Present synthesized context from `case_details` to Grok. Ask specific questions for guidance on information needs, legal strategy, research direction, or draft planning.
8. **Select Action/Tool**: Based on user input and Grok's guidance, choose the next action:
   - `get_case_details`: To refresh context
   - `update_case_details`: To save progress/findings
   - `query_bigquery`: To research legislation/jurisprudence 
   - `get_party_id_by_name`: To resolve party references for drafts
   - `generate_draft_pdf`: To create and store official documents
   - Ask User: Formulate clarifying questions
9. **Wait for Execution**: Wait for tool execution or LLM response.
10. **Process Results & Update Context**: Process the results/response, and update the central `case_details` using `update_case_details`.
11. **Iterate**: Repeat steps 6-10 until Grok indicates sufficient information for a plan/draft or the case objective is met.
12. **Submit Results**: When drafts are generated, notify the user. Provide final summaries or indicate completion.
13. **Handle Errors**: Follow the defined error handling protocol (Retry -> Grok -> User -> Ticket).
14. **Enter Standby**: If no immediate action is needed, wait for user input. Save state via `case_processing_state` if approaching timeout.

## LangGraph Implementation

The agent uses LangGraph, a framework for building LLM-powered applications based on state machines. The implementation consists of:

1. **Graph Definition**: Defined in `agent_orchestrator.py`, the graph establishes nodes and their connections.

2. **Node Implementation**: Individual nodes in `agent_nodes.py` and `llm_nodes.py` implement specific functionalities:
   - LLM interaction nodes (Gemini, Grok)
   - Tool execution nodes
   - Conditional routing nodes
   - State management nodes

3. **State Schema**: Defined in `agent_state.py`, specifying the structure of the state object passed between nodes.

4. **Graph Execution**: Managed by `agent.py`, which handles graph instantiation, state initialization, and execution.

5. **Configuration Loading**: Managed by `agent_config.py`, which loads runtime configurations from `agent-config/` and makes them available to the nodes.

## Tools and Integration

The agent integrates with external systems through tools that are:

1. **Defined** in `functions/src/agent-config/tools.json` using the OpenAI function calling schema format
2. **Implemented** as asynchronous functions in `functions/src/agent_tools.py`
3. **Loaded** at runtime by `agent_config.py::load_tools()`
4. **Executed** by specialized nodes in the LangGraph workflow

Key tools include case management functions, legal research capabilities, document generation, and quota verification.

## Error Handling and Recovery

The agent implements a robust error handling strategy:

1. **Node-level Error Handling**: Each node has built-in error handling to catch and process exceptions.

2. **Retry Mechanism**: For transient errors, nodes can automatically retry operations with exponential backoff.

3. **Graceful Degradation**: If a tool or LLM call fails, the agent can fall back to alternative approaches.

4. **User Communication**: The agent transparently communicates errors to users when necessary.

5. **State Preservation**: Critical state is preserved in Firestore to ensure recovery after interruptions.

## Privacy and Security Considerations

1. **Data Minimization**: The agent is designed to only capture and process information necessary for the legal case.

2. **PII Handling**: Personal Identifiable Information is properly secured and only used within the appropriate context.

3. **Access Control**: The agent enforces strict authorization checks to ensure users can only access their own cases or cases they have been granted access to.

4. **LLM Prompt Security**: Prompts are carefully designed to prevent unauthorized access to data or system features.

5. **Compliance**: The system is designed to comply with GDPR and Romanian data protection regulations.

## Future Enhancements

1. **Knowledge Distillation**: Implementing methods to reuse insights from past cases for similar legal scenarios.

2. **Enhanced Legal Research**: Expanding the capabilities of the `query_bigquery` tool to provide more targeted legal research.

3. **Multi-language Support**: Extending beyond Romanian to support additional languages.

4. **Advanced Document Analysis**: Implementing more sophisticated document parsing and understanding capabilities. 