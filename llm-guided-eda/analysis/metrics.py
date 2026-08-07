"""Experiment records -> pandas DataFrames and per-configuration metrics.

Input: ``experiments/results/<experiment_id>/<config>.jsonl`` (one
:class:`~experiments.record_schema.EpisodeRecord` per line) plus ``metadata.json``.

Conventions used by every analysis module:

* Rates are percentages (0-100). A configuration's completion rate is computed
  per run (successes / episodes recorded in that run x 100) and summarised as the
  mean and sample standard deviation (ddof=1) over runs; ``pooled`` values
  divide totals by totals (identical to the mean when every run is complete).
* The *outcome* of an attempt is ``"success"`` when the validator passed,
  otherwise the executor error type (taxonomy of :mod:`openroad.log_parser`), or
  ``"validation_failure"`` when the script ran cleanly but the validator failed.
  Episodes without any attempt get ``"harness_error"`` (aborted by the
  harness) or ``"no_attempt"``.
* Duplicate records of one (config, run, task) -- a resumed experiment may append
  a re-run -- are collapsed without looking at the outcome: a record without a
  harness error beats one with, then the latest ``timestamp_end`` wins.
* Episodes aborted by a harness error count as failures unless the caller drops
  them (``drop_harness_errors``); either way they are counted in the coverage.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from benchmark.task_loader import CATEGORIES, DIFFICULTIES, SPLIT_FILES
from common.config import load_config
from common.paths import RESULTS_DIR
from experiments.record_schema import AttemptRecord, EpisodeRecord, LLMCallRecord

_EXPERIMENT_CFG = load_config("experiment_config")
CONFIG_ORDER: list[str] = list(_EXPERIMENT_CFG.get("configurations") or {})
DEFAULT_RUNS: int = int(_EXPERIMENT_CFG.get("runs_per_config", 1))
CATEGORY_ORDER: list[str] = list(CATEGORIES)
DIFFICULTY_ORDER: list[str] = list(DIFFICULTIES)

SUCCESS = "success"
VALIDATION_FAILURE = "validation_failure"
HARNESS_ERROR = "harness_error"
NO_ATTEMPT = "no_attempt"
UNKNOWN_ERROR = "unknown_error"   # execution failed but no error type was recorded

TOKEN_COLUMNS = ["input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"]

EPISODE_COLUMNS = [
    "experiment_id", "config", "run", "task_id", "category", "difficulty", "split", "rag", "feedback",
    "max_attempts", "success", "first_attempt_success", "attempts_used", "n_attempts",
    "agent_declared_success", "final_error_type", "first_error_type", "first_outcome", "final_outcome",
    "final_exec_error", "recovered", "failed_executions", "total_execution_time_s", "wall_time_s",
    "llm_calls", *TOKEN_COLUMNS, "cost_usd", "n_cached_calls", "model", "models_reported",
    "timestamp_start", "timestamp_end", "harness_error", "error", "inconsistencies", "source",
]
ATTEMPT_COLUMNS = [
    "config", "run", "task_id", "category", "difficulty", "feedback", "max_attempts", "attempt", "is_final",
    "exec_success", "error_type", "outcome", "error_message", "failing_line", "failing_command",
    "execution_time_s", "validator_passed", "agent_verdict_ok", "diagnosed_error_type", "n_retrieved_chunks",
    "n_llm_calls", "n_cached_calls", *TOKEN_COLUMNS, "cost_usd",
]
_NULLABLE_BOOL = {"agent_declared_success", "final_exec_error", "agent_verdict_ok"}

_EPISODE_FIELDS = {f.name for f in fields(EpisodeRecord)}
_ATTEMPT_FIELDS = {f.name for f in fields(AttemptRecord)}
_CALL_FIELDS = {f.name for f in fields(LLMCallRecord)}
NAN = float("nan")


# --------------------------------------------------------------------- ordering
def ordered(values: Iterable[Any], order: Sequence[Any]) -> list[Any]:
    """Distinct non-missing values: those listed in ``order`` first (in that order), then the rest sorted."""
    present = list(dict.fromkeys(v for v in values if not _missing(v)))
    head = [v for v in order if v in present]
    return head + sorted((v for v in present if v not in order), key=str)


def order_configs(values: Iterable[str]) -> list[str]:
    return ordered(values, CONFIG_ORDER)


def sort_frame(df: pd.DataFrame, cols: Sequence[str] = ("config",)) -> pd.DataFrame:
    """Sort by the canonical configuration / category / difficulty order (other columns as is)."""
    if df.empty:
        return df.reset_index(drop=True)
    orders = {"config": CONFIG_ORDER, "category": CATEGORY_ORDER, "difficulty": DIFFICULTY_ORDER}
    tmp = df.copy()
    keys = []
    for c in cols:
        if c in orders:
            rank = {v: i for i, v in enumerate(ordered(tmp[c], orders[c]))}
            tmp[f"__o_{c}"] = tmp[c].map(rank)
            keys.append(f"__o_{c}")
        else:
            keys.append(c)
    tmp = tmp.sort_values(keys, kind="stable")
    return tmp.drop(columns=[k for k in keys if k.startswith("__o_")]).reset_index(drop=True)


def _missing(v: Any) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA


def rate(k: float, n: float) -> float:
    """``100 * k / n``, NaN when ``n`` is 0."""
    return 100.0 * float(k) / float(n) if n else NAN


# ---------------------------------------------------------------------- loading
@dataclass
class LoadReport:
    """What happened while reading the records (reported with the coverage)."""
    files: dict[str, dict[str, Any]] = field(default_factory=dict)
    malformed_lines: int = 0
    lenient_records: int = 0          # parsed after dropping unknown keys (schema drift)
    duplicates_dropped: dict[str, int] = field(default_factory=dict)
    harness_errors_dropped: dict[str, int] = field(default_factory=dict)
    other_split_dropped: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentData:
    experiment_id: str
    episodes: pd.DataFrame            # one row per (config, run, task)
    attempts: pd.DataFrame            # one row per OpenROAD execution
    metadata: dict[str, Any]
    report: LoadReport
    source_dir: Path | None = None

    @property
    def configs(self) -> list[str]:
        return order_configs(self.episodes["config"])


def parse_record(obj: dict[str, Any]) -> tuple[EpisodeRecord, bool]:
    """Strict schema parse, retried without unknown keys; returns (record, parsed_leniently)."""
    try:
        return EpisodeRecord.from_dict(obj), False
    except TypeError:
        pass
    clean = {k: v for k, v in obj.items() if k in _EPISODE_FIELDS}
    clean["attempts"] = [
        {**{k: v for k, v in a.items() if k in _ATTEMPT_FIELDS},
         "llm_calls": [{k: v for k, v in c.items() if k in _CALL_FIELDS} for c in a.get("llm_calls") or []]}
        for a in obj.get("attempts") or []]
    return EpisodeRecord.from_dict(clean), True   # still raises if a required field is missing


def read_records(path: Path, report: LoadReport) -> list[EpisodeRecord]:
    """Read one JSONL file, skipping (and counting) malformed lines such as a truncated last line."""
    data = path.read_bytes()
    info = {"sha256": hashlib.sha256(data).hexdigest(), "lines": 0, "records": 0, "malformed": 0, "lenient": 0}
    records: list[EpisodeRecord] = []
    for line in data.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        info["lines"] += 1
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise TypeError("not a JSON object")
            rec, lenient = parse_record(obj)
            _episode_row(rec, path.name)        # type checks: raise on unusable values
            _attempt_rows(rec)
        except (ValueError, TypeError, KeyError, AttributeError):
            info["malformed"] += 1
            continue
        info["records"] += 1
        info["lenient"] += int(lenient)
        records.append(rec)
    report.files[path.name] = info
    report.malformed_lines += info["malformed"]
    report.lenient_records += info["lenient"]
    if info["lines"] and not info["records"]:
        report.warnings.append(f"{path.name}: no valid episode records in {info['lines']} lines")
    elif info["malformed"]:
        report.warnings.append(f"{path.name}: skipped {info['malformed']} malformed line(s)")
    return records


def load_experiment(experiment_id: str, results_root: Path | str | None = None, *, split: str | None = None,
                    drop_harness_errors: bool = False) -> ExperimentData:
    """Load ``<results_root>/<experiment_id>/*.jsonl`` and ``metadata.json``."""
    exp_dir = Path(results_root or RESULTS_DIR) / experiment_id
    if not exp_dir.is_dir():
        raise FileNotFoundError(f"no results directory {exp_dir}")
    report = LoadReport()
    metadata: dict[str, Any] = {}
    meta_path = exp_dir / "metadata.json"
    if meta_path.is_file():
        raw = meta_path.read_bytes()
        report.files["metadata.json"] = {"sha256": hashlib.sha256(raw).hexdigest()}
        try:
            loaded = json.loads(raw)
            metadata = loaded if isinstance(loaded, dict) else {"value": loaded}
        except ValueError as e:
            report.warnings.append(f"metadata.json unreadable: {e}")
    else:
        report.warnings.append("metadata.json missing")
    sources: list[tuple[EpisodeRecord, str]] = []
    for path in sorted(exp_dir.glob("*.jsonl")):
        for rec in read_records(path, report):
            if path.stem != rec.config:
                report.warnings.append(f"{path.name}: record for configuration {rec.config}")
            sources.append((rec, path.name))
    if not sources:
        report.warnings.append(f"no episode records under {exp_dir}")
    return build_experiment(experiment_id, sources, metadata, report, split=split,
                            drop_harness_errors=drop_harness_errors, source_dir=exp_dir)


def build_experiment(experiment_id: str, records: Sequence[EpisodeRecord | tuple[EpisodeRecord, str]],
                     metadata: dict[str, Any] | None = None, report: LoadReport | None = None, *,
                     split: str | None = None, drop_harness_errors: bool = False,
                     source_dir: Path | None = None) -> ExperimentData:
    """Deduplicate records and build the episode / attempt DataFrames."""
    report = report or LoadReport()
    best: dict[tuple[str, int, str], tuple[tuple, EpisodeRecord, str]] = {}
    dups: Counter[str] = Counter()
    for i, item in enumerate(records):
        rec, source = item if isinstance(item, tuple) else (item, "")
        key = (rec.config, int(rec.run), rec.task_id)
        rank = (rec.error is None, str(rec.timestamp_end or ""), i)
        if key in best:
            dups[rec.config] += 1
            if rank < best[key][0]:
                continue
        best[key] = (rank, rec, source)
    report.duplicates_dropped = dict(dups)

    kept: list[tuple[EpisodeRecord, str]] = []
    dropped_harness: Counter[str] = Counter()
    for _, rec, source in best.values():
        if split is not None and rec.split != split:
            report.other_split_dropped += 1
            continue
        if drop_harness_errors and rec.error is not None:
            dropped_harness[rec.config] += 1
            continue
        kept.append((rec, source))
    report.harness_errors_dropped = dict(dropped_harness)
    if split is None and len({r.split for r, _ in kept}) > 1:
        report.warnings.append(f"records mix task splits {sorted({r.split for r, _ in kept})}")
    ids = {r.experiment_id for r, _ in kept}
    if ids and ids != {experiment_id}:
        report.warnings.append(f"records carry experiment_id {sorted(ids)} (loaded as {experiment_id})")

    ep_rows = [_episode_row(rec, source) for rec, source in kept]
    at_rows = [row for rec, _ in kept for row in _attempt_rows(rec)]
    episodes = _typed(pd.DataFrame(ep_rows, columns=EPISODE_COLUMNS))
    attempts = _typed(pd.DataFrame(at_rows, columns=ATTEMPT_COLUMNS))
    episodes = sort_frame(episodes, ("config", "run", "task_id"))
    attempts = sort_frame(attempts, ("config", "run", "task_id", "attempt"))
    return ExperimentData(experiment_id, episodes, attempts, dict(metadata or {}), report, source_dir)


def _typed(df: pd.DataFrame) -> pd.DataFrame:
    ints = ["run", "max_attempts", "attempts_used", "n_attempts", "failed_executions", "llm_calls", "attempt",
            "n_cached_calls", "n_retrieved_chunks", "n_llm_calls", *TOKEN_COLUMNS]
    floats = ["total_execution_time_s", "wall_time_s", "cost_usd", "execution_time_s"]
    bools = ["feedback", "success", "first_attempt_success", "recovered", "harness_error", "is_final",
             "exec_success", "validator_passed"]
    for c in df.columns:
        if c in ints:
            df[c] = df[c].astype("int64")
        elif c == "failing_line":
            df[c] = df[c].astype("Int64")
        elif c in floats:
            df[c] = df[c].astype("float64")
        elif c in bools:
            df[c] = df[c].astype(bool)
        elif c in _NULLABLE_BOOL:
            df[c] = df[c].astype("boolean")
    return df


def first_word(script: str, line: int | None) -> str | None:
    """First word of a 1-based script line (the failing command), ignoring leading Tcl brackets."""
    if line is None or line < 1:
        return None
    lines = script.splitlines()
    if line > len(lines):
        return None
    text = lines[line - 1].strip().lstrip("{}[;").strip()
    if not text or text.startswith("#"):
        return None
    word = text.split()[0].rstrip("]};")
    return word or None


def _episode_row(rec: EpisodeRecord, source: str) -> dict[str, Any]:
    atts = sorted(rec.attempts, key=lambda a: int(a.attempt))
    first, last = (atts[0], atts[-1]) if atts else (None, None)
    success, first_ok = bool(rec.success), bool(rec.first_attempt_success)
    if first is None or last is None:
        first_outcome = HARNESS_ERROR if rec.error else NO_ATTEMPT
        final_outcome = SUCCESS if success else (HARNESS_ERROR if rec.error else (rec.final_error_type or NO_ATTEMPT))
    else:
        first_outcome = SUCCESS if first_ok else (first.error_type or VALIDATION_FAILURE)
        final_outcome = SUCCESS if success else (rec.final_error_type or last.error_type or VALIDATION_FAILURE)
    issues = []
    if int(rec.attempts_used) != len(atts):
        issues.append("attempts_used")
    if first is not None and bool(first.validator_passed) != first_ok:
        issues.append("first_attempt_success")
    if last is not None and bool(last.validator_passed) != success:
        issues.append("success")
    if int(rec.failed_executions) != sum(not a.exec_success for a in atts):
        issues.append("failed_executions")
    if any(bool(a.exec_success) == (a.error_type is not None) for a in atts):
        issues.append("exec_success_vs_error_type")
    if [int(a.attempt) for a in atts] != list(range(1, len(atts) + 1)):
        issues.append("attempt_numbering")
    if len(atts) > int(rec.max_attempts):
        issues.append("attempts_over_budget")
    calls = [c for a in atts for c in a.llm_calls]
    return {
        "experiment_id": rec.experiment_id, "config": rec.config, "run": int(rec.run), "task_id": rec.task_id,
        "category": rec.category or "unknown", "difficulty": rec.difficulty or "unknown", "split": rec.split,
        "rag": rec.rag, "feedback": bool(rec.feedback), "max_attempts": int(rec.max_attempts),
        "success": success, "first_attempt_success": first_ok, "attempts_used": int(rec.attempts_used),
        "n_attempts": len(atts),
        "agent_declared_success": None if rec.agent_declared_success is None else bool(rec.agent_declared_success),
        "final_error_type": rec.final_error_type, "first_error_type": first.error_type if first else None,
        "first_outcome": first_outcome, "final_outcome": final_outcome,
        "final_exec_error": None if last is None else last.error_type is not None,
        "recovered": (not first_ok) and success, "failed_executions": int(rec.failed_executions),
        "total_execution_time_s": float(rec.total_execution_time_s), "wall_time_s": float(rec.wall_time_s),
        "llm_calls": int(rec.llm_calls), **{c: int(getattr(rec, c)) for c in TOKEN_COLUMNS},
        "cost_usd": float(rec.cost_usd), "n_cached_calls": sum(bool(c.cached) for c in calls),
        "model": rec.model, "models_reported": ";".join(sorted({c.model_reported for c in calls if c.model_reported})),
        "timestamp_start": rec.timestamp_start, "timestamp_end": rec.timestamp_end,
        "harness_error": rec.error is not None, "error": rec.error, "inconsistencies": ";".join(issues),
        "source": source,
    }


def _attempt_rows(rec: EpisodeRecord) -> list[dict[str, Any]]:
    atts = sorted(rec.attempts, key=lambda a: int(a.attempt))
    rows = []
    for i, a in enumerate(atts):
        failed = (not a.exec_success) or a.error_type is not None
        outcome = SUCCESS if a.validator_passed else (a.error_type or (UNKNOWN_ERROR if failed else VALIDATION_FAILURE))
        line = int(a.failing_line) if a.failing_line is not None else None
        rows.append({
            "config": rec.config, "run": int(rec.run), "task_id": rec.task_id,
            "category": rec.category or "unknown", "difficulty": rec.difficulty or "unknown",
            "feedback": bool(rec.feedback), "max_attempts": int(rec.max_attempts), "attempt": int(a.attempt),
            "is_final": i == len(atts) - 1, "exec_success": bool(a.exec_success), "error_type": a.error_type,
            "outcome": outcome, "error_message": a.error_message, "failing_line": line,
            "failing_command": first_word(a.script, line) if failed else None,
            "execution_time_s": float(a.execution_time_s), "validator_passed": bool(a.validator_passed),
            "agent_verdict_ok": None if a.agent_verdict_ok is None else bool(a.agent_verdict_ok),
            "diagnosed_error_type": a.diagnosed_error_type, "n_retrieved_chunks": len(a.retrieved_chunk_ids),
            "n_llm_calls": len(a.llm_calls), "n_cached_calls": sum(bool(c.cached) for c in a.llm_calls),
            **{c: sum(int(getattr(x, c)) for x in a.llm_calls) for c in TOKEN_COLUMNS},
            "cost_usd": sum(float(x.cost_usd) for x in a.llm_calls),
        })
    return rows


# ------------------------------------------------------------------ rate tables
def per_run_rates(episodes: pd.DataFrame, column: str = "success", by: Sequence[str] = ()) -> pd.DataFrame:
    """Rate (%) of a boolean episode column per (config, *by, run): columns n, k, rate."""
    keys = ["config", *by, "run"]
    if episodes.empty:
        return pd.DataFrame(columns=[*keys, "n", "k", "rate"])
    df = episodes[keys].copy()
    df["__v"] = episodes[column].astype(bool)
    out = df.groupby(keys, sort=False, dropna=False)["__v"].agg(n="size", k="sum").reset_index()
    out["k"] = out["k"].astype("int64")
    out["rate"] = 100.0 * out["k"] / out["n"]
    return sort_frame(out, keys)


def summarize_runs(per_run: pd.DataFrame, by: Sequence[str] = ()) -> pd.DataFrame:
    """Mean and sample std (ddof=1) over runs of a :func:`per_run_rates` table."""
    keys = ["config", *by]
    cols = [*keys, "n_runs", "n_episodes", "successes", "mean", "std", "pooled", "runs", "run_ids"]
    rows = []
    for key, grp in per_run.groupby(keys, sort=False, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        grp = grp.sort_values("run")
        rates = grp["rate"].to_numpy(float)
        rows.append({
            **dict(zip(keys, key)), "n_runs": len(rates), "n_episodes": int(grp["n"].sum()),
            "successes": int(grp["k"].sum()), "mean": float(rates.mean()),
            "std": float(rates.std(ddof=1)) if len(rates) > 1 else NAN,
            "pooled": rate(grp["k"].sum(), grp["n"].sum()),
            "runs": [float(r) for r in rates], "run_ids": [int(r) for r in grp["run"]],
        })
    return sort_frame(pd.DataFrame(rows, columns=cols), keys)


def rate_summary(episodes: pd.DataFrame, column: str = "success", by: Sequence[str] = ()) -> pd.DataFrame:
    """Per-run rate of ``column`` summarised over runs (mean, std, pooled, per-run values)."""
    out = summarize_runs(per_run_rates(episodes, column, by), by)
    if by and not out.empty:
        n_tasks = episodes.groupby(["config", *by], sort=False)["task_id"].nunique().rename("n_tasks").reset_index()
        out = out.merge(n_tasks, on=["config", *by], how="left")
    return out


def completion_by(episodes: pd.DataFrame, column: str) -> pd.DataFrame:
    """Completion rate per configuration and ``column`` (``"category"`` or ``"difficulty"``)."""
    return rate_summary(episodes, "success", (column,))


# ------------------------------------------------------------ headline metrics
def config_info(episodes: pd.DataFrame) -> pd.DataFrame:
    """Retrieval mode, feedback flag and attempt budget per configuration, as recorded."""
    rows = []
    for cfg in order_configs(episodes["config"]):
        ep = episodes[episodes["config"] == cfg]
        consistent = all(ep[c].nunique(dropna=False) <= 1 for c in ("rag", "feedback", "max_attempts"))
        modes = ep["rag"].dropna().astype(str).mode()
        rows.append({"config": cfg, "rag": str(modes.iloc[0]) if len(modes) else "unknown",
                     "feedback": bool(ep["feedback"].any()),
                     "max_attempts": int(ep["max_attempts"].max()), "consistent": consistent,
                     "models": ";".join(sorted(set(ep["model"].dropna().astype(str))))})
    return pd.DataFrame(rows, columns=["config", "rag", "feedback", "max_attempts", "consistent", "models"])


def main_results(episodes: pd.DataFrame) -> pd.DataFrame:
    """One row per configuration with the headline metrics.

    * completion / first-attempt success: per-run rates, mean and sample std over runs;
    * recovery rate: episodes whose attempt 1 failed the validator but whose final
      attempt passed / episodes whose attempt 1 failed x 100 (pooled over runs;
      episodes without any attempt are excluded; NaN for single-shot
      configurations, where no repair is possible);
    * failed executions: mean ``failed_executions`` per episode;
    * final execution-failure rate: % of episodes whose final attempt had a
      non-null ``error_type`` (episodes with at least one attempt);
    * rejected correct first attempts: episodes whose attempt 1 passed the validator
      but whose agent self-check rejected it, so the agent kept repairing (and how
      many of those ended failed). They are why first-attempt success can exceed
      cumulative success at k = 1, which counts episodes that *ended* after attempt 1;
    * mean attempts, OpenROAD execution time and wall time per episode.
    """
    info = config_info(episodes).set_index("config")
    comp = rate_summary(episodes, "success").set_index("config")
    first = rate_summary(episodes, "first_attempt_success").set_index("config")
    rows = []
    for cfg in order_configs(episodes["config"]):
        ep = episodes[episodes["config"] == cfg]
        attempted = ep[ep["n_attempts"] > 0]
        # an episode aborted before attempt 1 (harness error) has no attempt 1 that could have failed
        first_failed = ~ep["first_attempt_success"] & (ep["n_attempts"] > 0)
        n_ff, n_rec = int(first_failed.sum()), int((first_failed & ep["success"]).sum())
        rejected = ep["first_attempt_success"] & (ep["attempts_used"] > 1)
        single_shot = int(info.at[cfg, "max_attempts"]) <= 1
        rows.append({
            "config": cfg, "rag": info.at[cfg, "rag"], "feedback": bool(info.at[cfg, "feedback"]),
            "max_attempts": int(info.at[cfg, "max_attempts"]), "n_runs": int(comp.at[cfg, "n_runs"]),
            "n_tasks": int(ep["task_id"].nunique()), "n_episodes": len(ep), "successes": int(ep["success"].sum()),
            "completion_mean": comp.at[cfg, "mean"], "completion_std": comp.at[cfg, "std"],
            "completion_pooled": comp.at[cfg, "pooled"], "completion_runs": comp.at[cfg, "runs"],
            "run_ids": comp.at[cfg, "run_ids"],
            "first_attempt_mean": first.at[cfg, "mean"], "first_attempt_std": first.at[cfg, "std"],
            "first_attempt_pooled": first.at[cfg, "pooled"],
            "n_first_failed": n_ff, "n_recovered": n_rec, "recovery_rate": NAN if single_shot else rate(n_rec, n_ff),
            "n_first_rejected": int(rejected.sum()), "n_first_rejected_lost": int((rejected & ~ep["success"]).sum()),
            "failed_executions_mean": float(ep["failed_executions"].mean()),
            "final_exec_failure_rate": rate(int(attempted["final_exec_error"].sum()), len(attempted)),
            "attempts_mean": float(ep["attempts_used"].mean()),
            "exec_time_mean_s": float(ep["total_execution_time_s"].mean()),
            "wall_time_mean_s": float(ep["wall_time_s"].mean()),
            "cost_per_episode_usd": float(ep["cost_usd"].mean()),
            "harness_errors": int(ep["harness_error"].sum()),
        })
    return pd.DataFrame(rows)


def cost_table(episodes: pd.DataFrame) -> pd.DataFrame:
    """Token usage and cost per episode and per successful episode.

    ``*_per_episode`` is the mean over all episodes; ``*_per_success`` is the
    total over all episodes (failed ones included) divided by the number of
    successful episodes, i.e. what one solved task costs; ``cost_mean_successful_usd``
    is the mean cost of the successful episodes alone.
    """
    rows = []
    for cfg in order_configs(episodes["config"]):
        ep = episodes[episodes["config"] == cfg]
        s = int(ep["success"].sum())
        per_run_cost = ep.groupby("run")["cost_usd"].mean()
        total_tokens = ep[TOKEN_COLUMNS].sum(axis=1)
        row: dict[str, Any] = {"config": cfg, "n_episodes": len(ep), "successes": s,
                               "llm_calls_per_episode": float(ep["llm_calls"].mean()),
                               "cached_calls": int(ep["n_cached_calls"].sum())}
        for c in TOKEN_COLUMNS:
            row[f"{c}_per_episode"] = float(ep[c].mean())
            row[f"{c}_per_success"] = float(ep[c].sum()) / s if s else NAN
        row["total_tokens_per_episode"] = float(total_tokens.mean())
        row["total_tokens_per_success"] = float(total_tokens.sum()) / s if s else NAN
        row["cost_total_usd"] = float(ep["cost_usd"].sum())
        row["cost_per_episode_usd"] = float(ep["cost_usd"].mean())
        row["cost_per_episode_std_runs"] = float(per_run_cost.std(ddof=1)) if len(per_run_cost) > 1 else NAN
        row["cost_per_success_usd"] = float(ep["cost_usd"].sum()) / s if s else NAN
        row["cost_mean_successful_usd"] = float(ep.loc[ep["success"], "cost_usd"].mean()) if s else NAN
        rows.append(row)
    return pd.DataFrame(rows)


def cumulative_success(episodes: pd.DataFrame) -> pd.DataFrame:
    """% of episodes that ended successfully within k attempts (success and attempts_used <= k), per run.

    At k = 1 this is below first-attempt success when the agent's self-check rejected a correct
    attempt 1 and kept repairing (``n_first_rejected`` in :func:`main_results`).
    """
    rows = []
    for cfg in order_configs(episodes["config"]):
        ep = episodes[episodes["config"] == cfg]
        for k in range(1, int(ep["max_attempts"].max()) + 1):
            solved = ep["success"] & (ep["attempts_used"] <= k)
            per_run = 100.0 * solved.groupby(ep["run"]).mean()
            rows.append({"config": cfg, "attempt": k, "n_runs": len(per_run), "mean": float(per_run.mean()),
                         "std": float(per_run.std(ddof=1)) if len(per_run) > 1 else NAN,
                         "pooled": rate(int(solved.sum()), len(ep))})
    return pd.DataFrame(rows, columns=["config", "attempt", "n_runs", "mean", "std", "pooled"])


def confusion(declared: pd.Series, actual: pd.Series) -> dict[str, Any]:
    """Agent claim vs validator verdict; rows without a claim are counted, not scored.

    precision = TP / (TP + FP); recall = TP / (TP + FN);
    false-success rate = FP / (FP + TN), the share of validator failures the agent declared successful.
    """
    declared = declared.astype("boolean")
    mask = declared.notna().to_numpy(bool)
    d = declared[mask].astype(bool).to_numpy()
    a = actual.astype(bool).to_numpy()[mask]
    tp, fp = int((d & a).sum()), int((d & ~a).sum())
    fn, tn = int((~d & a).sum()), int((~d & ~a).sum())
    return {"n": int(mask.sum()), "n_undeclared": int((~mask).sum()), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": rate(tp, tp + fp), "recall": rate(tp, tp + fn), "false_success_rate": rate(fp, fp + tn),
            "accuracy": rate(tp + tn, tp + fp + fn + tn)}


def calibration(episodes: pd.DataFrame, attempts: pd.DataFrame) -> pd.DataFrame:
    """Agent self-verification vs validator, for feedback configurations.

    ``episode`` level compares ``agent_declared_success`` with the episode
    success; ``attempt`` level compares each attempt's ``agent_verdict_ok`` with
    that attempt's validator verdict.
    """
    rows = []
    for cfg in order_configs(episodes.loc[episodes["feedback"], "config"]):
        ep = episodes[episodes["config"] == cfg]
        rows.append({"config": cfg, "level": "episode", **confusion(ep["agent_declared_success"], ep["success"])})
        at = attempts[attempts["config"] == cfg]
        rows.append({"config": cfg, "level": "attempt", **confusion(at["agent_verdict_ok"], at["validator_passed"])})
    cols = ["config", "level", "n", "n_undeclared", "tp", "fp", "fn", "tn", "precision", "recall",
            "false_success_rate", "accuracy"]
    return pd.DataFrame(rows, columns=cols)


# --------------------------------------------------------------------- coverage
def expected_design(metadata: dict[str, Any], episodes: pd.DataFrame) -> dict[str, Any]:
    """Expected task ids, runs per configuration and configurations, and where each came from.

    ``metadata.json`` wins when it states them; otherwise the benchmark split
    file (only if every recorded task belongs to it), ``config/experiment_config.yaml``,
    or finally what was recorded.
    """
    observed_tasks = sorted(set(episodes["task_id"]))
    tasks, task_src = _meta_ids(metadata, ("task_ids", "tasks")), "metadata"
    if not tasks:
        tasks, task_src = _benchmark_ids({str(s) for s in episodes["split"].dropna()}), "benchmark task file"
        if not tasks or not set(observed_tasks) <= set(tasks):
            tasks, task_src = observed_tasks, "recorded episodes"
    runs, runs_src = _meta_int(metadata, ("runs_per_config", "runs", "n_runs")), "metadata"
    if runs is None:
        runs, runs_src = DEFAULT_RUNS, "config/experiment_config.yaml"
    max_seen = int(episodes.groupby("config")["run"].nunique().max()) if not episodes.empty else 0
    if max_seen > runs:
        runs, runs_src = max_seen, f"recorded episodes (more than the {runs} expected)"
    configs, cfg_src = _meta_ids(metadata, ("configurations", "configs", "config_names")), "metadata"
    if not configs:
        configs, cfg_src = list(CONFIG_ORDER), "config/experiment_config.yaml"
    configs = order_configs([*configs, *episodes["config"]])
    return {"task_ids": list(tasks), "n_tasks": len(tasks), "tasks_source": task_src,
            "runs_per_config": int(runs), "runs_source": runs_src, "configs": configs, "configs_source": cfg_src}


def _meta_ids(metadata: dict[str, Any], keys: Sequence[str]) -> list[str]:
    for k in keys:
        v = metadata.get(k)
        if isinstance(v, dict) and v:
            return [str(x) for x in v]
        if isinstance(v, list) and v:
            ids = [x.get("id", x.get("task_id")) if isinstance(x, dict) else x for x in v]
            return [str(x) for x in ids if isinstance(x, (str, int))]
    return []


def _meta_int(metadata: dict[str, Any], keys: Sequence[str]) -> int | None:
    for k in keys:
        v = metadata.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, int) and v > 0:
            return v
        if isinstance(v, list) and v:
            return len(v)
    return None


def _benchmark_ids(splits: set[str]) -> list[str]:
    ids: list[str] = []
    for s in sorted(splits):
        path = SPLIT_FILES.get(s)
        if path is None or not path.is_file():
            continue
        try:
            ids += [str(t["id"]) for t in json.loads(path.read_text())]
        except (ValueError, KeyError, TypeError):
            continue
    return ids


def coverage(data: ExperimentData) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Recorded vs expected episodes per configuration; returns (table, details incl. missing tasks)."""
    eps = data.episodes
    design = expected_design(data.metadata, eps)
    expected_tasks = set(design["task_ids"])
    n_runs = design["runs_per_config"]
    rows, missing = [], {}
    for cfg in design["configs"]:
        ep = eps[eps["config"] == cfg]
        run_ids = sorted(int(r) for r in ep["run"].unique())
        recorded = ep[ep["task_id"].isin(expected_tasks)]
        miss = {str(r): sorted(expected_tasks - set(ep.loc[ep["run"] == r, "task_id"])) for r in run_ids}
        miss = {r: t for r, t in miss.items() if t}
        n_missing = sum(len(t) for t in miss.values()) + max(n_runs - len(run_ids), 0) * len(expected_tasks)
        if miss or len(run_ids) < n_runs:
            missing[cfg] = {"runs_missing_entirely": max(n_runs - len(run_ids), 0), "missing_tasks_by_run": miss}
        expected = len(expected_tasks) * n_runs
        rows.append({
            "config": cfg, "expected_episodes": expected, "recorded_episodes": len(ep),
            "coverage_pct": rate(len(recorded), expected), "missing_episodes": n_missing,
            "unexpected_episodes": int(len(ep) - len(recorded)), "runs": run_ids,
            "n_tasks": int(ep["task_id"].nunique()), "harness_errors": int(ep["harness_error"].sum()),
            "harness_errors_dropped": int(data.report.harness_errors_dropped.get(cfg, 0)),
            "duplicates_dropped": int(data.report.duplicates_dropped.get(cfg, 0)),
            "inconsistent_records": int((ep["inconsistencies"] != "").sum()),
        })
    details = {**{k: v for k, v in design.items() if k != "task_ids"}, "missing": missing,
               "inconsistency_counts": _issue_counts(eps)}
    return pd.DataFrame(rows), details


def _issue_counts(episodes: pd.DataFrame) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for cfg in order_configs(episodes["config"]):
        c: Counter[str] = Counter()
        for s in episodes.loc[episodes["config"] == cfg, "inconsistencies"]:
            c.update(x for x in str(s).split(";") if x)
        if c:
            out[cfg] = dict(sorted(c.items()))
    return out


def models_reported(episodes: pd.DataFrame) -> dict[str, list[str]]:
    """Model ids echoed by the API per configuration (provenance)."""
    out = {}
    for cfg in order_configs(episodes["config"]):
        vals = episodes.loc[episodes["config"] == cfg, "models_reported"].dropna().astype(str)
        out[cfg] = sorted({m for v in vals for m in v.split(";") if m})
    return out


def as_float(v: Any) -> float:
    """Float or NaN (for table cells that may hold None)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return NAN
    return f if np.isfinite(f) else NAN
