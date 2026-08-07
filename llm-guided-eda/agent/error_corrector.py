"""Repair message: execution feedback appended after the assistant's previous answer.

Every section is bounded; the feedback (excluding retrieved documentation) stays
within about :data:`FEEDBACK_BUDGET` characters, shrinking the output tail first.
"""
from __future__ import annotations

from agent.error_classifier import Diagnosis, clip, script_log
from agent.prompts import (EXTRA_DOCS_HEADER, FINDINGS_HEADER, OUTPUT_TAIL_HEADER, REPAIR_FOOTER, REPAIR_HEADER,
                           STATE_HEADER, STATUS_EXECUTION, STATUS_SELF_CHECK)
from agent.state_manager import DesignState, diff
from agent.verifier import Verdict
from openroad.executor import ExecutionResult

FEEDBACK_BUDGET = 6000
TAIL_LINES = 40
TAIL_LINE_CHARS = 200
TAIL_CHARS = 2000
MAX_TOOL_ERRORS = 5
MAX_WARNINGS = 8
STATE_CHARS = 1000
FINDINGS_CHARS = 700


def _fence(text: str) -> str:
    longest = run = 0
    for c in text:
        run = run + 1 if c == "`" else 0
        longest = max(longest, run)
    f = "`" * max(3, longest + 1)
    return f"{f}\n{text}\n{f}"


def _tail(output: str, max_lines: int, max_chars: int) -> str:
    lines = [clip(l.rstrip(), TAIL_LINE_CHARS) for l in output.splitlines()][-max_lines:]
    while lines and len("\n".join(lines)) > max_chars:
        lines.pop(0)
    return "\n".join(lines)


def _state_section(result: ExecutionResult, before: DesignState, after: DesignState) -> str:
    if result.script_status == "policy_violation":
        text = "unchanged (the script was rejected before execution)"
    elif not after.available:
        text = after.summary()
    else:
        changes = diff(before, after)
        text = after.summary() + "\nChanges relative to the starting state: " + ("; ".join(changes) or "none")
    return clip(text, STATE_CHARS)


def build_repair_message(*, attempt: int, max_attempts: int, result: ExecutionResult, diagnosis: Diagnosis,
                         verdict: Verdict, before: DesignState, after: DesignState, docs: str | None = None,
                         truncated: bool = False) -> str:
    """Feedback on attempt ``attempt`` asking for a complete corrected script."""
    execution_failed = diagnosis.error_type != "validation_failure"
    head = [REPAIR_HEADER.format(attempt=attempt, max_attempts=max_attempts),
            STATUS_EXECUTION if execution_failed else STATUS_SELF_CHECK,
            f"Error type: {diagnosis.error_type}",
            f"Error: {diagnosis.message}"]
    if diagnosis.failing_line is not None:
        where = f"agent_script.tcl line {diagnosis.failing_line}"
        head.append(f"({where}: {diagnosis.failing_command_text})" if diagnosis.failing_command_text else f"({where})")
    errors = [e for e in diagnosis.tool_errors if e.strip() != diagnosis.message.strip()][:MAX_TOOL_ERRORS]
    if errors:
        head.append("Tool errors:\n" + "\n".join(f"- {clip(e, 240)}" for e in errors))
    if diagnosis.warnings:
        head.append("Warnings:\n" + "\n".join(f"- {clip(w, 160)}" for w in diagnosis.warnings[:MAX_WARNINGS]))
    if truncated:
        head.append("Note: your previous answer was cut off at the output-token limit; keep the answer concise.")

    findings = [r for r in verdict.reasons if not (execution_failed and r.startswith("The script did not run"))]
    rest = [STATE_HEADER, _state_section(result, before, after),
            FINDINGS_HEADER, clip("\n".join(f"- {r}" for r in findings) or "- none beyond the error above",
                                  FINDINGS_CHARS),
            f"Diagnosis: {diagnosis.hint}"]

    if result.script_status == "policy_violation":
        output = "(the script was not executed)"
    else:
        output = script_log(result).output.strip("\n") or "(no output)"
    fixed = len("\n".join(head + rest + [REPAIR_FOOTER])) + len(OUTPUT_TAIL_HEADER) + 20
    tail = _tail(output, TAIL_LINES, max(200, min(TAIL_CHARS, FEEDBACK_BUDGET - fixed)))
    parts = head + [OUTPUT_TAIL_HEADER + "\n" + _fence(tail or "(no output)")] + rest
    if docs:
        parts.append(f"{EXTRA_DOCS_HEADER}\n{docs}")
    parts.append(REPAIR_FOOTER)
    return "\n".join(parts)
