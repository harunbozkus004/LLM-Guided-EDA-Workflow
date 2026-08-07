"""Tests of the analysis package on SYNTHETIC experiment records.

Nothing here is a real result. Every record comes from :func:`fake_episode`
(experiment ids start with ``SYNTHETIC``, the model is ``synthetic-test-model``,
the provider ``mock``) and every output file goes to a pytest ``tmp_path``.
Expected values are worked out by hand in the comments.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from analysis import error_analysis as ea
from analysis import make_report
from analysis import metrics as mx
from analysis import statistics as st
from common.config import load_config
from common.paths import PAPER_DIR
from experiments.record_schema import AttemptRecord, EpisodeRecord, LLMCallRecord

FAKE_MODEL = "synthetic-test-model"
FAKE_EXPERIMENT = "SYNTHETIC-test"
CONFIGS = load_config("experiment_config")["configurations"]
SCRIPT = "# synthetic test script\nread_db inputs/x.odb\nglobal_placement -density 0.6\nreport_wns\n"


# ------------------------------------------------------------ fake records
def fake_call(purpose: str, cost: float, tokens: tuple[int, int, int, int], cached: bool = False) -> LLMCallRecord:
    return LLMCallRecord(
        purpose=purpose, provider="mock", model_requested=FAKE_MODEL, model_reported=FAKE_MODEL, effort=None,
        thinking=None, max_tokens=1000, input_tokens=tokens[0], output_tokens=tokens[1],
        cache_read_tokens=tokens[2], cache_write_tokens=tokens[3], cost_usd=cost, latency_s=0.1,
        stop_reason="end_turn", request_id=None, timestamp="2000-01-01T00:00:00Z", cached=cached)


def fake_attempt(i: int, outcome: str, *, verdict: bool | None = None, cost: float = 0.01,
                 tokens: tuple[int, int, int, int] = (100, 20, 0, 0), script: str = SCRIPT,
                 line: int | None = 3) -> AttemptRecord:
    """``outcome``: "ok" (clean, validator pass), "vf" (clean, validator fail) or an executor error type."""
    clean = outcome in ("ok", "vf")
    return AttemptRecord(
        attempt=i, script=script, exec_success=clean, error_type=None if clean else outcome,
        error_message=None if clean else f"synthetic {outcome}", failing_line=None if clean else line,
        execution_time_s=1.5, validator_passed=outcome == "ok",
        validator_summary="PASS (synthetic)" if outcome == "ok" else "FAIL - synthetic", agent_verdict_ok=verdict,
        llm_calls=[fake_call("generate" if i == 1 else "repair", cost, tokens)])


def fake_episode(config: str, run: int, task_id: str, outcomes: list[str], *, category: str = "placement",
                 difficulty: str = "easy", declared: bool | None = None, verdicts: list[bool | None] | None = None,
                 cost: float = 0.01, tokens: tuple[int, int, int, int] = (100, 20, 0, 0), error: str | None = None,
                 experiment_id: str = FAKE_EXPERIMENT, scripts: list[str] | None = None,
                 lines: list[int | None] | None = None, timestamp_end: str = "2000-01-01T00:01:00Z") -> dict:
    """One schema-conformant EpisodeRecord dict whose summary fields agree with its attempts."""
    cfg = CONFIGS[config]
    atts = [fake_attempt(i, o, verdict=(verdicts or [None] * len(outcomes))[i - 1], cost=cost, tokens=tokens,
                         script=(scripts or [SCRIPT] * len(outcomes))[i - 1],
                         line=(lines or [3] * len(outcomes))[i - 1])
            for i, o in enumerate(outcomes, 1)]
    success = bool(atts) and atts[-1].validator_passed
    rec = EpisodeRecord(
        experiment_id=experiment_id, config=config, run=run, task_id=task_id, category=category,
        difficulty=difficulty, split="test", rag=cfg["rag"], feedback=cfg["feedback"],
        max_attempts=cfg["max_attempts"], success=success,
        first_attempt_success=bool(atts) and atts[0].validator_passed, attempts_used=len(atts),
        agent_declared_success=declared,
        final_error_type=None if success or not atts else (atts[-1].error_type or "validation_failure"),
        failed_executions=sum(not a.exec_success for a in atts),
        total_execution_time_s=sum(a.execution_time_s for a in atts), wall_time_s=10.0 * len(atts) + 1.0,
        llm_calls=len(atts), input_tokens=tokens[0] * len(atts), output_tokens=tokens[1] * len(atts),
        cache_read_tokens=tokens[2] * len(atts), cache_write_tokens=tokens[3] * len(atts),
        cost_usd=cost * len(atts), model=FAKE_MODEL, timestamp_start="2000-01-01T00:00:00Z",
        timestamp_end=timestamp_end, attempts=atts, error=error)
    return rec.to_dict()


def experiment(dicts: list[dict], metadata: dict | None = None) -> mx.ExperimentData:
    return mx.build_experiment(FAKE_EXPERIMENT, [EpisodeRecord.from_dict(d) for d in dicts], metadata or {})


def feedback_set(config: str = "C_feedback", run: int = 0) -> list[dict]:
    """Five hand-made multi-attempt episodes (see test_recovery_failed_executions_attempts)."""
    return [
        fake_episode(config, run, "T1", ["invalid_command", "ok"]),
        fake_episode(config, run, "T2", ["vf", "invalid_argument", "vf"]),
        fake_episode(config, run, "T3", ["ok"]),
        fake_episode(config, run, "T4", ["tcl_syntax", "tcl_syntax", "invalid_command", "ok"]),
        fake_episode(config, run, "T5", ["runtime_failure", "runtime_failure"]),
    ]


def write_experiment(root: Path, exp_id: str, dicts: list[dict], metadata: dict | None) -> Path:
    exp_dir = root / exp_id
    exp_dir.mkdir(parents=True)
    by_config: dict[str, list[dict]] = {}
    for d in dicts:
        by_config.setdefault(d["config"], []).append(d)
    for cfg, items in by_config.items():
        (exp_dir / f"{cfg}.jsonl").write_text("".join(json.dumps(d) + "\n" for d in items))
    if metadata is not None:
        (exp_dir / "metadata.json").write_text(json.dumps(metadata))
    return exp_dir


# ----------------------------------------------------------------- metrics
def test_completion_per_run_mean_and_sample_std():
    # A_baseline, 4 tasks: run 0 solves 2/4 (50 %), run 1 3/4 (75 %), run 2 4/4 (100 %).
    solved = {0: 2, 1: 3, 2: 4}
    dicts = [fake_episode("A_baseline", r, f"T{t}", ["ok" if t < k else "vf"]) for r, k in solved.items()
             for t in range(4)]
    main = mx.main_results(experiment(dicts).episodes).set_index("config")
    row = main.loc["A_baseline"]
    assert row["completion_runs"] == [50.0, 75.0, 100.0]
    assert row["completion_mean"] == pytest.approx(75.0)
    assert row["completion_std"] == pytest.approx(25.0)          # sample SD (ddof=1) of 50, 75, 100
    assert row["completion_pooled"] == pytest.approx(75.0)
    assert row["first_attempt_mean"] == pytest.approx(75.0)      # single shot: attempt 1 is final
    assert math.isnan(row["recovery_rate"])                      # no repair possible in single shot


def test_single_run_has_undefined_std():
    data = experiment([fake_episode("B_rag", 0, f"T{t}", ["ok" if t else "vf"]) for t in range(4)])
    row = mx.main_results(data.episodes).iloc[0]
    assert row["completion_mean"] == pytest.approx(75.0) and math.isnan(row["completion_std"])


def test_recovery_failed_executions_attempts():
    eps = experiment(feedback_set()).episodes
    row = mx.main_results(eps).set_index("config").loc["C_feedback"]
    assert row["completion_mean"] == pytest.approx(60.0)         # T1, T3, T4
    assert row["first_attempt_mean"] == pytest.approx(20.0)      # T3
    # attempt 1 failed: T1, T2, T4, T5; final pass among them: T1, T4 -> 2/4
    assert (row["n_first_failed"], row["n_recovered"]) == (4, 2)
    assert row["recovery_rate"] == pytest.approx(50.0)
    assert row["failed_executions_mean"] == pytest.approx((1 + 1 + 0 + 3 + 2) / 5)
    assert row["final_exec_failure_rate"] == pytest.approx(20.0)  # only T5 ends on an execution error
    assert row["attempts_mean"] == pytest.approx((2 + 3 + 1 + 4 + 2) / 5)
    assert row["exec_time_mean_s"] == pytest.approx(1.5 * 12 / 5)
    assert (eps["inconsistencies"] == "").all()


def test_cumulative_success_by_attempt():
    cum = mx.cumulative_success(experiment(feedback_set()).episodes).set_index("attempt")
    # solved within k attempts: k=1 T3; k=2 +T1; k=3 same; k=4 +T4
    assert cum["mean"].tolist() == pytest.approx([20.0, 40.0, 40.0, 60.0])


def test_cost_and_tokens_per_episode_and_per_success():
    dicts = [fake_episode("A_baseline", 0, "T1", ["ok"], cost=0.10, tokens=(1000, 200, 50, 10)),
             fake_episode("A_baseline", 0, "T2", ["vf"], cost=0.30, tokens=(3000, 400, 150, 30))]
    row = mx.cost_table(experiment(dicts).episodes).iloc[0]
    assert row["cost_per_episode_usd"] == pytest.approx(0.20)
    assert row["cost_per_success_usd"] == pytest.approx(0.40)    # all spending / 1 solved task
    assert row["cost_mean_successful_usd"] == pytest.approx(0.10)
    assert row["input_tokens_per_episode"] == pytest.approx(2000)
    assert row["output_tokens_per_success"] == pytest.approx(600)
    assert row["cache_read_tokens_per_episode"] == pytest.approx(100)
    assert row["total_tokens_per_episode"] == pytest.approx((1260 + 3580) / 2)


def test_self_verification_calibration():
    # (declared, success): TP x2, FP x1, FN x1, TN x2, no verdict x1
    cases = [(True, "ok"), (True, "ok"), (True, "vf"), (False, "ok"), (False, "vf"), (False, "vf"), (None, "vf")]
    dicts = [fake_episode("D_full", 0, f"T{i}", [o], declared=d, verdicts=[d]) for i, (d, o) in enumerate(cases)]
    data = experiment(dicts)
    cal = mx.calibration(data.episodes, data.attempts).set_index("level")
    ep = cal.loc["episode"]
    assert (ep["tp"], ep["fp"], ep["fn"], ep["tn"], ep["n_undeclared"]) == (2, 1, 1, 2, 1)
    assert ep["precision"] == pytest.approx(200 / 3)
    assert ep["recall"] == pytest.approx(200 / 3)
    assert ep["false_success_rate"] == pytest.approx(100 / 3)
    assert ep["accuracy"] == pytest.approx(400 / 6)
    assert cal.loc["attempt", "tp"] == 2                         # one attempt per episode here
    single = experiment([fake_episode("A_baseline", 0, "T1", ["ok"])])
    assert mx.calibration(single.episodes, single.attempts).empty   # feedback configurations only


# --------------------------------------------------------------- statistics
def test_mcnemar_exact_on_known_table():
    # discordant 1 vs 7: p = 2 * P(X <= 1 | n=8, 1/2) = 2 * 9/256
    table = {"n11": 10, "n10": 1, "n01": 7, "n00": 32}
    assert st.mcnemar_exact(table) == pytest.approx(0.0703125)
    assert st.mcnemar_exact(table) == pytest.approx(stats.binomtest(1, 8, 0.5).pvalue)
    assert st.mcnemar_exact({"n11": 5, "n10": 0, "n01": 0, "n00": 5}) == 1.0


def test_compare_counts_and_mcnemar_from_episodes():
    # 50 tasks, 1 run: both solve T0-T9, only A solves T10, only B solves T11-T17 -> the table above
    a_ok = set(range(11))
    b_ok = set(range(10)) | set(range(11, 18))
    dicts = [fake_episode(c, 0, f"T{t:02d}", ["ok" if t in ok else "vf"])
             for c, ok in (("A_baseline", a_ok), ("B_rag", b_ok)) for t in range(50)]
    r = st.compare(experiment(dicts).episodes, "A_baseline", "B_rag", n_boot=2000)
    assert (r["runs_n11"], r["runs_n10"], r["runs_n01"], r["runs_n00"]) == (10, 1, 7, 32)
    assert r["mcnemar_runs_p"] == pytest.approx(0.0703125)
    assert r["mcnemar_majority_p"] == pytest.approx(0.0703125)
    assert r["diff_pp"] == pytest.approx(100 * 6 / 50)


def test_majority_vote_and_run_matching():
    # task X: A solves runs 0,1 (majority yes), B solves run 2 only (majority no)
    dicts = [fake_episode("A_baseline", r, "X", ["ok" if r < 2 else "vf"]) for r in range(3)]
    dicts += [fake_episode("B_rag", r, "X", ["ok" if r == 2 else "vf"]) for r in range(3)]
    r = st.compare(experiment(dicts).episodes, "A_baseline", "B_rag", n_boot=100)
    assert (r["runs_n11"], r["runs_n10"], r["runs_n01"], r["runs_n00"]) == (0, 2, 1, 0)
    assert (r["majority_n10"], r["majority_n01"]) == (1, 0)
    assert r["diff_pp"] == pytest.approx(100 * (1 / 3 - 2 / 3))


def test_bootstrap_ci_contains_true_difference_and_is_reproducible():
    # 40 tasks x 3 runs: A solves T0-T9, B solves T0-T19 -> true difference 10/40 = 25 pp
    dicts = [fake_episode(c, r, f"T{t:02d}", ["ok" if t < k else "vf"])
             for c, k in (("A_baseline", 10), ("B_rag", 20)) for r in range(3) for t in range(40)]
    eps = experiment(dicts).episodes
    r1 = st.compare(eps, "A_baseline", "B_rag")
    r2 = st.compare(eps, "A_baseline", "B_rag")
    assert r1["diff_pp"] == pytest.approx(25.0)
    assert r1["ci_low_pp"] < 25.0 < r1["ci_high_pp"]
    assert 0.0 < r1["ci_low_pp"] and r1["ci_high_pp"] < 50.0
    se = 100 * math.sqrt(0.25 * 0.75 / 40)                       # binomial SE of the mean difference
    assert r1["boot_se_pp"] == pytest.approx(se, rel=0.1)
    assert (r1["ci_low_pp"], r1["ci_high_pp"]) == (r2["ci_low_pp"], r2["ci_high_pp"])


def test_bootstrap_coverage_close_to_nominal():
    # 300 simulated benchmarks with a known mean difference of 0.2: the 95 % CI should cover it ~95 % of the time
    rng = np.random.default_rng(7)
    hits = 0
    for i in range(300):
        d = rng.choice([-1.0, 0.0, 1.0], size=50, p=[0.1, 0.6, 0.3])   # E[d] = 0.2
        lo, hi, _ = st.bootstrap_mean_ci(d, n_boot=1000, seed=i)
        hits += lo <= 0.2 <= hi
    assert 0.88 <= hits / 300 <= 0.99


def test_wilcoxon_settings_ties_and_all_zero():
    d = np.array([1 / 3, 2 / 3, 0, 0, 0, -1 / 3, 1, 1 / 3, 0, 2 / 3, 1 / 3, 0])
    ref = stats.wilcoxon(d, zero_method="pratt", method="asymptotic", correction=False)
    w = st.wilcoxon_signed_rank(d)
    assert w["p"] == pytest.approx(ref.pvalue) and w["statistic"] == pytest.approx(ref.statistic)
    assert w["n_nonzero"] == 7
    # float noise must not break ties: 1 - 2/3 and 2/3 - 1/3 are both one third
    noisy = np.array([1 - 2 / 3, 2 / 3 - 1 / 3, 1 / 3, -1 / 3, 1, 0])
    exact = np.array([1 / 3, 1 / 3, 1 / 3, -1 / 3, 1, 0])
    assert st.wilcoxon_signed_rank(noisy)["p"] == pytest.approx(st.wilcoxon_signed_rank(exact)["p"])
    assert st.wilcoxon_signed_rank(np.zeros(8)) == {"n_nonzero": 0, "statistic": 0.0, "z": 0.0, "p": 1.0}


def test_holm_adjustment():
    assert st.holm([0.01, 0.04, 0.03, 0.2]) == pytest.approx([0.04, 0.09, 0.09, 0.2])
    out = st.holm([0.01, float("nan"), 0.04])
    assert out[0] == pytest.approx(0.02) and math.isnan(out[1]) and out[2] == pytest.approx(0.04)


def test_cochran_q_known_matrix():
    # Q = (k-1)(k*sum C^2 - N^2) / (k*N - sum R^2) = 2*(3*38 - 100)/(30 - 22) = 3.5, df 2
    x = [[1, 1, 0], [1, 0, 0], [1, 1, 1], [0, 0, 0], [1, 0, 1], [1, 1, 0]]
    cfgs = ["A_baseline", "B_rag", "C_feedback"]
    dicts = [fake_episode(c, 0, f"T{i}", ["ok" if row[j] else "vf"]) for i, row in enumerate(x)
             for j, c in enumerate(cfgs)]
    q = st.cochran_q(experiment(dicts).episodes)
    assert (q["k"], q["n_tasks"], q["df"]) == (3, 6, 2)
    assert q["statistic"] == pytest.approx(3.5)
    assert q["p"] == pytest.approx(math.exp(-1.75))              # chi-square sf with 2 df
    same = [fake_episode(c, 0, "T0", ["ok"]) for c in cfgs]
    assert st.cochran_q(experiment(same).episodes)["p"] == 1.0   # no task with differing outcomes


def test_planned_comparisons_with_missing_configurations():
    dicts = [fake_episode(c, r, f"T{t}", ["ok" if (t + r) % k == 0 else "vf"])
             for c, k in (("A_baseline", 3), ("D_full", 2)) for r in range(3) for t in range(12)]
    df = st.planned_comparisons(experiment(dicts).episodes, n_boot=500).set_index("contrast")
    assert list(df.index) == [f"{a} vs {b}" for a, b, _ in st.PLANNED_CONTRASTS]
    assert df.loc["A_baseline vs B_rag", "note"] == "not recorded: B_rag"
    row = df.loc["A_baseline vs D_full"]
    assert row["n_tasks"] == 12 and row["note"] == ""
    # a family of one contrast: Holm leaves the p-value unchanged
    assert row["mcnemar_runs_p_holm"] == pytest.approx(row["mcnemar_runs_p"])
    assert row["wilcoxon_p_holm"] == pytest.approx(row["wilcoxon_p"])
    assert df["mcnemar_majority_p_holm"].isna().sum() == 5


# ------------------------------------------------------------ error analysis
def test_error_distributions_and_transitions():
    data = experiment(feedback_set())
    dist = ea.error_distribution(data.episodes, data.attempts)

    def counts(stage: str) -> dict[str, int]:
        sub = dist[(dist["stage"] == stage) & (dist["config"] == "C_feedback")]
        return dict(zip(sub["outcome"], sub["count"]))

    assert counts("first_attempt") == {"success": 1, "validation_failure": 1, "invalid_command": 1,
                                       "tcl_syntax": 1, "runtime_failure": 1}
    assert counts("final") == {"success": 3, "validation_failure": 1, "runtime_failure": 1}
    assert counts("failed_executions") == {"invalid_command": 2, "invalid_argument": 1, "tcl_syntax": 2,
                                           "runtime_failure": 2}
    fe = dist[(dist["stage"] == "failed_executions") & (dist["outcome"] == "tcl_syntax")].iloc[0]
    assert fe["pct"] == pytest.approx(100 * 2 / 7) and fe["per_episode"] == pytest.approx(2 / 5)

    trans = ea.transition_table(data.episodes)
    pairs = {(a, b): n for a, b, n in zip(trans["first_outcome"], trans["final_outcome"], trans["count"])}
    assert pairs == {("success", "success"): 1, ("validation_failure", "validation_failure"): 1,
                     ("invalid_command", "success"): 1, ("tcl_syntax", "success"): 1,
                     ("runtime_failure", "runtime_failure"): 1}
    rec = ea.recovery_by_first_outcome(data.episodes).set_index("first_outcome")
    assert rec.loc["invalid_command", "recovered"] == 1 and rec.loc["runtime_failure", "recovered"] == 0
    assert rec.loc["runtime_failure", "same_final"] == 1
    assert "success" not in rec.index


def test_failing_command_is_first_word_of_failing_line():
    assert mx.first_word(SCRIPT, 3) == "global_placement"
    assert mx.first_word("a\n   [detailed_route -x]\n", 2) == "detailed_route"
    assert mx.first_word("set x 1\n  # comment\n", 2) is None
    assert mx.first_word("set x 1\n", 5) is None and mx.first_word("set x 1\n", None) is None
    other = "puts hi\nestimate_parasitics -placement\n"
    dicts = [
        fake_episode("C_feedback", 0, "T1", ["invalid_argument", "invalid_argument", "ok"]),       # line 3 twice
        fake_episode("C_feedback", 0, "T2", ["missing_prerequisite", "vf"], scripts=[other, other], lines=[2, 2]),
        fake_episode("C_feedback", 0, "T3", ["unsafe_command"], lines=[None]),                      # no line known
    ]
    cmds = ea.failing_commands(experiment(dicts).attempts)
    overall = cmds[cmds["scope"] == "all"]
    assert list(zip(overall["command"], overall["count"])) == [("global_placement", 2), ("estimate_parasitics", 1)]
    assert overall["top_error_type"].tolist() == ["invalid_argument", "missing_prerequisite"]
    assert (overall["n_failed"].iloc[0], overall["n_located"].iloc[0]) == (4, 3)
    assert overall["pct"].iloc[0] == pytest.approx(200 / 3)


def test_task_profiles():
    dicts = []
    for c in ("A_baseline", "D_full"):
        for r in range(3):
            dicts.append(fake_episode(c, r, "NEVER", ["vf"], category="routing"))
            dicts.append(fake_episode(c, r, "ALWAYS", ["ok"], category="timing"))
            dicts.append(fake_episode(c, r, "DEPENDS", ["ok" if c == "D_full" else "vf"], category="cts"))
            dicts.append(fake_episode(c, r, "FLAKY", ["ok" if r == 0 else "vf"], category="cts"))
    prof = ea.task_profiles(experiment(dicts).episodes).set_index("task_id")
    assert prof.loc["NEVER", "profile"] == "never_solved"
    assert prof.loc["ALWAYS", "profile"] == "always_solved"
    assert prof.loc["DEPENDS", "profile"] == "configuration_dependent"
    assert (prof.loc["DEPENDS", "A_baseline"], prof.loc["DEPENDS", "D_full"]) == (0.0, 100.0)
    assert not prof.loc["DEPENDS", "run_dependent"] and prof.loc["FLAKY", "run_dependent"]
    assert ea.profile_counts(prof.reset_index()) == {"never_solved": 1, "always_solved": 1,
                                                     "configuration_dependent": 2}
    assert ea.profile_configs(prof.reset_index()) == ["A_baseline", "D_full"]


# --------------------------------------------------------- loading/coverage
def test_loading_deduplicates_and_skips_malformed_lines(tmp_path):
    clean_late = fake_episode("A_baseline", 0, "T1", ["ok"], timestamp_end="2000-01-01T00:09:00Z")
    clean_early = fake_episode("A_baseline", 0, "T1", ["vf"], timestamp_end="2000-01-01T00:05:00Z")
    harness = fake_episode("A_baseline", 0, "T1", [], error="RuntimeError: synthetic API outage",
                           timestamp_end="2000-01-01T00:10:00Z")
    drifted = fake_episode("A_baseline", 0, "T2", ["vf"])
    drifted["attempts"][0]["llm_calls"][0]["new_field"] = 1      # schema drift in a nested record
    lines = [json.dumps(d) for d in (clean_early, harness, clean_late, drifted)]
    lines += ['{"truncated": ', "[1, 2, 3]", json.dumps({"config": "A_baseline"})]
    exp_dir = tmp_path / "SYNTHETIC-load"
    exp_dir.mkdir()
    (exp_dir / "A_baseline.jsonl").write_text("\n".join(lines) + "\n")
    data = mx.load_experiment("SYNTHETIC-load", tmp_path)
    eps = data.episodes.set_index("task_id")
    assert len(eps) == 2
    # the harness-error record is newest but loses to a clean one; among clean records the latest wins
    assert bool(eps.loc["T1", "success"]) and not bool(eps.loc["T1", "harness_error"])
    assert data.report.duplicates_dropped == {"A_baseline": 2}
    assert data.report.malformed_lines == 3 and data.report.lenient_records == 1
    assert data.report.files["A_baseline.jsonl"]["records"] == 4
    assert "metadata.json missing" in data.report.warnings


def test_coverage_counts_missing_episodes_and_harness_errors(tmp_path):
    meta = {"task_ids": ["T1", "T2", "T3", "T4"], "runs_per_config": 3,
            "configurations": {"A_baseline": {}, "C_feedback": {}}}
    dicts = [fake_episode("A_baseline", r, t, ["ok"]) for r in (0, 1) for t in ("T1", "T2", "T3", "T4")
             if (r, t) != (1, "T3")]
    dicts += [fake_episode("C_feedback", r, t, ["vf", "ok"]) for r in range(3) for t in ("T1", "T2", "T3")]
    dicts.append(fake_episode("C_feedback", 0, "T4", [], error="RuntimeError: synthetic"))
    write_experiment(tmp_path, "SYNTHETIC-cov", dicts, meta)
    data = mx.load_experiment("SYNTHETIC-cov", tmp_path)
    cov, details = mx.coverage(data)
    cov = cov.set_index("config")
    # A: run 2 missing entirely (4) + T3 of run 1 (1); C: T4 missing in runs 1 and 2
    assert cov.loc["A_baseline", "recorded_episodes"] == 7 and cov.loc["A_baseline", "missing_episodes"] == 5
    assert cov.loc["A_baseline", "coverage_pct"] == pytest.approx(100 * 7 / 12)
    assert cov.loc["C_feedback", "missing_episodes"] == 2 and cov.loc["C_feedback", "harness_errors"] == 1
    assert details["tasks_source"] == "metadata" and details["runs_per_config"] == 3
    assert details["missing"]["A_baseline"]["missing_tasks_by_run"] == {"1": ["T3"]}
    # by default the aborted episode is a failure; with drop_harness_errors it becomes a missing episode
    main = mx.main_results(data.episodes).set_index("config")
    assert main.loc["C_feedback", "n_episodes"] == 10
    # the aborted episode has no attempt 1, so it is not in the recovery denominator: 9/9 recovered
    assert (main.loc["C_feedback", "n_first_failed"], main.loc["C_feedback", "n_recovered"]) == (9, 9)
    assert main.loc["C_feedback", "recovery_rate"] == pytest.approx(100.0)
    dropped = mx.load_experiment("SYNTHETIC-cov", tmp_path, drop_harness_errors=True)
    assert len(dropped.episodes[dropped.episodes["config"] == "C_feedback"]) == 9
    assert mx.coverage(dropped)[0].set_index("config").loc["C_feedback", "harness_errors_dropped"] == 1


def test_inconsistent_records_are_flagged():
    d = fake_episode("C_feedback", 0, "T1", ["vf", "ok"])
    d["first_attempt_success"] = True            # contradicts attempt 1
    d["failed_executions"] = 3
    issues = experiment([d]).episodes["inconsistencies"].iloc[0].split(";")
    assert set(issues) == {"first_attempt_success", "failed_executions"}


# ------------------------------------------------------------- end to end
def synthetic_benchmark(seed: int = 3, n_tasks: int = 14, runs: int = 3) -> list[dict]:
    """A whole fake experiment: six configurations x ``runs`` x ``n_tasks`` with random outcomes."""
    rng = random.Random(seed)
    cats = ["floorplanning", "placement", "timing", "cts", "routing", "inspection", "optimization"]
    errors = ["invalid_command", "invalid_argument", "tcl_syntax", "missing_prerequisite",
              "incorrect_design_context", "runtime_failure", "tool_error", "unsafe_command"]
    p_first = {"A_baseline": 0.15, "B_rag": 0.27, "C_feedback": 0.15, "D_full": 0.27, "E_vector_only": 0.22,
               "F_single_repair": 0.27, "G_targeted_repair": 0.27}
    out = []
    for cfg, spec in CONFIGS.items():
        for r in range(runs):
            for t in range(n_tasks):
                ease = (t % 5) / 12.0 - (0.15 if t % 7 == 6 else 0.0)
                outcomes = []
                for a in range(spec["max_attempts"]):
                    if rng.random() < p_first[cfg] + ease + 0.05 * a:
                        outcomes.append("ok")
                        break
                    outcomes.append(rng.choice(errors + ["vf"]))
                ok = outcomes[-1] == "ok"
                declared = (ok if rng.random() < 0.85 else not ok) if spec["feedback"] else None
                out.append(fake_episode(cfg, r, f"SYN-{t:02d}", outcomes, category=cats[t % len(cats)],
                                        difficulty=["easy", "medium", "hard"][t % 3], declared=declared,
                                        cost=0.02 + 0.01 * (spec["rag"] != "none"), experiment_id="SYNTHETIC-e2e",
                                        tokens=(1200, 300, 800, 100)))
    return out


def _snapshot(path: Path) -> dict[str, float]:
    return {str(p): p.stat().st_mtime for p in path.rglob("*")} if path.exists() else {}


def test_make_report_end_to_end(tmp_path):
    dicts = synthetic_benchmark()
    meta = {"experiment_id": "SYNTHETIC-e2e", "note": "synthetic test data, not a real experiment",
            "task_ids": [f"SYN-{t:02d}" for t in range(14)], "runs_per_config": 3,
            "configurations": dict(CONFIGS)}
    write_experiment(tmp_path / "results", "SYNTHETIC-e2e", dicts, meta)
    out = tmp_path / "report"
    before = _snapshot(PAPER_DIR)
    rc = make_report.main(["--experiment", "SYNTHETIC-e2e", "--results-root", str(tmp_path / "results"),
                           "--out-dir", str(out), "--n-boot", "2000"])
    assert rc == 0
    assert _snapshot(PAPER_DIR) == before                       # nothing written into paper/

    for stem in make_report.TABLE_WRITERS:
        assert (out / "tables" / f"{stem}.csv").stat().st_size > 0
        assert (out / "tables" / f"{stem}.md").read_text().startswith("# ")
    figures = ["completion_by_config", "category_heatmap", "error_types_first_vs_final",
               "cumulative_success_by_attempt", "cost_vs_completion", "failed_executions_per_task",
               "failed_executions_by_task", "success_by_task"]
    from PIL import Image
    for name in figures:
        assert (out / "figures" / f"{name}.pdf").read_bytes().startswith(b"%PDF")
        with Image.open(out / "figures" / f"{name}.png") as im:
            assert round(im.info["dpi"][0]) == 300

    summary = json.loads((out / "results_summary.json").read_text())   # strict JSON (no NaN)
    assert summary["experiment_id"] == "SYNTHETIC-e2e"
    assert set(summary["configurations"]) == set(CONFIGS)
    # recompute the headline numbers straight from the raw records, independently of the package
    for cfg in CONFIGS:
        rates = [100 * np.mean([d["success"] for d in dicts if d["config"] == cfg and d["run"] == r])
                 for r in range(3)]
        row = summary["configurations"][cfg]
        assert row["completion_mean"] == pytest.approx(np.mean(rates))
        assert row["completion_std"] == pytest.approx(np.std(rates, ddof=1))
        assert row["completion_runs"] == pytest.approx(rates)
        costs = [d["cost_usd"] for d in dicts if d["config"] == cfg]
        assert row["cost_per_episode_usd"] == pytest.approx(np.mean(costs))
        assert summary["coverage"]["per_config"][cfg]["coverage_pct"] == pytest.approx(100.0)

    def task_rate(cfg: str, task: str) -> float:
        return np.mean([d["success"] for d in dicts if d["config"] == cfg and d["task_id"] == task])

    a_vs_d = summary["contrasts"]["A_baseline vs D_full"]
    tasks = [f"SYN-{t:02d}" for t in range(14)]
    diff = 100 * np.mean([task_rate("D_full", t) - task_rate("A_baseline", t) for t in tasks])
    assert a_vs_d["diff_pp"] == pytest.approx(diff)
    assert a_vs_d["ci_low_pp"] <= a_vs_d["diff_pp"] <= a_vs_d["ci_high_pp"]
    assert set(summary["contrasts"]) == {f"{a} vs {b}" for a, b, _ in st.PLANNED_CONTRASTS}
    assert set(summary["follow_up_contrasts"]) == {f"{a} vs {b}" for a, b, _ in st.FOLLOW_UP_CONTRASTS}
    assert summary["cochran_q"]["k"] == len(st.ABLATION_CONFIGS) == 6  # follow-up configs excluded
    assert summary["cochran_q"]["n_tasks"] == 14
    assert sum(summary["task_profiles"]["counts"].values()) == 14
    assert summary["analysis_settings"]["wilcoxon"]["zero_method"] == "pratt"
    assert summary["inputs"]["metadata"]["note"].startswith("synthetic")
    assert "tables/main_results.md" in summary["outputs"] and "figures/success_by_task.pdf" in summary["outputs"]
    main_md = (out / "tables" / "main_results.md").read_text()
    for cfg in CONFIGS:
        assert f"| {cfg} |" in main_md


def test_make_report_errors_without_records(tmp_path, capsys):
    (tmp_path / "results" / "SYNTHETIC-empty").mkdir(parents=True)
    rc = make_report.main(["--experiment", "SYNTHETIC-empty", "--results-root", str(tmp_path / "results"),
                           "--out-dir", str(tmp_path / "out"), "--no-figures"])
    assert rc == 1 and "no usable episode records" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()
