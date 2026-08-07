"""Safety restrictions for executing LLM-generated Tcl.

Two independent layers:

1. A static policy check that rejects Tcl the agent has no legitimate reason to
   run (external processes, sockets, interpreter tricks, harness tampering).
2. An OS-level macOS Seatbelt profile (``sandbox-exec``): network denied,
   process execution denied, writes confined to the run directory, and reads of
   the user's home directory denied except for the repository itself.

On hosts without Seatbelt the Docker image provides the equivalent isolation
(read-only mounts, no network); the static policy then also rejects absolute
paths so scripts can only touch the run directory.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

# Commands an agent script may never invoke (anywhere in command position).
FORBIDDEN_COMMANDS = {
    "exec": "running external programs is not permitted",
    "socket": "network access is not permitted",
    "load": "loading shared libraries is not permitted",
    "interp": "creating Tcl interpreters is not permitted",
    "cd": "changing the working directory is not permitted; use paths relative to the run directory",
    "vwait": "event loops are not permitted",
    "package": "loading Tcl packages is not permitted",
    "rename": "renaming commands is not permitted",
}
_CMD_POSITION = r"(?:^|[;\[]|\n|\{)\s*"
_FORBIDDEN_RE = re.compile(_CMD_POSITION + r"(" + "|".join(FORBIDDEN_COMMANDS) + r")\b", re.MULTILINE)
_PIPE_OPEN_RE = re.compile(r"\bopen\s+[\"{]?\s*\|")
_FILE_MUTATE_RE = re.compile(r"\bfile\s+(delete|rename|link|attributes)\b")
_HARNESS_RE = re.compile(r"__harness|__probe|harness_script_status")
_ABS_PATH_RE = re.compile(r"(?:^|[\s{\"'=])(/(?!dev/null\b)[A-Za-z0-9_.~-][^\s\"'}\]]*)")
_HOME_RE = re.compile(r"(?:^|[\s{\"'])~[/\s]")
_PARENT_RE = re.compile(r"(?:^|[\s{\"'/])\.\.(?:/|$)")


@dataclass
class PolicyReport:
    violations: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


def _strip_comments(script: str) -> str:
    out = []
    for line in script.splitlines():
        if line.lstrip().startswith("#"):
            continue
        out.append(line)
    return "\n".join(out)


def check_policy(script: str, allow_absolute_paths: bool) -> PolicyReport:
    """Statically check an agent script; returns the list of violations."""
    code = _strip_comments(script)
    rep = PolicyReport()
    for m in _FORBIDDEN_RE.finditer(code):
        cmd = m.group(1)
        rep.violations.append(f"'{cmd}': {FORBIDDEN_COMMANDS[cmd]}")
    if _PIPE_OPEN_RE.search(code):
        rep.violations.append("'open |...': pipes to external programs are not permitted")
    for m in _FILE_MUTATE_RE.finditer(code):
        # With the OS sandbox, delete/rename can only touch the run directory
        # (e.g. replacing an old report), so only links/attributes stay forbidden.
        if allow_absolute_paths and m.group(1) in ("delete", "rename"):
            continue
        rep.violations.append(f"'file {m.group(1)}': deleting/renaming/linking files is not permitted")
    if _HARNESS_RE.search(code):
        rep.violations.append("referencing harness internals is not permitted")
    if _PARENT_RE.search(code):
        rep.violations.append("'..' paths are not permitted; stay inside the run directory")
    if _HOME_RE.search(code):
        rep.violations.append("'~' home-directory paths are not permitted")
    if not allow_absolute_paths:
        for m in _ABS_PATH_RE.finditer(code):
            rep.violations.append(f"absolute path '{m.group(1)}' is not permitted; use paths relative to the run directory")
    # de-duplicate while keeping order
    rep.violations = list(dict.fromkeys(rep.violations))
    return rep


def seatbelt_available() -> bool:
    return platform.system() == "Darwin" and shutil.which("sandbox-exec") is not None


def _sb(path: Path | str) -> str:
    return str(path).replace("\\", "\\\\").replace('"', '\\"')


def seatbelt_profile(run_dir: Path, readable_root: Path, openroad_bin: Path) -> str:
    """Seatbelt (SBPL) profile for one OpenROAD execution."""
    home = Path(os.path.expanduser("~")).resolve()
    tmp = Path(os.environ.get("TMPDIR", "/tmp")).resolve()
    return (
        "(version 1)"
        "(allow default)"
        "(deny network*)"
        "(deny process-exec)"
        f'(allow process-exec (literal "{_sb(openroad_bin)}"))'
        f'(deny file-read* (subpath "{_sb(home)}"))'
        f'(allow file-read* (subpath "{_sb(readable_root)}") (subpath "{_sb(run_dir)}"))'
        "(allow file-read-metadata)"
        "(deny file-write*)"
        f'(allow file-write* (subpath "{_sb(run_dir)}") (subpath "{_sb(tmp)}")'
        ' (literal "/dev/null") (regex #"^/dev/tty") (regex #"^/dev/fd/"))'
    )
