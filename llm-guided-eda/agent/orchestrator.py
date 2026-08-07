"""One agent episode: generate -> execute -> self-check -> (diagnose -> repair) for one task.

Every attempt executes the complete script in a NEW run directory from the
task's starting snapshot, so failed attempts are rolled back by construction.
The benchmark validator scores every attempt for the analysis, but its verdict
is never shown to the LLM and never influences control flow: the agent stops
when its own self-check passes (feedback configurations) or after one attempt.
"""
from __future__ import annotations

import shutil
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agent.command_generator import extract_tcl
from agent.error_classifier import diagnose
from agent.error_corrector import build_repair_message
from agent.llm import LLMClient, LLMError, can_continue, utc_now
from agent.planner import retrieval_query
from agent.prompts import SYSTEM_PROMPT, generation_message
from agent.retrieval import DocRetriever
from agent.targeted_retrieval import SyntaxCards
from agent.state_manager import DesignState
from agent.verifier import verify
from benchmark.design_context import design_context
from benchmark.states import load_baseline_probe
from benchmark.task_loader import Task
from benchmark.task_validator import validate
from common.config import load_config
from experiments.record_schema import AttemptRecord, EpisodeRecord, LLMCallRecord
from openroad.executor import OpenROADExecutor

RAG_MODES = ("none", "hybrid", "vector", "bm25")


@dataclass(frozen=True)
class AgentConfig:
    name: str
    rag: str = "none"            # none | hybrid | vector | bm25
    feedback: bool = False       # execution feedback + iterative repair
    max_attempts: int = 1        # OpenROAD executions allowed per task
    final_k: int = 6             # chunks retrieved per query
    max_context_chars: int = 14000
    top_k_semantic: int = 8      # recorded for provenance; the rag module applies them
    top_k_keyword: int = 8
    rrf_k: int = 60
    targeted_repair: bool = False        # add the exact syntax card of the failing command to repairs
    first_attempt_from: str | None = None  # reuse this configuration's first-attempt generations (same prompt)

    def __post_init__(self) -> None:
        if self.rag not in RAG_MODES:
            raise ValueError(f"{self.name}: rag must be one of {RAG_MODES}, got {self.rag!r}")
        if self.max_attempts < 1:
            raise ValueError(f"{self.name}: max_attempts must be >= 1")
        if self.targeted_repair and not (self.use_rag and self.feedback):
            raise ValueError(f"{self.name}: targeted_repair needs retrieval and feedback")

    def record(self) -> dict[str, Any]:
        """Settings for metadata.json; the optional fields appear only when set, so older records still match."""
        d = asdict(self)
        if not self.targeted_repair:
            d.pop("targeted_repair")
        if self.first_attempt_from is None:
            d.pop("first_attempt_from")
        return d

    @property
    def use_rag(self) -> bool:
        return self.rag != "none"

    @property
    def attempt_budget(self) -> int:
        return self.max_attempts if self.feedback else 1


def config_names() -> list[str]:
    return list(load_config("experiment_config").get("configurations") or {})


def load_agent_config(name: str) -> AgentConfig:
    """Configuration ``name`` from config/experiment_config.yaml."""
    exp = load_config("experiment_config")
    configs = exp.get("configurations") or {}
    if name not in configs:
        raise KeyError(f"unknown configuration {name!r}; known: {sorted(configs)}")
    spec, r = configs[name], exp.get("retrieval") or {}
    return AgentConfig(
        name=name, rag=str(spec.get("rag", "none")).lower(), feedback=bool(spec.get("feedback", False)),
        max_attempts=int(spec.get("max_attempts", 1)), final_k=int(r.get("final_k", 6)),
        max_context_chars=int(r.get("max_context_chars", 14000)), top_k_semantic=int(r.get("top_k_semantic", 8)),
        top_k_keyword=int(r.get("top_k_keyword", 8)), rrf_k=int(r.get("rrf_k", 60)),
        targeted_repair=bool(spec.get("targeted_repair", False)), first_attempt_from=spec.get("first_attempt_from"))


def cache_key(experiment_id: str, cfg: AgentConfig, run_index: int, task_id: str, attempt: int) -> str:
    """Replay-cache key: every (experiment, config, run, task, attempt) is an independent sample.

    With ``first_attempt_from`` the first attempt uses that configuration's key, so an identical
    generation prompt replays the same sample (common random numbers for a paired comparison).
    """
    name = cfg.first_attempt_from if attempt == 1 and cfg.first_attempt_from else cfg.name
    return f"{experiment_id}/{name}/run{run_index}/{task_id}/attempt{attempt}"


def episode_label(experiment_id: str, cfg: AgentConfig, run_index: int, task_id: str, attempt: int) -> str:
    return f"{experiment_id}/{cfg.name}/run{run_index}/{task_id}/attempt{attempt}"


def run_episode(task: Task, cfg: AgentConfig, llm: LLMClient, retriever: DocRetriever | None,
                executor: OpenROADExecutor, run_root: Path, experiment_id: str, run_index: int,
                cards: SyntaxCards | None = None) -> EpisodeRecord:
    """Run one task under one configuration. LLM failures after retries are recorded in
    ``EpisodeRecord.error``; only fatal LLM errors (credentials, model) propagate."""
    t0 = time.monotonic()
    started = utc_now()
    state = task.state
    before = DesignState.from_probe(load_baseline_probe(task.start_state))
    episode_dir = Path(run_root) / experiment_id / cfg.name / f"run{run_index}" / task.id
    attempts: list[AttemptRecord] = []
    calls: list[LLMCallRecord] = []
    error: str | None = None
    try:
        if cfg.use_rag and retriever is None:
            raise ValueError(f"configuration {cfg.name} (rag={cfg.rag}) needs a retriever")
        if cfg.targeted_repair and cards is None:
            raise ValueError(f"configuration {cfg.name} (targeted_repair) needs syntax cards")
        docs, shown = None, []
        if cfg.use_rag:
            chunks = retriever.retrieve(retrieval_query(task.instruction), k=cfg.final_k)
            docs = retriever.format_context(chunks, cfg.max_context_chars)
            shown = [c.id for c in chunks]
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": generation_message(task.instruction, design_context(state), docs)}]
        resp = llm.complete(SYSTEM_PROMPT, messages, purpose="generate",
                            cache_key=cache_key(experiment_id, cfg, run_index, task.id, 1))
        calls.append(resp.call)
        retrieved = list(shown)
        for k in range(1, cfg.attempt_budget + 1):
            script = extract_tcl(resp.text)
            run_dir = episode_dir / f"attempt{k}"
            shutil.rmtree(run_dir, ignore_errors=True)  # leftovers of an interrupted run must not count
            result = executor.run(script, run_dir, preamble=state.preamble(), links=state.links(),
                                  label=episode_label(experiment_id, cfg, run_index, task.id, k))
            hidden = validate(task, result, executor)  # scoring only
            after = DesignState.from_probe(result.probe)
            verdict = verify(task.instruction, result, before, after)
            diag = None if verdict.ok else diagnose(result, verdict, script)
            attempts.append(AttemptRecord(
                attempt=k, script=script, exec_success=result.error_type is None, error_type=result.error_type,
                error_message=result.error_message, failing_line=result.failing_line,
                execution_time_s=result.execution_time, validator_passed=hidden.passed,
                validator_summary=hidden.summary(), agent_verdict_ok=verdict.ok,
                agent_verdict_reasons=list(verdict.reasons), diagnosed_error_type=diag.error_type if diag else None,
                retrieved_chunk_ids=retrieved, llm_calls=[resp.call], run_dir=result.run_dir))
            executor.cleanup(run_dir)
            if verdict.ok or k == cfg.attempt_budget or not can_continue(resp):
                break
            extra_docs, retrieved = None, []
            if cfg.use_rag:
                targeted = cards.for_diagnosis(diag) if cfg.targeted_repair else None
                budget = cfg.max_context_chars - (len(targeted.text) + 2 if targeted and targeted.text else 0)
                fresh = [c for c in retriever.retrieve(diag.retrieval_query, k=cfg.final_k)
                         if c.id not in shown and not (targeted and c.id in targeted.ids)]
                parts = [targeted.text] if targeted and targeted.text else []
                if fresh and budget > 0:
                    parts.append(retriever.format_context(fresh, budget))
                    retrieved = [c.id for c in fresh]
                    shown += retrieved
                if targeted and targeted.cards:
                    retrieved = targeted.ids + retrieved
                extra_docs = "\n\n".join(parts) or None
            repair = build_repair_message(attempt=k, max_attempts=cfg.max_attempts, result=result, diagnosis=diag,
                                          verdict=verdict, before=before, after=after, docs=extra_docs,
                                          truncated=resp.call.stop_reason == "max_tokens")
            messages.append({"role": "assistant", "content": resp.assistant_content})  # verbatim, append-only
            messages.append({"role": "user", "content": repair})
            resp = llm.complete(SYSTEM_PROMPT, messages, purpose="repair",
                                cache_key=cache_key(experiment_id, cfg, run_index, task.id, k + 1))
            calls.append(resp.call)
    except LLMError as e:
        if e.fatal:
            raise
        error = f"LLMError: {e}"
    except Exception:  # harness-level failure: record it and let the experiment continue
        error = "episode aborted: " + traceback.format_exc(limit=6)

    last = attempts[-1] if attempts else None
    final_error = None
    if last is not None:
        final_error = last.error_type or (None if last.validator_passed else "validation_failure")
    return EpisodeRecord(
        experiment_id=experiment_id, config=cfg.name, run=run_index, task_id=task.id, category=task.category,
        difficulty=task.difficulty, split=task.split, rag=cfg.rag, feedback=cfg.feedback,
        max_attempts=cfg.max_attempts,
        success=error is None and last is not None and last.validator_passed,
        first_attempt_success=bool(attempts) and attempts[0].validator_passed,
        attempts_used=len(attempts),
        agent_declared_success=last.agent_verdict_ok if last else None,
        final_error_type=final_error,
        failed_executions=sum(a.error_type is not None for a in attempts),
        total_execution_time_s=round(sum(a.execution_time_s for a in attempts), 3),
        wall_time_s=round(time.monotonic() - t0, 3),
        llm_calls=len(calls),
        input_tokens=sum(c.input_tokens for c in calls),
        output_tokens=sum(c.output_tokens for c in calls),
        cache_read_tokens=sum(c.cache_read_tokens for c in calls),
        cache_write_tokens=sum(c.cache_write_tokens for c in calls),
        cost_usd=round(sum(c.cost_usd for c in calls), 6),
        model=llm.model, timestamp_start=started, timestamp_end=utc_now(), attempts=attempts, error=error)
