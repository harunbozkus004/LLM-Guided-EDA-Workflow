"""Tests of the sandboxed OpenROAD executor (real OpenROAD, ~0.3 s per execution).

Run directories are created under experiments/runs/_pytest/ and removed afterwards.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from benchmark.states import get_state, load_baseline_probe
from common.paths import ROOT, RUNS_DIR
from openroad.executor import ExecutionResult, OpenROADExecutor


@pytest.fixture(scope="module")
def executor() -> OpenROADExecutor:
    return OpenROADExecutor()


@pytest.fixture
def run_root() -> Path:
    root = RUNS_DIR / "_pytest" / f"executor_{uuid.uuid4().hex[:8]}"
    yield root
    shutil.rmtree(root, ignore_errors=True)
    try:
        root.parent.rmdir()
    except OSError:
        pass


def run(executor: OpenROADExecutor, run_root: Path, script: str, state: str = "synth",
        **kwargs) -> tuple[ExecutionResult, Path]:
    spec = get_state(state)
    run_dir = run_root / uuid.uuid4().hex[:6]
    return executor.run(script, run_dir, preamble=spec.preamble(), links=spec.links(), **kwargs), run_dir


def test_clean_script(executor, run_root):
    script = ('puts "hello from the agent"\n'
              "set f [open outputs/area.txt w]\n"
              "puts $f [llength [get_cells *]]\n"
              "close $f\n"
              "report_design_area\n")
    res, run_dir = run(executor, run_root, script)
    assert res.success and res.error_type is None and res.script_status == "ok"
    assert "hello from the agent" in res.agent_output
    assert "Design area" in res.agent_output
    assert [a["path"] for a in res.artifacts] == ["outputs/area.txt"] and res.artifacts[0]["size"] > 0
    assert res.probe["design_loaded"] is True
    assert res.probe["inst_count"] == load_baseline_probe("synth")["inst_count"]
    assert (run_dir / "final.odb").is_file() and (run_dir / "result.json").is_file()
    assert (run_dir / "agent_script.tcl").read_text() == script


def test_invalid_command_classified_with_failing_line(executor, run_root):
    script = "puts start\nset x 1\nmagic_place_everything -effort high\nputs never_printed\n"
    res, _ = run(executor, run_root, script)
    assert not res.success and res.script_status == "error"
    assert res.error_type == "invalid_command"
    assert res.failing_line == 3
    assert "magic_place_everything" in res.error_message
    assert "never_printed" not in res.agent_output.replace("puts never_printed", "")
    assert res.probe is not None and res.probe["design_loaded"]  # the probe still runs after a script error


def test_tcl_syntax_error(executor, run_root):
    res, _ = run(executor, run_root, "puts ok\nif {1}{puts x}\n")
    assert not res.success and res.script_status == "error"
    assert res.error_type == "tcl_syntax"
    assert "extra characters after close-brace" in res.error_message
    assert res.failing_line == 2


# The harness probe prints [ERROR ...] lines after the agent script (DRT-0002 from
# detailed_route_num_drvs, GRT-0086 from grt::have_routes); they must never be taken
# for the agent's own error.
@pytest.mark.parametrize("script,expected", [
    ('puts "x\nif {1 {\n  puts y\n', "tcl_syntax"),
    ("initialize_floorplan -utilization 35 -bogus_flag 3\n", "invalid_argument"),
    ("source platform/does_not_exist.tcl\n", "missing_file"),
    ("global_placement\n", "missing_prerequisite"),
])
def test_executor_classification_ignores_probe_messages(executor, run_root, script, expected):
    res, _ = run(executor, run_root, script)
    assert res.error_type == expected
    assert "DRT-0002" not in (res.error_message or "")


def test_policy_violation_not_executed(executor, run_root):
    res, run_dir = run(executor, run_root, "puts hi\nexec ls -l\n")
    assert res.error_type == "unsafe_command" and res.script_status == "policy_violation"
    assert "exec" in res.error_message and res.policy_violations
    assert res.probe is None and res.execution_time == 0.0
    assert not (run_dir / "stdout.log").exists()  # OpenROAD was never started


def test_timeout(executor, run_root):
    res, _ = run(executor, run_root, "set i 0\nwhile {1} { incr i }\n", timeout_s=2)
    assert res.timed_out and not res.success
    assert res.error_type == "runtime_failure" and res.script_status == "timeout"
    assert res.execution_time < 30


def test_seatbelt_blocks_write_outside_run_dir(executor, run_root):
    if not executor.use_seatbelt:
        pytest.skip("macOS seatbelt not available on this host")
    target = run_root / f"outside_{uuid.uuid4().hex[:6]}.txt"  # inside the repository, outside the run dir
    assert ROOT in target.parents
    run_root.mkdir(parents=True, exist_ok=True)
    res, run_dir = run(executor, run_root, f'set f [open "{target}" w]\nputs $f leaked\nclose $f\n')
    assert run_dir not in target.parents
    assert not res.success and res.script_status == "error"  # rejected by the OS sandbox, not the static policy
    assert not target.exists()
    ok, _ = run(executor, run_root, "set f [open outputs/inside.txt w]\nputs $f fine\nclose $f\n")
    assert ok.success and [a["path"] for a in ok.artifacts] == ["outputs/inside.txt"]
