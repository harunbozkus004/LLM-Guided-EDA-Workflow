"""Configuration C: execution feedback and iterative repair (up to 4 executions), no retrieval.

    python -m experiments.feedback_only --experiment-id ID [--runs 1 2 3] [--split test] [--parallel N] ...

Accepts every option of experiments.run_experiment except --config.
"""
from __future__ import annotations

import sys

from experiments.run_experiment import main

PRESET = ["--config", "C_feedback"]

if __name__ == "__main__":
    sys.exit(main(PRESET + sys.argv[1:]))
