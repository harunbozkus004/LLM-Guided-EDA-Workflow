"""Retrieval over the knowledge base: dense (FAISS), keyword (BM25) or hybrid (RRF).

Usage (the agent's interface)::

    retriever = Retriever.load("hybrid")            # or "vector" / "bm25"
    chunks = retriever.retrieve("legalize placement after global placement", k=6)
    context = format_context(chunks, max_chars=14000)

hybrid = reciprocal rank fusion (k = ``rrf_k``) of the top ``top_k_semantic``
vector hits and top ``top_k_keyword`` BM25 hits (config/experiment_config.yaml,
section ``retrieval``), then the final top k. Chunks with the same source +
section are deduplicated, keeping the best: each ranker's candidate list holds
distinct sections (so a section split into several chunks cannot crowd a pool),
fusion is done per section, and the section is represented by its best ranked
chunk. vector / bm25 mode use one ranker's distinct-section list. The knowledge
base is loaded once per process and shared by all Retriever instances;
``retrieve`` is thread-safe.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from common.config import load_config
from common.jsonl import read_jsonl
from common.paths import KB_DIR
from rag.document_chunker import Chunk

MODES = ("hybrid", "vector", "bm25")
CHUNK_FILES = ("documentation/chunks.jsonl", "examples/chunks.jsonl")
EMBEDDINGS_DIR = "embeddings"
EXAMPLE_TYPES = ("example", "flow_script")


@dataclass
class RetrievedChunk:
    id: str
    text: str
    source: str
    section: str
    url: str
    doc_type: str
    score: float            # hybrid: RRF score; vector: cosine similarity; bm25: BM25 score
    rank: int               # 1-based rank in the returned list


def rrf_fuse(rankings: Sequence[Sequence[int]], k: int = 60) -> list[tuple[int, float]]:
    """Reciprocal rank fusion: score(d) = sum over rankings of 1 / (k + rank(d)), ranks from 1.

    Ties are broken by the best single rank, then by the earlier ranking list, then by item.
    """
    scores: dict[int, float] = {}
    best: dict[int, tuple[int, int]] = {}
    for li, ranking in enumerate(rankings):
        for r, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + r)
            best[item] = min(best.get(item, (r, li)), (r, li))
    return sorted(scores.items(), key=lambda kv: (-kv[1], best[kv[0]], kv[0]))


class _KnowledgeBase:
    """Chunks plus lazily loaded indexes of one knowledge-base directory."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        emb = kb_dir / EMBEDDINGS_DIR
        manifest_path = kb_dir / "manifest.json"
        self.manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        by_id: dict[str, Chunk] = {}
        for name in CHUNK_FILES:
            for d in read_jsonl(kb_dir / name):
                c = Chunk.from_dict(d)
                by_id[c.id] = c
        ids_path = emb / "chunk_ids.json"
        order = json.loads(ids_path.read_text()) if ids_path.exists() else list(by_id)
        missing = [i for i in order if i not in by_id]
        if missing or len(order) != len(by_id):
            raise ValueError(f"{kb_dir}: chunk files and index disagree "
                             f"({len(missing)} indexed ids missing, {len(by_id)} chunks, {len(order)} ids); "
                             "rebuild with python -m rag.build_index")
        self.chunks = [by_id[i] for i in order]
        self._lock = threading.Lock()
        self._vectors = None
        self._bm25 = None
        self._embedder = None

    def _ensure_vectors(self) -> None:
        if self._vectors is not None:
            return
        with self._lock:
            if self._vectors is not None:
                return
            from rag.embeddings import MODEL_NAME, MODEL_REVISION, get_embedder
            from rag.vector_store import VectorStore, import_faiss

            info = self.manifest.get("embedding", {})
            embedder = get_embedder(info.get("model", MODEL_NAME), info.get("revision", MODEL_REVISION))
            # many small concurrent single-query searches: no intra-search parallelism
            import_faiss().omp_set_num_threads(1)
            store = VectorStore.load(self.kb_dir / EMBEDDINGS_DIR)
            if store.ids != [c.id for c in self.chunks]:
                raise ValueError(f"{self.kb_dir}: FAISS ids do not match the chunk files")
            if embedder.dim != store.dim:
                raise ValueError(f"embedding dim {embedder.dim} != index dim {store.dim}")
            self._embedder, self._vectors = embedder, store

    def _ensure_bm25(self) -> None:
        if self._bm25 is not None:
            return
        with self._lock:
            if self._bm25 is None:
                from rag.bm25_retriever import BM25Index

                index = BM25Index.load(self.kb_dir / EMBEDDINGS_DIR)
                if len(index) != len(self.chunks):
                    raise ValueError(f"{self.kb_dir}: BM25 index size does not match the chunk files")
                self._bm25 = index

    def vector_search(self, query: str, k: int) -> list[tuple[int, float]]:
        self._ensure_vectors()
        return self._vectors.search(self._embedder.embed_query(query), k)

    def bm25_search(self, query: str, k: int) -> list[tuple[int, float]]:
        self._ensure_bm25()
        return self._bm25.search(query, k)


_KB_CACHE: dict[Path, _KnowledgeBase] = {}
_KB_CACHE_LOCK = threading.Lock()


def _knowledge_base(kb_dir: Path) -> _KnowledgeBase:
    with _KB_CACHE_LOCK:
        if kb_dir not in _KB_CACHE:
            _KB_CACHE[kb_dir] = _KnowledgeBase(kb_dir)
        return _KB_CACHE[kb_dir]


class Retriever:
    def __init__(self, kb: _KnowledgeBase, mode: str, top_k_semantic: int = 8,
                 top_k_keyword: int = 8, rrf_k: int = 60, max_examples: int | None = None):
        if mode not in MODES:
            raise ValueError(f"unknown retrieval mode {mode!r}; expected one of {MODES}")
        self.kb, self.mode = kb, mode
        self.top_k_semantic, self.top_k_keyword, self.rrf_k = top_k_semantic, top_k_keyword, rrf_k
        # Optional soft cap on example / flow-script chunks among the final k (None = off, the
        # default): extra examples only fill slots that no documentation candidate can take.
        self.max_examples = max_examples

    @classmethod
    def load(cls, mode: str = "hybrid", kb_dir: Path | None = None) -> "Retriever":
        """Load (once per process and directory) the knowledge base and its indexes for ``mode``."""
        if mode not in MODES:
            raise ValueError(f"unknown retrieval mode {mode!r}; expected one of {MODES}")
        kb = _knowledge_base(Path(kb_dir or KB_DIR).resolve())
        cfg = load_config("experiment_config").get("retrieval", {})
        cap = cfg.get("max_examples")
        retriever = cls(kb, mode, int(cfg.get("top_k_semantic", 8)), int(cfg.get("top_k_keyword", 8)),
                        int(cfg.get("rrf_k", 60)), None if cap is None else int(cap))
        if mode != "bm25":
            kb._ensure_vectors()
        if mode != "vector":
            kb._ensure_bm25()
        return retriever

    def _distinct(self, hits: list[tuple[int, float]], n: int) -> list[tuple[int, float]]:
        """The first ``n`` hits with distinct (source, section)."""
        out: list[tuple[int, float]] = []
        seen: set[tuple[str, str]] = set()
        for row, score in hits:
            c = self.kb.chunks[row]
            if (c.source, c.section) not in seen:
                seen.add((c.source, c.section))
                out.append((row, score))
                if len(out) == n:
                    break
        return out

    def ranked(self, query: str, k: int) -> list[tuple[int, float]]:
        """Candidate ranking as (chunk row, score), one chunk per (source, section)."""
        n_vec, n_kw = max(self.top_k_semantic, k), max(self.top_k_keyword, k)
        # Over-fetch so that each pool still holds n distinct sections after deduplication.
        vec = self._distinct(self.kb.vector_search(query, 4 * n_vec), n_vec) if self.mode != "bm25" else []
        kw = self._distinct(self.kb.bm25_search(query, 4 * n_kw), n_kw) if self.mode != "vector" else []
        if self.mode != "hybrid":
            return vec or kw
        key = lambda row: (self.kb.chunks[row].source, self.kb.chunks[row].section)  # noqa: E731
        best_row: dict[tuple[str, str], int] = {}
        for row, _ in sorted(((r, rank) for hits in (vec, kw) for rank, (r, _) in enumerate(hits)),
                             key=lambda x: x[1]):
            best_row.setdefault(key(row), row)        # best ranked chunk of each section (vector first)
        keys = list(best_row)
        index = {kk: i for i, kk in enumerate(keys)}
        fused = rrf_fuse([[index[key(r)] for r, _ in vec], [index[key(r)] for r, _ in kw]], self.rrf_k)
        return [(best_row[keys[i]], score) for i, score in fused]

    def retrieve(self, query: str, k: int = 6) -> list[RetrievedChunk]:
        if k <= 0 or not query or not query.strip():
            return []
        picked: list[tuple[Chunk, float]] = []
        held: list[tuple[Chunk, float]] = []          # examples beyond max_examples
        seen: set[tuple[str, str]] = set()
        for row, score in self.ranked(query, k):
            c = self.kb.chunks[row]
            if (c.source, c.section) in seen:
                continue
            seen.add((c.source, c.section))
            if (self.max_examples is not None and c.doc_type in EXAMPLE_TYPES
                    and sum(p.doc_type in EXAMPLE_TYPES for p, _ in picked) >= self.max_examples):
                held.append((c, score))
                continue
            picked.append((c, score))
            if len(picked) == k:
                break
        picked += held[:k - len(picked)]
        return [RetrievedChunk(id=c.id, text=c.text, source=c.source, section=c.section, url=c.url,
                               doc_type=c.doc_type, score=float(score), rank=i)
                for i, (c, score) in enumerate(picked, start=1)]


def format_context(chunks: list[RetrievedChunk], max_chars: int = 14000) -> str:
    """"[1] <source> > <section>\\n<text>\\n\\n[2] ..." cut on chunk boundaries at ``max_chars``.

    Chunks are added in order until the next one would exceed ``max_chars``; only when the
    first chunk alone is longer than ``max_chars`` is it truncated.
    """
    parts: list[str] = []
    used = 0
    for i, c in enumerate(chunks, start=1):
        head = f"{c.source} > {c.section}" if c.section else c.source
        block = f"[{i}] {head}\n{c.text.strip()}"
        extra = len(block) + (2 if parts else 0)
        if used + extra > max_chars:
            if not parts and max_chars > 0:
                parts.append(block[:max_chars])
            break
        parts.append(block)
        used += extra
    return "\n\n".join(parts)
