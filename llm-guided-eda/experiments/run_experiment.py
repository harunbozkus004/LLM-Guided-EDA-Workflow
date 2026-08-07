"""Run agent configurations over benchmark tasks; one JSON line per (configuration, run, task) episode.

    python -m experiments.run_experiment --config all --runs 1 2 3 --split test --experiment-id main \
        [--tasks FP-01 PL-03 ...] [--parallel N] [--provider local|anthropic|openai_compatible|mock] \
        [--model M] [--effort E]

The default provider is the free local llama.cpp server of config/model_config.yaml
(start it first with ``scripts/llm_server.sh start``); with it, 6 episodes run in
parallel by default (the server has 4 slots; the rest overlap with OpenROAD runs).

Records are appended to experiments/results/<id>/<config>.jsonl. The run is
resumable: an episode already recorded without an error is skipped, so an
interrupted experiment is continued by repeating the same command (the LLM
replay cache in experiments/llm_cache avoids paying twice for interrupted
episodes). experiments/results/<id>/metadata.json documents the setup; resuming
with different generation settings is refused. Per-attempt sandboxes go to
experiments/runs/<id>/ (git-ignored).

``--provider mock`` answers every request with the task's reference script
(pipeline smoke test, no API calls).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import logging
import urllib.error
import urllib.request
import platform
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from common.config import load_config
from common.jsonl import append_jsonl, read_jsonl
from common.paths import KB_DIR, RESULTS_DIR, ROOT, RUNS_DIR, rel
from agent.llm import PROVIDERS, LLMClient, LLMError, Responder, plain_text, make_llm, utc_now
from agent.orchestrator import AgentConfig, config_names, load_agent_config, run_episode
from agent.prompts import SYSTEM_PROMPT
from agent.retrieval import DocRetriever, load_retriever
from agent.targeted_retrieval import SyntaxCards
from benchmark.task_loader import Task, load_tasks, task_set_hash
from experiments.record_schema import EpisodeRecord
from openroad.executor import OpenROADExecutor

log = logging.getLogger("experiments")
PACKAGES = ["anthropic", "openai", "sentence-transformers", "faiss-cpu", "rank-bm25", "numpy", "pandas", "scipy",
            "statsmodels", "PyYAML", "python-dotenv", "pypdf", "torch"]
# Settings that must not change when an experiment is resumed.
CONTROLLED = ("provider", "model", "effort", "thinking", "max_tokens", "temperature", "base_url", "sampling",
              "enable_thinking", "seed")
LOCAL_PARALLEL_EPISODES = 6


def reference_responder(tasks: list[Task]) -> Responder:
    """Mock policy for smoke runs: answer every request with the task's reference script."""
    scripts = {t.instruction: t.reference_tcl() for t in tasks}

    def respond(system: str, messages: list[dict[str, Any]], purpose: str) -> str:
        first = plain_text(messages[0]["content"])
        for instruction, script in scripts.items():
            if first.startswith(f"TASK\n{instruction}\n"):
                return f"Mock answer: the benchmark reference script.\n```tcl\n{script.rstrip()}\n```\n"
        return "```tcl\n# mock: unknown task\n```\n"

    return respond


# ------------------------------------------------------------------ metadata
def _sha12(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.is_file() else None


def _openroad_version(executor: OpenROADExecutor) -> str | None:
    try:
        out = subprocess.run([str(executor.openroad_bin), "-version"], capture_output=True, text=True, timeout=60,
                             cwd=RUNS_DIR if RUNS_DIR.is_dir() else ROOT,
                             env={"HOME": str(RUNS_DIR), "PATH": "/usr/bin:/bin", "LANG": "C"})
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _git_commit() -> str | None:
    if not (ROOT / ".git").exists():
        return None
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _packages() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _get_json(url: str, timeout: float = 5.0) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (local server URL from the config)
        return json.loads(r.read().decode())


def local_server_info(base_url: str) -> dict[str, Any]:
    """``/v1/models`` and ``/props`` of the llama.cpp server; raises OSError if it is unreachable."""
    base = base_url.rstrip("/")
    root = base[: -len("/v1")] if base.endswith("/v1") else base
    info: dict[str, Any] = {"url": base, "models": _get_json(f"{base}/models")}
    try:
        props = _get_json(f"{root}/props")
    except (OSError, ValueError) as e:
        info["props"] = f"unavailable: {e}"
        return info
    if isinstance(props, dict):
        for key in ("chat_template", "chat_template_tool_use"):  # long: recorded as a hash
            tmpl = props.pop(key, None)
            if isinstance(tmpl, str):
                info[f"{key}_sha256"] = hashlib.sha256(tmpl.encode()).hexdigest()[:12]
    info["props"] = props
    # The server reports absolute paths; keep them relative to the repository in the records.
    return json.loads(json.dumps(info).replace(json.dumps(str(ROOT) + "/")[1:-1], ""))


def build_metadata(args: argparse.Namespace, llm: LLMClient, configs: list[AgentConfig], tasks: list[Task],
                   retrievers: dict[str, DocRetriever], executor: OpenROADExecutor,
                   server_info: dict[str, Any] | None = None) -> dict[str, Any]:
    or_cfg = load_config("openroad_config")
    meta: dict[str, Any] = {
        "experiment_id": args.experiment_id,
        "llm": llm.settings(),
        "configurations": {c.name: c.record() for c in configs},
        "retrieval": load_config("experiment_config").get("retrieval"),
        "retrievers": {mode: r.description for mode, r in retrievers.items()},
        "runs": sorted(args.runs),
        "split": args.split,
        "tasks": sorted(t.id for t in tasks),
        "task_set_hash": task_set_hash(args.split),
        "knowledge_base_manifest_hash": _sha12(KB_DIR / "manifest.json"),
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:12],
        "openroad": {"version": or_cfg.get("openroad_version"), "binary": rel(executor.openroad_bin),
                     "reported": _openroad_version(executor), "timeout_s": executor.timeout_s,
                     "threads": executor.threads, "seatbelt": executor.use_seatbelt},
        "python": sys.version.split()[0],
        "packages": _packages(),
        "platform": {"system": platform.platform(), "machine": platform.machine(),
                     "processor": platform.processor() or None},
        "git_commit": _git_commit(),
    }
    if llm.provider == "local":
        meta["local_llm"] = load_config("model_config").get("local_llm")
        meta["local_server"] = server_info
    return meta


def merge_metadata(path: Path, new: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    """Combine with an existing metadata.json; refuse to mix generation settings or task sets."""
    if not path.is_file():
        return {**new, "start": session["start"], "end": None, "sessions": [session]}
    old = json.loads(path.read_text())
    problems = [f"llm.{k}: {old['llm'].get(k)!r} -> {new['llm'].get(k)!r}" for k in CONTROLLED
                if old.get("llm", {}).get(k) != new["llm"].get(k)]
    for key in ("split", "task_set_hash", "knowledge_base_manifest_hash", "system_prompt_sha256"):
        if old.get(key) != new.get(key):
            problems.append(f"{key}: {old.get(key)!r} -> {new.get(key)!r}")
    for name, cfg in new["configurations"].items():
        if name in old.get("configurations", {}) and old["configurations"][name] != cfg:
            problems.append(f"configuration {name} changed")
    if problems:
        raise SystemExit(f"experiment '{new['experiment_id']}' was started with different settings:\n  "
                         + "\n  ".join(problems) + "\nUse a new --experiment-id (or restore the settings).")
    merged = {**old, **new}
    merged["configurations"] = {**old.get("configurations", {}), **new["configurations"]}
    merged["retrievers"] = {**old.get("retrievers", {}), **new["retrievers"]}
    merged["runs"] = sorted(set(old.get("runs", [])) | set(new["runs"]))
    merged["tasks"] = sorted(set(old.get("tasks", [])) | set(new["tasks"]))
    merged["start"] = old.get("start") or session["start"]
    merged["end"] = None
    merged["sessions"] = old.get("sessions", []) + [session]
    return merged


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, default=str) + "\n")
    tmp.replace(path)


# ------------------------------------------------------------------ main
def parse_args(argv: list[str] | None) -> argparse.Namespace:
    exp = load_config("experiment_config")
    ap = argparse.ArgumentParser(prog="python -m experiments.run_experiment",
                                 description="Run agent configurations over benchmark tasks.")
    ap.add_argument("--config", nargs="+", default=["all"],
                    help="configuration name(s) from config/experiment_config.yaml, or 'all'")
    ap.add_argument("--runs", nargs="+", type=int, default=list(range(1, int(exp.get("runs_per_config", 3)) + 1)),
                    help="run indices (independent repetitions)")
    ap.add_argument("--split", choices=["test", "dev"], default=exp.get("task_split", "test"))
    ap.add_argument("--tasks", nargs="+", help="task ids (default: every task of the split)")
    ap.add_argument("--parallel", type=int,
                    help=f"episodes run concurrently (default: {LOCAL_PARALLEL_EPISODES} for the local provider, "
                         f"else parallel_episodes of config/experiment_config.yaml)")
    ap.add_argument("--experiment-id", required=True, help="results go to experiments/results/<id>/")
    ap.add_argument("--provider", choices=list(PROVIDERS), help="default: provider of config/model_config.yaml")
    ap.add_argument("--model", help="override the model of config/model_config.yaml")
    ap.add_argument("--effort", help="override output_config.effort (anthropic provider only)")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.experiment_id):
        ap.error("--experiment-id may contain only letters, digits, '_', '.' and '-'")
    if (args.parallel is not None and args.parallel < 1) or any(r < 1 for r in args.runs):
        ap.error("--parallel and --runs must be positive")
    return args


def default_parallel(provider: str) -> int:
    """Concurrent episodes when --parallel is not given."""
    if provider == "local":
        return LOCAL_PARALLEL_EPISODES
    return int(load_config("experiment_config").get("parallel_episodes", 8))


def _summary_lines(out_dir: Path, configs: list[AgentConfig], runs: list[int], task_ids: set[str]) -> list[str]:
    lines = [f"{'config':16s} {'episodes':>8s} {'pass':>5s} {'rate':>6s} {'attempts':>8s} {'errors':>6s} "
             f"{'cost_usd':>9s}"]
    for cfg in configs:
        latest: dict[tuple[int, str], dict] = {}
        for rec in read_jsonl(out_dir / f"{cfg.name}.jsonl"):
            if rec["run"] in runs and rec["task_id"] in task_ids:
                key = (rec["run"], rec["task_id"])
                if key not in latest or latest[key].get("error") or not rec.get("error"):
                    latest[key] = rec
        recs = list(latest.values())
        if not recs:
            continue
        n, ok = len(recs), sum(r["success"] for r in recs)
        lines.append(f"{cfg.name:16s} {n:8d} {ok:5d} {ok / n:6.1%} {sum(r['attempts_used'] for r in recs) / n:8.2f} "
                     f"{sum(bool(r.get('error')) for r in recs):6d} {sum(r['cost_usd'] for r in recs):9.4f}")
    return lines


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    names = config_names() if "all" in args.config else list(dict.fromkeys(args.config))
    configs = [load_agent_config(n) for n in names]
    tasks = load_tasks(args.split, args.tasks)
    if not tasks:
        raise SystemExit(f"no tasks in split '{args.split}'")

    model_cfg = load_config("model_config")
    provider = args.provider or model_cfg.get("provider", "local")
    if args.parallel is None:
        args.parallel = default_parallel(provider)
    overrides: dict[str, Any] = {"provider": provider, "model": args.model, "effort": args.effort}
    if provider == "mock":
        overrides["mock_responses"] = reference_responder(tasks)
    llm = make_llm(overrides)
    server_info = None
    if provider == "local":
        base_url = (model_cfg.get("local_llm") or {}).get("base_url", "http://127.0.0.1:8080/v1")
        try:
            server_info = local_server_info(base_url)
        except (OSError, ValueError) as e:
            raise SystemExit(f"the local LLM server at {base_url} is not reachable ({e}).\n"
                             "Start it with: scripts/llm_server.sh start")
    executor = OpenROADExecutor()
    retrievers = {mode: load_retriever(mode, allow_fake=provider == "mock")
                  for mode in sorted({c.rag for c in configs if c.use_rag})}
    cards = SyntaxCards.load() if any(c.targeted_repair for c in configs) else None

    out_dir = RESULTS_DIR / args.experiment_id
    meta_path = out_dir / "metadata.json"
    session = {"start": utc_now(), "end": None, "argv": sys.argv[1:] if argv is None else list(argv),
               "status": "running"}
    if server_info is not None:
        session["local_server"] = server_info
    new_meta = build_metadata(args, llm, configs, tasks, retrievers, executor, server_info)
    if cards is not None:
        new_meta["syntax_cards"] = cards.description
    metadata = merge_metadata(meta_path, new_meta, session)
    write_json(meta_path, metadata)

    done = {(r["config"], r["run"], r["task_id"]) for c in configs for r in read_jsonl(out_dir / f"{c.name}.jsonl")
            if not r.get("error")}
    episodes = [(cfg, run, task) for run in sorted(args.runs) for task in tasks for cfg in configs
                if (cfg.name, run, task.id) not in done]
    skipped = len(configs) * len(args.runs) * len(tasks) - len(episodes)
    print(f"experiment {args.experiment_id}: {len(configs)} config(s) x {len(args.runs)} run(s) x {len(tasks)} "
          f"task(s); {len(episodes)} to run, {skipped} already recorded; provider={llm.provider} "
          f"model={llm.model} parallel={args.parallel} -> {rel(out_dir)}", flush=True)

    stop = threading.Event()
    fatal: list[str] = []
    progress = {"n": 0}
    lock = threading.Lock()

    def work(cfg: AgentConfig, run: int, task: Task) -> EpisodeRecord | None:
        if stop.is_set():
            return None
        try:
            rec = run_episode(task, cfg, llm, retrievers.get(cfg.rag), executor, RUNS_DIR, args.experiment_id, run,
                              cards=cards)
        except LLMError as e:  # fatal: every remaining episode would fail the same way
            stop.set()
            fatal.append(str(e))
            return None
        append_jsonl(out_dir / f"{cfg.name}.jsonl", rec.to_dict())
        verdict = f"ERROR ({rec.error.splitlines()[0][:120]})" if rec.error else ("PASS" if rec.success else "FAIL")
        with lock:
            progress["n"] += 1
            print(f"[{progress['n']:4d}/{len(episodes)}] {cfg.name:16s} run{run} {task.id:10s} -> {verdict:5s} "
                  f"attempts={rec.attempts_used}/{cfg.attempt_budget} llm={rec.llm_calls} cost=${rec.cost_usd:.4f} "
                  f"exec={rec.total_execution_time_s:.1f}s wall={rec.wall_time_s:.1f}s", flush=True)
        return rec

    status = "completed"
    t0 = time.monotonic()
    pool = ThreadPoolExecutor(max_workers=args.parallel)
    try:
        futures = [pool.submit(work, *ep) for ep in episodes]
        for f in as_completed(futures):
            f.result()
    except KeyboardInterrupt:
        status = "interrupted"
        stop.set()
        print("interrupted: waiting for running episodes to finish; rerun the same command to resume", flush=True)
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
    if fatal:
        status = "aborted"
        print(f"aborted on a fatal LLM error (nothing recorded for unfinished episodes): {fatal[0]}", flush=True)

    session.update(end=utc_now(), status=status, episodes_recorded=progress["n"], episodes_skipped=skipped)
    metadata["end"] = session["end"]
    write_json(meta_path, metadata)
    print(f"\n{status} in {time.monotonic() - t0:.1f}s; records in {rel(out_dir)}")
    print("\n".join(_summary_lines(out_dir, configs, sorted(args.runs), {t.id for t in tasks})))
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
