"""LLM clients: Anthropic, OpenAI-compatible endpoints, a scripted mock, and a replay cache.

Every call returns an :class:`LLMResponse` with the response text, the content
blocks to append verbatim to the conversation, and an
:class:`~experiments.record_schema.LLMCallRecord` (model reported by the API,
generation settings, token usage, cost, latency, timestamp).

Experimental control: no sampling parameters (temperature/top_p/top_k) are ever
sent to the Anthropic API, and server-side model fallbacks are never enabled -- a refusal is
recorded as ``stop_reason="refusal"`` instead of being answered by another model.
The local llama.cpp model (provider ``local``, the default) is sampled with fixed
settings and a per-call seed derived from the replay ``cache_key``, so every
(experiment, configuration, run, task, attempt) is reproducible yet independent.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from common.config import load_config, resolve
from common.paths import ROOT
from experiments.record_schema import LLMCallRecord

log = logging.getLogger(__name__)

# callable(system, messages, purpose) -> response text
Responder = Callable[[str, list[dict[str, Any]], str], str]
PROVIDERS = ("local", "anthropic", "openai_compatible", "mock")
LOCAL_SERVER_SLOTS = 4  # llama-server -np (scripts/llm_server.sh)


class LLMError(RuntimeError):
    """An LLM request failed after the SDK's own retries.

    ``fatal`` errors (bad credentials, unknown model, missing permission) would
    fail every episode the same way, so the experiment runner stops on them.
    """

    def __init__(self, message: str, *, fatal: bool = False):
        super().__init__(message)
        self.fatal = fatal


@dataclass
class LLMResponse:
    text: str                                # concatenated text blocks
    assistant_content: list[dict[str, Any]]  # all response blocks, appended verbatim (never edited)
    call: LLMCallRecord


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def can_continue(resp: LLMResponse) -> bool:
    """Whether the assistant turn can be appended and the conversation continued.

    A refusal, or a turn without any text (e.g. ``max_tokens`` reached while
    thinking), cannot be followed by a repair request.
    """
    if resp.call.stop_reason == "refusal":
        return False
    return any(b.get("type") == "text" and b.get("text") for b in resp.assistant_content)


# ------------------------------------------------------------------ helpers
_env_loaded = False
_env_lock = threading.Lock()


def load_env() -> None:
    """Load ``<repo>/.env`` (git-ignored) without overriding existing variables."""
    global _env_loaded
    with _env_lock:
        if _env_loaded:
            return
        _env_loaded = True
        path = ROOT / ".env"
        if path.is_file():
            from dotenv import load_dotenv
            load_dotenv(path, override=False)


_slots: threading.BoundedSemaphore | None = None
_slots_lock = threading.Lock()


def request_slots(limit: int) -> threading.BoundedSemaphore:
    """Process-wide limit on concurrent API requests (the first configured limit wins)."""
    global _slots
    with _slots_lock:
        if _slots is None:
            _slots = threading.BoundedSemaphore(max(1, int(limit)))
        return _slots


_warned_models: set[str] = set()
_warn_lock = threading.Lock()


def cost_usd(model: str, input_tokens: int, output_tokens: int, cache_read_tokens: int = 0,
             cache_write_tokens: int = 0, pricing: dict[str, dict[str, float]] | None = None) -> float:
    """Cost from ``pricing_usd_per_mtok`` in config/model_config.yaml (0.0 for unknown models)."""
    table = pricing if pricing is not None else (load_config("model_config").get("pricing_usd_per_mtok") or {})
    price = table.get(model)
    if price is None:
        with _warn_lock:
            if model not in _warned_models:
                _warned_models.add(model)
                log.warning("no pricing for model %r in config/model_config.yaml; recording cost 0.0", model)
        return 0.0
    total = (input_tokens * price.get("input", 0.0) + output_tokens * price.get("output", 0.0)
             + cache_read_tokens * price.get("cache_read", 0.0) + cache_write_tokens * price.get("cache_write", 0.0))
    return round(total / 1e6, 8)


def _block_dict(block: Any) -> dict[str, Any]:
    """A response content block as the plain dict the API sent (fields unchanged)."""
    if isinstance(block, dict):
        return copy.deepcopy(block)
    return block.to_dict(mode="json")


def plain_text(content: Any) -> str:
    """Text of a message content (string or list of blocks); non-text blocks are dropped."""
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


# ------------------------------------------------------------------ clients
class LLMClient:
    """One chat completion over a system prompt and a list of messages."""

    provider = "base"

    def __init__(self, model: str, *, max_tokens: int, effort: str | None = None, thinking: str | None = None):
        self.model = model
        self.max_tokens = int(max_tokens)
        self.effort = effort
        self.thinking = thinking

    def complete(self, system: str, messages: list[dict[str, Any]], *, purpose: str,
                 cache_key: str | None = None) -> LLMResponse:
        raise NotImplementedError

    def settings(self) -> dict[str, Any]:
        """Generation settings (experiment metadata and replay-cache key)."""
        return {"provider": self.provider, "model": self.model, "max_tokens": self.max_tokens,
                "effort": self.effort, "thinking": self.thinking}

    def _call_record(self, *, purpose: str, model_reported: str | None, input_tokens: int, output_tokens: int,
                     cache_read: int, cache_write: int, latency: float, stop_reason: str | None,
                     request_id: str | None, timestamp: str, seed: int | None = None,
                     sampling: dict[str, Any] | None = None) -> LLMCallRecord:
        reported = model_reported or self.model
        if reported != self.model:
            log.warning("model %r was requested but the API reported %r", self.model, reported)
        price_model = reported if reported in (load_config("model_config").get("pricing_usd_per_mtok") or {}) \
            else self.model
        return LLMCallRecord(
            purpose=purpose, provider=self.provider, model_requested=self.model, model_reported=reported,
            effort=self.effort, thinking=self.thinking, max_tokens=self.max_tokens,
            input_tokens=input_tokens, output_tokens=output_tokens, cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            cost_usd=cost_usd(price_model, input_tokens, output_tokens, cache_read, cache_write),
            latency_s=round(latency, 3), stop_reason=stop_reason, request_id=request_id, timestamp=timestamp,
            seed=seed, sampling=copy.deepcopy(sampling) if sampling else None)


def call_seed(cache_key: str) -> int:
    """Per-call sampling seed: the first 32 bits of sha256(cache_key)."""
    return int(hashlib.sha256(cache_key.encode()).hexdigest()[:8], 16)


class AnthropicClient(LLMClient):
    """Anthropic models through the official ``anthropic`` SDK (Messages API)."""

    provider = "anthropic"

    def __init__(self, model: str, *, max_tokens: int, effort: str | None, thinking: str | None,
                 use_prompt_cache: bool = True, timeout_s: float = 600.0, max_retries: int = 4,
                 max_concurrent: int = 6, client: Any = None):
        super().__init__(model, max_tokens=max_tokens, effort=effort, thinking=thinking)
        self.use_prompt_cache = use_prompt_cache
        self.timeout_s = float(timeout_s)
        self.max_retries = int(max_retries)
        self._slots = request_slots(max_concurrent)
        if client is None:
            import anthropic
            load_env()
            # Retries (429, 5xx, connection errors) are done by the SDK with backoff.
            client = anthropic.Anthropic(timeout=self.timeout_s, max_retries=self.max_retries)
        self.client = client

    def settings(self) -> dict[str, Any]:
        return {**super().settings(), "use_prompt_cache": self.use_prompt_cache, "max_retries": self.max_retries,
                "request_timeout_s": self.timeout_s}

    def request(self, system: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Keyword arguments for ``messages.create``: no sampling parameters, no fallbacks."""
        req: dict[str, Any] = {"model": self.model, "max_tokens": self.max_tokens, "messages": messages}
        if self.use_prompt_cache:
            req["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        else:
            req["system"] = system
        if self.thinking and self.thinking != "none":
            req["thinking"] = {"type": self.thinking}
        if self.effort:
            req["output_config"] = {"effort": self.effort}
        return req

    def complete(self, system: str, messages: list[dict[str, Any]], *, purpose: str,
                 cache_key: str | None = None) -> LLMResponse:
        import anthropic

        req = self.request(system, messages)
        timestamp = utc_now()
        t0 = time.monotonic()
        try:
            with self._slots:
                msg = self.client.messages.create(**req)
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError, anthropic.NotFoundError) as e:
            raise LLMError(f"{type(e).__name__} ({e.status_code}): {e.message}", fatal=True) from e
        except anthropic.RateLimitError as e:
            raise LLMError(f"rate limited after {self.max_retries} retries: {e.message}") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"{type(e).__name__} ({e.status_code}) after retries: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError(f"{type(e).__name__} after {self.max_retries} retries: {e}") from e
        latency = time.monotonic() - t0

        blocks = [_block_dict(b) for b in msg.content]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if msg.stop_reason == "refusal":
            details = getattr(msg, "stop_details", None)
            log.warning("request declined (stop_reason=refusal, category=%s)", getattr(details, "category", None))
        elif msg.stop_reason == "max_tokens":
            log.warning("response truncated at max_tokens=%d", self.max_tokens)
        usage = msg.usage
        call = self._call_record(
            purpose=purpose, model_reported=getattr(msg, "model", None),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            cache_read=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            cache_write=int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
            latency=latency, stop_reason=msg.stop_reason,
            request_id=getattr(msg, "_request_id", None) or getattr(msg, "id", None), timestamp=timestamp)
        return LLMResponse(text, blocks, call)


class OpenAICompatClient(LLMClient):
    """Any OpenAI-compatible chat-completions endpoint (llama.cpp server, vLLM, OpenAI, ...).

    ``sampling`` may hold ``temperature``, ``top_p`` and ``presence_penalty``
    (standard parameters) and ``top_k`` and ``min_p`` (sent in ``extra_body``, as
    llama.cpp and vLLM accept them). ``enable_thinking`` (Qwen-style chat
    templates) is sent as ``chat_template_kwargs``; ``seed_per_call`` sends
    :func:`call_seed` of the ``cache_key``. Only ``message.content`` is used as the
    answer: reasoning that a server returns separately (``reasoning_content``) is
    never included.
    """

    provider = "openai_compatible"
    # finish_reason -> the stop_reason vocabulary used in the records
    _STOP = {"stop": "end_turn", "length": "max_tokens", "content_filter": "refusal", "tool_calls": "tool_use"}
    _STANDARD = ("temperature", "top_p", "presence_penalty")
    _EXTRA = ("top_k", "min_p")

    def __init__(self, model: str, *, max_tokens: int, base_url: str | None = None, api_key: str | None = None,
                 temperature: float | None = None, sampling: dict[str, Any] | None = None,
                 enable_thinking: bool | None = None, seed_per_call: bool = False, provider: str | None = None,
                 max_tokens_param: str = "max_tokens", timeout_s: float = 600.0, max_retries: int = 4,
                 max_concurrent: int = 6, client: Any = None):
        thinking = None if enable_thinking is None else ("enabled" if enable_thinking else "disabled")
        super().__init__(model, max_tokens=max_tokens, thinking=thinking)
        if provider:
            self.provider = provider
        sampling = {k: v for k, v in (sampling or {}).items() if v is not None}
        if temperature is not None:
            sampling.setdefault("temperature", temperature)
        unknown = set(sampling) - set(self._STANDARD) - set(self._EXTRA)
        if unknown:
            raise ValueError(f"unsupported sampling settings {sorted(unknown)}")
        self.sampling = sampling
        self.enable_thinking = enable_thinking
        self.seed_per_call = seed_per_call
        self.base_url = base_url
        self.max_tokens_param = max_tokens_param
        self.max_retries = int(max_retries)
        self.timeout_s = float(timeout_s)
        self._slots = request_slots(max_concurrent)
        if client is None:
            import openai
            client = openai.OpenAI(base_url=base_url, api_key=api_key, timeout=self.timeout_s,
                                   max_retries=self.max_retries)
        self.client = client

    def settings(self) -> dict[str, Any]:
        return {**super().settings(), "base_url": self.base_url, "sampling": dict(self.sampling),
                "enable_thinking": self.enable_thinking, "seed": "per_call" if self.seed_per_call else None,
                "max_retries": self.max_retries, "request_timeout_s": self.timeout_s}

    def request(self, system: str, messages: list[dict[str, Any]], cache_key: str | None = None) -> dict[str, Any]:
        msgs = [{"role": "system", "content": system}]
        msgs += [{"role": m["role"], "content": plain_text(m["content"])} for m in messages]
        req: dict[str, Any] = {"model": self.model, "messages": msgs, self.max_tokens_param: self.max_tokens}
        req.update({k: self.sampling[k] for k in self._STANDARD if k in self.sampling})
        extra: dict[str, Any] = {k: self.sampling[k] for k in self._EXTRA if k in self.sampling}
        if self.enable_thinking is not None:
            extra["chat_template_kwargs"] = {"enable_thinking": bool(self.enable_thinking)}
        if extra:
            req["extra_body"] = extra
        if self.seed_per_call and cache_key is not None:
            req["seed"] = call_seed(cache_key)
        return req

    def complete(self, system: str, messages: list[dict[str, Any]], *, purpose: str,
                 cache_key: str | None = None) -> LLMResponse:
        import openai

        req = self.request(system, messages, cache_key)
        timestamp = utc_now()
        t0 = time.monotonic()
        try:
            with self._slots:
                resp = self.client.chat.completions.create(**req)
        except (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError) as e:
            raise LLMError(f"{type(e).__name__} ({e.status_code}): {e.message}", fatal=True) from e
        except openai.RateLimitError as e:
            raise LLMError(f"rate limited after {self.max_retries} retries: {e.message}") from e
        except openai.APIStatusError as e:
            raise LLMError(f"{type(e).__name__} ({e.status_code}) after retries: {e.message}") from e
        except openai.APIConnectionError as e:
            raise LLMError(f"{type(e).__name__} after {self.max_retries} retries "
                           f"({self.base_url or 'default endpoint'}): {e}") from e
        latency = time.monotonic() - t0

        choice = resp.choices[0] if getattr(resp, "choices", None) else None
        text = (choice.message.content or "") if choice is not None else ""
        finish = getattr(choice, "finish_reason", None)
        if finish == "length":
            log.warning("response truncated at max_tokens=%d", self.max_tokens)
        usage = getattr(resp, "usage", None)
        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        details = getattr(usage, "prompt_tokens_details", None)
        cached = int(getattr(details, "cached_tokens", 0) or 0)
        written = int(getattr(details, "cache_write_tokens", 0) or 0)
        extra = req.get("extra_body", {})
        sent = {**{k: req[k] for k in self._STANDARD if k in req}, **{k: extra[k] for k in self._EXTRA if k in extra}}
        call = self._call_record(
            purpose=purpose, model_reported=getattr(resp, "model", None),
            input_tokens=max(prompt - cached - written, 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            cache_read=cached, cache_write=written, latency=latency,
            stop_reason=self._STOP.get(finish, finish), request_id=getattr(resp, "id", None), timestamp=timestamp,
            seed=req.get("seed"), sampling=sent or None)
        return LLMResponse(text, [{"type": "text", "text": text}], call)


class MockLLM(LLMClient):
    """Deterministic scripted responses for tests and smoke runs (no network).

    ``responses`` is either a list of strings (returned in order; the last one
    repeats) or a callable ``(system, messages, purpose) -> str``. Every request
    is recorded in :attr:`calls` exactly as it was sent.
    """

    provider = "mock"

    def __init__(self, responses: Sequence[str] | Responder, *, model: str = "mock", max_tokens: int = 16000):
        super().__init__(model, max_tokens=max_tokens)
        if not callable(responses) and not list(responses):
            raise ValueError("MockLLM needs at least one scripted response")
        self._responses = responses if callable(responses) else list(responses)
        self._next = 0
        self._lock = threading.Lock()
        self.calls: list[dict[str, Any]] = []

    def complete(self, system: str, messages: list[dict[str, Any]], *, purpose: str,
                 cache_key: str | None = None) -> LLMResponse:
        timestamp = utc_now()
        sent = copy.deepcopy(messages)
        with self._lock:
            self.calls.append({"system": system, "messages": sent, "purpose": purpose, "cache_key": cache_key})
            if callable(self._responses):
                text = None
            else:
                text = self._responses[min(self._next, len(self._responses) - 1)]
                self._next += 1
        if text is None:
            text = self._responses(system, sent, purpose)
        n_in = (len(system) + len(json.dumps(sent))) // 4  # rough size, for accounting tests only
        call = LLMCallRecord(
            purpose=purpose, provider=self.provider, model_requested=self.model, model_reported=self.model,
            effort=None, thinking=None, max_tokens=self.max_tokens, input_tokens=n_in,
            output_tokens=len(text) // 4, cache_read_tokens=0, cache_write_tokens=0, cost_usd=0.0,
            latency_s=0.0, stop_reason="end_turn", request_id=None, timestamp=timestamp)
        return LLMResponse(text, [{"type": "text", "text": text}], call)


class ReplayCache(LLMClient):
    """On-disk response cache so that an interrupted experiment resumes without re-billing.

    The key is the sha256 of (provider, model, effort, thinking, max_tokens,
    system, messages, cache_key). Callers put experiment id, configuration, run,
    task and attempt into ``cache_key``, so independent runs never share a
    response; calls without a ``cache_key`` bypass the cache.
    """

    def __init__(self, inner: LLMClient, cache_dir: Path | str, *, enabled: bool = True):
        super().__init__(inner.model, max_tokens=inner.max_tokens, effort=inner.effort, thinking=inner.thinking)
        self.inner = inner
        self.provider = inner.provider
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled

    def settings(self) -> dict[str, Any]:
        return {**self.inner.settings(), "replay_cache": self.enabled}

    def key(self, system: str, messages: list[dict[str, Any]], cache_key: str | None) -> str:
        payload = {"provider": self.inner.provider, "model": self.inner.model, "effort": self.inner.effort,
                   "thinking": self.inner.thinking, "max_tokens": self.inner.max_tokens,
                   "system": system, "messages": messages, "cache_key": cache_key}
        sampling = getattr(self.inner, "sampling", None)
        if sampling:  # a response sampled with other settings is a different sample
            payload["sampling"] = sampling
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()

    def path(self, key: str, cache_key: str) -> Path:
        namespace = "".join(c if c.isalnum() or c in "-_." else "_" for c in cache_key.split("/", 1)[0]) or "_"
        return self.cache_dir / namespace / key[:2] / f"{key}.json"

    def complete(self, system: str, messages: list[dict[str, Any]], *, purpose: str,
                 cache_key: str | None = None) -> LLMResponse:
        if not self.enabled or cache_key is None:
            return self.inner.complete(system, messages, purpose=purpose, cache_key=cache_key)
        key = self.key(system, messages, cache_key)
        path = self.path(key, cache_key)
        if path.is_file():
            try:
                data = json.loads(path.read_text())
                call = replace(LLMCallRecord(**data["call"]), purpose=purpose, cached=True)
                return LLMResponse(data["text"], data["assistant_content"], call)
            except (OSError, ValueError, KeyError, TypeError) as e:
                log.warning("ignoring unreadable replay-cache entry %s: %s", path, e)
        resp = self.inner.complete(system, messages, purpose=purpose, cache_key=cache_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{uuid.uuid4().hex[:8]}.tmp")
        tmp.write_text(json.dumps({"cache_key": cache_key, "text": resp.text,
                                   "assistant_content": resp.assistant_content, "call": asdict(resp.call)}))
        tmp.replace(path)
        return resp


# ------------------------------------------------------------------ factory
def make_llm(overrides: dict[str, Any] | None = None) -> LLMClient:
    """Build the configured client (config/model_config.yaml + overrides), wrapped in a ReplayCache.

    Overrides use the config keys (``provider``, ``model``, ``effort``, ...); for
    the mock provider ``mock_responses`` (list or callable) sets the script. The
    replay cache is enabled by default except for the mock provider. Provider
    ``local`` is the llama.cpp server of the ``local_llm`` section (no API key).
    """
    overrides = {k: v for k, v in (overrides or {}).items() if v is not None}
    cfg = {**load_config("model_config"), **overrides}
    provider = cfg.get("provider", "local")
    common = {"timeout_s": float(cfg.get("request_timeout_s", 600)), "max_retries": int(cfg.get("max_retries", 4)),
              "max_concurrent": int(cfg.get("max_concurrent_requests", 6))}
    inner: LLMClient
    if provider == "local":
        loc = cfg.get("local_llm") or {}
        common["max_concurrent"] = int(loc.get("max_concurrent", LOCAL_SERVER_SLOTS))
        inner = OpenAICompatClient(overrides.get("model") or loc["model"],
                                   max_tokens=int(overrides.get("max_tokens") or loc.get("max_tokens", 8192)),
                                   base_url=loc.get("base_url", "http://127.0.0.1:8080/v1"),
                                   api_key="local",  # the server needs no key; the SDK needs a non-empty one
                                   sampling=loc.get("sampling") or {},
                                   enable_thinking=bool(loc.get("enable_thinking", False)),
                                   seed_per_call=loc.get("seed", "per_call") == "per_call", provider="local",
                                   **common)
    elif provider == "anthropic":
        inner = AnthropicClient(cfg["model"], max_tokens=int(cfg.get("max_tokens", 16000)), effort=cfg.get("effort"),
                                thinking=cfg.get("thinking"), use_prompt_cache=bool(cfg.get("use_prompt_cache", True)),
                                **common)
    elif provider == "openai_compatible":
        load_env()
        oc = cfg.get("openai_compatible") or {}
        model = overrides.get("model") or os.environ.get(oc.get("model_env", "LLM_MODEL")) or cfg["model"]
        inner = OpenAICompatClient(model, max_tokens=int(cfg.get("max_tokens", 16000)),
                                   base_url=os.environ.get(oc.get("base_url_env", "LLM_BASE_URL")) or None,
                                   api_key=os.environ.get(oc.get("api_key_env", "LLM_API_KEY")) or None,
                                   temperature=oc.get("temperature"), sampling=oc.get("sampling"),
                                   max_tokens_param=oc.get("max_tokens_param", "max_tokens"), **common)
    elif provider == "mock":
        responses = cfg.get("mock_responses") or ["```tcl\n# mock response\n```"]
        inner = MockLLM(responses, model=overrides.get("model", "mock"), max_tokens=int(cfg.get("max_tokens", 16000)))
    else:
        raise ValueError(f"unknown LLM provider {provider!r} ({' | '.join(PROVIDERS)})")
    enabled = bool(cfg.get("replay_cache", provider != "mock"))
    return ReplayCache(inner, resolve(cfg.get("cache_dir", "experiments/llm_cache")), enabled=enabled)
