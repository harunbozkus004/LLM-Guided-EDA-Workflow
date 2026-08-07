"""Controlled execution interface between Python and OpenROAD.

Each execution gets a fresh run directory::

    run_dir/
      platform/ -> Nangate45 platform files (read-only)
      design/   -> gcd netlist + SDC (read-only)
      inputs/   -> starting-state database snapshot(s)
      outputs/  -> the only place agent scripts are told to write
      agent_script.tcl  the (LLM-generated) script under test
      harness.tcl       preamble -> agent script -> probe -> final.odb
      probe.json        actual design state after the script
      stdout.log, stderr.log, result.json

Every attempt starts from the same immutable snapshot, which gives rollback
for free: a failed attempt never contaminates the next one.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from common.config import load_config, resolve
from common.paths import ROOT, rel
from openroad import log_parser, sandbox

PROBE_TCL = Path(__file__).parent / "tcl" / "probe.tcl"
LARGE_OUTPUT_BYTES = 2 * 1024 * 1024

HARNESS_TEMPLATE = r"""# Auto-generated execution harness (not visible to the agent).
fconfigure stdout -buffering line
set ::harness_script_status not_run
set_thread_count @THREADS@
@PREAMBLE@
puts "HARNESS_PREAMBLE_DONE"
rename exit __harness_real_exit
proc exit {{code 0}} { return -code error "HARNESS_EXIT_CALLED $code" }
set ::harness_script_status running
puts "HARNESS_AGENT_SCRIPT_BEGIN"
set ::harness_rc [catch {source -echo agent_script.tcl} ::harness_err]
puts "HARNESS_AGENT_SCRIPT_END"
if {$::harness_rc == 0 || [string match "*HARNESS_EXIT_CALLED*" $::harness_err]} {
  set ::harness_script_status ok
} else {
  set ::harness_script_status error
  puts "HARNESS_SCRIPT_ERROR: [string map [list "\n" " | "] $::harness_err]"
  puts "HARNESS_ERROR_INFO_BEGIN"
  puts $::errorInfo
  puts "HARNESS_ERROR_INFO_END"
}
puts "HARNESS_SCRIPT_STATUS: $::harness_script_status"
@PROBE@
@FINAL_DB@
puts "HARNESS_DONE"
__harness_real_exit 0
"""

ORACLE_TEMPLATE = r"""# Auto-generated validator query (trusted, harness-owned).
fconfigure stdout -buffering line
set_thread_count 1
@PREAMBLE@
proc __oracle_emit {json} { set f [open @OUT@ w]; puts $f $json; close $f }
proc __oracle_json {v} {
  if {[string is double -strict $v] && ![string match -nocase {*inf*} $v] && ![string match -nocase {*nan*} $v]} { return $v }
  return "\"[string map [list \\ \\\\ \" \\\" \n \\n \t \\t] $v]\""
}
# Emit a flat Tcl dict as a JSON object (numbers stay numbers, everything else becomes a string).
proc __oracle_emit_dict {d} {
  set parts {}
  dict for {k v} $d { lappend parts "[__oracle_json $k]: [__oracle_json $v]" }
  __oracle_emit "\{[join $parts {, }]\}"
}
@BODY@
exit 0
"""


@dataclass
class ExecutionResult:
    success: bool
    exit_code: int | None
    stdout: str
    stderr: str
    error_type: str | None
    error_message: str | None
    errors: list[str]
    warnings: list[str]
    execution_time: float
    timed_out: bool
    memory_exceeded: bool
    script_status: str
    policy_violations: list[str]
    artifacts: list[dict[str, Any]]
    probe: dict[str, Any] | None
    run_dir: str
    error_info: str | None = None
    agent_output: str = ""
    label: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_logs: bool = True) -> dict[str, Any]:
        d = asdict(self)
        if not include_logs:
            d["stdout"] = d["stdout"][-4000:]
            d["stderr"] = d["stderr"][-2000:]
            d["agent_output"] = d["agent_output"][-4000:]
            d["probe"] = None
        return d

    @property
    def failing_line(self) -> int | None:
        """Line number of the failing command in agent_script.tcl, if known."""
        import re
        for text in (self.error_message or "", self.error_info or ""):
            m = re.search(r"agent_script\.tcl(?:,| line)\s*(\d+)", text)
            if m:
                return int(m.group(1))
        return None


class OpenROADExecutor:
    def __init__(self, config: dict[str, Any] | None = None):
        cfg = dict(load_config("openroad_config"))
        cfg.update(config or {})
        self.cfg = cfg
        self.openroad_bin = resolve(cfg["openroad_bin"]).resolve()
        self.timeout_s = float(cfg.get("timeout_s", 300))
        self.memory_limit_mb = float(cfg.get("memory_limit_mb", 6144))
        self.threads = int(cfg.get("threads", 1))
        self.write_final_db = bool(cfg.get("write_final_db", True))
        sb = cfg.get("sandbox", {}) or {}
        self.static_policy = bool(sb.get("static_policy", True))
        mode = str(sb.get("seatbelt", "auto"))
        self.use_seatbelt = sandbox.seatbelt_available() if mode == "auto" else mode == "on"
        if not self.openroad_bin.exists():
            raise FileNotFoundError(f"OpenROAD not found at {self.openroad_bin}; run scripts/setup_env.sh")

    # ------------------------------------------------------------------ setup
    def prepare_run_dir(self, run_dir: Path, links: dict[str, Path]) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "outputs").mkdir(exist_ok=True)
        (run_dir / "tmp").mkdir(exist_ok=True)
        for name, target in links.items():
            link = run_dir / name
            link.parent.mkdir(parents=True, exist_ok=True)
            if link.is_symlink() or link.exists():
                continue
            link.symlink_to(Path(target).resolve())

    def _command(self, run_dir: Path, script_name: str) -> list[str]:
        cmd = [str(self.openroad_bin), "-no_init", "-no_splash", "-exit", script_name]
        if self.use_seatbelt:
            profile = sandbox.seatbelt_profile(run_dir.resolve(), ROOT, self.openroad_bin)
            cmd = ["/usr/bin/sandbox-exec", "-p", profile] + cmd
        return cmd

    def _env(self, run_dir: Path) -> dict[str, str]:
        # Deliberately minimal: no API keys or user environment reach OpenROAD.
        return {
            "HOME": str(run_dir.resolve()),
            "PATH": "/usr/bin:/bin",
            "TMPDIR": str((run_dir / "tmp").resolve()),
            "LANG": "C",
            "LC_ALL": "C",
            "QT_QPA_PLATFORM": "offscreen",
        }

    # -------------------------------------------------------------- execution
    def _spawn(self, run_dir: Path, script_name: str, timeout_s: float,
               log_prefix: str = "") -> tuple[int | None, bool, bool, float]:
        stdout_f = open(run_dir / f"{log_prefix}stdout.log", "w")
        stderr_f = open(run_dir / f"{log_prefix}stderr.log", "w")
        start = time.monotonic()
        proc = subprocess.Popen(
            self._command(run_dir, script_name), cwd=run_dir, stdout=stdout_f, stderr=stderr_f,
            stdin=subprocess.DEVNULL, env=self._env(run_dir), start_new_session=True,
        )
        timed_out = memory_exceeded = False
        stop = threading.Event()

        def watchdog() -> None:
            nonlocal memory_exceeded
            while not stop.wait(1.0):
                rss_mb = _rss_mb(proc.pid)
                if rss_mb is not None and rss_mb > self.memory_limit_mb:
                    memory_exceeded = True
                    _kill_group(proc)
                    return

        wd = threading.Thread(target=watchdog, daemon=True)
        wd.start()
        try:
            exit_code = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(proc)
            exit_code = proc.wait()
        finally:
            stop.set()
            stdout_f.close()
            stderr_f.close()
        return exit_code, timed_out, memory_exceeded, time.monotonic() - start

    def run(self, script: str, run_dir: Path, *, preamble: str, links: dict[str, Path],
            label: str = "", timeout_s: float | None = None) -> ExecutionResult:
        """Execute an agent script in a fresh sandboxed OpenROAD session."""
        run_dir = Path(run_dir)
        self.prepare_run_dir(run_dir, links)
        (run_dir / "agent_script.tcl").write_text(script if script.endswith("\n") else script + "\n")
        shutil.copyfile(PROBE_TCL, run_dir / "probe.tcl")
        harness = (HARNESS_TEMPLATE
                   .replace("@THREADS@", str(self.threads))
                   .replace("@PREAMBLE@", preamble.strip())
                   .replace("@PROBE@", "source probe.tcl")
                   .replace("@FINAL_DB@", 'if {[catch {write_db final.odb} __e]} { puts "HARNESS_FINAL_DB_ERROR: $__e" }'
                            if self.write_final_db else ""))
        (run_dir / "harness.tcl").write_text(harness)

        violations: list[str] = []
        if self.static_policy:
            violations = sandbox.check_policy(script, allow_absolute_paths=self.use_seatbelt).violations
        if violations:
            parsed = log_parser.ParsedLog(None, None, "policy_violation", [], [], None, "")
            error_type, message = log_parser.classify_execution(
                policy_violations=violations, timed_out=False, memory_exceeded=False, exit_code=None, parsed=parsed)
            result = ExecutionResult(
                success=False, exit_code=None, stdout="", stderr="", error_type=error_type,
                error_message=f"Script rejected by safety policy (not executed): {message}",
                errors=violations, warnings=[], execution_time=0.0, timed_out=False, memory_exceeded=False,
                script_status="policy_violation", policy_violations=violations, artifacts=[], probe=None,
                run_dir=rel(run_dir), label=label)
            self._save(run_dir, result)
            return result

        exit_code, timed_out, mem, elapsed = self._spawn(run_dir, "harness.tcl", timeout_s or self.timeout_s)
        stdout = (run_dir / "stdout.log").read_text(errors="replace")
        stderr = (run_dir / "stderr.log").read_text(errors="replace")
        parsed = log_parser.parse_log(stdout)
        probe = None
        probe_path = run_dir / "probe.json"
        if probe_path.exists():
            try:
                probe = json.loads(probe_path.read_text())
            except json.JSONDecodeError as e:
                probe = {"probe_error": f"invalid probe JSON: {e}"}
        error_type, message = log_parser.classify_execution(
            policy_violations=[], timed_out=timed_out, memory_exceeded=mem, exit_code=exit_code, parsed=parsed)
        if error_type is None and (probe is None or "probe_error" in probe):
            error_type, message = "runtime_failure", "design-state probe failed: " + str(
                (probe or {}).get("probe_error", "no probe output"))
        errors = parsed.tool_errors[:]
        if parsed.script_error:
            errors.append(parsed.script_error)
        result = ExecutionResult(
            success=error_type is None, exit_code=exit_code, stdout=stdout, stderr=stderr,
            error_type=error_type, error_message=message, errors=list(dict.fromkeys(errors)),
            warnings=parsed.warnings, execution_time=round(elapsed, 3), timed_out=timed_out,
            memory_exceeded=mem, script_status="timeout" if timed_out else parsed.script_status,
            policy_violations=[], artifacts=self._artifacts(run_dir), probe=probe, run_dir=rel(run_dir),
            error_info=parsed.error_info, agent_output=parsed.agent_output, label=label)
        self._save(run_dir, result)
        return result

    def query(self, run_dir: Path, *, preamble: str, body: str, links: dict[str, Path],
              name: str = "oracle", timeout_s: float = 300) -> dict[str, Any]:
        """Run a trusted, validator-owned Tcl query; the body calls __oracle_emit <json>."""
        run_dir = Path(run_dir)
        self.prepare_run_dir(run_dir, links)
        out = f"{name}.json"
        (run_dir / out).unlink(missing_ok=True)
        script = (ORACLE_TEMPLATE.replace("@PREAMBLE@", preamble.strip())
                  .replace("@OUT@", out).replace("@BODY@", body.strip()))
        (run_dir / f"{name}.tcl").write_text(script)
        exit_code, timed_out, _, _ = self._spawn(run_dir, f"{name}.tcl", timeout_s, log_prefix=f"{name}_")
        log = (run_dir / f"{name}_stdout.log").read_text(errors="replace")
        if timed_out or not (run_dir / out).exists():
            raise RuntimeError(f"oracle query '{name}' failed (exit {exit_code}); log tail:\n{log[-2000:]}")
        return json.loads((run_dir / out).read_text())

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _artifacts(run_dir: Path) -> list[dict[str, Any]]:
        out = []
        base = run_dir / "outputs"
        for p in sorted(base.rglob("*")):
            if p.is_file():
                out.append({"path": str(p.relative_to(run_dir)), "size": p.stat().st_size})
        return out

    @staticmethod
    def _save(run_dir: Path, result: ExecutionResult) -> None:
        d = result.to_dict(include_logs=False)
        (run_dir / "result.json").write_text(json.dumps(d, indent=1, default=str))

    def cleanup(self, run_dir: Path) -> None:
        """Drop large regenerable files once a run has been validated."""
        run_dir = Path(run_dir)
        if self.cfg.get("keep_large_outputs"):
            return
        (run_dir / "final.odb").unlink(missing_ok=True)
        shutil.rmtree(run_dir / "tmp", ignore_errors=True)
        for p in (run_dir / "outputs").rglob("*"):
            if p.is_file() and p.stat().st_size > LARGE_OUTPUT_BYTES:
                p.write_text(f"[removed after validation: {p.stat().st_size} bytes]\n")


def _rss_mb(pid: int) -> float | None:
    try:
        out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
        return float(out.stdout.strip()) / 1024.0 if out.stdout.strip() else None
    except (subprocess.SubprocessError, ValueError):
        return None


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
