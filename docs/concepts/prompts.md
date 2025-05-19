# Agent Prompts

## Overview

The Relex AI Agent utilizes a single, comprehensive system prompt, defined in `functions/src/agent-config/agent_loop.txt`, to guide its interactions with underlying Large Language Models (LLMs) and orchestrate its behavior. This prompt is critical for ensuring the agent operates effectively in Romanian legal contexts, maintaining consistency, accuracy, and role-appropriate conduct for its dual LLM architecture (Gemini as Paralegal, Grok as Lawyer).

## Core Prompting Philosophy: Single System Prompt (`agent_loop.txt`)

The agent's core prompting logic is consolidated into `agent_loop.txt`. This file serves as the central directive for the agent and is meticulously structured to guide its reasoning and actions. It includes:

* **Defined Personas & Roles**: Specific personas for "Gemini (Paralegal)" and "Grok (Avocat Expert)" are outlined, detailing their traits, primary responsibilities, and behavioral guidelines.
* **Core Mission**: The agent's overarching objective.
* **Operational Guide (Skeleton of Thought - SoT)**: The main workflow is structured using a Skeleton of Thought, outlining distinct phases of case processing (e.g., Initialization, Intent Determination, Complexity/Resource Check, Information Gathering, Grok Consultation, Instruction Execution, Review/Refinement, Response Generation, Finalization).
* **Reasoning Techniques**:
    * **Chain of Thought (CoT)**: Mandated for detailed, step-by-step reasoning within SoT phases by Gemini.
    * **Tree of Thoughts (ToT)**: Utilized by Grok for evaluating multiple legal strategies or complex decision points.
* **Gemini-Grok Interaction Protocol (PIGG)**: Defines the structured format for information exchange between Gemini and Grok, ensuring clarity and efficiency. Gemini provides context summaries and specific questions; Grok provides reasoned answers, strategic plans, and actionable instructions.
* **Tool Usage Protocol (PUU)**: Specifies how and when Gemini should use the tools defined in `functions/src/agent-config/tools.json`.
* **Proactive Risk & Assumption Management**: Instructs both personas to identify and communicate key assumptions and potential risks.
* **Response Formatting Guidelines**: Directives for structuring user-facing responses.
* **Error Handling & Escalation Protocol**: Guidelines for managing errors and escalating issues.
* **Romanian Language**: The entire `agent_loop.txt` is written in Romanian.

## Supporting Configuration Files in `functions/src/agent-config/`

* **`agent_loop.txt`**: The primary, consolidated system prompt (as described above).
* **`modules.txt`**: Contains reusable blocks of Romanian text (e.g., disclaimers, standard greeting/closing phrases, explanations of standard procedures). `agent_loop.txt` instructs the agent on when to incorporate these modules, often referenced by unique keys (e.g., `[DISCLAIMER_GENERAL_ASSISTANT]`).
* **`tools.json`**: Defines the schema, parameters, and descriptions for all tools available to the agent, using the OpenAI function calling JSON schema format.

## Loading Mechanism (`agent_config.py`)

The `functions/src/agent_config.py` module is responsible for loading these runtime configurations:
* It loads `agent_loop.txt` as the main system prompt.
* It parses `modules.txt` into a dictionary of modular text components.
* It loads `tools.json` for tool definitions.
* The `get_system_prompt()` function (or equivalent logic) in `agent_config.py` now primarily returns or constructs the prompt based on `agent_loop.txt`, potentially integrating snippets from `modules.txt` as directed by the main loop logic.

The `prompt.txt` file is no longer used as it has been consolidated into `agent_loop.txt`.

## Prompt Design Principles

1. **Romanian Language Focus**: All prompts are designed to encourage responses in Romanian, the primary working language of the agent.

2. **Dual LLM Collaboration**: Prompts establish and maintain the distinct roles of Gemini (Assistant) and Grok (Reasoner).

3. **Context Management**: Prompts include mechanisms for effectively maintaining and referencing case context.

4. **Legal Domain Specialization**: Prompts are tailored for Romanian legal procedures, terminology, and requirements.

5. **Tool Usage Guidance**: Prompts include instructions for when and how to use available tools.

## Core Prompt Components

The following sections describe the general structure and purpose of prompts stored in the runtime configuration files. For the most up-to-date and complete prompt content, refer to the actual files in `functions/src/agent-config/`.

### System Prompt Structure

The consolidated system prompt in `agent_loop.txt` establishes the agent's identity and capabilities, covering:
- Agent identity and purpose
- Dual LLM collaboration approach with defined personas
- Romanian language requirements
- Tool usage guidelines through the Protocol for Tool Usage (PUU)
- Legal domain specialization
- Structured workflow phases (SoT)
- Error handling protocols

### Role-Specific Definitions

The `agent_loop.txt` file clearly defines the distinct roles for each LLM:

#### Gemini (Paralegal) Role

The Gemini role is defined in specific sections of `agent_loop.txt` and focuses on:
- User interaction and communication
- Tool usage and implementation
- Document drafting and formatting
- Information gathering and organization
- Coordinating with Grok for legal expertise

#### Grok (Lawyer) Role

The Grok role is defined in dedicated sections of `agent_loop.txt` and focuses on:
- Legal analysis and reasoning
- Strategy development
- Validation of Gemini's work
- Identification of information gaps
- Providing expert legal guidance

## Modular Text Components

The `modules.txt` file contains reusable text components that can be incorporated into agent responses:

1. **Component Storage**: Text modules are stored in `modules.txt` with unique identifiers
2. **Reference Format**: Components are referenced using keys like `[DISCLAIMER_GENERAL_ASSISTANT]`
3. **Component Integration**: The agent incorporates these components as directed by `agent_loop.txt`

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