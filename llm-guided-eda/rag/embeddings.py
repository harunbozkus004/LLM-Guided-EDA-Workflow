"""Sentence embeddings with BAAI/bge-small-en-v1.5 (pinned revision, cached in .tools/cache).

``common.paths`` is imported before anything from Hugging Face so that every
cache (HF_HOME, SENTENCE_TRANSFORMERS_HOME, ...) points into the repository.
The model is downloaded once; afterwards it is always loaded offline from the
pinned snapshot. Embeddings are L2-normalised float32; queries (only) get the
bge retrieval instruction prefix.
"""
from __future__ import annotations

import common.paths  # noqa: F401  (must precede huggingface / sentence_transformers imports)

import functools
import os
import threading
from pathlib import Path
from typing import Sequence

import numpy as np

from common.paths import CACHE

MODEL_NAME = "BAAI/bge-small-en-v1.5"
MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"   # snapshot used for the published index
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
MODEL_CACHE = CACHE / "sentence_transformers"
MAX_SEQ_LENGTH = 512          # bge-small position-embedding limit; longer inputs are truncated
BATCH_SIZE = 32


def model_files_present(model_name: str = MODEL_NAME, revision: str = MODEL_REVISION) -> bool:
    snap = MODEL_CACHE / f"models--{model_name.replace('/', '--')}" / "snapshots" / revision
    return (snap / "tokenizer.json").exists() and any(snap.glob("model.safetensors"))


@functools.lru_cache(maxsize=None)
def tokenizer_path(model_name: str = MODEL_NAME, revision: str = MODEL_REVISION) -> Path:
    """Local path of the model's tokenizer.json (downloads the file if it is missing)."""
    from huggingface_hub import hf_hub_download

    kwargs = dict(repo_id=model_name, filename="tokenizer.json", revision=revision,
                  cache_dir=str(MODEL_CACHE))
    try:
        return Path(hf_hub_download(local_files_only=True, **kwargs))
    except Exception:
        return Path(hf_hub_download(**kwargs))


class TokenCounter:
    """Token counts with the embedding model's own (fast, Rust) WordPiece tokenizer.

    Special tokens ([CLS]/[SEP]) are not counted. Thread-safe; results are memoised.
    """

    def __init__(self, model_name: str = MODEL_NAME, revision: str = MODEL_REVISION):
        from tokenizers import Tokenizer

        self._tok = Tokenizer.from_file(str(tokenizer_path(model_name, revision)))
        self._tok.no_truncation()
        self._tok.no_padding()
        self._lock = threading.Lock()
        self._memo: dict[str, int] = {}

    def __call__(self, text: str) -> int:
        n = self._memo.get(text)
        if n is None:
            with self._lock:
                n = len(self._tok.encode(text, add_special_tokens=False).ids)
            self._memo[text] = n
        return n

    def tokens(self, text: str) -> list[str]:
        with self._lock:
            return self._tok.encode(text, add_special_tokens=False).tokens


@functools.lru_cache(maxsize=None)
def get_token_counter() -> TokenCounter:
    return TokenCounter()


class Embedder:
    """Batched, deterministic (CPU by default) sentence embeddings; ``encode`` is serialised
    by a lock so one instance can be shared by a thread pool."""

    def __init__(self, model_name: str = MODEL_NAME, revision: str = MODEL_REVISION,
                 device: str = "cpu", batch_size: int = BATCH_SIZE):
        offline = model_files_present(model_name, revision)
        if offline:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer

        self.model_name, self.revision, self.device, self.batch_size = model_name, revision, device, batch_size
        self.model = SentenceTransformer(model_name, revision=revision, device=device,
                                         cache_folder=str(MODEL_CACHE), local_files_only=offline)
        self.model.max_seq_length = MAX_SEQ_LENGTH
        self.model.eval()
        self._lock = threading.Lock()

    @property
    def dim(self) -> int:
        return int(self.model.get_embedding_dimension() if hasattr(self.model, "get_embedding_dimension")
                   else self.model.get_sentence_embedding_dimension())

    def _encode(self, texts: Sequence[str], show_progress: bool = False) -> np.ndarray:
        import torch

        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        with self._lock, torch.inference_mode():
            vecs = self.model.encode(list(texts), batch_size=self.batch_size, normalize_embeddings=True,
                                     convert_to_numpy=True, show_progress_bar=show_progress)
        return np.ascontiguousarray(vecs, dtype=np.float32)

    def embed_documents(self, texts: Sequence[str], show_progress: bool = False) -> np.ndarray:
        return self._encode(texts, show_progress)

    def embed_queries(self, queries: Sequence[str]) -> np.ndarray:
        return self._encode([QUERY_PREFIX + q for q in queries])

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed_queries([query])[0]


_embedders: dict[tuple[str, str, str], Embedder] = {}
_embedders_lock = threading.Lock()


def get_embedder(model_name: str = MODEL_NAME, revision: str = MODEL_REVISION,
                 device: str = "cpu") -> Embedder:
    """Process-wide shared Embedder (loaded once)."""
    key = (model_name, revision, device)
    with _embedders_lock:
        if key not in _embedders:
            _embedders[key] = Embedder(model_name, revision, device)
        return _embedders[key]


def library_versions() -> dict[str, str]:
    import sentence_transformers
    import tokenizers
    import torch
    import transformers

    from rag.vector_store import import_faiss

    faiss = import_faiss()

    return {"sentence_transformers": sentence_transformers.__version__, "transformers": transformers.__version__,
            "torch": torch.__version__, "tokenizers": tokenizers.__version__, "faiss": faiss.__version__}
