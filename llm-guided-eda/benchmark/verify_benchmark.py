"""Verify benchmark tasks with positive and negative controls.

For every task:
  * the reference script must PASS its validator;
  * every alternative valid solution in ``controls.alternatives`` must PASS;
  * an empty script must FAIL (the starting state alone never satisfies a task);
  * every plausible-but-wrong script in ``controls.negatives`` must FAIL.

    python -m benchmark.verify_benchmark [--split test|dev|all] [--ids FP-01 ...] [--jobs 8]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common.paths import BENCHMARK_DIR, RUNS_DIR
from benchmark.task_loader import Task, load_tasks
from benchmark.task_validator import validate
from openroad.executor import OpenROADExecutor

EMPTY_SCRIPT = "# negative control: do nothing\n"


def controls_for(task: Task) -> list[tuple[str, str, bool]]:
    """(label, script text, expected_pass) for every control of a task."""
    items = [("reference", task.reference_tcl(), True), ("empty", EMPTY_SCRIPT, False)]
    for i, p in enumerate(task.controls.get("alternatives", []), 1):
        items.append((f"alt{i}", (BENCHMARK_DIR / p).read_text(), True))
    for i, p in enumerate(task.controls.get("negatives", []), 1):
        items.append((f"neg{i}", (BENCHMARK_DIR / p).read_text(), False))
    return items


def run_control(executor: OpenROADExecutor, task: Task, label: str, script: str, expect: bool) -> dict:
    run_dir = RUNS_DIR / "verify" / task.id / label
    shutil.rmtree(run_dir, ignore_errors=True)
    res = executor.run(script, run_dir, preamble=task.state.preamble(), links=task.state.links(),
                       label=f"{task.id}/{label}")
    val = validate(task, res, executor)
    ok = val.passed == expect
    return {
        "task": task.id, "control": label, "expected_pass": expect, "passed": val.passed, "ok": ok,
        "summary": val.summary(), "validator_error": val.validator_error, "error_type": res.error_type,
        "error_message": res.error_message, "time": res.execution_time, "run_dir": res.run_dir,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["test", "dev", "all"])
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--fragment", help="verify tasks straight from one fragment (benchmark/tasks/<cat>.json)")
    ap.add_argument("--report", action="store_true", help="write benchmark/verification_report.{json,md}")
    args = ap.parse_args()

    if args.fragment:
        from benchmark.task_loader import _check
        tasks = [Task(**d) for d in json.loads(Path(args.fragment).read_text())]
        errors: list[str] = []
        for t in tasks:
            _check(t, errors)
        if errors:
            print("schema errors:\n  " + "\n  ".join(errors))
            return 1
        tasks = [t for t in tasks if not args.ids or t.id in args.ids]
    else:
        splits = ["test", "dev"] if args.split == "all" else [args.split]
        tasks = [t for s in splits for t in load_tasks(s) if not args.ids or t.id in args.ids]
    executor = OpenROADExecutor()
    jobs = [(t, *c) for t in tasks for c in controls_for(t)]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(lambda j: run_control(executor, *j), jobs))

    bad = [r for r in rows if not r["ok"]]
    for r in rows:
        mark = "ok " if r["ok"] else "BAD"
        print(f"[{mark}] {r['task']:10s} {r['control']:9s} expect={'PASS' if r['expected_pass'] else 'FAIL'} "
              f"got={'PASS' if r['passed'] else 'FAIL'}  {r['summary'][:150]}")
        if r["validator_error"]:
            print("      validator error:", r["validator_error"].strip().splitlines()[-1])
    print(f"\n{len(rows) - len(bad)}/{len(rows)} controls behaved as expected across {len(tasks)} tasks")

    if args.report:
        (BENCHMARK_DIR / "verification_report.json").write_text(json.dumps(rows, indent=1))
        lines = ["# Benchmark verification report", "",
                 f"{len(rows) - len(bad)}/{len(rows)} controls behaved as expected across {len(tasks)} tasks.", "",
                 "| Task | Control | Expected | Got | Detail |", "|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['task']} | {r['control']} | {'PASS' if r['expected_pass'] else 'FAIL'} | "
                         f"{'PASS' if r['passed'] else 'FAIL'} | {r['summary'][:120].replace('|', '/')} |")
        (BENCHMARK_DIR / "verification_report.md").write_text("\n".join(lines) + "\n")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
