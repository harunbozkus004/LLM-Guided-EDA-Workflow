"""Script extraction from LLM answers and the generation call."""
from __future__ import annotations

import re
from typing import Any, Iterator

from agent.llm import LLMClient, LLMResponse

_OPEN_RE = re.compile(r"^[ \t]{0,3}(?P<fence>`{3,}|~{3,})[ \t]*(?P<info>[^`\n]*?)[ \t]*$")


def fenced_blocks(text: str) -> Iterator[tuple[str, str]]:
    """(info string, body) of every fenced code block; an unclosed fence runs to the end."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    while i < len(lines):
        m = _OPEN_RE.match(lines[i])
        if not m:
            i += 1
            continue
        fence = m.group("fence")
        close = re.compile(rf"^[ \t]{{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$")
        body: list[str] = []
        j = i + 1
        while j < len(lines) and not close.match(lines[j]):
            body.append(lines[j])
            j += 1
        yield m.group("info").strip(), "\n".join(body)
        i = j + 1


def _clean(script: str) -> str:
    script = script.strip("\n")
    return script + "\n" if script.strip() else ""


def extract_tcl(text: str) -> str:
    """The script in an LLM answer.

    First fenced block whose info string is ``tcl`` (case-insensitive); else the
    first fenced block of any kind; else the whole text.
    """
    text = text or ""
    blocks = list(fenced_blocks(text))
    for info, body in blocks:
        if info.split()[:1] and info.split()[0].lower() == "tcl":
            return _clean(body)
    if blocks:
        return _clean(blocks[0][1])
    return _clean(text.replace("\r\n", "\n"))


def generate(llm: LLMClient, system: str, messages: list[dict[str, Any]], *, purpose: str,
             cache_key: str | None = None) -> tuple[str, LLMResponse]:
    """One LLM call; returns (extracted script, full response)."""
    resp = llm.complete(system, messages, purpose=purpose, cache_key=cache_key)
    return extract_tcl(resp.text), resp
