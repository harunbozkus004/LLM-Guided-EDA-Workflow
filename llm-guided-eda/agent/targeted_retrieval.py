"""Targeted repair retrieval: the exact syntax card of the command named in an error.

The generic repair retrieval searches with the error text. This adds, for the
command(s) the failing line actually calls (or the error message names), the
``command_syntax`` chunk of the knowledge base -- the option list parsed from
the tool's own ``define_cmd_args``/``parse_key_args`` of this OpenROAD version.
When the command does not exist in this build (``invalid command name``), the
prompt says so and shows the cards of the documented commands with the closest
names instead. No extra LLM call is made.
"""
from __future__ import annotations

import ast
import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from common.jsonl import read_jsonl
from common.paths import KB_DIR

if TYPE_CHECKING:
    from agent.error_classifier import Diagnosis

CARD_DOC_TYPE = "command_syntax"
CHUNK_FILES = ("documentation/chunks.jsonl", "examples/chunks.jsonl")
MAX_COMMANDS = 3                 # commands with a card per repair prompt
MAX_CARDS_PER_COMMAND = 2
MAX_SUGGESTIONS = 3              # similar documented names for a nonexistent command
SUGGESTION_CUTOFF = 0.6          # difflib ratio
TARGETED_HEADER = "EXACT SYNTAX of the command(s) in the error (from this OpenROAD version):"

_MISSING_RE = re.compile(r'invalid command name "([^"]+)"')
_COMMAND_POSITION_RE = re.compile(r"(?:^|[\[;{])\s*([A-Za-z_][\w:]*)")
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class SyntaxCard:
    """Same fields as ``rag.hybrid_retriever.RetrievedChunk``."""
    id: str
    text: str
    source: str
    section: str
    url: str = ""
    doc_type: str = CARD_DOC_TYPE
    score: float = 0.0
    rank: int = 0


@dataclass
class TargetedDocs:
    commands: list[str] = field(default_factory=list)   # commands whose cards are shown
    missing: str | None = None                          # nonexistent command named by the error
    cards: list[SyntaxCard] = field(default_factory=list)
    text: str = ""

    @property
    def ids(self) -> list[str]:
        return [c.id for c in self.cards]


def _commands_field(value: object) -> list[str]:
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return []
    return [str(v) for v in value] if isinstance(value, (list, tuple)) else []


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


class SyntaxCards:
    """Command-syntax cards of the knowledge base, looked up by exact command name."""

    def __init__(self, cards: dict[str, list[SyntaxCard]], description: str = "in-memory syntax cards"):
        self.by_command = {name: list(cs) for name, cs in cards.items() if cs}
        self.description = description

    @classmethod
    def load(cls, kb_dir: Path | None = None) -> "SyntaxCards":
        root = Path(kb_dir or KB_DIR)
        cards: dict[str, list[SyntaxCard]] = {}
        for name in CHUNK_FILES:
            path = root / name
            if not path.exists():
                continue
            for d in read_jsonl(path):
                if d.get("doc_type") != CARD_DOC_TYPE:
                    continue
                card = SyntaxCard(id=d["id"], text=d["text"], source=d.get("source", ""),
                                  section=d.get("section", ""), url=d.get("url", ""))
                for command in _commands_field(d.get("commands")):
                    cards.setdefault(command, []).append(card)
        return cls(cards, f"{CARD_DOC_TYPE} chunks of {root.name}/ ({len(cards)} commands)")

    def __len__(self) -> int:
        return len(self.by_command)

    def suggestions(self, name: str) -> list[str]:
        return difflib.get_close_matches(name, sorted(self.by_command), n=MAX_SUGGESTIONS, cutoff=SUGGESTION_CUTOFF)

    def commands_in(self, text: str | None, *, command_position: bool) -> list[str]:
        """Documented commands in ``text``: in Tcl command position only, or anywhere as a whole word."""
        rx = _COMMAND_POSITION_RE if command_position else _WORD_RE
        return [w for w in _unique(m.group(1) if command_position else m.group(0) for m in rx.finditer(text or ""))
                if w in self.by_command]

    def for_diagnosis(self, diagnosis: "Diagnosis") -> TargetedDocs:
        """Cards for the command(s) involved in an execution error (empty for self-check failures)."""
        out = TargetedDocs()
        if diagnosis.error_type in ("validation_failure", "unsafe_command"):
            return out
        m = _MISSING_RE.search(diagnosis.message)
        if m and m.group(1) not in self.by_command:
            out.missing = m.group(1)
        commands = self.suggestions(out.missing) if out.missing else []
        commands += self.commands_in(diagnosis.failing_command_text, command_position=True)
        commands += self.commands_in(" ".join([diagnosis.message, *diagnosis.tool_errors[:2]]),
                                     command_position=False)
        out.commands = _unique(commands)[:MAX_COMMANDS]
        out.cards = _unique_cards(c for name in out.commands for c in self.by_command[name][:MAX_CARDS_PER_COMMAND])
        out.text = self._render(out)
        return out

    def _render(self, docs: TargetedDocs) -> str:
        lines: list[str] = []
        if docs.missing:
            note = f"`{docs.missing}` is not a command in this OpenROAD version."
            suggested = [c for c in docs.commands if c in self.suggestions(docs.missing)]
            if suggested:
                note += " Documented commands with similar names: " + ", ".join(f"`{c}`" for c in suggested) + "."
            lines.append(note)
        if docs.cards:
            lines.append(TARGETED_HEADER)
            for i, c in enumerate(docs.cards, start=1):
                head = f"{c.source} > {c.section}" if c.section else c.source
                lines.append(f"[S{i}] {head}\n{c.text.strip()}")
        return "\n".join(lines)


def _unique_cards(cards: Iterable[SyntaxCard]) -> list[SyntaxCard]:
    seen: set[str] = set()
    out = []
    for c in cards:
        if c.id not in seen:
            seen.add(c.id)
            out.append(c)
    return out
