"""Diagnosis of a failed attempt, used to build the repair prompt.

Failed executions are classified with the executor's rule-based taxonomy
(``openroad.log_parser``) applied to what the agent script itself printed. The
harness's design-state probe runs after the script in the same session and can
print its own ``[ERROR ...]`` lines (e.g. ``DRT-0002 Detailed routing has not
been run yet``); those are excluded so that they are never reported to the agent
as the script's error. A clean run whose self-check failed is diagnosed as
``validation_failure``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent.planner import repair_query
from agent.prompts import HINTS
from agent.verifier import Verdict
from openroad import log_parser
from openroad.executor import ExecutionResult

MAX_MESSAGE_CHARS = 600
MAX_COMMAND_CHARS = 300
_LOCATION_RE = re.compile(r"^Error:\s*\S+,\s*\d+\s*")       # "Error: agent_script.tcl, 12 "
_SCRIPT_LINE_RE = re.compile(r"agent_script\.tcl(?:,| line)\s*(\d+)")
# Kept as classified by the executor: they do not come from a Tcl/tool error message.
_NOT_RECLASSIFIED = {"unsafe_command", "runtime_failure"}


@dataclass
class Diagnosis:
    error_type: str
    message: str
    failing_line: int | None
    failing_command_text: str | None
    hint: str
    retrieval_query: str = ""
    tool_errors: list[str] = field(default_factory=list)   # printed while the agent script ran
    warnings: list[str] = field(default_factory=list)
    executor_error_type: str | None = None


@dataclass
class ScriptLog:
    """Messages printed while the agent script ran (harness and probe output excluded)."""
    script_error: str | None
    errors: list[str]
    warnings: list[str]
    output: str


def script_log(result: ExecutionResult) -> ScriptLog:
    parsed = log_parser.parse_log(result.stdout or "")
    output = parsed.agent_output if result.stdout else (result.agent_output or "")
    errors: list[str] = []
    warnings: list[str] = []
    for line in output.splitlines():
        m = log_parser.MSG_RE.match(line.strip())
        if m:
            level, tool, num, text = m.groups()
            (errors if level in ("ERROR", "CRITICAL") else warnings).append(f"[{level} {tool}-{num}] {text}")
        elif line.startswith("Error:"):
            errors.append(line.strip())
    return ScriptLog(parsed.script_error, list(dict.fromkeys(errors)), list(dict.fromkeys(warnings)), output)


def clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 15].rstrip() + " ...[truncated]"


def _informative(msg: str) -> bool:
    return len(_LOCATION_RE.sub("", msg).strip()) > 12


def _tcl_complete(text: str) -> bool:
    """Approximation of Tcl's ``info complete`` (balanced braces, quotes and brackets)."""
    braces = brackets = 0
    quoted = False
    at_start = True
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            at_start = False
            continue
        if at_start and c == "#" and braces == 0 and not quoted:
            nl = text.find("\n", i)
            i = len(text) if nl < 0 else nl
            continue
        if c == "{" and not quoted:
            braces += 1
        elif c == "}" and not quoted and braces:
            braces -= 1
        elif c == '"' and braces == 0:
            quoted = not quoted
        elif c == "[" and braces == 0:
            brackets += 1
        elif c == "]" and braces == 0 and brackets:
            brackets -= 1
        if c in "\n;" and braces == 0 and not quoted and brackets == 0:
            at_start = True
        elif not c.isspace():
            at_start = False
        i += 1
    return braces == 0 and not quoted and brackets == 0


def command_at_line(script: str, line: int | None) -> str | None:
    """Text of the command that ends on ``line`` (whitespace-collapsed).

    OpenSTA's ``source`` reports the line on which a (possibly multi-line)
    command became complete, so the whole command is reconstructed.
    """
    lines = (script or "").splitlines()
    if line is None or not 1 <= line <= len(lines):
        return None
    buf: list[str] = []
    for i, text in enumerate(lines, 1):
        buf.append(text)
        if not text.endswith("\\") and _tcl_complete("\n".join(buf) + "\n"):
            if i >= line:
                break
            buf = []
    command = " ".join(" ".join(t.rstrip("\\") for t in buf).split())
    return clip(command, MAX_COMMAND_CHARS) or None


def diagnose(result: ExecutionResult, verdict: Verdict, script: str | None = None) -> Diagnosis | None:
    """Diagnosis of a failed attempt (None when the run was clean and the self-check passed)."""
    if result.error_type is None and verdict.ok:
        return None
    log = script_log(result)
    line: int | None = None
    if result.error_type is not None:
        etype, message = result.error_type, result.error_message or ""
        if result.error_type not in _NOT_RECLASSIFIED and (log.script_error or log.errors):
            message = log.script_error or ""
            if log.errors and not _informative(message):
                message = log.errors[-1]
            etype = log_parser.classify_message(message + " " + " ".join(log.errors[-2:]))
            m = _SCRIPT_LINE_RE.search(log.script_error or "")
            line = int(m.group(1)) if m else None
        if line is None and result.error_type != "unsafe_command":
            line = result.failing_line
    else:
        etype = "validation_failure"
        message = " ".join(verdict.reasons)
    message = clip(_LOCATION_RE.sub("", message).strip(), MAX_MESSAGE_CHARS)
    diag = Diagnosis(error_type=etype, message=message, failing_line=line,
                     failing_command_text=command_at_line(script or "", line),
                     hint=HINTS.get(etype, HINTS["tool_error"]), tool_errors=log.errors, warnings=log.warnings,
                     executor_error_type=result.error_type)
    diag.retrieval_query = repair_query(diag)
    return diag
