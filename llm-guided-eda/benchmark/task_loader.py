"""Benchmark task definitions.

Tasks are authored as per-category fragments in ``benchmark/tasks/*.json`` and
merged (with schema checks) into ``benchmark/tasks.json`` (evaluation split)
and ``benchmark/dev_tasks.json`` (development split, used only for prompt
engineering and debugging -- never for reported results).

    python -m benchmark.task_loader merge
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from common.paths import BENCHMARK_DIR
from benchmark.states import STATES, StateSpec, get_state

CATEGORIES = {
    "floorplanning": ("FP", 8),
    "placement": ("PL", 10),
    "timing": ("TA", 8),
    "cts": ("CT", 6),
    "routing": ("RT", 8),
    "inspection": ("IN", 6),
    "optimization": ("OP", 4),
}
DIFFICULTIES = ("easy", "medium", "hard")
SPLIT_FILES = {"test": BENCHMARK_DIR / "tasks.json", "dev": BENCHMARK_DIR / "dev_tasks.json"}


@dataclass
class Task:
    id: str
    category: str
    difficulty: str
    instruction: str
    start_state: str
    expected_commands: list[str]
    expected_outcome: str
    validator: dict[str, Any]
    reference_script: str
    required_outputs: list[str] = field(default_factory=list)
    controls: dict[str, list[str]] = field(default_factory=dict)
    split: str = "test"
    notes: str = ""

    @property
    def state(self) -> StateSpec:
        return get_state(self.start_state)

    def reference_tcl(self) -> str:
        return (BENCHMARK_DIR / self.reference_script).read_text()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_tasks(split: str = "test", ids: list[str] | None = None) -> list[Task]:
    path = SPLIT_FILES[split]
    tasks = [Task(**d) for d in json.loads(path.read_text())]
    if ids:
        wanted = set(ids)
        tasks = [t for t in tasks if t.id in wanted]
        missing = wanted - {t.id for t in tasks}
        if missing:
            raise KeyError(f"unknown task ids: {sorted(missing)}")
    return tasks


def task_set_hash(split: str = "test") -> str:
    return hashlib.sha256(SPLIT_FILES[split].read_bytes()).hexdigest()[:12]


def _check(task: Task, errors: list[str]) -> None:
    import benchmark.validators  # noqa: F401  (registers validators)
    from benchmark.task_validator import VALIDATORS

    prefix = f"{task.id}:"
    if task.category not in CATEGORIES:
        errors.append(f"{prefix} unknown category {task.category}")
    if task.difficulty not in DIFFICULTIES:
        errors.append(f"{prefix} bad difficulty {task.difficulty}")
    if task.start_state not in STATES:
        errors.append(f"{prefix} unknown start_state {task.start_state}")
    if task.validator.get("name") not in VALIDATORS:
        errors.append(f"{prefix} validator '{task.validator.get('name')}' is not registered")
    if not (BENCHMARK_DIR / task.reference_script).exists():
        errors.append(f"{prefix} missing reference script {task.reference_script}")
    for kind in ("alternatives", "negatives"):
        for p in task.controls.get(kind, []):
            if not (BENCHMARK_DIR / p).exists():
                errors.append(f"{prefix} missing control script {p}")
    for out in task.required_outputs:
        if not out.startswith("outputs/"):
            errors.append(f"{prefix} required output {out} must live under outputs/")
        elif out not in task.instruction:
            errors.append(f"{prefix} required output {out} is not named in the instruction")


def merge(partial: bool = False) -> None:
    """Merge fragments; ``partial`` skips the per-category count check (work in progress)."""
    tasks: list[Task] = []
    for frag in sorted((BENCHMARK_DIR / "tasks").glob("*.json")):
        for d in json.loads(frag.read_text()):
            tasks.append(Task(**d))
    errors: list[str] = []
    ids = Counter(t.id for t in tasks)
    errors += [f"duplicate task id {i}" for i, n in ids.items() if n > 1]
    for t in tasks:
        _check(t, errors)
    test = sorted((t for t in tasks if t.split == "test"), key=lambda t: t.id)
    dev = sorted((t for t in tasks if t.split == "dev"), key=lambda t: t.id)
    counts = Counter(t.category for t in test)
    for cat, (_, want) in CATEGORIES.items():
        if counts.get(cat, 0) != want and not partial:
            errors.append(f"category {cat}: {counts.get(cat, 0)} test tasks, expected {want}")
    if errors:
        raise SystemExit("task merge failed:\n  " + "\n  ".join(errors))
    for split, items in (("test", test), ("dev", dev)):
        SPLIT_FILES[split].write_text(json.dumps([t.to_dict() for t in items], indent=1) + "\n")
    diff = Counter(t.difficulty for t in test)
    print(f"merged {len(test)} test tasks {dict(counts)} difficulties {dict(diff)}; {len(dev)} dev tasks")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["merge"])
    ap.add_argument("--partial", action="store_true", help="allow incomplete categories")
    merge(partial=ap.parse_args().partial)
