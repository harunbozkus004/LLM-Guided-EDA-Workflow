"""Documentation retrieval for the agent.

:class:`RagRetriever` adapts ``rag.hybrid_retriever`` (imported lazily, so the
agent and its tests do not need the knowledge base). :class:`FakeRetriever` is a
deterministic stand-in used by the tests and -- clearly logged -- by mock smoke
runs when the knowledge base is not available.
"""
from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, replace
from typing import Any, Protocol

log = logging.getLogger(__name__)


class DocRetriever(Protocol):
    mode: str
    description: str

    def retrieve(self, query: str, k: int = 6) -> list[Any]: ...

    def format_context(self, chunks: list[Any], max_chars: int) -> str: ...


class RagRetriever:
    """Adapter around ``rag.hybrid_retriever.Retriever`` (mode: hybrid | vector | bm25)."""

    def __init__(self, mode: str):
        from rag.hybrid_retriever import Retriever, format_context

        self.mode = mode
        self.description = f"rag.hybrid_retriever.Retriever.load({mode!r})"
        self._retriever = Retriever.load(mode)
        self._format = format_context
        self._lock = threading.Lock()  # episodes run in threads; the index is not assumed thread-safe

    def retrieve(self, query: str, k: int = 6) -> list[Any]:
        with self._lock:
            return list(self._retriever.retrieve(query, k=k))

    def format_context(self, chunks: list[Any], max_chars: int) -> str:
        return self._format(chunks, max_chars)


@dataclass(frozen=True)
class FakeChunk:
    """Same fields as ``rag.hybrid_retriever.RetrievedChunk``."""
    id: str
    text: str
    source: str = "fake"
    section: str = ""
    url: str = ""
    doc_type: str = "fake"
    score: float = 0.0
    rank: int = 0


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def default_fake_corpus() -> list[FakeChunk]:
    topics = ["floorplan initialize_floorplan utilization aspect ratio core space", "make_tracks routing tracks",
              "place_pins io pins", "tapcell tap cells", "pdngen power grid", "global_placement density",
              "detailed_placement legalize", "clock_tree_synthesis clock tree buffers", "global_route guides",
              "detailed_route drc", "filler_placement filler cells", "report_checks timing slack"]
    return [FakeChunk(id=f"fake-{i:02d}", text=f"FAKE DOCUMENTATION (no knowledge base loaded): {t}.",
                      section=t.split()[0]) for i, t in enumerate(topics)]


class FakeRetriever:
    """Deterministic keyword-overlap retrieval over an in-memory corpus (NOT real documentation)."""

    def __init__(self, chunks: list[FakeChunk] | None = None, mode: str = "fake"):
        self.mode = mode
        self.description = "FakeRetriever (NOT real documentation)"
        self.chunks = list(chunks) if chunks is not None else default_fake_corpus()
        self.queries: list[tuple[str, int]] = []
        self._lock = threading.Lock()

    def retrieve(self, query: str, k: int = 6) -> list[FakeChunk]:
        with self._lock:
            self.queries.append((query, k))
        q = _tokens(query)
        ranked = sorted(enumerate(self.chunks), key=lambda ic: (-len(q & _tokens(ic[1].text + " " + ic[1].section)),
                                                                ic[0]))
        return [replace(c, score=float(len(q & _tokens(c.text + " " + c.section))), rank=r)
                for r, (_, c) in enumerate(ranked[:k], 1)]

    def format_context(self, chunks: list[Any], max_chars: int) -> str:
        text = "\n\n".join(f"[{c.rank}] {c.source} :: {c.section} (id {c.id})\n{c.text}" for c in chunks)
        return text[:max_chars]


def load_retriever(mode: str, *, allow_fake: bool = False) -> DocRetriever:
    """The real retriever for ``mode``; with ``allow_fake`` (mock provider only) fall back to FakeRetriever."""
    try:
        return RagRetriever(mode)
    except Exception as e:  # missing module, missing index, ...: anything that prevents real retrieval
        if not allow_fake:
            raise RuntimeError(f"cannot load the '{mode}' retriever from rag.hybrid_retriever: "
                               f"{type(e).__name__}: {e}") from e
        log.warning("rag.hybrid_retriever unavailable for mode %r (%s: %s); using FakeRetriever. Retrieved "
                    "'documentation' is NOT real -- allowed only with the mock provider.", mode, type(e).__name__, e)
        return FakeRetriever(mode=f"fake:{mode}")
