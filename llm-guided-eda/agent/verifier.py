"""The agent's own self-check after each execution.

It NEVER uses the benchmark validators or task parameters. A verdict combines:

  (a) the execution was clean (no Tcl/tool error, timeout or policy rejection);
  (b) every ``outputs/<file>`` named in the instruction exists and is non-empty;
  (c) operations the instruction asks to PERFORM are visible in the design state
      read back from the database -- only when the starting state did not
      already satisfy them.

The intent vocabulary in (c) is generic physical-design language fixed a priori
(it is not tuned on the benchmark tasks). Precision matters more than recall: a
false alarm makes the agent rewrite a script that may already be correct, so an
operation counts as requested only when an imperative "perform" verb governs the
term (``run global placement``, ``insert tap cells``, ``legalize the placement``).
Reporting/inspection requests, negations (``do not run ...``) and phrases such as
``report timing after global routing`` never create expectations.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent.state_manager import DesignState
from openroad.executor import ExecutionResult

PERFORM_VERBS = {
    "run", "rerun", "re-run", "perform", "insert", "reinsert", "re-insert", "build", "rebuild", "create", "recreate",
    "place", "re-place", "route", "reroute", "re-route", "synthesize", "synthesise", "legalize", "legalise",
    "execute", "complete", "add", "generate", "regenerate", "initialize", "initialise", "apply", "construct",
    "finish", "implement", "define", "redo",
    # gerunds ("after running global placement, ..."; "without running ..." is a negation)
    "running", "rerunning", "performing", "inserting", "building", "creating", "placing", "routing", "synthesizing",
    "synthesising", "legalizing", "legalising", "executing", "completing", "adding", "generating", "initializing",
    "initialising", "applying", "constructing", "finishing", "implementing", "defining",
}
TWO_WORD_VERBS = {("carry", "out"), ("set", "up"), ("carrying", "out"), ("setting", "up")}
# Verbs that make the clause a report/inspection request: the term is their object, not an operation.
INSPECT_VERBS = {
    "report", "reports", "reporting", "check", "checks", "checking", "print", "write", "writes", "writing", "read",
    "show", "display", "list", "count", "measure", "compare", "analyze", "analyse", "inspect", "query", "save",
    "dump", "extract", "get", "find", "compute", "calculate", "evaluate", "verify", "explain", "describe",
    "summarize", "summarise", "estimate", "plot", "examine", "determine", "identify", "output", "export",
    "record", "log", "remove", "delete", "undo", "keep", "preserve",
}
# Words between a verb and the term that detach the term from the verb.
BLOCKERS = {
    "after", "before", "following", "from", "of", "on", "in", "into", "for", "during", "using", "with",
    "without", "that", "which", "whether", "if", "when", "than", "once", "until", "via", "by", "per", "except",
    "excluding", "but", "prior", "since", "while", "where", "whose", "as", "instead", "rather", "other",
} | INSPECT_VERBS
NEGATIONS = {"not", "don't", "dont", "do't", "never", "without", "no", "avoid", "skip", "nor", "shouldn't",
             "mustn't", "cannot", "can't", "neither", "instead", "rather"}
DETERMINERS = {"the", "a", "an", "this", "that", "these", "those", "its", "their", "our", "your", "his", "her",
               "each", "every", "any", "some", "final", "previous", "initial", "existing", "current", "same"}
# A term followed by one of these nouns is a modifier ("global placement report"), not the operation.
_MODIFIED = (r"(?![\s_-]+(?:report|reports|summary|density|statistics|stats|results?|map|metrics|quality|"
             r"congestion|overflow|log|file|data|options?|parameters?|settings?|status|info|information|rows?|"
             r"blockages?|sites?|padding|grid|legality|region|regions|utilization|area|constraints?|keepouts?|"
             r"halos?|time|runtime|step|stage|command|flow|script|engine|iterations?|wirelength|hpwl|checks?|"
             r"violations?|errors?|warnings?|skew|latency|depth|analysis|drop|pitch|layers?|nets?|wires?|wiring|"
             r"routing)\b)")
_PASSIVE = re.compile(
    r"^\s+(?:[\w-]+\s+){0,2}?(?:must|should|needs?\s+to|has\s+to|have\s+to|is\s+to|are\s+to)\s+be\s+(?:re-?)?"
    r"(?:run|performed|built|created|inserted|placed|routed|synthesi[sz]ed|legali[sz]ed|done|completed|generated|"
    r"added|initiali[sz]ed|defined|executed|applied|constructed)\b", re.I)
_OUTPUT_RE = re.compile(r"(?<![\w/.-])outputs/[A-Za-z0-9_.\-/]*[A-Za-z0-9_\-]")


@dataclass(frozen=True)
class Intent:
    flag: str                    # DesignState flag expected after the script
    action: str                  # phrase used in self-check findings
    terms: tuple[str, ...]       # noun phrases that need a governing perform verb
    imperatives: tuple[str, ...] = ()  # phrases that contain their own imperative verb


_PINS = r"(?:all\s+(?:of\s+)?)?(?:the\s+)?(?:top[\s-]level\s+)?(?:IO|I/O|io|input/output|boundary)?\s*(?:pins|ports)\b"
INTENTS: list[Intent] = [
    Intent("floorplan_initialized", "initialize the floorplan",
           (r"\bfloorplan(?:ning)?(?:[\s_-]+initiali[sz]ation)?\b", r"\binitiali[sz]e_floorplan\b"),
           (r"\binitiali[sz]e\s+(?:the\s+|a\s+)?(?:new\s+)?floorplan\b",)),
    Intent("tracks_defined", "create the routing tracks",
           (r"\b(?:routing\s+)?tracks?\b", r"\bmake_tracks\b")),
    Intent("io_pins_placed", "place the IO pins",
           (r"\b(?:IO|I/O|io)?[\s_-]*pin[\s_-]+placement\b", r"\bplace_pins?\b"),
           (r"\bplace\s+" + _PINS,)),
    Intent("tapcells_inserted", "insert tap cells",
           (r"\b(?:well[\s-]?)?tap[\s_-]*cells?\b", r"\btapcells?\b", r"\bwell[\s-]?taps?\b")),
    Intent("power_grid_built", "build the power grid",
           (r"\bpower[\s_-]+(?:grid|distribution[\s_-]+network|network|mesh|straps?|rings?)\b", r"\b(?-i:PDN)\b",
            r"\bpdngen\b", r"\bpower\s+and\s+ground\s+(?:grid|network|mesh|straps|rings)\b")),
    Intent("cells_placed", "place the standard cells",
           (r"\bglobal[\s_-]+plac(?:e|er|ement|ing)\b", r"\b(?:standard[\s-]+)?cell[\s_-]+placement\b"),
           (r"\bplace\s+(?:all\s+(?:of\s+)?)?(?:the\s+)?(?:standard[\s-]+|logic\s+|remaining\s+|unplaced\s+)?"
            r"(?:cells|instances|design|netlist)\b(?!['’]s)", r"\bglobally\s+place\b")),
    Intent("placement_legal", "legalize the placement",
           (r"\bdetail(?:ed)?[\s_-]+placement\b", r"\blegali[sz]ation\b"),
           (r"\blegali[sz]e\b",)),
    Intent("cts_completed", "synthesize the clock tree",
           (r"\bclock[\s_-]+tree(?:s|[\s_-]+synthesis)?\b", r"\b(?-i:CTS)\b"),
           (r"\bsynthesi[sz]e\s+(?:the\s+|a\s+)?clock\b",)),
    Intent("global_routing_completed", "run global routing",
           (r"\bglobal(?:ly)?[\s_-]+rout(?:e|es|ing)\b",),
           (r"\bglobally\s+route\b",)),
    Intent("detailed_routing_completed", "run detailed routing",
           (r"\bdetail(?:ed)?[\s_-]+rout(?:e|es|ing)\b",),
           (r"\bdetail(?:ed)?[\s-]+route\s+(?:the|all)\b",)),
    Intent("fillers_inserted", "insert filler cells",
           (r"\bfill(?:er)?[\s_-]*cells?\b", r"\bfillers\b", r"\bfiller[\s_-]+(?:placement|insertion)\b")),
]
_TERM_RES = {i.flag: [re.compile(t + _MODIFIED, re.I) for t in i.terms] for i in INTENTS}
_IMP_RES = {i.flag: [re.compile(t, re.I) for t in i.imperatives] for i in INTENTS}
_WORD_RE = re.compile(r"[A-Za-z][\w'’/-]*")


@dataclass
class Verdict:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    execution_clean: bool = True
    expectations: list[str] = field(default_factory=list)  # state flags checked in (c)


# ------------------------------------------------------------------ intents
def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?;:])\s+|\n+", text) if s.strip()]


def _negated(words: list[str], i: int) -> bool:
    return any(w.lower() in NEGATIONS for w in words[max(0, i - 3):i])


def _verb_at(words: list[str], i: int) -> int | None:
    """Index of the first word of a perform verb ending at position i, if any."""
    w = words[i].lower()
    if i > 0 and (words[i - 1].lower(), w) in TWO_WORD_VERBS:
        start = i - 1
    elif w in PERFORM_VERBS:
        start = i
    else:
        return None
    if start > 0 and words[start - 1].lower() in DETERMINERS:
        return None  # "the complete floorplan", "the final route": a noun phrase, not an imperative
    return start


def _governed(prefix: str) -> bool:
    """Whether the words right before a term contain a perform verb that governs it."""
    words = _WORD_RE.findall(prefix)[-7:]
    for i in range(len(words) - 1, -1, -1):
        start = _verb_at(words, i)
        if start is not None:
            return not _negated(words, start)
        if words[i].lower() in BLOCKERS:
            return False
    return False


def requested_operations(instruction: str) -> list[str]:
    """State flags of the operations the instruction asks to perform."""
    found: list[str] = []
    for sentence in _sentences(instruction):
        for intent in INTENTS:
            if intent.flag in found:
                continue
            hit = False
            for rx in _IMP_RES[intent.flag]:
                for m in rx.finditer(sentence):
                    words = _WORD_RE.findall(sentence[:m.start()])
                    prev_det = bool(words) and words[-1].lower() in DETERMINERS
                    if not prev_det and not _negated(words, len(words)):
                        hit = True
                        break
                if hit:
                    break
            if not hit:
                for rx in _TERM_RES[intent.flag]:
                    for m in rx.finditer(sentence):
                        if _governed(sentence[:m.start()]) or _PASSIVE.match(sentence[m.end():]):
                            hit = True
                            break
                    if hit:
                        break
            if hit:
                found.append(intent.flag)
    return found


def requested_outputs(instruction: str) -> list[str]:
    """Every ``outputs/<file>`` path named in the instruction (in order, unique)."""
    return list(dict.fromkeys(m.group(0) for m in _OUTPUT_RE.finditer(instruction)))


# ------------------------------------------------------------------ verdict
def _state_problem(flag: str, s: DesignState) -> str:
    return {
        "floorplan_initialized": "the floorplan is not initialized (no placement rows or no core area)",
        "tracks_defined": "no routing tracks are defined",
        "io_pins_placed": f"not all IO pins are placed ({s.io_pins_placed_count}/{s.io_pin_count})",
        "tapcells_inserted": "the design contains no tap cells",
        "power_grid_built": "no power-grid wiring exists on the power/ground nets",
        "cells_placed": f"not all standard cells are placed ({s.logic_placed_count}/{s.logic_inst_count})",
        "placement_legal": "the placement is not legal (check_placement fails or cells are unplaced)",
        "cts_completed": "no clock tree exists (register clock pins are still driven directly by the clock port)",
        "global_routing_completed": "no global routing result (route guides) exists",
        "detailed_routing_completed": f"detailed routing is incomplete "
                                      f"({s.routed_net_count}/{s.routable_net_count} nets routed)",
        "fillers_inserted": "the design contains no filler cells",
    }[flag]


def verify(instruction: str, result: ExecutionResult, before: DesignState, after: DesignState) -> Verdict:
    """Self-check one execution; ``before`` is the starting state, ``after`` the probed result."""
    reasons: list[str] = []
    clean = result.error_type is None and result.script_status == "ok"
    if not clean:
        reasons.append(f"The script did not run cleanly ({result.error_type or result.script_status}).")

    sizes = {a["path"]: a.get("size", 0) for a in result.artifacts or []}
    for path in requested_outputs(instruction):
        if path not in sizes:
            reasons.append(f"The requested output file {path} was not written.")
        elif not sizes[path]:
            reasons.append(f"The requested output file {path} is empty.")

    checked: list[str] = []
    actions = {i.flag: i.action for i in INTENTS}
    if after.available and after.design_loaded:
        for flag in requested_operations(instruction):
            if getattr(before, flag):
                continue  # already true in the starting state: nothing to verify
            checked.append(flag)
            if not getattr(after, flag):
                reasons.append(f"The task asks to {actions[flag]}, but {_state_problem(flag, after)}.")
    elif clean:
        reasons.append("The design state could not be read after the script.")
    return Verdict(ok=not reasons, reasons=reasons, execution_clean=clean, expectations=checked)
