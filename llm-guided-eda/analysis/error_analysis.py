"""Error analysis: what goes wrong, and what execution feedback repairs.

Outcome categories are those of :mod:`analysis.metrics`: ``success``, the
executor error taxonomy of :mod:`openroad.log_parser`, ``validation_failure``
(the script ran cleanly but the validator failed), and ``harness_error`` /
``no_attempt`` for episodes that never produced an attempt.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from analysis.metrics import (HARNESS_ERROR, NAN, NO_ATTEMPT, SUCCESS, UNKNOWN_ERROR, VALIDATION_FAILURE,
                              order_configs, ordered, rate, sort_frame)

# Executor failure taxonomy (openroad/log_parser.py) in a fixed reporting order.
ERROR_TYPES = [
    "invalid_command", "invalid_argument", "tcl_syntax", "missing_prerequisite", "missing_file",
    "incorrect_design_context", "runtime_failure", "unsafe_command", "tool_error",
]
OUTCOME_ORDER = [SUCCESS, VALIDATION_FAILURE, *ERROR_TYPES, UNKNOWN_ERROR, HARNESS_ERROR, NO_ATTEMPT]
STAGES = {
    "first_attempt": "attempt 1 outcome (% of episodes)",
    "final": "final outcome (% of episodes)",
    "failed_executions": "all failed executions (% of failed executions)",
}
PROFILES = ("never_solved", "always_solved", "configuration_dependent")
PROFILE_COLUMNS = ["task_id", "category", "difficulty", "n_episodes", "n_success", "success_rate", "profile",
                   "run_dependent"]


def outcome_order(values: Iterable[str]) -> list[str]:
    return ordered(values, OUTCOME_ORDER)


def failed_attempts(attempts: pd.DataFrame) -> pd.DataFrame:
    """Attempts whose OpenROAD execution failed (error, timeout or policy rejection)."""
    return attempts[~attempts["exec_success"] | attempts["error_type"].notna()]


def error_distribution(episodes: pd.DataFrame, attempts: pd.DataFrame) -> pd.DataFrame:
    """Outcome distribution per configuration and stage (long format).

    Stages: ``first_attempt`` and ``final`` (outcome of attempt 1 / of the final
    attempt; ``pct`` = % of episodes, ``success`` included), and
    ``failed_executions`` (error type of every failed execution; ``pct`` = % of
    failed executions, ``per_episode`` = failed executions of that type per episode).
    """
    cols = ["config", "stage", "outcome", "count", "n", "pct", "per_episode"]
    rows = []
    for cfg in order_configs(episodes["config"]):
        ep = episodes[episodes["config"] == cfg]
        for stage, col in (("first_attempt", "first_outcome"), ("final", "final_outcome")):
            counts = ep[col].value_counts()
            for outcome in outcome_order(counts.index):
                c = int(counts[outcome])
                rows.append({"config": cfg, "stage": stage, "outcome": outcome, "count": c, "n": len(ep),
                             "pct": rate(c, len(ep)), "per_episode": NAN})
        fa = failed_attempts(attempts[attempts["config"] == cfg])
        counts = fa["error_type"].fillna(UNKNOWN_ERROR).value_counts()
        for outcome in outcome_order(counts.index):
            c = int(counts[outcome])
            rows.append({"config": cfg, "stage": "failed_executions", "outcome": outcome, "count": c, "n": len(fa),
                         "pct": rate(c, len(fa)), "per_episode": c / len(ep) if len(ep) else NAN})
    return pd.DataFrame(rows, columns=cols)


def transition_table(episodes: pd.DataFrame) -> pd.DataFrame:
    """Counts of attempt-1 outcome -> final outcome per configuration (long format)."""
    cols = ["config", "first_outcome", "final_outcome", "count"]
    if episodes.empty:
        return pd.DataFrame(columns=cols)
    df = episodes.groupby(["config", "first_outcome", "final_outcome"]).size().rename("count").reset_index()
    first_rank = {v: i for i, v in enumerate(outcome_order(df["first_outcome"]))}
    final_rank = {v: i for i, v in enumerate(outcome_order(df["final_outcome"]))}
    df["__a"], df["__b"] = df["first_outcome"].map(first_rank), df["final_outcome"].map(final_rank)
    return sort_frame(df, ("config", "__a", "__b")).drop(columns=["__a", "__b"])[cols]


def recovery_by_first_outcome(episodes: pd.DataFrame) -> pd.DataFrame:
    """For multi-attempt configurations: episodes whose attempt 1 failed, by attempt-1 outcome.

    ``recovered`` = final attempt passed the validator; ``same_final`` = the
    final outcome is the attempt-1 failure type again.
    """
    cols = ["config", "first_outcome", "n", "recovered", "recovery_rate", "same_final", "mean_attempts"]
    rows = []
    multi = episodes[(episodes["max_attempts"] > 1) & ~episodes["first_attempt_success"] & (episodes["n_attempts"] > 0)]
    for cfg in order_configs(multi["config"]):
        ep = multi[multi["config"] == cfg]
        for outcome in outcome_order(ep["first_outcome"]):
            g = ep[ep["first_outcome"] == outcome]
            rec = int(g["success"].sum())
            rows.append({"config": cfg, "first_outcome": outcome, "n": len(g), "recovered": rec,
                         "recovery_rate": rate(rec, len(g)),
                         "same_final": int((g["final_outcome"] == outcome).sum()),
                         "mean_attempts": float(g["attempts_used"].mean())})
    return pd.DataFrame(rows, columns=cols)


def failing_commands(attempts: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Most common failing commands (first word of the failing script line), overall and per configuration.

    ``pct`` is relative to the failed executions whose failing line is known
    (``n_located``); policy rejections and timeouts usually have none.
    """
    cols = ["scope", "rank", "command", "count", "pct", "top_error_type", "n_failed", "n_located"]
    fa = failed_attempts(attempts)
    rows = []
    scopes = [("all", fa)] + [(cfg, fa[fa["config"] == cfg]) for cfg in order_configs(fa["config"])]
    for scope, grp in scopes:
        located = grp[grp["failing_command"].notna()]
        counts = located["failing_command"].value_counts()
        counts = counts.sort_index(kind="stable").sort_values(ascending=False, kind="stable")
        for rank, (cmd, c) in enumerate(counts.head(top_n).items(), 1):
            types = located.loc[located["failing_command"] == cmd, "error_type"].fillna(UNKNOWN_ERROR).value_counts()
            types = types.sort_index(kind="stable").sort_values(ascending=False, kind="stable")
            rows.append({"scope": scope, "rank": rank, "command": cmd, "count": int(c), "pct": rate(c, len(located)),
                         "top_error_type": types.index[0], "n_failed": len(grp), "n_located": len(located)})
    return pd.DataFrame(rows, columns=cols)


def task_profiles(episodes: pd.DataFrame) -> pd.DataFrame:
    """Per-task success across configurations.

    ``profile``: ``never_solved`` (no successful episode in any configuration or
    run), ``always_solved`` (every episode succeeded) or ``configuration_dependent``
    (anything in between). ``run_dependent`` marks tasks whose outcome varied
    between runs of at least one configuration. Per-configuration columns hold
    the task's success rate (%) over runs.
    """
    if episodes.empty:
        return pd.DataFrame(columns=PROFILE_COLUMNS)
    configs = order_configs(episodes["config"])
    rates = 100.0 * episodes.pivot_table(index="task_id", columns="config", values="success", aggfunc="mean")
    rates = rates.reindex(columns=configs)
    g = episodes.groupby("task_id")
    out = pd.DataFrame({
        "category": g["category"].first(), "difficulty": g["difficulty"].first(),
        "n_episodes": g.size(), "n_success": g["success"].sum().astype(int),
    })
    out["success_rate"] = 100.0 * out["n_success"] / out["n_episodes"]
    out["profile"] = np.select([out["n_success"] == 0, out["n_success"] == out["n_episodes"]],
                               ["never_solved", "always_solved"], "configuration_dependent")
    vals = rates.to_numpy(float)
    out["run_dependent"] = ((vals > 0) & (vals < 100)).any(axis=1)
    out = pd.concat([out, rates], axis=1).reset_index().rename(columns={"index": "task_id"})
    out.columns.name = None
    return sort_frame(out, ("category", "task_id"))


def profile_configs(profiles: pd.DataFrame) -> list[str]:
    """The per-configuration rate columns of a :func:`task_profiles` table."""
    return order_configs(c for c in profiles.columns if c not in PROFILE_COLUMNS)


def profile_counts(profiles: pd.DataFrame) -> dict[str, int]:
    counts = profiles["profile"].value_counts() if not profiles.empty else pd.Series(dtype=int)
    return {p: int(counts.get(p, 0)) for p in PROFILES}
