# Agent Prompts

## Overview

The Relex AI Agent utilizes a single, comprehensive system prompt, defined in `functions/src/agent-config/agent_loop.txt`, to guide its interactions with underlying Large Language Models (LLMs) and orchestrate its behavior. This prompt is critical for ensuring the agent operates effectively in Romanian legal contexts, maintaining consistency, accuracy, and role-appropriate conduct for its dual LLM architecture (Gemini as Paralegal, Grok as Lawyer). The entire prompt is in Romanian.

## Core Prompting Philosophy: Single System Prompt (`agent_loop.txt`)

The agent's core prompting logic is consolidated into `functions/src/agent-config/agent_loop.txt`. This file serves as the central directive for the agent and is meticulously structured. Key elements include:

* **Fundamental Principles**: Emphasizes legal neutrality, information compression, linguistic prudence, and adherence to source data.
* **User Dialogue Language Management**: Defines protocol for detecting user language from a list of supported locales (e.g., `ro, en, fr...` as defined in `SUPPORTED_USER_LANGUAGES` in `functions/src/agent_config.py`) and responding in kind, defaulting to Romanian for unsupported languages. Internal agent language is strictly Romanian.
* **Defined Personas & Essential Responsibilities**: Concise roles for "Gemini (Paralegal Asistent)" and "Grok (Strateg Juridic)", detailing their core traits and key responsibilities.
* **Operational Framework (Skeleton of Thought - SoT)**: The main workflow is structured using an SoT, outlining distinct phases of case processing.
* **Reasoning Techniques Integration**: Implicit and explicit use of Chain of Thought (CoT) for Gemini's detailed analysis/execution and Tree of Thoughts (ToT) for Grok's strategic evaluations.
* **Gemini-Grok Interaction Protocol (PIGG - Compressed)**: Defines a concise, structured format for information exchange.
* **Tool Usage Protocol (PUU - Essentialized)**: Specifies principles and trigger points for tools defined in `functions/src/agent-config/tools.json`.
* **Integrated Risk & Assumption Management**: Directives for continuous identification and neutral communication of relevant risks and assumptions.
* **User Response Formatting**: Guidelines for clear, concise, professional, and legally neutral user-facing responses, including a mandatory disclaimer.
* **Error Handling & Escalation Protocol**: Simplified, direct steps for managing errors.

## Supporting Configuration Files in `functions/src/agent-config/`

* **`agent_loop.txt`**: The primary, consolidated system prompt. All content is in Romanian. (Content iteratively refined by Operator).
* **`modules.txt`**: Contains reusable blocks of Romanian text (e.g., disclaimers like `[DISCLAIMER_LEGAL_NEUTRAL]`). `agent_loop.txt` instructs when to incorporate these modules. (Content iteratively refined by Operator).
* **`tools.json`**: Defines the schema, parameters, and descriptions for all tools available to the agent.

## Loading Mechanism (`agent_config.py`)

The `functions/src/agent_config.py` module loads these runtime configurations. It primarily loads `agent_loop.txt` as the system prompt and `modules.txt` for text snippets. The file `prompt.txt` is obsolete and no longer used.