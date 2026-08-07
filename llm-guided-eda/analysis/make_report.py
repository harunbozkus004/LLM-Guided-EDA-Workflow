"""Build the report tables, figures and headline numbers of one experiment.

    python -m analysis.make_report --experiment <id> [--out-dir paper] [--results-root experiments/results]

Writes

    <out>/tables/<name>.csv        full-precision values
    <out>/tables/<name>.md         formatted tables with their definitions
    <out>/figures/<name>.png|pdf   300-dpi PNG and vector PDF
    <out>/results_summary.json     every headline number cited by the paper

Every number is computed from the episode records of
``<results-root>/<id>/*.jsonl``; expected counts (tasks, runs) come from
``metadata.json``, the benchmark task file or ``config/experiment_config.yaml``
and are only used to report coverage. Existing files of the same name are
overwritten; nothing else in the output directory is touched.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd

from common.config import resolve
from common.paths import PAPER_DIR, rel
from analysis import error_analysis as ea
from analysis import metrics as mx
from analysis import statistics as st

NA = "n/a"


# ------------------------------------------------------------------ formatting
def fnum(v: Any, digits: int = 1) -> str:
    f = mx.as_float(v)
    return NA if math.isnan(f) else f"{f:.{digits}f}"


def fpm(mean: Any, std: Any, digits: int = 1) -> str:
    m, s = mx.as_float(mean), mx.as_float(std)
    if math.isnan(m):
        return NA
    return f"{m:.{digits}f}" if math.isnan(s) else f"{m:.{digits}f} \u00b1 {s:.{digits}f}"


def fp(p: Any) -> str:
    f = mx.as_float(p)
    if math.isnan(f):
        return NA
    return "<0.001" if f < 0.001 else f"{f:.3f}"


def fp_eq(p: Any) -> str:
    """``p = 0.123`` / ``p < 0.001`` for running text."""
    s = fp(p)
    return f"p {s[0]} {s[1:]}" if s.startswith("<") else f"p = {s}"


def fint(v: Any) -> str:
    f = mx.as_float(v)
    return NA if math.isnan(f) else str(int(round(f)))


def fruns(values: Any, digits: int = 1) -> str:
    return " / ".join(fnum(v, digits) for v in (values or [])) or NA


def md_table(df: pd.DataFrame) -> str:
    """GitHub-flavoured Markdown table (cells are rendered with ``str``)."""
    def cell(v: Any) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(cell(c) for c in df.columns) + " |",
             "|" + "|".join("---" for _ in df.columns) + "|"]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def _csv_ready(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if out[c].map(lambda v: isinstance(v, (list, tuple))).any():
            out[c] = out[c].map(lambda v: ";".join(str(x) for x in v) if isinstance(v, (list, tuple)) else v)
    return out


# --------------------------------------------------------------------- tables
def compute_tables(data: mx.ExperimentData, *, n_boot: int = st.N_BOOT, seed: int = st.SEED) -> dict[str, Any]:
    """Every table of the report as DataFrames (plus Cochran's Q and coverage details as dicts)."""
    ep, at = data.episodes, data.attempts
    coverage, coverage_details = mx.coverage(data)
    return {
        "settings": {"n_boot": n_boot, "seed": seed},
        "coverage": coverage, "coverage_details": coverage_details,
        "main_results": mx.main_results(ep),
        "per_category": mx.completion_by(ep, "category"),
        "per_difficulty": mx.completion_by(ep, "difficulty"),
        "cost": mx.cost_table(ep),
        "calibration": mx.calibration(ep, at),
        "cumulative_success": mx.cumulative_success(ep),
        "statistics": st.planned_comparisons(ep, n_boot=n_boot, seed=seed),
        "follow_up": st.planned_comparisons(ep, st.FOLLOW_UP_CONTRASTS, n_boot=n_boot, seed=seed),
        "cochran_q": st.cochran_q(ep, [c for c in st.ABLATION_CONFIGS if c in set(ep["config"])]),
        "errors": ea.error_distribution(ep, at),
        "transitions": ea.transition_table(ep),
        "recovery_by_error": ea.recovery_by_first_outcome(ep),
        "failing_commands": ea.failing_commands(at),
        "task_profiles": ea.task_profiles(ep),
    }


def _md_coverage(t: dict[str, Any], data: mx.ExperimentData) -> str:
    d, rep = t["coverage_details"], data.report
    df = t["coverage"]
    view = pd.DataFrame({
        "Configuration": df["config"], "Expected": df["expected_episodes"].map(fint),
        "Recorded": df["recorded_episodes"].map(fint), "Coverage %": df["coverage_pct"].map(fnum),
        "Missing": df["missing_episodes"].map(fint), "Runs": df["runs"].map(lambda r: ", ".join(map(str, r)) or NA),
        "Tasks": df["n_tasks"].map(fint), "Harness errors": df["harness_errors"].map(fint),
        "Duplicates dropped": df["duplicates_dropped"].map(fint),
        "Inconsistent records": df["inconsistent_records"].map(fint),
    })
    notes = [
        f"Expected design: {d['n_tasks']} tasks (source: {d['tasks_source']}) x {d['runs_per_config']} runs "
        f"(source: {d['runs_source']}); configurations from {d['configs_source']}.",
        f"Malformed lines skipped: {rep.malformed_lines}; records parsed after dropping unknown fields: "
        f"{rep.lenient_records}; records of another split dropped: {rep.other_split_dropped}.",
        "Harness errors are episodes aborted by an exception in the experiment harness; they count as failures "
        "unless the report was built with --exclude-harness-errors (then they are missing episodes).",
    ]
    if d["inconsistency_counts"]:
        notes.append("Inconsistent records (episode fields that disagree with their attempts): "
                     + "; ".join(f"{c}: {v}" for c, v in d["inconsistency_counts"].items()))
    notes += [f"Warning: {w}" for w in rep.warnings]
    return _doc("Data coverage", notes, md_table(view))


def _md_main(t: dict[str, Any]) -> str:
    df = t["main_results"]
    view = pd.DataFrame({
        "Configuration": df["config"], "RAG": df["rag"], "Feedback": df["feedback"].map({True: "yes", False: "no"}),
        "Max attempts": df["max_attempts"], "Episodes": df["n_episodes"],
        "Completion % (mean \u00b1 SD)": [fpm(m, s) for m, s in zip(df["completion_mean"], df["completion_std"])],
        "Per run %": df["completion_runs"].map(fruns),
        "First-attempt %": [fpm(m, s) for m, s in zip(df["first_attempt_mean"], df["first_attempt_std"])],
        "Recovery %": [f"{fnum(r)} ({k}/{n})" if not math.isnan(mx.as_float(r)) else NA
                       for r, k, n in zip(df["recovery_rate"], df["n_recovered"], df["n_first_failed"])],
        "Correct attempt 1 rejected (then lost)": [f"{k} ({l})" if m > 1 else NA for k, l, m in
                                                   zip(df["n_first_rejected"], df["n_first_rejected_lost"],
                                                       df["max_attempts"])],
        "Failed exec./task": df["failed_executions_mean"].map(lambda v: fnum(v, 2)),
        "Final exec. failure %": df["final_exec_failure_rate"].map(fnum),
        "Attempts": df["attempts_mean"].map(lambda v: fnum(v, 2)),
        "Exec. time (s)": df["exec_time_mean_s"].map(fnum), "Wall time (s)": df["wall_time_mean_s"].map(fnum),
    })
    notes = [
        "Completion and first-attempt success: per-run rate (successes / episodes recorded in the run x 100); "
        "mean and sample SD (ddof=1) over runs.",
        "Recovery: episodes whose attempt 1 failed the validator but whose final attempt passed / episodes whose "
        "attempt 1 failed (pooled over runs; n/a for single-shot configurations).",
        "Failed exec./task: mean number of failed OpenROAD executions (error, timeout or policy rejection) per "
        "episode. Final exec. failure: % of episodes whose final script did not execute cleanly.",
        "Correct attempt 1 rejected: episodes whose attempt 1 passed the validator but failed the agent's own "
        "self-check, so the agent kept repairing; in parentheses, how many of them then ended failed. First-attempt "
        "success counts these episodes; cumulative success at k = 1 (episodes that ended after one attempt) does not.",
        "Exec. time: total OpenROAD execution time per episode; wall time: whole episode incl. LLM calls.",
    ]
    return _doc("Main results", notes, md_table(view))


def _md_group(t: dict[str, Any], key: str, title: str) -> str:
    df = t[key]
    col = "category" if key == "per_category" else "difficulty"
    configs = mx.order_configs(df["config"])
    groups = mx.ordered(df[col], mx.CATEGORY_ORDER if col == "category" else mx.DIFFICULTY_ORDER)
    rows = []
    for g in groups:
        sub = df[df[col] == g].set_index("config")
        n = int(sub["n_tasks"].max()) if len(sub) else 0
        rows.append({col.capitalize(): g, "Tasks": n,
                     **{c: fpm(sub.at[c, "mean"], sub.at[c, "std"]) if c in sub.index else NA for c in configs}})
    notes = [f"Completion % per {col} (mean \u00b1 SD over runs of the per-run rate within the {col}). "
             "Tasks = number of distinct tasks recorded."]
    return _doc(title, notes, md_table(pd.DataFrame(rows)))


def _md_statistics(t: dict[str, Any], key: str = "statistics") -> str:
    df = t[key]
    view = pd.DataFrame({
        "Contrast (a vs b)": df["contrast"], "Effect": df["label"], "Tasks": df["n_tasks"].map(fint),
        "a %": df["mean_a"].map(fnum), "b %": df["mean_b"].map(fnum),
        "\u0394 b\u2212a (pp) [95% CI]": [f"{fnum(d)} [{fnum(lo)}, {fnum(hi)}]" if not math.isnan(mx.as_float(d)) else NA
                                          for d, lo, hi in zip(df["diff_pp"], df["ci_low_pp"], df["ci_high_pp"])],
        "McNemar runs: a-only/b-only": [f"{fint(x)}/{fint(y)}" for x, y in zip(df["runs_n10"], df["runs_n01"])],
        "p runs (Holm)": [f"{fp(p)} ({fp(h)})" for p, h in zip(df["mcnemar_runs_p"], df["mcnemar_runs_p_holm"])],
        "McNemar majority: a-only/b-only": [f"{fint(x)}/{fint(y)}" for x, y in zip(df["majority_n10"],
                                                                                    df["majority_n01"])],
        "p majority (Holm)": [f"{fp(p)} ({fp(h)})" for p, h in zip(df["mcnemar_majority_p"],
                                                                    df["mcnemar_majority_p_holm"])],
        "Wilcoxon p (Holm)": [f"{fp(p)} ({fp(h)})" for p, h in zip(df["wilcoxon_p"], df["wilcoxon_p_holm"])],
        "Note": df["note"].fillna(""),
    })
    q = t["cochran_q"]
    q_line = (f"Cochran's Q over {q['k']} configurations ({', '.join(q['configs'])}) on per-task majority outcomes "
              f"of {q['n_tasks']} tasks recorded for all of them: Q = {fnum(q['statistic'], 2)}, df = {q['df']}, "
              f"{fp_eq(q['p'])}." + (f" ({q['note']})" if q.get("note") else ""))
    s = t["settings"]
    notes = [
        "\u0394 = mean completion of b minus a over the tasks recorded for both (per-task success averaged over "
        f"runs); 95% CI: percentile paired bootstrap over tasks ({s['n_boot']:,} replicates, seed {s['seed']}).",
        "McNemar: exact two-sided test on discordant pairs; 'runs' pairs (task, run) by run index, 'majority' "
        "pairs per-task majority outcomes (solved in more than half of the runs). a-only / b-only = pairs solved "
        "only by a / only by b.",
        f"Wilcoxon signed-rank on per-task success rates, zero_method='{st.WILCOXON_ZERO_METHOD}' (zero "
        f"differences ranked, then dropped), {st.WILCOXON_METHOD} normal approximation with tie correction; "
        "p = 1 when every difference is zero.",
        "Holm-Bonferroni adjustment within each test family across the planned contrasts with data.",
        q_line,
    ]
    if key == "follow_up":
        notes[-2:] = ["Follow-up contrasts were added after the planned analysis and form their own Holm family "
                      "(one contrast: adjusted p = unadjusted p); the planned contrasts are unaffected."]
        return _doc("Statistical comparisons (follow-up contrasts)", notes, md_table(view))
    return _doc("Statistical comparisons (planned contrasts)", notes, md_table(view))


def _md_errors(t: dict[str, Any]) -> str:
    df = t["errors"]
    configs = mx.order_configs(df["config"])
    parts = []
    for stage, title in ea.STAGES.items():
        sub = df[df["stage"] == stage]
        rows = []
        for o in ea.outcome_order(sub["outcome"]):
            row: dict[str, Any] = {"Outcome": o}
            for c in configs:
                hit = sub[(sub["config"] == c) & (sub["outcome"] == o)]
                row[c] = f"{int(hit['count'].iloc[0])} ({fnum(hit['pct'].iloc[0])}%)" if len(hit) else "0"
            rows.append(row)
        totals = {"Outcome": "total"}
        for c in configs:
            n = sub.loc[sub["config"] == c, "n"]
            totals[c] = str(int(n.iloc[0])) if len(n) else "0"
        rows.append(totals)
        parts.append(f"## {title[0].upper() + title[1:]}\n\n" + md_table(pd.DataFrame(rows)))
    notes = ["Outcome = 'success', the executor error type, or 'validation_failure' (script ran cleanly but the "
             "validator failed). Cells: count (%)."]
    return _doc("Error types", notes, "\n\n".join(parts))


def _md_transitions(t: dict[str, Any]) -> str:
    df = t["recovery_by_error"]
    view = pd.DataFrame({
        "Configuration": df["config"], "Attempt-1 outcome": df["first_outcome"], "Episodes": df["n"],
        "Recovered": df["recovered"], "Recovery %": df["recovery_rate"].map(fnum),
        "Same failure at end": df["same_final"], "Mean attempts": df["mean_attempts"].map(lambda v: fnum(v, 2)),
    })
    notes = ["Episodes of multi-attempt configurations whose attempt 1 failed the validator, by the attempt-1 "
             "outcome. Recovered = the final attempt passed. The full attempt-1 -> final outcome matrix is in "
             "error_transitions.csv."]
    return _doc("Error transitions (attempt 1 -> final)", notes, md_table(view))


def _md_commands(t: dict[str, Any]) -> str:
    df = t["failing_commands"]
    overall = df[df["scope"] == "all"]
    configs = [c for c in mx.order_configs(df.loc[df["scope"] != "all", "scope"])]
    rows = []
    for r in overall.itertuples(index=False):
        row: dict[str, Any] = {"Rank": r.rank, "Command": f"`{r.command}`", "All": f"{r.count} ({fnum(r.pct)}%)",
                               "Most common error": r.top_error_type}
        for c in configs:
            hit = df[(df["scope"] == c) & (df["command"] == r.command)]
            row[c] = int(hit["count"].iloc[0]) if len(hit) else "-"
        rows.append(row)
    n_failed = int(overall["n_failed"].iloc[0]) if len(overall) else 0
    n_loc = int(overall["n_located"].iloc[0]) if len(overall) else 0
    notes = [f"First word of the failing script line, over the {n_loc} of {n_failed} failed executions whose "
             "failing line is known (policy rejections and timeouts have none). Per-configuration columns count "
             "occurrences ('-' = not among that configuration's top commands)."]
    return _doc("Most common failing commands", notes, md_table(pd.DataFrame(rows)) if rows else "(none)")


def _md_profiles(t: dict[str, Any]) -> str:
    df = t["task_profiles"]
    configs = ea.profile_configs(df)
    view = pd.DataFrame({"Task": df["task_id"], "Category": df["category"], "Difficulty": df["difficulty"],
                         **{c: df[c].map(lambda v: fnum(v, 0)) for c in configs},
                         "Profile": df["profile"].str.replace("_", " "),
                         "Run-dependent": df["run_dependent"].map({True: "yes", False: "no"})})
    counts = ea.profile_counts(df)
    notes = ["Per-configuration cells: success rate % over runs. Profile: never solved (no successful episode), "
             "always solved (every episode succeeded) or configuration-dependent; run-dependent = outcome varied "
             "between runs of at least one configuration.",
             "Counts: " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in counts.items())
             + f"; run-dependent {int(df['run_dependent'].sum()) if len(df) else 0}."]
    return _doc("Per-task profile", notes, md_table(view))


def _md_cost(t: dict[str, Any]) -> str:
    df = t["cost"]
    view = pd.DataFrame({
        "Configuration": df["config"], "LLM calls/task": df["llm_calls_per_episode"].map(lambda v: fnum(v, 2)),
        "Input tok/task": df["input_tokens_per_episode"].map(lambda v: fnum(v, 0)),
        "Output tok/task": df["output_tokens_per_episode"].map(lambda v: fnum(v, 0)),
        "Cache-read tok/task": df["cache_read_tokens_per_episode"].map(lambda v: fnum(v, 0)),
        "Cache-write tok/task": df["cache_write_tokens_per_episode"].map(lambda v: fnum(v, 0)),
        "Cost/task (USD)": df["cost_per_episode_usd"].map(lambda v: fnum(v, 4)),
        "Cost/solved task (USD)": df["cost_per_success_usd"].map(lambda v: fnum(v, 4)),
        "Tokens/solved task": df["total_tokens_per_success"].map(lambda v: fnum(v, 0)),
        "Total cost (USD)": df["cost_total_usd"].map(lambda v: fnum(v, 2)),
    })
    notes = ["Per task = mean over all episodes. Per solved task = total over all episodes (failed ones included) "
             "divided by the number of successful episodes. Tokens = input + output + cache read + cache write. "
             "Costs are those recorded by the agent (list prices in config/model_config.yaml)."]
    return _doc("Token usage and cost", notes, md_table(view))


def _md_calibration(t: dict[str, Any]) -> str:
    df = t["calibration"]
    view = pd.DataFrame({
        "Configuration": df["config"], "Level": df["level"], "Scored": df["n"], "No verdict": df["n_undeclared"],
        "TP": df["tp"], "FP": df["fp"], "FN": df["fn"], "TN": df["tn"],
        "Precision %": df["precision"].map(fnum), "Recall %": df["recall"].map(fnum),
        "False-success %": df["false_success_rate"].map(fnum), "Accuracy %": df["accuracy"].map(fnum),
    })
    notes = ["Agent self-verification vs the hidden validator (feedback configurations). Episode level: "
             "agent_declared_success vs episode success; attempt level: agent_verdict_ok vs that attempt's "
             "validator verdict. Positive = success. Precision = TP/(TP+FP); recall = TP/(TP+FN); "
             "false-success rate = FP/(FP+TN), the share of validator failures the agent declared successful."]
    return _doc("Agent self-verification calibration", notes, md_table(view) if len(df) else "(no feedback configuration)")


def _md_cumulative(t: dict[str, Any]) -> str:
    df = t["cumulative_success"]
    configs = mx.order_configs(df["config"])
    kmax = int(df["attempt"].max()) if len(df) else 0
    rows = []
    for c in configs:
        sub = df[df["config"] == c].set_index("attempt")
        rows.append({"Configuration": c, **{f"k={k}": fpm(sub.at[k, "mean"], sub.at[k, "std"]) if k in sub.index
                                             else "-" for k in range(1, kmax + 1)}})
    notes = ["% of episodes that ended successfully within k attempts (success and attempts used <= k), "
             "mean \u00b1 SD over runs.",
             "k = 1 can be lower than first-attempt success in the main results: an attempt 1 that passed the "
             "validator but was rejected by the agent's self-check did not end the episode, so it counts at a "
             "later k if a repair also passed, and never if the episode ended failed "
             "(see 'Correct attempt 1 rejected' in the main results)."]
    return _doc("Cumulative success by attempt", notes, md_table(pd.DataFrame(rows)) if rows else "(none)")


def _doc(title: str, notes: Sequence[str], body: str) -> str:
    return f"# {title}\n\n" + "\n".join(f"- {n}" for n in notes) + "\n\n" + body + "\n"


TABLE_WRITERS: dict[str, tuple[str, Callable[..., str]]] = {
    # file stem -> (key in compute_tables, markdown renderer)
    "coverage": ("coverage", _md_coverage),
    "main_results": ("main_results", _md_main),
    "per_category": ("per_category", lambda t: _md_group(t, "per_category", "Completion by task category")),
    "per_difficulty": ("per_difficulty", lambda t: _md_group(t, "per_difficulty", "Completion by difficulty")),
    "statistics": ("statistics", _md_statistics),
    "statistics_follow_up": ("follow_up", lambda t: _md_statistics(t, "follow_up")),
    "errors": ("errors", _md_errors),
    "error_transitions": ("transitions", _md_transitions),
    "failing_commands": ("failing_commands", _md_commands),
    "task_profiles": ("task_profiles", _md_profiles),
    "cost": ("cost", _md_cost),
    "calibration": ("calibration", _md_calibration),
    "cumulative_success": ("cumulative_success", _md_cumulative),
}


def write_tables(tables: dict[str, Any], data: mx.ExperimentData, out_dir: Path) -> list[Path]:
    tdir = out_dir / "tables"
    tdir.mkdir(parents=True, exist_ok=True)
    written = []
    for stem, (key, render) in TABLE_WRITERS.items():
        csv = tdir / f"{stem}.csv"
        _csv_ready(tables[key]).to_csv(csv, index=False)
        md = tdir / f"{stem}.md"
        md.write_text(render(tables, data) if stem == "coverage" else render(tables))
        written += [csv, md]
    extra = {"recovery_by_error_type": tables["recovery_by_error"],
             "statistics_cochran_q": pd.DataFrame([{k: (";".join(v) if isinstance(v, list) else
                                                        json.dumps(v) if isinstance(v, dict) else v)
                                                    for k, v in tables["cochran_q"].items()}])}
    for stem, df in extra.items():
        p = tdir / f"{stem}.csv"
        _csv_ready(df).to_csv(p, index=False)
        written.append(p)
    return written


# ------------------------------------------------------------------- summary
def clean(obj: Any) -> Any:
    """JSON-safe copy: numpy scalars -> Python, NaN/inf -> None, floats to 10 significant digits."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        return float(f"{f:.10g}") if math.isfinite(f) else None
    if obj is None or obj is pd.NA:
        return None
    if isinstance(obj, Path):
        return str(obj)
    return obj


def _records(df: pd.DataFrame, drop: Sequence[str] = ()) -> list[dict[str, Any]]:
    return [{k: v for k, v in r.items() if k not in drop} for r in df.to_dict(orient="records")]


def _by(df: pd.DataFrame, *keys: str, drop: Sequence[str] = ()) -> dict[str, Any]:
    """Nest rows as {key1: {key2: row}} (keys removed from the row)."""
    out: dict[str, Any] = {}
    for r in _records(df, drop):
        node = out
        for k in keys[:-1]:
            node = node.setdefault(str(r.pop(k)), {})
        node[str(r.pop(keys[-1]))] = r
    return out


def build_summary(data: mx.ExperimentData, tables: dict[str, Any], *, n_boot: int, seed: int,
                  split: str | None, drop_harness_errors: bool, outputs: Sequence[Path], out_dir: Path) -> dict[str, Any]:
    """Every headline number, keyed for citation in the paper."""
    main = tables["main_results"].merge(tables["cost"].drop(columns=["n_episodes", "successes"]), on="config",
                                        how="left", suffixes=("", "_cost"))
    profiles = tables["task_profiles"]
    errs = tables["errors"]
    q = tables["cochran_q"]
    configs = mx.order_configs(data.episodes["config"])
    best = max(configs, key=lambda c: mx.as_float(main.set_index("config").at[c, "completion_mean"])) if configs else None
    return clean({
        "experiment_id": data.experiment_id,
        "generated_by": "python -m analysis.make_report",
        "analysis_settings": {
            "completion": "per-run successes / episodes recorded in the run x 100; mean and sample SD (ddof=1) over runs",
            "bootstrap": {"replicates": n_boot, "seed": seed, "ci_level": st.CI_LEVEL,
                          "method": "percentile, paired, tasks resampled with replacement, per-task success averaged over runs"},
            "mcnemar": "exact two-sided binomial test on discordant pairs",
            "majority_rule": "task solved when more than half of its recorded runs succeeded",
            "wilcoxon": {"zero_method": st.WILCOXON_ZERO_METHOD, "method": st.WILCOXON_METHOD,
                         "correction": False, "all_zero_differences": "p = 1"},
            "multiple_comparisons": "Holm-Bonferroni within each test family across the planned contrasts",
            "harness_errors": "dropped (missing)" if drop_harness_errors else "counted as failures",
            "split_filter": split,
        },
        "inputs": {"results_dir": rel(data.source_dir) if data.source_dir else None,
                   "files": data.report.files, "metadata": data.metadata},
        "coverage": {
            "per_config": _by(tables["coverage"], "config"),
            **{k: v for k, v in tables["coverage_details"].items()},
            "episodes_total": len(data.episodes), "attempts_total": len(data.attempts),
            "malformed_lines": data.report.malformed_lines, "lenient_records": data.report.lenient_records,
            "other_split_dropped": data.report.other_split_dropped, "warnings": data.report.warnings,
        },
        "configurations": _by(main, "config"),
        "best_config_by_completion": best,
        "per_category": _by(tables["per_category"], "config", "category"),
        "per_difficulty": _by(tables["per_difficulty"], "config", "difficulty"),
        "calibration": _by(tables["calibration"], "config", "level"),
        "cumulative_success": _by(tables["cumulative_success"], "config", "attempt"),
        "contrasts": _by(tables["statistics"], "contrast"),
        "follow_up_contrasts": _by(tables["follow_up"], "contrast"),
        "cochran_q": q,
        "errors": _by(errs, "stage", "config", "outcome"),
        "recovery_by_first_error": _by(tables["recovery_by_error"], "config", "first_outcome"),
        "failing_commands": {s: _records(g.drop(columns=["scope"]))
                             for s, g in tables["failing_commands"].groupby("scope", sort=False)},
        "task_profiles": {
            "counts": ea.profile_counts(profiles),
            **{p: profiles.loc[profiles["profile"] == p, "task_id"].tolist() for p in ea.PROFILES},
            "run_dependent": profiles.loc[profiles["run_dependent"].astype(bool), "task_id"].tolist()
            if len(profiles) else [],
        },
        "models_reported": mx.models_reported(data.episodes),
        "outputs": sorted(str(p.relative_to(out_dir)) for p in outputs),
    })


# ----------------------------------------------------------------------- main
def build_report(experiment_id: str, out_dir: Path | str = PAPER_DIR, *, results_root: Path | str | None = None,
                 n_boot: int = st.N_BOOT, seed: int = st.SEED, split: str | None = None,
                 drop_harness_errors: bool = False, figures: bool = True) -> dict[str, Any]:
    """Load the records, write tables, figures and ``results_summary.json``; returns the summary."""
    data = mx.load_experiment(experiment_id, results_root, split=split, drop_harness_errors=drop_harness_errors)
    if data.episodes.empty:
        raise ValueError(f"no usable episode records for experiment '{experiment_id}': {data.report.warnings}")
    out_dir = Path(out_dir)
    tables = compute_tables(data, n_boot=n_boot, seed=seed)
    outputs = write_tables(tables, data, out_dir)
    if figures:
        from analysis.plots import make_figures   # matplotlib only when figures are wanted
        outputs += make_figures(tables, data.episodes, data.attempts, out_dir / "figures")
    summary_path = out_dir / "results_summary.json"
    summary = build_summary(data, tables, n_boot=n_boot, seed=seed, split=split,
                            drop_harness_errors=drop_harness_errors, outputs=[*outputs, summary_path], out_dir=out_dir)
    summary_path.write_text(json.dumps(summary, indent=1, allow_nan=False) + "\n")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build report tables, figures and results_summary.json.")
    ap.add_argument("--experiment", required=True, help="experiment id (directory under the results root)")
    ap.add_argument("--out-dir", default=str(PAPER_DIR), help="output directory (default: paper/)")
    ap.add_argument("--results-root", default=None, help="directory holding <experiment>/ (default: experiments/results)")
    ap.add_argument("--split", choices=["test", "dev"], default=None, help="keep only episodes of this task split")
    ap.add_argument("--exclude-harness-errors", action="store_true",
                    help="treat episodes aborted by a harness error as missing instead of failed")
    ap.add_argument("--n-boot", type=int, default=st.N_BOOT, help="bootstrap replicates")
    ap.add_argument("--seed", type=int, default=st.SEED, help="bootstrap seed")
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args(argv)
    out_dir = resolve(args.out_dir)
    results_root = resolve(args.results_root) if args.results_root else None
    try:
        summary = build_report(args.experiment, out_dir, results_root=results_root, n_boot=args.n_boot,
                               seed=args.seed, split=args.split, drop_harness_errors=args.exclude_harness_errors,
                               figures=not args.no_figures)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for cfg, row in summary["configurations"].items():
        cov = summary["coverage"]["per_config"].get(cfg, {})
        print(f"{cfg:18s} completion {fpm(row['completion_mean'], row['completion_std'])} %  "
              f"({row['n_episodes']} episodes, coverage {fnum(cov.get('coverage_pct'))} %)")
    for w in summary["coverage"]["warnings"]:
        print(f"warning: {w}")
    print(f"wrote {len(summary['outputs'])} files under {rel(out_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
