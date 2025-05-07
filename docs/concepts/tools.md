# Agent Tools

## Overview

The Relex AI Agent uses a variety of tools to interact with the system and external services. These tools enable the agent to perform case management, research, document generation, and other essential functions.

## Runtime Configuration and Implementation

The agent tools system consists of two critical components:

1. **Tool Definitions (Runtime Configuration)**:
   - **Location**: `functions/src/agent-config/tools.json`
   - **Purpose**: This file defines the schema, parameters, and descriptions for all tools available to the LLMs. It uses the OpenAI function calling JSON schema format.
   - **Loading**: The `agent_config.py` module loads these definitions via the `load_tools()` function
   - **Importance**: This is a critical runtime configuration file that must be deployed with the agent

2. **Tool Implementation**:
   - **Location**: `functions/src/agent_tools.py`
   - **Purpose**: This Python module contains the actual implementation of each tool as asynchronous functions
   - **Integration**: When a LLM selects a tool based on the schema in `tools.json`, the corresponding Python function in `agent_tools.py` is invoked

3. **Configuration/Implementation Relationship**:
   - Each tool defined in `tools.json` must have a corresponding implementation in `agent_tools.py`
   - The parameter names and types in `tools.json` must match the function signatures in `agent_tools.py`
   - The `agent_config.py` module provides functions like `get_tool_by_name()` that bridge between the JSON definitions and their Python implementations

## Available Tools

The following sections describe the purpose and general parameters of the key tools. For the complete and most up-to-date tool definitions, refer to the actual `tools.json` file in `functions/src/agent-config/`.

### Case Management Tools

#### `get_case_details`

Retrieves detailed information about a specific case from Firestore.

**Parameters:**
- `case_id` (string): The ID of the case to retrieve

**Returns:**
- A dictionary containing all case details, including basic metadata, parties involved, legal analysis, documents, timeline, notes, and tags

#### `update_case_details`

Updates or adds information to a case in Firestore.

**Parameters:**
- `case_id` (string): The ID of the case to update
- `updates` (object): An object containing fields to update or add to the case document

**Returns:**
- Status information about the update operation

### Research Tools

#### `query_bigquery`

Searches Romanian legal databases for relevant legislation and case law.

**Parameters:**
- `query_string` (string): SQL query to execute on BigQuery
- `table_name` (string): Target table name ('legislatie' or 'jurisprudenta')

**Returns:**
- Results from the legal database matching the query

### Document Generation Tools

#### `generate_draft_pdf`

Creates a legal document in PDF format based on provided content.

**Parameters:**
- `case_id` (string): The ID of the case
- `markdown_content` (string): Markdown content for the document
- `draft_name` (string): Name of the document
- `revision` (integer): Revision number

**Returns:**
- Document ID and access information

### Party Management Tools

#### `get_party_id_by_name`

Resolves a party name to its ID in the system.

**Parameters:**
- `case_id` (string): The ID of the case
- `mentioned_name` (string): Name of the party to look up

**Returns:**
- Party ID and metadata if found

### Quota Management Tools

#### `check_quota`

Checks if the user or organization has sufficient quota for the case.

**Parameters:**
- `user_id` (string): The ID of the user
- `organization_id` (string, optional): The ID of the organization
- `case_tier` (integer): The determined case tier (1, 2, or 3)

**Returns:**
- Quota availability information and subscription status

### Expert Consultation Tools

#### `consult_grok`

Sends a specific legal question to the Grok LLM for expert analysis.

**Parameters:**
- `case_id` (string): The ID of the case
- `context` (object): Relevant case context
- `specific_question` (string): The specific legal question to analyze

**Returns:**
- Detailed legal analysis from Grok

## Error Handling

All tools implement consistent error handling with custom exception classes defined in `agent_tools.py`:

- `QuotaError`: For quota-related issues
- `PaymentError`: For payment processing issues
- `DatabaseError`: For Firestore operation failures
- `GrokError`: For Grok API communication issues
- `PDFGenerationError`: For issues with document generation

Each tool function includes comprehensive try/except blocks that catch and properly handle these exceptions.

## Tool Extension

New tools can be added to the system by:

1. Adding a new tool definition to `functions/src/agent-config/tools.json` using the OpenAI function calling schema format
2. Implementing the corresponding async function in `functions/src/agent_tools.py`
3. Updating any relevant agent nodes in `agent_nodes.py` to utilize the new tool
4. Ensuring the prompt in `prompt.txt` includes appropriate instructions for when and how to use the new tool 