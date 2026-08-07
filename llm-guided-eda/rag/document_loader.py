"""Load the version-pinned OpenROAD / OpenSTA / ORFS sources into Documents.

Only files under ``third_party/`` are read (pinned commits in
``third_party/VERSIONS.txt``). Nothing from ``benchmark/`` may ever enter the
knowledge base: reference solutions would leak the held-out test set.

Document kinds (``doc_type``):
  readme          README.md files (src/<tool>/README.md is the primary command documentation)
  guide           docs/**/*.md user guides and tutorials
  command_syntax  one card per ``define_cmd_args`` block of a tool's Tcl sources
  reference_pdf   OpenSTA command reference (doc/OpenSTA.pdf), one Document per command
  example         official regression-test scripts (src/<tool>/test/*.tcl, OpenSTA examples)
  flow_script     reference flows (OpenROAD test/*.tcl, ORFS flow/scripts, Nangate45 platform)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from common.paths import THIRD_PARTY

GITHUB = {
    "OpenROAD": "https://github.com/The-OpenROAD-Project/OpenROAD",
    "OpenSTA": "https://github.com/The-OpenROAD-Project/OpenSTA",
    "OpenROAD-flow-scripts": "https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts",
}
DOC_TYPES = ("readme", "guide", "command_syntax", "reference_pdf", "example", "flow_script")

# Contributor-process docs and doc-site scaffolding: no information about using the tools.
SKIPPED_DOCS = {
    "OpenROAD/docs/README.md": "documentation build instructions",
    "OpenROAD/docs/tutorials/index.md": "link-only page",
    "OpenROAD/docs/user/FAQS.md": "link-only page",
    "OpenROAD/docs/misc/NewToolDocExample.md": "documentation template",
    "OpenROAD/docs/contrib/CI.md": "contributor process",
    "OpenROAD/docs/contrib/CodingPractices.md": "C++ coding practices",
    "OpenROAD/docs/contrib/GitGuide.md": "contributor process",
    "OpenROAD/docs/contrib/GettingInvolved.md": "contributor process",
    "OpenROAD-flow-scripts/docs/user/DockerShell.md": "link-only page",
    "OpenROAD-flow-scripts/docs/user/Jenkins.md": "CI process",
    "OpenROAD-flow-scripts/docs/user/Flow_QoR_CI.md": "CI process",
    "OpenROAD-flow-scripts/docs/tutorials/TutorialHome.md": "link-only page",
}
# Test infrastructure rather than flows.
SKIPPED_SCRIPTS = {
    "OpenROAD/test/helpers.tcl": "test infrastructure",
    "OpenROAD/test/regression.tcl": "test infrastructure",
    "OpenROAD/test/regression_tests.tcl": "test infrastructure",
    "OpenROAD/test/regression_vars.tcl": "test infrastructure",
    "OpenROAD-flow-scripts/flow/scripts/synth.tcl": "Yosys script, not OpenROAD Tcl",
    "OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl": "Yosys script, not OpenROAD Tcl",
    "OpenROAD-flow-scripts/flow/scripts/synth_hier_report.tcl": "Yosys script, not OpenROAD Tcl",
    "OpenROAD-flow-scripts/flow/scripts/yosys.tcl": "Yosys launcher",
    "OpenROAD-flow-scripts/flow/scripts/klayout.tcl": "KLayout launcher",
}
# Markdown sections that never carry usage information.
BOILERPLATE_SECTIONS = {
    "license", "authors", "references", "external references", "regression tests", "faqs", "faq",
    "bug reports", "code of conduct", "how to contribute", "how to get in touch", "site map",
    "acknowledgements", "acknowledgments", "citation", "contributors",
}

_LICENSE_RE = re.compile(
    r"copyright|license|redistribution|warrant|spdx|permission is hereby granted", re.I)
_FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*(.*?)\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_HTML_TAGS = ("img|p|br|div|span|a|b|i|em|strong|sup|sub|table|thead|tbody|tr|td|th|center|"
              "details|summary|hr|font|kbd|picture|source|video|iframe|h[1-6]|ul|ol|li|code|pre")
_HTML_TAG_RE = re.compile(rf"</?(?:{_HTML_TAGS})\b[^>]*?/?>", re.I)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\((?:[^()]|\([^)]*\))*\)")
_REF_LINK_RE = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")
_REF_DEF_RE = re.compile(r"^\s*\[[^\]]+\]:\s+\S+")
_AUTOLINK_RE = re.compile(r"<(https?://[^>\s]+)>")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")
_EMPTY_ROW_RE = re.compile(r"^\s*\|[\s|]*\|\s*$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

# First words that do not count as tool commands when judging whether a script is trivial.
_NON_COMMANDS = {
    "set", "source", "puts", "exit", "if", "else", "elseif", "foreach", "for", "while", "proc",
    "return", "incr", "append", "lappend", "global", "expr", "catch", "close", "open", "file",
    "lindex", "llength", "lsort", "string", "regexp", "regsub", "namespace", "package",
    "variable", "unset", "array", "dict", "info", "list", "format", "switch", "break",
    "continue", "eval", "upvar", "error", "}", "{", "make_result_file", "diff_file",
    "diff_files", "lassign", "lsearch", "lrange", "split", "join", "concat", "after",
}
_HARNESS_LINE_RE = re.compile(
    r"^\s*(source\s+\"?(\./)?helpers\.tcl\"?|diff_files?\b|diff_file_vs_|report_file\b)")
HARNESS_NOTE = "# note: make_result_file is a regression-test helper (helpers.tcl), not an OpenROAD command"


@dataclass
class Document:
    text: str
    source: str            # "<upstream repo>/<path in repo>", e.g. "OpenROAD/src/gpl/README.md"
    url: str               # GitHub permalink at the pinned commit
    doc_type: str
    tool: str
    title: str
    section: str = ""      # preset heading path (syntax cards, PDF entries); else derived by the chunker
    fmt: str = "markdown"  # markdown | script | text: how the chunker parses ``text``
    atomic: bool = False   # never split (command syntax cards)
    line_map: list[int] = field(default_factory=list)  # scripts: source line number of each text line
    commands: list[str] = field(default_factory=list)  # commands this document defines


# --------------------------------------------------------------------------- helpers

def read_versions(root: Path = THIRD_PARTY) -> dict[str, str]:
    """Pinned commit of every upstream repository (third_party/VERSIONS.txt)."""
    versions = {}
    for line in (root / "VERSIONS.txt").read_text().splitlines():
        parts = line.split()
        if len(parts) == 2:
            versions[parts[0]] = parts[1]
    return versions


def source_of(path: Path, root: Path = THIRD_PARTY) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def permalink(source: str, versions: dict[str, str]) -> str:
    repo, _, rel = source.partition("/")
    return f"{GITHUB[repo]}/blob/{versions[repo]}/{rel}"


def tool_of(source: str) -> str:
    parts = source.split("/")
    if parts[0] == "OpenSTA":
        return "sta"
    if parts[0] == "OpenROAD-flow-scripts":
        return "orfs"
    if len(parts) > 2 and parts[1] == "src":
        return parts[2].lower()
    if len(parts) > 1 and parts[1] == "test":
        return "flow"
    return "openroad"


def github_slug(heading: str) -> str:
    """GitHub's anchor for a markdown heading (without the duplicate suffix)."""
    text = re.sub(r"[`*_~]", lambda m: "_" if m.group(0) == "_" else "", heading.strip().lower())
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def strip_inline_markdown(text: str) -> str:
    return re.sub(r"[`*]", "", _LINK_RE.sub(r"\1", text)).strip()


# --------------------------------------------------------------------------- markdown / html

def clean_markdown(text: str) -> str:
    """Strip images, badges, html tags/comments and link targets; keep code blocks verbatim."""
    text = _CONTROL_RE.sub("", _HTML_COMMENT_RE.sub("", text.replace("\r\n", "\n")))
    out: list[str] = []
    fence: str | None = None          # closing marker of the open code fence
    admonition: str | None = None     # closing marker of an open MyST admonition
    drop_until: str | None = None     # closing marker of a dropped directive block
    for line in text.split("\n"):
        m = _FENCE_RE.match(line)
        if drop_until is not None:
            if m and m.group(2).startswith(drop_until) and not m.group(3):
                drop_until = None
            continue
        if fence is not None:
            out.append(line)
            if m and m.group(2).startswith(fence) and not m.group(3):
                fence = None
            continue
        if m:
            marker, info = m.group(2), m.group(3)
            if admonition is not None and marker.startswith(admonition) and not info:
                admonition = None
                continue
            directive = re.match(r"\{([\w-]+)\}\s*(.*)", info)
            if directive:
                name, rest = directive.group(1).lower(), directive.group(2)
                if name in {"note", "warning", "tip", "seealso", "important", "caution", "hint"}:
                    admonition = marker
                    out.append(f"{name.capitalize()}: {_clean_prose_line(rest)}".rstrip())
                else:   # {tableofcontents}, {include}, {eval-rst}: doc-site scaffolding
                    drop_until = marker
                continue
            if info.split()[:1] == ["mermaid"]:
                drop_until = marker           # diagram source: layout noise, no usage information
                continue
            fence = marker
            out.append(f"{m.group(1)}{marker}{info.split()[0] if info else ''}")
            continue
        if _REF_DEF_RE.match(line):
            continue
        cleaned = _clean_prose_line(line)
        if line.strip() and not cleaned.strip():
            continue                      # line held only an image / badge / tag
        if _EMPTY_ROW_RE.match(cleaned) and "|" in line and not _TABLE_SEP_RE.match(line):
            continue                      # table row that held only images
        if _TABLE_SEP_RE.match(cleaned) and "|" in cleaned and (not out or "|" not in out[-1]):
            continue                      # separator of a table whose header was dropped
        out.append(cleaned)
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def _clean_prose_line(line: str) -> str:
    # Protect inline code spans: placeholders such as `<file>` must survive tag stripping.
    spans: list[str] = []

    def keep(m: re.Match) -> str:
        spans.append(m.group(0))
        return f"\x00{len(spans) - 1}\x00"

    s = re.sub(r"`[^`]*`", keep, line)
    s = _IMAGE_RE.sub("", s)
    s = re.sub(r"\[\s*\]\([^)]*\)", "", s)        # empty links left by badges
    s = _LINK_RE.sub(r"\1", s)
    s = _REF_LINK_RE.sub(r"\1", s)
    s = _AUTOLINK_RE.sub(r"\1", s)
    s = _HTML_TAG_RE.sub("", s)
    s = re.sub(r"\s*\((?:link|here|\.pdf)\)", "", s)    # "([link](url))" leftovers
    s = re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], s)
    return s.rstrip()


def drop_boilerplate_sections(md: str) -> str:
    """Remove sections such as License / Authors / Regression tests (and their subsections)."""
    out: list[str] = []
    fence: str | None = None
    skip_level: int | None = None
    for line in md.split("\n"):
        m = _FENCE_RE.match(line)
        if fence is None:
            h = _HEADING_RE.match(line)
            if h:
                level = len(h.group(1))
                if skip_level is not None and level <= skip_level:
                    skip_level = None
                title = strip_inline_markdown(h.group(2)).lower().rstrip(":")
                if skip_level is None and title in BOILERPLATE_SECTIONS:
                    skip_level = level
            if m:
                fence = m.group(2)
        elif m and m.group(2).startswith(fence) and not m.group(3):
            fence = None
        if skip_level is None:
            out.append(line)
    return "\n".join(out)


def markdown_title(md: str, default: str) -> str:
    fence = False
    for line in md.split("\n"):
        if _FENCE_RE.match(line):
            fence = not fence
        h = _HEADING_RE.match(line) if not fence else None
        if h and len(h.group(1)) == 1:
            return strip_inline_markdown(h.group(2))
    return default


def tool_descriptions(root: Path = THIRD_PARTY) -> dict[str, str]:
    """Tool namespace -> descriptive name, from the "Tool Flow Namespace" list of the
    OpenROAD developer guide (e.g. gpl -> "RePlAce Global Placer")."""
    path = root / "OpenROAD" / "docs" / "contrib" / "DeveloperGuide.md"
    if not path.exists():
        return {}
    out = {}
    for m in re.finditer(r"^- (.+?) \(\[(\w+)\]\(", path.read_text(), re.M):
        out[m.group(2).lower()] = _CONTROL_RE.sub("", m.group(1)).strip()
    return out


def load_markdown(path: Path, doc_type: str, versions: dict[str, str], root: Path = THIRD_PARTY,
                  tool_names: dict[str, str] | None = None) -> Document:
    """A markdown file. A tool README's title is extended with the tool's namespace and
    descriptive name when the heading alone is opaque ("RePlAce" -> "RePlAce (gpl: RePlAce
    Global Placer)"), so the heading path tells retrieval which flow step it documents."""
    source = source_of(path, root)
    md = drop_boilerplate_sections(clean_markdown(path.read_text(errors="replace")))
    tool = tool_of(source)
    title = markdown_title(md, path.stem)
    desc = (tool_names or {}).get(tool)
    if desc and re.fullmatch(r"OpenROAD/src/\w+/README\.md", source) and desc.lower() != title.lower():
        title = f"{title} ({tool}: {desc})"
    return Document(text=md, source=source, url=permalink(source, versions), doc_type=doc_type,
                    tool=tool, title=title)


def html_to_markdown(html: str) -> str:
    """Minimal HTML -> markdown: headings become '#' headings, <pre> becomes fenced code."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    for pre in soup.find_all("pre"):
        pre.replace_with(f"\n```\n{pre.get_text()}\n```\n")
    for level in range(1, 7):
        for h in soup.find_all(f"h{level}"):
            h.replace_with(f"\n{'#' * level} {h.get_text(' ', strip=True)}\n")
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    text = soup.get_text()
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def load_html(path: Path, doc_type: str, versions: dict[str, str],
              root: Path = THIRD_PARTY) -> Document:
    source = source_of(path, root)
    md = drop_boilerplate_sections(clean_markdown(html_to_markdown(path.read_text(errors="replace"))))
    return Document(text=md, source=source, url=permalink(source, versions), doc_type=doc_type,
                    tool=tool_of(source), title=markdown_title(md, path.stem))


# --------------------------------------------------------------------------- Tcl scripts

def strip_license_header(lines: list[str]) -> int:
    """Index of the first line after a leading comment block that is a license header."""
    i = 0
    while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
        i += 1
    header = "\n".join(lines[:i])
    if i and _LICENSE_RE.search(header):
        while i < len(lines) and not lines[i].strip():
            i += 1
        return i
    return 0


def count_commands(text: str) -> int:
    """Number of tool commands in a script (Tcl builtins and test-harness helpers excluded)."""
    n, continued = 0, False
    for raw in text.split("\n"):
        line = raw.strip()
        prev_continued, continued = continued, line.endswith("\\")
        if prev_continued or not line or line.startswith("#"):
            continue
        word = re.match(r"\[?([A-Za-z_][\w:]*)", line)
        if word and word.group(1) not in _NON_COMMANDS:
            n += 1
    return n


def load_script(path: Path, doc_type: str, versions: dict[str, str],
                root: Path = THIRD_PARTY, strip_harness: bool = False) -> Document:
    """A Tcl (or Makefile-syntax) script; license header and optional test-harness lines removed."""
    source = source_of(path, root)
    lines = path.read_text(errors="replace").replace("\r\n", "\n").split("\n")
    start = strip_license_header(lines)
    kept: list[str] = []
    line_map: list[int] = []
    uses_result_file = False
    for i in range(start, len(lines)):
        line = lines[i].rstrip()
        if strip_harness and _HARNESS_LINE_RE.match(line):
            continue
        uses_result_file |= "make_result_file" in line
        kept.append(line)
        line_map.append(i + 1)
    while kept and not kept[-1].strip():
        kept.pop()
        line_map.pop()
    if strip_harness and uses_result_file:
        kept.insert(0, HARNESS_NOTE)
        line_map.insert(0, line_map[0] if line_map else 1)
    return Document(text="\n".join(kept) + "\n", source=source, url=permalink(source, versions),
                    doc_type=doc_type, tool=tool_of(source), title=path.name, fmt="script",
                    line_map=line_map)


# --------------------------------------------------------------------------- command syntax cards

def _skip_ws(text: str, i: int) -> int:
    while i < len(text):
        if text[i] in " \t":
            i += 1
        elif text.startswith("\\\n", i):
            i += 2
        else:
            break
    return i


def _tcl_word(text: str, i: int) -> tuple[str, int]:
    """Parse one Tcl word at ``i`` (braced, quoted or bare). Returns (word, end index)."""
    i = _skip_ws(text, i)
    if i >= len(text):
        return "", i
    if text[i] == "{":
        depth, j = 0, i
        while j < len(text):
            c = text[j]
            if c == "\\":
                j += 2
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[i + 1:j], j + 1
            j += 1
        return text[i + 1:], len(text)
    if text[i] == '"':
        j = i + 1
        while j < len(text) and text[j] != '"':
            j += 2 if text[j] == "\\" else 1
        return text[i + 1:j], j + 1
    m = re.compile(r"[^\s\\]+").match(text, i)
    return (m.group(0), m.end()) if m else ("", i)


def format_syntax(command: str, arglist: str) -> str:
    lines = [ln.strip().rstrip("\\").strip() for ln in arglist.split("\n")]
    lines = [ln for ln in lines if ln]
    if not lines:
        return command
    if len(lines) == 1:
        return f"{command} {lines[0]}"
    return command + "\n" + "\n".join(f"    {ln}" for ln in lines)


def _leading_comments(lines: list[str], idx: int) -> list[str]:
    """Contiguous comment lines directly above line ``idx`` (rule lines dropped)."""
    out: list[str] = []
    j = idx - 1
    while j >= 0 and lines[j].lstrip().startswith("#"):
        out.append(lines[j].strip())
        j -= 1
    out.reverse()
    return [c for c in out if re.sub(r"[#=\-*\s]", "", c)]


def _proc_option_lists(text: str, command: str, start: int) -> tuple[list[str], list[str]]:
    """keys/flags of the first ``parse_key_args "<command>"`` call after ``start``."""
    end = len(text)
    nxt = re.compile(r"^\s*(sta::)?define_cmd_args\b", re.M).search(text, start + 1)
    if nxt:
        end = nxt.start()
    body = text[start:end]
    m = re.search(rf'parse_key_args\s+"?{re.escape(command)}"?\s+\w+', body)
    if not m:
        return [], []
    keys: list[str] = []
    flags: list[str] = []
    i = m.end()
    for _ in range(2):
        word, j = _tcl_word(body, i)
        if word not in ("keys", "flags"):
            break
        values, i = _tcl_word(body, j)
        (keys if word == "keys" else flags).extend(re.findall(r"-[\w]+", values))
    return keys, flags


def load_command_cards(path: Path, versions: dict[str, str],
                       root: Path = THIRD_PARTY) -> list[Document]:
    """One Document per ``define_cmd_args`` block: exact syntax plus the leading comments."""
    source = source_of(path, root)
    base_url = permalink(source, versions)
    text = path.read_text(errors="replace").replace("\r\n", "\n")
    lines = text.split("\n")
    cards: list[Document] = []
    for m in re.finditer(r"^[ \t]*(?:sta::)?define_cmd_args\b", text, re.M):
        name, i = _tcl_word(text, m.end())
        arglist, end = _tcl_word(text, i)
        if not re.fullmatch(r"[A-Za-z_][\w:]*", name or ""):
            continue
        first = text.count("\n", 0, m.start())
        last = text.count("\n", 0, max(end - 1, m.start()))
        comments = _leading_comments(lines, first)
        # A proc's own leading comments when it is separated from define_cmd_args.
        proc = re.compile(rf"^\s*proc(?:_redirect)?\s+{re.escape(name)}\b", re.M).search(text, end)
        if proc:
            proc_line = text.count("\n", 0, proc.start())
            if proc_line > last + 1:
                comments += [c for c in _leading_comments(lines, proc_line) if c not in comments]
        keys, flags = _proc_option_lists(text, name, end)
        body = "\n".join(comments + [format_syntax(name, arglist)])
        if keys or flags:
            body += "\n# options parsed by the implementation (parse_key_args):"
            if keys:
                body += "\n#   keys (take a value): " + " ".join(keys)
            if flags:
                body += "\n#   flags: " + " ".join(flags)
        start_line = first + 1 - len(_leading_comments(lines, first))
        cards.append(Document(
            text=body + "\n", source=source, url=f"{base_url}#L{start_line}-L{last + 1}",
            doc_type="command_syntax", tool=tool_of(source), title=f"{name} (syntax)",
            section=name, fmt="text", atomic=True, commands=[name]))
    return cards


# --------------------------------------------------------------------------- OpenSTA PDF

def load_sta_reference_pdf(path: Path, versions: dict[str, str], root: Path = THIRD_PARTY,
                           unmatched: list[str] | None = None) -> list[Document]:
    """Split the OpenSTA reference into one Document per section / command / variable.

    Headings are recognised by font: Helvetica-Bold 14 pt / 12 pt are section / subsection
    headings, LiberationMono-Bold starts a command (or variable) entry, and the
    "Alphabetical Index" heading ends the reference. Text before the first heading
    (title page, table of contents) is dropped.
    """
    from pypdf import PdfReader

    source = source_of(path, root)
    base_url = permalink(source, versions)
    entries: list[tuple[int, str, list[str]]] = []   # (page, section path, lines)
    top = ""
    for pno, page in enumerate(PdfReader(str(path)).pages):
        heads: list[tuple[int, str]] = []             # (level, text) in content-stream order

        def visit(t, cm, tm, font, size, heads=heads):
            name = font.get("/BaseFont", "") if font else ""
            s = t.strip()
            if not s:
                return
            if "Mono-Bold" in name:
                if s.startswith("_") and heads and heads[-1][0] == 3:
                    heads[-1] = (3, heads[-1][1] + s)        # "set_power" + "_activity"
                elif re.fullmatch(r"[A-Za-z_]\w*", s):
                    heads.append((3, s))
            elif "Helvetica-Bold" in name and size >= 12:
                heads.append((1 if size >= 14 else 2, s))
            elif "Bold" in name and s == "Alphabetical Index":
                heads.append((0, s))

        lines = page.extract_text(visitor_text=visit).split("\n")
        marks: dict[int, tuple[int, str]] = {}
        cursor = 0
        for level, head in heads:
            # Entry lines sometimes lose the space after the name ("cmd[-opt]", "cmdarg"):
            # prefer a clean match, then fall back to a plain prefix match.
            clean = re.compile(rf"{re.escape(head)}(?=[\s\[{{|-]|$)")
            hit = next((k for k in range(cursor, len(lines))
                        if lines[k].strip() == head or (level == 3 and clean.match(lines[k].strip()))),
                       None)
            if hit is None and level == 3:
                hit = next((k for k in range(cursor, len(lines))
                            if lines[k].strip().startswith(head)), None)
            if hit is None:
                if unmatched is not None:
                    unmatched.append(f"page {pno + 1}: {head}")
                continue
            rest = lines[hit].strip()[len(head):]
            if level == 3 and rest and not rest[0].isspace():
                lines[hit] = f"{head} {rest}"
            marks[hit] = (level, head)
            cursor = hit + 1
        for k, raw in enumerate(lines):
            if k in marks:
                level, head = marks[k]
                if level == 0:
                    break
                if level == 1:
                    top = head
                    entries.append((pno + 1, head, []))
                elif level == 2:
                    entries.append((pno + 1, f"{top} > {head}", []))
                else:
                    entries.append((pno + 1, f"{top} > {head}", [raw.strip()]))
            elif entries and raw.strip():
                # option table rows lose the gap between the cells ("-optionWhen ...")
                entries[-1][2].append(re.sub(r"^(-\w+?[a-z0-9])([A-Z][a-z])", r"\1 \2", raw.rstrip()))
        if any(level == 0 for level, _ in marks.values()):
            break
    docs = []
    for page_no, section, body in entries:
        if not body:
            continue
        name = section.split(" > ")[-1]
        docs.append(Document(
            text="\n".join(body) + "\n", source=source, url=f"{base_url}#page={page_no}",
            doc_type="reference_pdf", tool="sta", title="OpenSTA command reference",
            section=section, fmt="text",
            commands=[name] if section.startswith("Commands > ") else []))
    return docs


# --------------------------------------------------------------------------- corpus

def _shingles(text: str, stem: str, n: int = 4) -> set[tuple[str, ...]]:
    body = "\n".join(ln for ln in text.split("\n") if not ln.strip().startswith("#"))
    body = body.replace(stem, "STEM")
    toks = re.findall(r"[A-Za-z_][\w.]*|-?\d+(?:\.\d+)?|\S", body)
    toks = ["0" if re.fullmatch(r"-?\d+(?:\.\d+)?", t) else t for t in toks]
    return {tuple(toks[i:i + n]) for i in range(max(1, len(toks) - n + 1))}


def dedupe_examples(docs: list[Document], threshold: float = 0.9
                    ) -> tuple[list[Document], list[tuple[str, str, float]]]:
    """Drop scripts whose token 4-gram Jaccard similarity to an already kept script of the
    same tool is >= threshold (files are visited in sorted order)."""
    kept: list[Document] = []
    sigs: list[tuple[str, set]] = []
    dropped: list[tuple[str, str, float]] = []
    for d in docs:
        stem = Path(d.source).stem
        sig = _shingles(d.text, stem)
        best, best_src = 0.0, ""
        for tool, (src, other) in zip((k.tool for k in kept), sigs):
            if tool != d.tool:
                continue
            union = len(sig | other)
            sim = len(sig & other) / union if union else 1.0
            if sim > best:
                best, best_src = sim, src
        if best >= threshold:
            dropped.append((d.source, best_src, round(best, 3)))
            continue
        kept.append(d)
        sigs.append((d.source, sig))
    return kept, dropped


def load_corpus(root: Path = THIRD_PARTY, min_commands: int = 3,
                dedupe_threshold: float = 0.9) -> tuple[list[Document], dict]:
    """Every Document of the knowledge base, in a deterministic order, plus load statistics."""
    versions = read_versions(root)
    docs: list[Document] = []
    stats: dict = {"skipped": [], "trivial_examples": [], "duplicate_examples": []}

    def skip(path: Path, reason: str) -> None:
        stats["skipped"].append({"source": source_of(path, root), "reason": reason})

    tool_names = tool_descriptions(root)

    def md(paths, doc_type):
        for p in paths:
            src = source_of(p, root)
            if src in SKIPPED_DOCS:
                skip(p, SKIPPED_DOCS[src])
                continue
            if p.suffix in (".html", ".htm"):
                doc = load_html(p, doc_type, versions, root)
            else:
                doc = load_markdown(p, doc_type, versions, root, tool_names)
            if doc.text.strip():
                docs.append(doc)

    ord_ = root / "OpenROAD"
    sta = root / "OpenSTA"
    orfs = root / "OpenROAD-flow-scripts"
    s = sorted

    # Documentation
    md([ord_ / "README.md", orfs / "README.md", sta / "README.md"], "readme")
    md(s((ord_ / "src").glob("*/README.md")), "readme")
    md(s(p for p in (ord_ / "docs").rglob("*") if p.suffix in (".md", ".html")), "guide")
    md(s((orfs / "docs" / "user").glob("*.md")) + s((orfs / "docs" / "tutorials").glob("*.md")), "guide")
    for p in s((ord_ / "src").glob("*/src/*.tcl")) + s(sta.glob("*/*.tcl")):
        if p.parent.name in ("test", "examples"):
            continue
        docs.extend(load_command_cards(p, versions, root))
    pdf = sta / "doc" / "OpenSTA.pdf"
    if pdf.exists():
        unmatched: list[str] = []
        docs.extend(load_sta_reference_pdf(pdf, versions, root, unmatched))
        stats["pdf_unmatched_headings"] = unmatched

    # Flow scripts (OpenROAD test/*.tcl design wrappers are kept: they hold the flow settings)
    flow = (s((ord_ / "test").glob("*.tcl")) + s((orfs / "flow" / "scripts").glob("*.tcl"))
            + s((orfs / "flow" / "platforms" / "nangate45").glob("*.tcl")))
    mk = orfs / "flow" / "platforms" / "nangate45" / "config.mk"
    for p in flow + ([mk] if mk.exists() else []):
        src = source_of(p, root)
        if src in SKIPPED_SCRIPTS:
            skip(p, SKIPPED_SCRIPTS[src])
            continue
        doc = load_script(p, "flow_script", versions, root)
        if not doc.text.strip():
            skip(p, "empty")
            continue
        docs.append(doc)

    # Official examples (regression tests)
    examples: list[Document] = []
    for p in s((ord_ / "src").glob("*/test/*.tcl")) + s((sta / "examples").glob("*.tcl")):
        if p.name.startswith("regression") or p.name == "helpers.tcl":
            skip(p, "test infrastructure")
            continue
        doc = load_script(p, "example", versions, root, strip_harness=True)
        if count_commands(doc.text) < min_commands:
            stats["trivial_examples"].append(doc.source)
            continue
        examples.append(doc)
    examples, dropped = dedupe_examples(examples, dedupe_threshold)
    stats["duplicate_examples"] = [{"source": a, "near_duplicate_of": b, "jaccard": j}
                                   for a, b, j in dropped]
    docs.extend(examples)
    stats["versions"] = versions
    return docs, stats
