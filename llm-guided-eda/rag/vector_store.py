"""FAISS exact inner-product index over L2-normalised chunk embeddings (= cosine similarity)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

INDEX_FILE, IDS_FILE, VECTORS_FILE = "chunks.faiss", "chunk_ids.json", "embeddings.npy"


def import_faiss():
    """Import faiss, on macOS only after torch: the two wheels bundle separate libomp copies
    and loading faiss's first makes torch segfault (see rag/__init__.py)."""
    if sys.platform == "darwin" and "faiss" not in sys.modules:
        try:
            import torch  # noqa: F401
        except ImportError:
            pass
    import faiss

    return faiss


class VectorStore:
    """``faiss.IndexFlatIP`` plus the chunk id of every row. Searching is read-only and
    thread-safe (FAISS CPU indexes allow concurrent ``search`` calls)."""

    def __init__(self, index, ids: list[str]):
        if index.ntotal != len(ids):
            raise ValueError(f"index has {index.ntotal} vectors but {len(ids)} ids")
        self.index = index
        self.ids = ids

    @classmethod
    def build(cls, vectors: np.ndarray, ids: list[str]) -> "VectorStore":
        faiss = import_faiss()

        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if vectors.ndim != 2 or len(vectors) != len(ids):
            raise ValueError("vectors must be a (len(ids), dim) matrix")
        norms = np.linalg.norm(vectors, axis=1)
        if len(norms) and not np.allclose(norms, 1.0, atol=1e-3):
            raise ValueError("vectors must be L2-normalised")
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        return cls(index, list(ids))

    @property
    def dim(self) -> int:
        return int(self.index.d)

    def __len__(self) -> int:
        return int(self.index.ntotal)

    def search(self, query: np.ndarray, k: int) -> list[tuple[int, float]]:
        """Top-k (row, cosine similarity) for one normalised query vector."""
        if k <= 0 or not len(self):
            return []
        q = np.ascontiguousarray(query, dtype=np.float32).reshape(1, -1)
        scores, rows = self.index.search(q, min(k, len(self)))
        return [(int(r), float(s)) for r, s in zip(rows[0], scores[0]) if r >= 0]

    def save(self, directory: Path, vectors: np.ndarray | None = None) -> None:
        faiss = import_faiss()

        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(directory / INDEX_FILE))
        (directory / IDS_FILE).write_text(json.dumps(self.ids))
        if vectors is not None:
            np.save(directory / VECTORS_FILE, np.ascontiguousarray(vectors, dtype=np.float32))

    @classmethod
    def load(cls, directory: Path) -> "VectorStore":
        faiss = import_faiss()

        index = faiss.read_index(str(directory / INDEX_FILE))
        return cls(index, json.loads((directory / IDS_FILE).read_text()))
