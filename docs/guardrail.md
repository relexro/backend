# LLM Guardrails Framework for Relex Backend Development & Debugging (v2 - Script-Based Ops & Strict Debugging)

## Purpose

This framework provides **absolute, non-negotiable guardrails** for any LLM or AI agent contributing to the Relex backend project (`backend_folder`). Its sole purpose is to enforce disciplined, precise, and effective development and debugging, specifically counteracting common LLM failure modes:
- **Hallucination:** Inventing code, files, APIs, or logic not grounded in project reality.
- **File Proliferation / Incorrect Modification:** Creating unnecessary new files or modifying the wrong files instead of performing targeted fixes in the correct location.
- **Debugging Loops / Superficial Fixes:** Mindlessly repeating failed fixes, creating mocks/workarounds instead of addressing the root cause directly.
- **Context Ignorance:** Failing to utilize provided error messages, logs, and project documentation effectively.
- **Improper Infrastructure Management:** Using `terraform` commands directly instead of designated scripts.

This framework mandates a first-principles, evidence-based approach. **Fix the source. No workarounds. No mocks. No direct `terraform` commands for standard operations. No excuses.**

## Core Principles

- **Grounding & Precision**: Every action **must** be justified by specific evidence from `docs/`, existing code (`functions/src/`, `terraform/`), error messages, or explicit instructions. Follow specifications *exactly*.
- **Targeted In-Place Modification**: Identify and modify the **correct, existing** file and function/resource. **Fix code directly at the source of the error.** Do not create new files or modify unrelated code as a workaround. Maintain project structure (`functions.md`, `architecture.md`).
- **Root Cause Analysis**: Debugging **starts** with analyzing the error message, relevant code, and logs (`debug.sh`). Determine the *fundamental* cause.
- **Systematic, Direct Debugging**: Follow a defined, iterative debugging process focused on fixing the root cause in the original code. If a fix fails, **change the analysis and approach**, do not repeat blindly or create mocks.
- **Script-Based Infrastructure Management**: Use designated shell scripts (`deploy.sh`, `destroy.sh`, etc.) for all standard infrastructure operations. Direct `terraform` use is strictly limited to specific, justified state management tasks and must be non-interactive.
- **Accountability & Verification**: Log actions and justifications. Verify changes against requirements, schemas (`data_models.md`, `openapi_spec.yaml`), and through testing using designated scripts (`debug.sh`).

## Guardrails: What to Do (Mandatory Actions)

### 1. Grounding and Planning
- **Do** **always** consult relevant `docs/` files, the specific code file (`.py`, `.tf`), and any provided error messages *before* writing or modifying *any* code or configuration.
- **Do** explicitly state the file(s) and function(s)/resource(s) targeted for modification based on the requirement and existing structure.
- **Do** cross-reference function signatures, API schemas (`openapi_spec.yaml`), tool definitions (`agent-config/tools.json`), and data models (`docs/data_models.md`) before implementing interactions.

### 2. Code Modification and File Management
- **Do** modify **existing** files *at the precise location* indicated by requirements or error analysis. Locate the correct module/function based on `docs/functions.md` and the existing codebase structure.
- **Do** justify the creation of any **new** file by explaining why existing files are unsuitable and how the new file fits the established architecture (`docs/architecture.md`). This requires explicit approval or instruction.
- **Do** ensure all code modifications adhere to project standards (Python typing, docstrings, Terraform formatting, structured logging).
- **Do** update dependencies (`requirements.txt`) methodically with pinned versions (`==X.Y.Z`) when necessary.

### 3. Infrastructure Management (Scripts Only)
- **Do** use the provided shell scripts in the `terraform/` directory for **all** standard infrastructure operations:
    - Deployment: `./deploy.sh` (Assumes non-interactive or handles prompts internally).
    - Destruction: `./destroy.sh` (Assumes non-interactive or handles prompts internally).
    - Debugging/Logs: `./debug.sh` (Used to retrieve logs and status).
    - State Cleaning (Use with EXTREME caution, only if instructed): `./clean_functions_state.sh`, `./force_delete_functions.sh`.
- **Do** only use direct `terraform` commands *if explicitly required* for complex state manipulation (e.g., unlocking a stuck state) and **only** with non-interactive flags like `-force` (e.g., `terraform state unlock -force <LOCK_ID>`). General `plan` or `apply` via direct `terraform` commands is forbidden.

### 4. Debugging and Error Handling (Strictly In-Place)
- **Do** start debugging by **precisely analyzing** the full error message and traceback.
- **Do** use `./debug.sh` or specific `gcloud` commands (as per `README.md`) to gather logs and context.
- **Do** **locate the exact line(s)** of code referenced in the traceback within the **correct, original file**.
- **Do** cross-reference the failing code with relevant documentation (`docs/`, function docstrings, tool definitions) to understand intended behavior.
- **Do** formulate a **specific hypothesis** about the **root cause** based on the analysis.
- **Do** implement a **targeted fix addressing the root cause directly within the original file and function**.
- **Do** verify the fix by rerunning the operation or using `./debug.sh`. Check logs for success and absence of the original error.
- **Do** **explicitly change the hypothesis and approach** if a fix fails. State the *new* analysis and the *different* proposed solution targeting the original code. Do not introduce workarounds elsewhere.

### 5. Verification and Validation
- **Do** verify successful deployments by checking function status via `./debug.sh` or GCP console (if accessible) and reviewing logs.
- **Do** validate Firestore data structures against `docs/data_models.md` after modifications that affect data.
- **Do** test API endpoints using tools like `curl` or Postman against the deployed function, verifying against `openapi_spec.yaml`.

## Guardrails: What **Not** to Do (Prohibited Actions)

### 1. Hallucination and Invention
- **Do not** invent function names, parameters, class attributes, Terraform resource types, or file paths. Verify against existing code and documentation.
- **Do not** assume the existence or behavior of any code, API, or resource not explicitly defined in the project.

### 2. File, Code Structure, and Workaround Violations
- **Do not** create a new file if the required functionality or fix belongs in an existing module.
- **Do not** create temporary files or mock functions/classes *solely for debugging purposes*. Debug and fix the issue in the actual, original code.
- **Do not** modify code *outside* the identified error source file/function as a workaround. Address the root cause directly.
- **Do not** comment out failing code as a "fix". Identify and correct the underlying problem.
- **Do not** duplicate functionality. Modify or reuse existing code.

### 3. Ineffective Debugging & Process Violations
- **Do not** attempt a fix without first analyzing the full error message and relevant code in its original file.
- **Do not** repeatedly try the exact same failed solution. **Analyze why it failed and change the approach.**
- **Do not** apply generic fixes without understanding the specific error context within the project code.
- **Do not** ignore error messages or logs; analyze them for root cause clues.
- **Do not** run `terraform plan`, `terraform apply`, or `terraform destroy` directly. Use the designated `.sh` scripts.
- **Do not** run *any* script or permitted `terraform` command interactively; ensure non-interactive execution (e.g., using `-y` if needed by a script, or `-force` for commands like `unlock`).

### 4. Context Ignorance
- **Do not** disregard provided error messages, logs, or specific instructions.
- **Do not** modify code without first reading the relevant function/module documentation or comments in the original file.

## Strict Debugging Protocol (LLM Execution Flow - v2)

1.  **ERROR DETECTED**: Halt execution. Capture the **complete** error message, traceback, and the operation being attempted.
2.  **ANALYZE**:
    * Parse the error message: Identify error type and specific details.
    * Examine the traceback: Pinpoint the **exact original file(s) and line number(s)**.
    * **Retrieve Code**: Fetch the content of the identified **original file(s)**.
    * **Gather Logs**: Execute `./debug.sh` or relevant `gcloud` log commands to get runtime context.
    * **Consult Context**: Review relevant `docs/`, function docstrings, and specifications related to the failing code section *in the original file*.
    * **Formulate Hypothesis**: Based *only* on the error, traceback, logs, and code context, state a specific, verifiable hypothesis about the **root cause** within the original code.
3.  **PLAN FIX**: Propose a **targeted code modification** within the **original file(s)** and function(s) to address the *specific hypothesized root cause*. No mocks, no workarounds in other files.
4.  **ATTEMPT FIX**: Apply the planned modification **directly to the original file(s)**.
5.  **VERIFY**:
    * Rerun the operation that caused the error.
    * Check application/function status and logs using `./debug.sh`.
    * Confirm the original error is gone *and* no new errors related to the fix have appeared. Ensure the fix addresses the *root cause*, not just a symptom.
6.  **EVALUATE**:
    * **Success?** -> Proceed. Log the successful fix and justification.
    * **Failure?** -> **STOP**. Go back to Step 1 with the *new* error message/traceback/log output. **CRITICAL: DO NOT RE-APPLY THE SAME FAILED FIX OR CREATE WORKAROUNDS.** Formulate a *new hypothesis* and *different approach* targeting the root cause in the original code, based on the *new* evidence. If stuck after 2-3 distinct, analyzed attempts targeting the original code, explicitly state the failed hypotheses and request external guidance.

## Conclusion

This framework enforces extreme discipline, focusing on direct, in-place fixes and script-based infrastructure management. It combats common LLM failure modes by mandating root cause analysis, forbidding workarounds and mocks, and restricting interaction with Terraform to approved scripts or specific, non-interactive commands. Adherence is mandatory for stable and maintainable development.