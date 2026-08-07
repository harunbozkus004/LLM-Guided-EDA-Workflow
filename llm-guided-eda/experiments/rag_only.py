"""Configuration B: single-shot generation with hybrid retrieval-augmented generation.

    python -m experiments.rag_only --experiment-id ID [--runs 1 2 3] [--split test] [--parallel N] ...

Accepts every option of experiments.run_experiment except --config.
"""
from __future__ import annotations

import sys

from experiments.run_experiment import main

PRESET = ["--config", "B_rag"]

if __name__ == "__main__":
    sys.exit(main(PRESET + sys.argv[1:]))
