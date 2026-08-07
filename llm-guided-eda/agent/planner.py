"""Retrieval queries for the initial generation and for repairs."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.error_classifier import Diagnosis

MAX_QUERY_CHARS = 1000


def _norm(text: str | None) -> str:
    return " ".join((text or "").split())


def retrieval_query(instruction: str) -> str:
    """Query for the initial documentation lookup: the whitespace-normalized instruction."""
    return _norm(instruction)


def repair_query(diagnosis: "Diagnosis") -> str:
    """Query for error-specific documentation: message, failing command and error-type words."""
    parts = [_norm(diagnosis.message), _norm(diagnosis.failing_command_text),
             _norm(diagnosis.error_type.replace("_", " "))]
    return " ".join(p for p in parts if p)[:MAX_QUERY_CHARS]
