"""Independent task validators.

A validator decides whether a benchmark task was actually accomplished, using
only ground truth produced by the harness:

* ``ctx.probe``     -- design-state probe taken right after the agent script
* ``ctx.baseline``  -- the same probe for the untouched starting state
* output files      -- reports the task asked the agent to write
* ``ctx.query``     -- trusted Tcl queries against the final database (final.odb)

Validators never look at the LLM's explanation of what it did. They are used
only for scoring; the agent never sees them or their parameters.

Register a validator with::

    @register("floorplan_utilization")
    def _(ctx: ValidationContext, params: dict) -> list[Check]:
        ...
"""
from __future__ import annotations

import hashlib
import json
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from common.paths import ROOT, STATES_DIR
from benchmark.states import load_baseline_probe
from benchmark.task_loader import Task
from openroad.executor import ExecutionResult, OpenROADExecutor


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ValidationResult:
    passed: bool
    checks: list[Check] = field(default_factory=list)
    validator_error: str | None = None

    def summary(self) -> str:
        failed = [c for c in self.checks if not c.passed]
        if self.passed:
            return f"PASS ({len(self.checks)} checks)"
        parts = [f"{c.name}: {c.detail}" for c in failed]
        if self.validator_error:
            parts.append(f"validator error: {self.validator_error.splitlines()[-1]}")
        return "FAIL - " + "; ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ValidatorFn = Callable[["ValidationContext", dict], list[Check]]
VALIDATORS: dict[str, ValidatorFn] = {}


def register(name: str) -> Callable[[ValidatorFn], ValidatorFn]:
    def deco(fn: ValidatorFn) -> ValidatorFn:
        if name in VALIDATORS:
            raise ValueError(f"validator '{name}' registered twice")
        VALIDATORS[name] = fn
        return fn
    return deco


class ValidationContext:
    def __init__(self, task: Task, result: ExecutionResult, executor: OpenROADExecutor):
        self.task = task
        self.result = result
        self.executor = executor
        self.run_dir = ROOT / result.run_dir
        self.probe: dict[str, Any] = result.probe or {}
        self.baseline: dict[str, Any] = load_baseline_probe(task.start_state)
        self.stdout = result.stdout
        self.agent_output = result.agent_output

    # ---------------------------------------------------------------- files
    def output_path(self, name: str) -> Path:
        name = name if name.startswith("outputs/") else f"outputs/{name}"
        return self.run_dir / name

    def read_output(self, name: str) -> str | None:
        p = self.output_path(name)
        if not p.is_file():
            return None
        return p.read_text(errors="replace")

    # -------------------------------------------------------------- queries
    def query(self, body: str, name: str = "oracle") -> dict[str, Any]:
        """Trusted Tcl query against the database left by the agent script.

        ``body`` runs after the usual state preamble (liberty, SDC, RC) with the
        final database loaded, and must call ``__oracle_emit <json-string>`` or
        ``__oracle_emit_dict [dict create key value ...]`` (flat dict; numbers
        stay numbers, everything else becomes a JSON string).
        """
        final_db = self.run_dir / "final.odb"
        if not final_db.exists():
            raise RuntimeError("final.odb missing (agent session did not complete)")
        return self.executor.query(self.run_dir, preamble=self.task.state.preamble("final.odb"),
                                   body=body, links=self.task.state.links(), name=name)

    def query_baseline(self, body: str, name: str = "baseline") -> dict[str, Any]:
        """Same as :meth:`query` but on the untouched starting state (cached)."""
        key = hashlib.sha256((self.task.start_state + "\n" + body).encode()).hexdigest()[:16]
        cache = STATES_DIR / "_oracle_cache" / f"{self.task.start_state}_{key}.json"
        if cache.exists():
            return json.loads(cache.read_text())
        import shutil
        import uuid
        work = STATES_DIR / "_oracle_cache" / f"work_{key}_{uuid.uuid4().hex[:8]}"
        data = self.executor.query(work, preamble=self.task.state.preamble(), body=body,
                                   links=self.task.state.links(), name=name)
        tmp = cache.with_suffix(f".{uuid.uuid4().hex[:8]}.tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(cache)  # atomic: concurrent validators may compute the same entry
        shutil.rmtree(work, ignore_errors=True)
        return data


def validate(task: Task, result: ExecutionResult, executor: OpenROADExecutor) -> ValidationResult:
    """Score one execution of one task."""
    import benchmark.validators  # noqa: F401  (registers all validators)

    checks: list[Check] = []
    if task.validator.get("require_clean_exit", True):
        clean = result.error_type is None and result.script_status == "ok"
        checks.append(Check("script_completed", clean,
                            "" if clean else f"{result.error_type}: {(result.error_message or '')[:200]}"))
    if not result.probe or "probe_error" in result.probe or not result.probe.get("design_loaded"):
        checks.append(Check("design_state_available", False, "no usable design-state probe"))
        return ValidationResult(False, checks)
    ctx = ValidationContext(task, result, executor)
    fn = VALIDATORS[task.validator["name"]]
    try:
        checks += fn(ctx, dict(task.validator.get("params", {})))
    except Exception:  # validator bugs must be visible, never silently pass
        return ValidationResult(False, checks, validator_error=traceback.format_exc())
    if not checks:
        return ValidationResult(False, [Check("validator_returned_checks", False, "validator returned no checks")])
    return ValidationResult(all(c.passed for c in checks), checks)
