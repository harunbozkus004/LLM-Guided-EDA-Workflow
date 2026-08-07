"""Parsing of OpenROAD/Tcl output and rule-based failure classification.

Failure types (blueprint taxonomy + two refinements):

    invalid_command          unsupported / hallucinated Tcl command
    invalid_argument         wrong flag, wrong # args, bad value
    tcl_syntax               malformed Tcl (unbalanced braces/quotes)
    missing_prerequisite     required design state unavailable
    missing_file             LEF/DEF/Liberty/script path missing
    incorrect_design_context nonexistent objects or variables
    runtime_failure          crash, timeout, resource exhaustion
    unsafe_command           rejected by the safety policy (not executed)
    validation_failure       ran cleanly but the requested result is absent
    tool_error               any other tool-reported error
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MSG_RE = re.compile(r"^\[(ERROR|WARNING|CRITICAL)\s+([A-Z]{2,5})-(\d+)\]\s*(.*)$")
SCRIPT_ERROR_MARK = "HARNESS_SCRIPT_ERROR:"
ERROR_INFO_BEGIN = "HARNESS_ERROR_INFO_BEGIN"
ERROR_INFO_END = "HARNESS_ERROR_INFO_END"
STATUS_MARK = "HARNESS_SCRIPT_STATUS:"
PROBE_ERROR_MARK = "HARNESS_PROBE_ERROR:"
SCRIPT_BEGIN_MARK = "HARNESS_AGENT_SCRIPT_BEGIN"
SCRIPT_END_MARK = "HARNESS_AGENT_SCRIPT_END"

# Ordered (first match wins). Patterns are matched case-insensitively against
# the primary error message.
_RULES: list[tuple[str, re.Pattern]] = [
    ("invalid_command", re.compile(r"invalid command name|unknown command|ambiguous command name")),
    # SWIG argument conversion errors (wrong type passed to an OpenROAD API call)
    ("invalid_argument", re.compile(r"typeerror in method|in method '\w+', argument \d+")),
    ("tcl_syntax", re.compile(
        r"missing close-(brace|bracket)|extra characters after close-(brace|quote)|missing \"|"
        r"unmatched (open|close)|incomplete command|missing \)|syntax error in expression|"
        r"invalid bareword|missing operand|unbalanced")),
    ("missing_file", re.compile(
        r"couldn't open|cannot open|can't open|no such file|unable to open|failed to open|"
        r"file .* (does not exist|not found)|could not open|cannot read file")),
    ("incorrect_design_context", re.compile(
        r"no such variable|can't read \"|no such element|"
        r"(instance|net|pin|port|cell|clock|master|layer|site|object)s? .*(not found|does not exist)|"
        r"(cannot|could not|unable to) find (instance|net|pin|port|cell|clock|master|layer|site)|"
        r"no (instances?|nets?|pins?|ports?|cells?|clocks?) (found|matched|named)|not a valid (layer|site|master)|"
        r"unknown (layer|master|site|cell|instance|net|pin|port)|does not match any|no objects")),
    ("missing_prerequisite", re.compile(
        r"no rows|rows? (not|are not) (found|defined)|not placed|unplaced|no placement|"
        r"(design|instances?|cells?) (is|are) not placed|placement (is )?required|"
        r"no (floorplan|core area|die area)|floorplan (is )?(not|missing)|initialize_floorplan first|"
        r"(run|call|execute) (global_route|global_placement|detailed_placement|clock_tree_synthesis|"
        r"initialize_floorplan|estimate_parasitics|pin_access|link_design)|"
        r"no (global )?rout(e|es|ing)( found| available| guides)?|guides? (not found|missing|are missing)|"
        r"no guides|has not been (run|performed|created)|must (be run|first)|before running|"
        r"no liberty|liberty (is )?(not|missing)|not linked|no (design|block|database) (loaded|found)|"
        r"no clocks? (defined|found)|parasitics (are )?(not|missing)|no tracks|tracks? (not|are not) (defined|found)")),
    ("invalid_argument", re.compile(
        r"is not a known keyword or flag|wrong # args|unknown option|bad option|unknown keyword|"
        r"positional argument|requires (a|an|one|two|zero)?\s*\w*\s*(value|argument)|missing value|"
        r"must be (a|an|positive|between|greater|less|one of|in)|expected (integer|floating-point|boolean|number)|"
        r"is not a (valid|legal|positive)|invalid (value|argument|option|parameter)|out of range|"
        r"not supported|cannot be used with|mutually exclusive|only one of|illegal|not allowed|"
        r"requires? .* (to be|be) (specified|set)|usage:|no value given|bad (value|number)")),
]


@dataclass
class ParsedLog:
    script_error: str | None
    error_info: str | None
    script_status: str
    tool_errors: list[str]
    warnings: list[str]
    probe_error: str | None
    agent_output: str  # stdout produced while the agent script ran


def parse_log(stdout: str) -> ParsedLog:
    lines = stdout.splitlines()
    script_error = None
    error_info_lines: list[str] = []
    in_info = False
    status = "unknown"
    tool_errors: list[str] = []
    warnings: list[str] = []
    probe_error = None
    agent_lines: list[str] = []
    in_agent = False
    for line in lines:
        if line.startswith(SCRIPT_BEGIN_MARK):
            in_agent = True
            continue
        if line.startswith(SCRIPT_END_MARK):
            in_agent = False
            continue
        if line.startswith(ERROR_INFO_BEGIN):
            in_info = True
            continue
        if line.startswith(ERROR_INFO_END):
            in_info = False
            continue
        if in_info:
            error_info_lines.append(line)
            continue
        if line.startswith(SCRIPT_ERROR_MARK):
            script_error = line[len(SCRIPT_ERROR_MARK):].strip()
            continue
        if line.startswith(STATUS_MARK):
            status = line[len(STATUS_MARK):].strip()
            continue
        if line.startswith(PROBE_ERROR_MARK):
            probe_error = line[len(PROBE_ERROR_MARK):].strip()
            continue
        if not in_agent:
            # Messages from the harness preamble/probe (e.g. DRT-0002 printed by the
            # probe's catch-wrapped queries) are not the agent's errors.
            continue
        agent_lines.append(line)
        m = MSG_RE.match(line.strip())
        if m:
            level, tool, num, text = m.groups()
            entry = f"[{level} {tool}-{num}] {text}"
            if level in ("ERROR", "CRITICAL"):
                tool_errors.append(entry)
            else:
                warnings.append(entry)
        elif line.startswith("Error:"):
            tool_errors.append(line.strip())
    return ParsedLog(
        script_error=script_error,
        error_info="\n".join(error_info_lines) or None,
        script_status=status,
        tool_errors=list(dict.fromkeys(tool_errors)),
        warnings=list(dict.fromkeys(warnings)),
        probe_error=probe_error,
        agent_output="\n".join(agent_lines),
    )


def classify_message(message: str) -> str:
    """Map an error message to a failure type using deterministic rules."""
    text = message.lower()
    for name, rx in _RULES:
        if rx.search(text):
            return name
    return "tool_error"


def classify_execution(*, policy_violations: list[str], timed_out: bool, memory_exceeded: bool,
                       exit_code: int | None, parsed: ParsedLog) -> tuple[str | None, str | None]:
    """Return (error_type, primary_error_message) for an execution, or (None, None) if clean."""
    if policy_violations:
        return "unsafe_command", "; ".join(policy_violations)
    if timed_out:
        return "runtime_failure", "execution timed out"
    if memory_exceeded:
        return "runtime_failure", "memory limit exceeded"
    if parsed.script_status == "error" or parsed.script_error:
        msg = parsed.script_error or (parsed.tool_errors[0] if parsed.tool_errors else "unknown error")
        # OpenROAD reports the tool message on its own line; prefer it when the
        # Tcl-level error only says that an error occurred.
        if parsed.tool_errors and not _informative(msg):
            msg = parsed.tool_errors[-1]
        return classify_message(msg + " " + " ".join(parsed.tool_errors[-2:])), msg
    if exit_code not in (0, None) or parsed.script_status not in ("ok",):
        detail = f"OpenROAD exited abnormally (exit code {exit_code}, script status {parsed.script_status})"
        return "runtime_failure", detail
    return None, None


def _informative(msg: str) -> bool:
    stripped = re.sub(r"^Error:\s*\S+,\s*\d+\s*", "", msg).strip()
    return len(stripped) > 12
