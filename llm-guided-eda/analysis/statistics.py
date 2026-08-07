"""Paired statistical comparisons between experimental configurations.

Every comparison pairs two configurations on the benchmark tasks recorded for
both (``config_b - config_a``; positive = ``config_b`` completes more tasks):

1. Paired bootstrap CI of the difference in mean completion (percentage
   points): per-task success is averaged over runs, tasks are resampled with
   replacement (10,000 replicates, fixed seed, percentile interval).
2. Exact McNemar tests (two-sided binomial test on the discordant pairs) on
   (task, run) pairs matched by run index, and on per-task majority outcomes
   (a task counts as solved when more than half of its recorded runs succeeded;
   a tie -- possible only with an even number of runs -- counts as not solved).
   The run-matched test treats the runs of one task as independent pairs, which
   they are not; the majority-vote test uses one pair per task.
3. Wilcoxon signed-rank test on per-task success rates. ``zero_method="pratt"``:
   zero differences (tasks on which both configurations do equally well, the
   common case) take part in the ranking and their ranks are then dropped
   (Pratt 1959; scipy's more conservative option). The p-value uses the normal
   approximation adjusted for ties and zeros (``method="asymptotic"``, no
   continuity correction): with success rates in steps of 1/runs the exact
   null distribution does not apply. All-zero differences give p = 1.
4. Holm-Bonferroni adjustment within each test family across the planned
   contrasts that could be computed.
5. Cochran's Q across all configurations on per-task majority outcomes
   (tasks recorded for every configuration).
"""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.contingency_tables import cochrans_q, mcnemar
from statsmodels.stats.multitest import multipletests

from analysis.metrics import NAN, order_configs

PLANNED_CONTRASTS: list[tuple[str, str, str]] = [
    ("A_baseline", "B_rag", "retrieval, single shot"),
    ("A_baseline", "C_feedback", "feedback + repair, no retrieval"),
    ("B_rag", "D_full", "feedback + repair, with retrieval"),
    ("A_baseline", "D_full", "full system vs baseline"),
    ("D_full", "E_vector_only", "vector-only vs hybrid retrieval"),
    ("D_full", "F_single_repair", "2 vs 4 attempts"),
]
# Configurations of the planned ablation (Cochran's Q is computed over these only).
ABLATION_CONFIGS: list[str] = list(dict.fromkeys(c for a, b, _ in PLANNED_CONTRASTS for c in (a, b)))
# Added after the planned analysis; a separate Holm family, so the planned p-values are unchanged.
FOLLOW_UP_CONTRASTS: list[tuple[str, str, str]] = [
    ("D_full", "G_targeted_repair", "targeted syntax cards on repair"),
]
N_BOOT = 10_000
SEED = 20261106
CI_LEVEL = 0.95
WILCOXON_ZERO_METHOD = "pratt"
WILCOXON_METHOD = "asymptotic"
TEST_FAMILIES = ("mcnemar_runs", "mcnemar_majority", "wilcoxon")
STAT_COLUMNS = [
    "contrast", "label", "config_a", "config_b", "n_tasks", "mean_a", "mean_b", "diff_pp", "ci_low_pp",
    "ci_high_pp", "boot_se_pp", "runs_n_pairs", "runs_n11", "runs_n10", "runs_n01", "runs_n00", "mcnemar_runs_p",
    "mcnemar_runs_p_holm", "majority_n11", "majority_n10", "majority_n01", "majority_n00", "mcnemar_majority_p",
    "mcnemar_majority_p_holm", "wilcoxon_n_nonzero", "wilcoxon_statistic", "wilcoxon_z", "wilcoxon_p",
    "wilcoxon_p_holm", "note",
]
_DECIMALS = 12   # rounding of rate differences so that float noise cannot break ties


def task_rates(episodes: pd.DataFrame, config: str) -> pd.Series:
    """Per-task success rate (0-1) over the recorded runs of one configuration."""
    ep = episodes[episodes["config"] == config]
    return ep.groupby("task_id")["success"].mean().astype(float)


def majority(rates: pd.Series) -> pd.Series:
    """Per-task majority outcome: solved when more than half of the runs succeeded."""
    return rates > 0.5


def bootstrap_mean_ci(diff: Sequence[float], n_boot: int = N_BOOT, seed: int = SEED,
                      level: float = CI_LEVEL) -> tuple[float, float, float]:
    """Percentile bootstrap CI of the mean of paired differences; returns (low, high, bootstrap SE)."""
    d = np.asarray(diff, float)
    if d.size == 0:
        return NAN, NAN, NAN
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    chunk = max(1, 2_000_000 // d.size)
    for start in range(0, n_boot, chunk):
        stop = min(n_boot, start + chunk)
        means[start:stop] = d[rng.integers(0, d.size, size=(stop - start, d.size))].mean(axis=1)
    alpha = (1.0 - level) / 2.0
    lo, hi = np.quantile(means, [alpha, 1.0 - alpha])
    return float(lo), float(hi), float(means.std(ddof=1)) if n_boot > 1 else NAN


def contingency(a: Sequence[bool], b: Sequence[bool]) -> dict[str, int]:
    """Paired 2x2 counts: n11 both solved, n10 only a, n01 only b, n00 neither."""
    x, y = np.asarray(a, bool), np.asarray(b, bool)
    return {"n11": int((x & y).sum()), "n10": int((x & ~y).sum()), "n01": int((~x & y).sum()),
            "n00": int((~x & ~y).sum())}


def mcnemar_exact(table: dict[str, int]) -> float:
    """Two-sided exact McNemar p-value (binomial test on the discordant counts n10, n01)."""
    t = [[table["n11"], table["n10"]], [table["n01"], table["n00"]]]
    return float(mcnemar(t, exact=True).pvalue)


def wilcoxon_signed_rank(diff: Sequence[float]) -> dict[str, Any]:
    """Wilcoxon signed-rank test of paired differences (see module docstring for the settings)."""
    d = np.round(np.asarray(diff, float), _DECIMALS)
    nonzero = int(np.count_nonzero(d))
    if d.size == 0:
        return {"n_nonzero": 0, "statistic": NAN, "z": NAN, "p": NAN}
    if nonzero == 0:
        return {"n_nonzero": 0, "statistic": 0.0, "z": 0.0, "p": 1.0}
    res = stats.wilcoxon(d, zero_method=WILCOXON_ZERO_METHOD, method=WILCOXON_METHOD, correction=False)
    return {"n_nonzero": nonzero, "statistic": float(res.statistic),
            "z": float(getattr(res, "zstatistic", NAN)), "p": float(res.pvalue)}


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values; NaN entries stay NaN and are not part of the family."""
    p = np.asarray(pvalues, float)
    out = np.full(p.shape, NAN)
    ok = ~np.isnan(p)
    if ok.any():
        out[ok] = multipletests(p[ok], method="holm")[1]
    return out.tolist()


def compare(episodes: pd.DataFrame, a: str, b: str, *, n_boot: int = N_BOOT, seed: int = SEED) -> dict[str, Any]:
    """All paired tests of configuration ``b`` against ``a`` on their common tasks."""
    ra, rb = task_rates(episodes, a), task_rates(episodes, b)
    tasks = sorted(set(ra.index) & set(rb.index))
    ra, rb = ra.reindex(tasks), rb.reindex(tasks)
    diff = (rb - ra).to_numpy(float)
    lo, hi, se = bootstrap_mean_ci(diff, n_boot, seed)
    cols = ["task_id", "run", "success"]
    runs = episodes.loc[episodes["config"] == a, cols].merge(
        episodes.loc[episodes["config"] == b, cols], on=["task_id", "run"], suffixes=("_a", "_b"))
    t_runs = contingency(runs["success_a"], runs["success_b"])
    t_maj = contingency(majority(ra), majority(rb))
    w = wilcoxon_signed_rank(diff)
    return {
        "config_a": a, "config_b": b, "n_tasks": len(tasks),
        "mean_a": 100.0 * float(ra.mean()) if tasks else NAN, "mean_b": 100.0 * float(rb.mean()) if tasks else NAN,
        "diff_pp": 100.0 * float(diff.mean()) if tasks else NAN,
        "ci_low_pp": 100.0 * lo, "ci_high_pp": 100.0 * hi, "boot_se_pp": 100.0 * se,
        "runs_n_pairs": len(runs), **{f"runs_{k}": v for k, v in t_runs.items()},
        "mcnemar_runs_p": mcnemar_exact(t_runs) if len(runs) else NAN,
        **{f"majority_{k}": v for k, v in t_maj.items()},
        "mcnemar_majority_p": mcnemar_exact(t_maj) if tasks else NAN,
        "wilcoxon_n_nonzero": w["n_nonzero"], "wilcoxon_statistic": w["statistic"], "wilcoxon_z": w["z"],
        "wilcoxon_p": w["p"],
    }


def planned_comparisons(episodes: pd.DataFrame, contrasts: Sequence[tuple[str, str, str]] = PLANNED_CONTRASTS, *,
                        n_boot: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """One row per planned contrast with every test and Holm-adjusted p-values per test family.

    Contrasts whose configurations were not recorded stay in the table with a
    note and no statistics; they are not part of the Holm families.
    """
    present = set(episodes["config"])
    rows = []
    for a, b, label in contrasts:
        row: dict[str, Any] = {"contrast": f"{a} vs {b}", "label": label}
        lacking = [c for c in (a, b) if c not in present]
        if lacking:
            row.update({"config_a": a, "config_b": b, "n_tasks": 0, "note": f"not recorded: {', '.join(lacking)}"})
        else:
            row.update(compare(episodes, a, b, n_boot=n_boot, seed=seed))
            row["note"] = "" if row["n_tasks"] else "no common tasks"
        rows.append(row)
    df = pd.DataFrame(rows, columns=STAT_COLUMNS)
    for fam in TEST_FAMILIES:
        df[f"{fam}_p_holm"] = holm(df[f"{fam}_p"].astype(float).tolist())
    return df


def cochran_q(episodes: pd.DataFrame, configs: Sequence[str] | None = None) -> dict[str, Any]:
    """Cochran's Q on per-task majority outcomes, over tasks recorded for every configuration."""
    configs = order_configs(configs if configs is not None else episodes["config"])
    rates = (episodes[episodes["config"].isin(configs)]
             .groupby(["task_id", "config"])["success"].mean().unstack("config"))
    rates = rates.reindex(columns=configs).dropna()
    x = majority(rates.astype(float)).astype(int).to_numpy() if len(rates) else np.zeros((0, len(configs)), int)
    n, k = x.shape
    out: dict[str, Any] = {"configs": list(configs), "k": k, "n_tasks": n, "df": max(k - 1, 0),
                           "solved_by_majority": {c: int(s) for c, s in zip(configs, x.sum(axis=0))}}
    if k < 2 or n == 0:
        return {**out, "statistic": NAN, "p": NAN, "note": "needs at least 2 configurations and 1 common task"}
    row_sums = x.sum(axis=1)
    if np.all((row_sums == 0) | (row_sums == k)):
        return {**out, "statistic": 0.0, "p": 1.0, "note": "no task with differing majority outcomes"}
    res = cochrans_q(x)
    return {**out, "statistic": float(res.statistic), "df": int(res.df), "p": float(res.pvalue), "note": ""}
