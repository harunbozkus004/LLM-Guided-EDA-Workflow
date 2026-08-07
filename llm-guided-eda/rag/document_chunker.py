"""Heading-aware chunking measured in embedding-model tokens.

Every Document is parsed into a tree of sections (markdown headings, banner
comments of Tcl scripts). A section whose whole subtree fits the token budget
becomes one chunk (its sub-headings stay inline); larger sections are packed
block by block (paragraphs, list items, table rows, code blocks, Tcl
statements) into chunks of at most ``target_tokens``, and consecutive chunks of
the same section overlap by up to ``overlap_tokens`` (whole sentences / lines).

Never split: command syntax cards (atomic documents) and code blocks that fit
the budget. Only a block that is itself larger than the budget is cut (code by
lines, prose by sentences, tables by rows with the header repeated).

Each chunk carries its heading path; the text that is embedded and BM25-indexed
starts with ``"<source> > <section>"`` (see ``Chunk.embed_text``).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field, fields
from typing import Callable, Iterable

from rag.document_loader import Document, github_slug, strip_inline_markdown

TARGET_TOKENS = 600
OVERLAP_TOKENS = 80
MIN_SECTION_TOKENS = 8      # a section's own text below this is not emitted on its own
MERGE_BELOW_TOKENS = 128    # consecutive script sections smaller than this share a chunk
CHUNKER_VERSION = "1.0"

_FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*(.*?)\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_SENTENCE_RE = re.compile(r"(?<=[.!?:])\s+(?=[A-Z0-9`(\[\"'-])")
_RULE_RE = re.compile(r"^\s*#[\s#=\-*~_+]*$")     # decorative comment lines ("#####", "# ----", "#")
_COMMENT_RE = re.compile(r"^\s*#")

TokenCount = Callable[[str], int]


@dataclass
class Chunk:
    id: str                 # stable content hash of source + section + text
    text: str               # chunk body shown to the LLM (without the source/section prefix)
    source: str             # "<upstream repo>/<path>", e.g. "OpenROAD/src/gpl/README.md"
    section: str            # heading path, e.g. "RePlAce > Commands"
    url: str                # GitHub permalink at the pinned commit (with anchor / line range)
    doc_type: str
    tool: str
    title: str
    n_tokens: int           # tokens of ``text`` (embedding-model tokenizer)
    commands: list[str] = field(default_factory=list)

    def embed_text(self) -> str:
        """Text used for embedding and BM25: '<source> > <section>' header line + body."""
        head = f"{self.source} > {self.section}" if self.section else self.source
        return f"{head}\n{self.text}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        return cls(**{f.name: d[f.name] for f in fields(cls) if f.name in d})


def chunk_id(source: str, section: str, text: str) -> str:
    return hashlib.sha256(f"{source}\n{section}\n{text}".encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- units and sections

@dataclass
class _Unit:
    text: str
    tokens: int
    group: int                  # consecutive units of one group are joined with ``joiner``
    joiner: str = "\n"
    head: str = ""              # re-emitted before every chunk part of the group (code fence, table header)
    tail: str = ""              # re-emitted after it (closing fence)
    wrap_tokens: int = 0        # tokens of head + tail
    sentences: bool = False     # prose: the overlap may take trailing sentences of it
    lines: tuple[int, int] = (0, 0)   # source line range (scripts)


@dataclass
class _Node:
    title: str
    level: int
    anchor: str = ""
    units: list[_Unit] = field(default_factory=list)
    children: list["_Node"] = field(default_factory=list)


class _Groups:
    def __init__(self) -> None:
        self.n = 0

    def new(self) -> int:
        self.n += 1
        return self.n


def _split_words(text: str, budget: int, count: TokenCount) -> list[str]:
    """Cut an over-long sentence / line into pieces of at most ``budget`` tokens."""
    pieces, cur = [], []
    for word in text.split():
        if cur and count(" ".join(cur + [word])) > budget:
            pieces.append(" ".join(cur))
            cur = []
        cur.append(word)
    if cur:
        pieces.append(" ".join(cur))
    return pieces


def _prose_units(text: str, group: int, count: TokenCount, budget: int) -> list[_Unit]:
    n = count(text)
    if n <= budget:
        return [_Unit(text, n, group, " ", sentences=True)]
    out = []
    for sent in _SENTENCE_RE.split(" ".join(text.split())):
        for piece in ([sent] if count(sent) <= budget else _split_words(sent, budget, count)):
            out.append(_Unit(piece, count(piece), group, " ", sentences=True))
    return out


def _line_units(lines: list[str], group: int, count: TokenCount, budget: int,
                head: str = "", tail: str = "", line_nos: list[int] | None = None) -> list[_Unit]:
    wrap = (count(head) if head else 0) + (count(tail) if tail else 0)
    out = []
    for k, line in enumerate(lines):
        no = line_nos[k] if line_nos else 0
        n = count(line)
        pieces = [line] if n <= budget - wrap else _split_words(line, budget - wrap, count)
        for piece in pieces:
            out.append(_Unit(piece, count(piece), group, "\n", head, tail, wrap, lines=(no, no)))
    return out


# --------------------------------------------------------------------------- markdown

def _md_blocks(text: str) -> list[tuple[str, list[str], int, str]]:
    """(kind, lines, heading level, heading title); kind in heading|code|table|list|para."""
    lines = text.split("\n")
    blocks: list[tuple[str, list[str], int, str]] = []
    i = 0

    def starts_block(ln: str) -> bool:
        return bool(_FENCE_RE.match(ln) or _HEADING_RE.match(ln) or ln.lstrip().startswith("|"))

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = _FENCE_RE.match(line)
        if m:
            marker = m.group(2)
            j = i + 1
            while j < len(lines):
                m2 = _FENCE_RE.match(lines[j])
                if m2 and m2.group(2).startswith(marker) and not m2.group(3):
                    break
                j += 1
            block = lines[i:j + 1]
            if j >= len(lines):                       # unterminated fence at end of file
                block.append(m.group(1) + marker)
            blocks.append(("code", block, 0, ""))
            i = j + 1
            continue
        h = _HEADING_RE.match(line)
        if h:
            blocks.append(("heading", [line], len(h.group(1)), strip_inline_markdown(h.group(2))))
            i += 1
            continue
        if line.lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            blocks.append(("table", lines[i:j], 0, ""))
            i = j
            continue
        kind = "list" if _LIST_RE.match(line) else "para"
        j = i + 1
        while j < len(lines) and lines[j].strip() and not starts_block(lines[j]):
            if kind == "para" and _LIST_RE.match(lines[j]):
                break
            j += 1
        if kind == "list" and blocks and blocks[-1][0] == "list":
            blocks[-1][1].extend(lines[i:j])       # loose list: keep items in one group
        else:
            blocks.append((kind, lines[i:j], 0, ""))
        i = j
    return blocks


def _md_tree(doc: Document, count: TokenCount, budget: int) -> _Node:
    root = _Node(doc.title, 0)
    stack = [root]
    groups = _Groups()
    slugs: dict[str, int] = {}
    for kind, lines, level, title in _md_blocks(doc.text):
        if kind == "heading":
            slug = github_slug(title)
            k = slugs.get(slug, 0)
            slugs[slug] = k + 1
            node = _Node(title, level, slug if k == 0 else f"{slug}-{k}")
            while stack[-1].level >= level:
                stack.pop()
            stack[-1].children.append(node)
            stack.append(node)
            continue
        units = stack[-1].units
        g = groups.new()
        body = "\n".join(lines)
        if kind == "code":
            n = count(body)
            if n <= budget:
                units.append(_Unit(body, n, g))
            else:
                units.extend(_line_units(lines[1:-1] if len(lines) > 2 else lines, g, count, budget,
                                         head=lines[0], tail=lines[-1] if len(lines) > 1 else ""))
        elif kind == "table":
            n = count(body)
            if n <= budget or len(lines) <= 2:
                units.append(_Unit(body, n, g))
            else:
                units.extend(_line_units(lines[2:], g, count, budget, head="\n".join(lines[:2])))
        elif kind == "list":
            items: list[list[str]] = []
            for ln in lines:
                if _LIST_RE.match(ln) or not items:
                    items.append([ln])
                else:
                    items[-1].append(ln)
            for item in items:
                text = "\n".join(item)
                n = count(text)
                if n <= budget:
                    units.append(_Unit(text, n, g, "\n", sentences=True))
                else:
                    units.extend(_prose_units(text, groups.new(), count, budget))
        else:
            units.extend(_prose_units(body, g, count, budget))
    # A single top-level heading is the document's title: use it (or the document's
    # extended title, see document_loader.load_markdown) as the root.
    if not root.units and len(root.children) == 1:
        root = root.children[0]
        if doc.title.startswith(root.title):
            root.title = doc.title
    return root


# --------------------------------------------------------------------------- Tcl / Makefile scripts

def _brace_delta(line: str) -> int:
    clean = re.sub(r"\\.", "", line)
    return clean.count("{") - clean.count("}")


def _script_events(doc: Document) -> list[tuple[str, list[str], list[int]]]:
    """(kind, lines, line numbers); kind in blank|rule|comment|stmt. Statements span
    backslash continuations and unbalanced braces (proc / if / foreach bodies)."""
    lines = doc.text.rstrip("\n").split("\n")
    nos = doc.line_map or list(range(1, len(lines) + 1))
    events: list[tuple[str, list[str], list[int]]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            events.append(("blank", [], []))
            i += 1
            continue
        if _COMMENT_RE.match(line) and not line.rstrip().endswith("\\"):
            events.append(("rule" if _RULE_RE.match(line) else "comment", [line], [nos[i]]))
            i += 1
            continue
        stmt, stmt_nos, depth = [], [], 0
        while i < len(lines):
            ln = lines[i]
            if not _RULE_RE.match(ln):                # decorative comment lines inside bodies
                stmt.append(ln)
                stmt_nos.append(nos[i])
            depth = max(0, depth + _brace_delta(ln))
            i += 1
            if depth == 0 and not ln.rstrip().endswith("\\"):
                break
        events.append(("stmt", stmt, stmt_nos))
    return events


def _script_tree(doc: Document, count: TokenCount, budget: int) -> _Node:
    events = _script_events(doc)
    meaningful = [k for k, e in enumerate(events) if e[0] != "blank"]
    heading_at: set[int] = set()
    for pos, k in enumerate(meaningful):
        if events[k][0] != "comment":
            continue
        prev_k = meaningful[pos - 1] if pos > 0 else None
        next_k = meaningful[pos + 1] if pos + 1 < len(meaningful) else None
        if (prev_k is not None and events[prev_k][0] == "rule") or \
           (next_k is not None and events[next_k][0] == "rule"):
            if not (prev_k is not None and prev_k in heading_at):
                heading_at.add(k)
    root = _Node(doc.title, 0)
    node = root
    groups = _Groups()
    g = groups.new()
    for k, (kind, lines, nos) in enumerate(events):
        if kind == "blank":
            g = groups.new()
            continue
        if kind == "rule":
            continue
        if k in heading_at:
            title = lines[0].strip().lstrip("#").strip()
            node = _Node(title, 1)
            root.children.append(node)
            g = groups.new()
            continue
        text = "\n".join(lines)
        n = count(text)
        if n <= budget:
            node.units.append(_Unit(text, n, g, "\n", lines=(nos[0], nos[-1])))
        else:
            node.units.extend(_line_units(lines, g, count, budget, line_nos=nos))
    return root


# --------------------------------------------------------------------------- packing

def _cost(units: list[_Unit]) -> int:
    total, prev = 0, None
    for u in units:
        total += u.tokens + (u.wrap_tokens if u.group != prev else 0)
        prev = u.group
    return total


def _render(units: list[_Unit]) -> str:
    parts, i = [], 0
    while i < len(units):
        j = i
        while j < len(units) and units[j].group == units[i].group:
            j += 1
        body = units[i].joiner.join(u.text for u in units[i:j])
        parts.append("\n".join(x for x in (units[i].head, body, units[i].tail) if x))
        i = j
    return "\n\n".join(parts)


def _overlap(units: list[_Unit], budget: int, count: TokenCount) -> list[_Unit]:
    """Trailing whole units (or trailing sentences of a prose unit) of at most ``budget`` tokens."""
    out: list[_Unit] = []
    for u in reversed(units):
        if _cost([u] + out) <= budget:
            out.insert(0, u)
            continue
        if u.sentences:
            tail: list[str] = []
            for sent in reversed(_SENTENCE_RE.split(" ".join(u.text.split()))):
                cand = " ".join([sent] + tail)
                if _cost([_Unit(cand, count(cand), u.group, " ")] + out) > budget:
                    break
                tail.insert(0, sent)
            if tail:
                text = " ".join(tail)
                out.insert(0, _Unit(text, count(text), u.group, " ", u.head, u.tail, u.wrap_tokens,
                                    sentences=True, lines=u.lines))
        break
    return out


def _pack(units: list[_Unit], target: int, overlap: int, count: TokenCount) -> list[list[_Unit]]:
    chunks: list[list[_Unit]] = []
    cur: list[_Unit] = []
    for u in units:
        if cur and _cost(cur + [u]) > target:
            chunks.append(cur)
            cur = _overlap(cur, overlap, count)
            if _cost(cur + [u]) > target:
                cur = []
        cur.append(u)
    if cur:
        chunks.append(cur)
    return chunks


def _heading_text(node: _Node, fmt: str) -> str:
    return f"# {node.title}" if fmt == "script" else f"{'#' * max(node.level, 1)} {node.title}"


def _subtree_tokens(node: _Node, fmt: str, count: TokenCount, is_root: bool = True) -> int:
    own = _cost(node.units) + (0 if is_root else count(_heading_text(node, fmt)))
    return own + sum(_subtree_tokens(c, fmt, count, False) for c in node.children)


def _flatten(node: _Node, fmt: str, groups: _Groups, count: TokenCount,
             is_root: bool = True) -> list[_Unit]:
    """The node's units with every descendant inlined under its own heading line.
    Heading units get negative group ids."""
    units: list[_Unit] = []
    if not is_root:
        heading = _heading_text(node, fmt)
        units.append(_Unit(heading, count(heading), -groups.new()))
    units.extend(node.units)
    for child in node.children:
        units.extend(_flatten(child, fmt, groups, count, False))
    return units


def _url(doc: Document, anchor: str, units: list[_Unit]) -> str:
    if doc.fmt == "script":
        nos = [n for u in units for n in u.lines if n]
        return f"{doc.url}#L{min(nos)}-L{max(nos)}" if nos else doc.url
    if doc.fmt == "markdown" and anchor:
        return f"{doc.url}#{anchor}"
    return doc.url


def chunk_document(doc: Document, count: TokenCount, target_tokens: int = TARGET_TOKENS,
                   overlap_tokens: int = OVERLAP_TOKENS) -> list[Chunk]:
    def make(section: str, text: str, url: str) -> Chunk:
        text = text.strip("\n")
        return Chunk(id=chunk_id(doc.source, section, text), text=text, source=doc.source,
                     section=section, url=url, doc_type=doc.doc_type, tool=doc.tool, title=doc.title,
                     n_tokens=count(text), commands=list(doc.commands))

    if not doc.text.strip():
        return []
    if doc.atomic:
        return [make(doc.section or doc.title, doc.text, doc.url)]
    if doc.fmt == "text":
        groups = _Groups()
        g = groups.new()
        units = _line_units([ln for ln in doc.text.split("\n") if ln.strip()], g, count, target_tokens)
        return [make(doc.section or doc.title, _render(p), doc.url)
                for p in _pack(units, target_tokens, overlap_tokens, count)]

    root = (_script_tree if doc.fmt == "script" else _md_tree)(doc, count, target_tokens)
    if doc.section:
        root.title = doc.section
    groups = _Groups()
    out: list[Chunk] = []

    def emit(node: _Node, path: list[str]) -> None:
        section = " > ".join(p for p in path if p)
        if _subtree_tokens(node, doc.fmt, count) <= target_tokens:
            units = _flatten(node, doc.fmt, groups, count)
            if any(u.group > 0 for u in units):          # not only heading lines
                out.append(make(section, _render(units), _url(doc, node.anchor, units)))
            return
        # A markdown section's own text that is only a few tokens long (e.g. "Commands:") is
        # dropped when its subsections are chunked separately; script text is always kept.
        if node.units and (doc.fmt == "script" or _cost(node.units) >= MIN_SECTION_TOKENS):
            for part in _pack(node.units, target_tokens, overlap_tokens, count):
                out.append(make(section, _render(part), _url(doc, node.anchor, part)))
        # Children of a virtual root (file / several top-level headings) do not repeat its title.
        base = path if node.level > 0 else []
        if doc.fmt != "script":
            for child in node.children:
                emit(child, base + [child.title])
            return
        # Script sections are consecutive flow steps: merge runs of small ones into one chunk.
        run: list[_Node] = []

        def flush() -> None:
            if len(run) == 1:
                emit(run[0], base + [run[0].title])
            elif run:
                units = [u for n in run for u in _flatten(n, doc.fmt, groups, count, False)]
                title = " / ".join(n.title for n in run)
                out.append(make(" > ".join(base + [title]), _render(units), _url(doc, "", units)))
            run.clear()

        for child in node.children:
            size = _subtree_tokens(child, doc.fmt, count, False)
            if size >= MERGE_BELOW_TOKENS:
                flush()
                emit(child, base + [child.title])
                continue
            if run and sum(_subtree_tokens(n, doc.fmt, count, False) for n in run) + size > target_tokens:
                flush()
            run.append(child)
        flush()

    emit(root, [root.title])
    return [c for c in out if c.text.strip()]


def chunk_documents(docs: Iterable[Document], count: TokenCount, target_tokens: int = TARGET_TOKENS,
                    overlap_tokens: int = OVERLAP_TOKENS, max_chunks: dict[str, int] | None = None
                    ) -> tuple[list[Chunk], dict]:
    """Chunks of all documents in order. Exact duplicate texts are kept once, and
    ``max_chunks`` (doc_type -> limit) keeps only the first chunks of very long documents.
    Returns (chunks, statistics)."""
    seen: set[str] = set()
    chunks: list[Chunk] = []
    stats: dict = {"duplicates_dropped": 0, "truncated_documents": {}}
    for doc in docs:
        parts = chunk_document(doc, count, target_tokens, overlap_tokens)
        limit = (max_chunks or {}).get(doc.doc_type)
        if limit is not None and len(parts) > limit:
            stats["truncated_documents"][doc.source] = len(parts)
            parts = parts[:limit]
        for c in parts:
            key = hashlib.sha256(" ".join(c.text.split()).encode()).hexdigest()
            if key in seen:
                stats["duplicates_dropped"] += 1
                continue
            seen.add(key)
            chunks.append(c)
    return chunks, stats
