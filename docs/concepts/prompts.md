# Agent Prompts

## Overview

The Relex AI Agent uses carefully designed prompts to interact with its underlying Large Language Models (LLMs). These prompts are critical for ensuring the agent operates effectively in Romanian legal contexts while maintaining consistency, accuracy, and appropriate behavior.

## Runtime Configuration

The agent's prompts are defined in external configuration files loaded at runtime by the `agent_config.py` module:

1. **Configuration Files Location**: All prompt files are stored in the `functions/src/agent-config/` directory, which is a critical runtime directory that must be deployed with the agent.

2. **Primary Configuration Files**:
   - `prompt.txt`: Contains the core system prompts and templates used by different LLMs
   - `modules.txt`: Contains modular components that can be assembled into the final prompts
   - `agent_loop.txt`: Describes the agent's operational flow

3. **Loading Mechanism**: The `agent_config.py` module contains specialized functions to load these files:
   - `load_prompts()`: Parses `prompt.txt` into a dictionary of named prompt sections
   - `load_modules()`: Parses `modules.txt` into a dictionary of modular components
   - `load_agent_loop()`: Loads the agent loop description
   - `get_system_prompt()`: Assembles a complete system prompt using both prompts and modules

4. **Dynamic Assembly**: The `get_system_prompt()` function can assemble different types of prompts based on the requested `prompt_type` parameter, enhancing reusability.

## Prompt Design Principles

1. **Romanian Language Focus**: All prompts are designed to encourage responses in Romanian, the primary working language of the agent.

2. **Dual LLM Collaboration**: Prompts establish and maintain the distinct roles of Gemini (Assistant) and Grok (Reasoner).

3. **Context Management**: Prompts include mechanisms for effectively maintaining and referencing case context.

4. **Legal Domain Specialization**: Prompts are tailored for Romanian legal procedures, terminology, and requirements.

5. **Tool Usage Guidance**: Prompts include instructions for when and how to use available tools.

## Core Prompt Components

The following sections describe the general structure and purpose of prompts stored in the runtime configuration files. For the most up-to-date and complete prompt content, refer to the actual files in `functions/src/agent-config/`.

### System Prompt

The core system prompt establishes the agent's identity and capabilities. This is loaded from sections of `prompt.txt` and enhanced with content from `modules.txt` via the `get_system_prompt()` function in `agent_config.py`.

The system prompt covers:
- Agent identity and purpose
- Dual LLM collaboration approach
- Romanian language requirements
- Tool usage guidelines
- Legal domain specialization

### Role-Specific Prompts

The configuration files define separate prompts for each LLM role:

#### Gemini (Assistant) Role

The Gemini role is defined in specific sections of the prompt files and focuses on:
- User interaction and communication
- Tool usage and implementation
- Document drafting and formatting
- Information gathering and organization

#### Grok (Reasoner) Role

The Grok role is defined in dedicated sections and focuses on:
- Legal analysis and reasoning
- Strategy development
- Validation of the Assistant's work
- Identification of information gaps

## Prompt Templates and Placeholders

The runtime configuration files include templates with placeholders that are populated dynamically during agent operation:

1. **Template Storage**: Templates are stored in specific sections of `prompt.txt`
2. **Placeholder Format**: Templates use `{{placeholder}}` syntax for dynamic content
3. **Template Processing**: Templates are processed at runtime with case-specific data

## Implementation Details

The prompt system integration with the agent workflow:

1. **Configuration Loading**: `agent_config.py` loads all prompt files at module initialization
2. **Prompt Retrieval**: Agent components call `get_system_prompt()` or other retrieval functions to get the appropriate prompts
3. **LLM Integration**: The `llm_nodes.py` module applies prompts when calling LLMs
4. **Dynamic Content**: The `agent_nodes.py` module handles inserting dynamic content into prompt templates

## Prompt Optimization

The prompts are continuously refined based on:

1. **Effectiveness Analysis**: Reviewing agent performance to identify prompt weaknesses
2. **Legal Accuracy**: Ensuring prompts lead to legally correct and precise responses
3. **Efficiency**: Optimizing prompts to reduce token usage and response time
4. **User Experience**: Adjusting prompts to improve clarity and helpfulness of responses 