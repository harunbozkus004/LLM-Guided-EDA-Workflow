"""Ablations E (vector-only retrieval) and F (a single repair attempt) of the full agent.

    python -m experiments.ablation --experiment-id ID [--runs 1 2 3] [--split test] [--parallel N] ...

Accepts every option of experiments.run_experiment except --config.
"""
from __future__ import annotations

import sys

from experiments.run_experiment import main

PRESET = ["--config", "E_vector_only", "F_single_repair"]

if __name__ == "__main__":
    sys.exit(main(PRESET + sys.argv[1:]))
