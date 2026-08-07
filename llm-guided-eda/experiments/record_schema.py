"""Experiment record schema shared by the experiment runner and the analysis code.

One JSON line per (configuration, run, task) episode is appended to
``experiments/results/<experiment_id>/<config>.jsonl``; experiment-level
metadata goes to ``experiments/results/<experiment_id>/metadata.json``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any


@dataclass
class LLMCallRecord:
    purpose: str                    # "generate" | "repair"
    provider: str
    model_requested: str
    model_reported: str             # model id echoed by the API
    effort: str | None
    thinking: str | None
    max_tokens: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    latency_s: float
    stop_reason: str | None
    request_id: str | None
    timestamp: str                  # ISO-8601 UTC
    cached: bool = False            # served from the local replay cache (no new API call)
    seed: int | None = None         # per-call sampling seed sent to the server (local/OpenAI-compatible)
    sampling: dict[str, Any] | None = None  # sampling settings sent (temperature, top_p, ...), if any


@dataclass
class AttemptRecord:
    attempt: int                    # 1-based
    script: str
    exec_success: bool              # ran without Tcl/tool error, timeout or policy rejection
    error_type: str | None          # executor classification (None if the execution was clean)
    error_message: str | None
    failing_line: int | None
    execution_time_s: float
    validator_passed: bool          # hidden benchmark verdict for this attempt (analysis only)
    validator_summary: str
    agent_verdict_ok: bool | None   # agent self-verification (None when not run)
    agent_verdict_reasons: list[str] = field(default_factory=list)
    diagnosed_error_type: str | None = None   # what the agent was told (incl. validation_failure)
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    llm_calls: list[LLMCallRecord] = field(default_factory=list)
    run_dir: str = ""


@dataclass
class EpisodeRecord:
    experiment_id: str
    config: str
    run: int
    task_id: str
    category: str
    difficulty: str
    split: str
    rag: str                        # none | hybrid | vector | bm25
    feedback: bool
    max_attempts: int
    success: bool                   # validator verdict on the final attempt
    first_attempt_success: bool
    attempts_used: int
    agent_declared_success: bool | None
    final_error_type: str | None    # final attempt error_type, or "validation_failure" if clean but failed
    failed_executions: int          # attempts whose execution errored, timed out or was rejected
    total_execution_time_s: float
    wall_time_s: float
    llm_calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    model: str
    timestamp_start: str
    timestamp_end: str
    attempts: list[AttemptRecord] = field(default_factory=list)
    error: str | None = None        # harness-level exception that aborted the episode, if any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EpisodeRecord":
        d = dict(d)
        attempts = []
        for a in d.pop("attempts", []):
            a = dict(a)
            a["llm_calls"] = [LLMCallRecord(**c) for c in a.get("llm_calls", [])]
            attempts.append(AttemptRecord(**{k: v for k, v in a.items() if k in _names(AttemptRecord)}))
        rec = cls(**{k: v for k, v in d.items() if k in _names(cls)})
        rec.attempts = attempts
        return rec


def _names(cls: type) -> set[str]:
    return {f.name for f in fields(cls)}
