"""Repository paths and cache hygiene.

Importing this module redirects every cache that Python libraries would
otherwise create in the user's home directory (Hugging Face, torch,
matplotlib, sentence-transformers) into ``.tools/cache`` inside the repository.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tools"
CACHE = TOOLS / "cache"
CONFIG_DIR = ROOT / "config"
THIRD_PARTY = ROOT / "third_party"
BENCHMARK_DIR = ROOT / "benchmark"
STATES_DIR = BENCHMARK_DIR / "initial_states"
KB_DIR = ROOT / "knowledge_base"
EXPERIMENTS_DIR = ROOT / "experiments"
RESULTS_DIR = EXPERIMENTS_DIR / "results"
RUNS_DIR = EXPERIMENTS_DIR / "runs"
LLM_CACHE_DIR = EXPERIMENTS_DIR / "llm_cache"
PAPER_DIR = ROOT / "paper"

_CACHE_VARS = {
    "HF_HOME": CACHE / "huggingface",
    "SENTENCE_TRANSFORMERS_HOME": CACHE / "sentence_transformers",
    "TORCH_HOME": CACHE / "torch",
    "MPLCONFIGDIR": CACHE / "matplotlib",
    "XDG_CACHE_HOME": CACHE,
}
for _name, _path in _CACHE_VARS.items():
    os.environ.setdefault(_name, str(_path))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def rel(path: Path | str) -> str:
    """Path relative to the repository root (for logs and metadata)."""
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)
