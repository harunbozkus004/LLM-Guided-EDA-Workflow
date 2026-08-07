"""Exact prompt text.

The prompts are identical for every experimental configuration except for the
optional documentation sections (RAG) and the repair messages (execution
feedback). Hints are generic per error type and never mention task-specific facts.
"""
from __future__ import annotations

SYSTEM_PROMPT = "\n".join([
    "You are an expert ASIC physical-design engineer who writes Tcl scripts for the OpenROAD tool.",
    "You receive a physical-design task, a description of the current OpenROAD session and design state, "
    "and possibly reference documentation and feedback from executing a previous script.",
    "Write one complete Tcl script that accomplishes the task when it is sourced in that session.",
    "Rules:",
    "- Use only commands and options that exist in the stated OpenROAD version. Do not invent commands or options.",
    "- The design and libraries are already loaded. Do not reload them unless the task requires it.",
    "- Use relative paths. Write requested files into outputs/ with exactly the requested names.",
    "- Do not use exec, sockets, cd, package, rename, or files outside the run directory.",
    "- Before the script you may state brief assumptions in one or two sentences. "
    "Then return the complete script in a single fenced code block marked tcl.",
    "- Do not claim that the task is complete: the script will be executed and checked.",
])

DOCS_HEADER = ("REFERENCE DOCUMENTATION (retrieved from the documentation of this exact "
               "OpenROAD/OpenSTA version)")
GENERATE_FOOTER = "Write the Tcl script."

REPAIR_HEADER = "EXECUTION RESULT (attempt {attempt} of {max_attempts})"
STATUS_EXECUTION = "FAILED: execution error"
STATUS_SELF_CHECK = "FAILED: self-check"
OUTPUT_TAIL_HEADER = "Output tail (last 40 lines your script printed):"
STATE_HEADER = "Design state after your script (read from the OpenROAD database):"
FINDINGS_HEADER = "Self-check findings:"
EXTRA_DOCS_HEADER = "ADDITIONAL DOCUMENTATION for this error"
REPAIR_FOOTER = ("Your script was run from the original starting state and its partial changes were discarded. "
                 "Return the complete corrected script in a single tcl code block.")

HINTS: dict[str, str] = {
    "invalid_command": "The command does not exist in this OpenROAD version. Use a documented command.",
    "invalid_argument": "An option or argument is not accepted by this version. Check the exact command syntax.",
    "tcl_syntax": "The script is not valid Tcl. Check braces, brackets and quotes.",
    "missing_prerequisite": "A required earlier design step or setting is missing. Check the design state and "
                            "perform the prerequisite steps first.",
    "missing_file": "A referenced file does not exist. Use the files listed in the context.",
    "incorrect_design_context": "The script refers to objects or variables that do not exist in this session. "
                                "Inspect the design to find the correct names.",
    "runtime_failure": "Execution crashed, timed out or exceeded resource limits.",
    "unsafe_command": "The script used a forbidden operation. Remove it.",
    "validation_failure": "The script ran without errors, but the self-check found that the requested result "
                          "is missing.",
    "tool_error": "The tool reported an error. Read the message and fix the cause.",
}


def generation_message(instruction: str, context: str, docs: str | None = None) -> str:
    """First user message: task, design context and (RAG only) retrieved documentation."""
    msg = f"TASK\n{instruction}\n\n{context}"
    if docs is not None:
        msg += f"\n{DOCS_HEADER}\n{docs}\n"
    return msg + f"\n{GENERATE_FOOTER}"
