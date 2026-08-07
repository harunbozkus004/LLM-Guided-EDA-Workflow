"""Configuration A (baseline): single-shot generation, no retrieval, no execution feedback.

    python -m experiments.baseline --experiment-id ID [--runs 1 2 3] [--split test] [--parallel N] ...

Accepts every option of experiments.run_experiment except --config.
"""
from __future__ import annotations

import sys

from experiments.run_experiment import main

PRESET = ["--config", "A_baseline"]

if __name__ == "__main__":
    sys.exit(main(PRESET + sys.argv[1:]))
