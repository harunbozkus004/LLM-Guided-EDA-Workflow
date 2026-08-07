"""Tests of the LLM agent (mock LLMs only; episodes run real OpenROAD, ~0.3 s per execution).

Run directories and caches are created under experiments/runs/_pytest/ and removed afterwards.
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import urllib.error
import uuid
from pathlib import Path

import anthropic
import httpx2
import pytest

from agent import orchestrator
from agent.command_generator import extract_tcl
from agent.error_classifier import command_at_line, diagnose
from agent.error_corrector import FEEDBACK_BUDGET, build_repair_message
from agent.llm import (AnthropicClient, LLMError, MockLLM, OpenAICompatClient, ReplayCache, call_seed, can_continue,
                       cost_usd, make_llm, plain_text)
from agent.orchestrator import AgentConfig, load_agent_config, run_episode
from agent.prompts import DOCS_HEADER, EXTRA_DOCS_HEADER, HINTS, SYSTEM_PROMPT, generation_message
from agent.retrieval import FakeChunk, FakeRetriever
from agent.targeted_retrieval import TARGETED_HEADER, SyntaxCard, SyntaxCards
from agent.error_classifier import Diagnosis
from agent.state_manager import DesignState, diff
from agent.verifier import requested_operations, requested_outputs, verify
from benchmark.states import STATES, get_state, load_baseline_probe
from benchmark.task_loader import load_tasks
from benchmark.task_validator import Check, ValidationResult
from common.jsonl import read_jsonl
from common.paths import RESULTS_DIR, RUNS_DIR
from openroad.executor import ExecutionResult, OpenROADExecutor

# ------------------------------------------------------------------ fixtures
BAD_SCRIPT = "create_floorplan -utilization 35 -aspect_ratio 1.0 \\\n  -core_space 5\nsource platform/Nangate45.tracks\n"
NOOP_SCRIPT = 'puts "inspecting only"\n'


def answer(script: str) -> str:
    return f"Assumption: the site is the platform default.\n```tcl\n{script}```\n"


@pytest.fixture(scope="module")
def executor() -> OpenROADExecutor:
    return OpenROADExecutor()


@pytest.fixture(scope="module")
def task():
    return load_tasks("dev", ["DEV-EX-01"])[0]


@pytest.fixture
def run_root() -> Path:
    root = RUNS_DIR / "_pytest" / f"agent_{uuid.uuid4().hex[:8]}"
    yield root
    shutil.rmtree(root, ignore_errors=True)
    try:
        root.parent.rmdir()
    except OSError:
        pass


def cfg(name: str, rag: str = "none", feedback: bool = False, max_attempts: int = 1, final_k: int = 2) -> AgentConfig:
    return AgentConfig(name=name, rag=rag, feedback=feedback, max_attempts=max_attempts, final_k=final_k)


def doc_retriever() -> FakeRetriever:
    return FakeRetriever([
        FakeChunk("doc-fp", "initialize_floorplan -utilization -aspect_ratio -core_space floorplan utilization core "
                            "die aspect ratio spacing", section="ifp"),
        FakeChunk("doc-tracks", "make_tracks creates routing tracks for the metal layers", section="tracks"),
        FakeChunk("doc-error", "invalid command name: list the commands available in this version", section="tcl"),
        FakeChunk("doc-gpl", "global_placement -density target", section="gpl"),
    ])


def all_text(llm: MockLLM) -> str:
    """Everything sent to the LLM, as plain text (no JSON escaping)."""
    return "\n".join([c["system"] for c in llm.calls] + [plain_text(m["content"]) for c in llm.calls
                                                         for m in c["messages"]])


def fake_result(*, error_type=None, status="ok", artifacts=(), probe=None, stdout="", message=None,
                agent_output="") -> ExecutionResult:
    return ExecutionResult(success=error_type is None, exit_code=0, stdout=stdout, stderr="", error_type=error_type,
                           error_message=message, errors=[], warnings=[], execution_time=0.1, timed_out=False,
                           memory_exceeded=False, script_status=status, policy_violations=[],
                           artifacts=list(artifacts), probe=probe, run_dir="experiments/runs/_fake",
                           agent_output=agent_output)


def state(name: str) -> DesignState:
    return DesignState.from_probe(load_baseline_probe(name))


# ------------------------------------------------------------------ extract_tcl
@pytest.mark.parametrize("text,expected", [
    ("Plan.\n```bash\nls\n```\nScript:\n```tcl\nputs a\n```\n", "puts a\n"),            # tcl block wins
    ("```TCL\nputs b\n```", "puts b\n"),                                                 # case-insensitive
    ("```tcl title=flow.tcl\nputs c\n```", "puts c\n"),                                  # extra info words
    ("```\nputs d\n```\n```python\nprint(1)\n```", "puts d\n"),                          # first block fallback
    ("```text\nputs e\n```", "puts e\n"),
    ("puts f\nputs g\n", "puts f\nputs g\n"),                                           # no fence: whole text
    ("```tcl\nputs h\nforeach x {1 2} {\n  puts $x", "puts h\nforeach x {1 2} {\n  puts $x\n"),  # unclosed
    ("~~~tcl\nputs i\n~~~", "puts i\n"),                                                 # tilde fence
    ("```tcl\r\nputs j\r\n```\r\n", "puts j\n"),                                         # CRLF
    ("````tcl\nputs \"```\"\n````", 'puts "```"\n'),                                     # longer fence
    ("   ```tcl\n  if {1} {\n    puts k\n  }\n   ```", "  if {1} {\n    puts k\n  }\n"),  # indentation kept
    ("", ""),
    ("```tcl\n```", ""),
])
def test_extract_tcl(text, expected):
    assert extract_tcl(text) == expected


# ------------------------------------------------------------------ prompts
def test_system_prompt_and_generation_message():
    lines = SYSTEM_PROMPT.split("\n")
    assert lines[0] == "You are an expert ASIC physical-design engineer who writes Tcl scripts for the OpenROAD tool."
    assert lines[3] == "Rules:" and len(lines) == 10
    assert lines[-1] == "- Do not claim that the task is complete: the script will be executed and checked."
    plain = generation_message("Do X.", "CONTEXT\n")
    assert plain == "TASK\nDo X.\n\nCONTEXT\n\nWrite the Tcl script."
    with_docs = generation_message("Do X.", "CONTEXT\n", "DOC TEXT")
    assert with_docs == f"TASK\nDo X.\n\nCONTEXT\n\n{DOCS_HEADER}\nDOC TEXT\n\nWrite the Tcl script."


# ------------------------------------------------------------------ state manager
def test_design_state_from_baseline_probes():
    expected = {  # flags that are True in each starting state
        "synth": {"design_loaded"},
        "fp_init": {"design_loaded", "floorplan_initialized", "tracks_defined"},
        "floorplan": {"design_loaded", "floorplan_initialized", "tracks_defined", "io_pins_placed",
                      "tapcells_inserted", "power_grid_built"},
        "gplaced": {"design_loaded", "floorplan_initialized", "tracks_defined", "io_pins_placed",
                    "tapcells_inserted", "power_grid_built", "cells_placed"},
    }
    expected["placed"] = expected["gplaced"] | {"placement_legal"}
    expected["cts"] = expected["placed"] | {"cts_completed"}
    expected["grouted"] = expected["cts"] | {"global_routing_completed"}
    expected["routed"] = expected["grouted"] | {"detailed_routing_completed", "fillers_inserted"}
    for name in STATES:
        flags = state(name).flags()
        assert {k for k, v in flags.items() if v} == expected[name], name
    assert DesignState.from_probe(None).available is False
    assert "probe failed" in DesignState.from_probe({"probe_error": "boom"}).summary()
    changes = diff(state("floorplan"), state("gplaced"))
    assert "standard cells placed: no -> yes" in changes
    assert "placed standard cells: 0 -> 347" in changes
    assert diff(state("placed"), state("placed")) == []
    assert "clock tree: yes" in state("cts").summary()


# ------------------------------------------------------------------ verifier
POSITIVE_INTENTS = [
    ("Initialize the floorplan with 40% utilization and create the routing tracks.",
     {"floorplan_initialized", "tracks_defined"}),
    ("Run global placement with a target density of 0.6.", {"cells_placed"}),
    ("Place the standard cells, then legalize the placement.", {"cells_placed", "placement_legal"}),
    ("Perform detailed placement so that every cell sits on a legal site.", {"placement_legal"}),
    ("Synthesize the clock tree using BUF_X4 as the root buffer.", {"cts_completed"}),
    ("Run clock tree synthesis and report the skew.", {"cts_completed"}),
    ("Globally route the design and write the guides to outputs/route.guide.", {"global_routing_completed"}),
    ("Run detailed routing with 4 iterations.", {"detailed_routing_completed"}),
    ("Insert tap cells every 20 um and build the power grid.", {"tapcells_inserted", "power_grid_built"}),
    ("Place the IO pins on metal3 and metal4.", {"io_pins_placed"}),
    ("Insert filler cells into the empty sites.", {"fillers_inserted"}),
    ("Run pdngen to create the PDN.", {"power_grid_built"}),
    ("Global placement must be run with routability mode enabled.", {"cells_placed"}),
    ("Re-run global routing with a 0.3 layer adjustment.", {"global_routing_completed"}),
    ("Use global_placement and then run detailed_placement.", {"placement_legal"}),
    ("Remove the filler cells, run detailed placement and re-insert the filler cells.",
     {"placement_legal", "fillers_inserted"}),
]
NEGATIVE_INTENTS = [
    "Report the worst setup slack after global routing to outputs/wns.rpt.",
    "Write the HPWL of the global placement result to outputs/hpwl.txt.",
    "Do not run detailed routing; only report the global routing congestion.",
    "Without running clock tree synthesis, report the clock skew.",
    "Report the number of filler cells and tap cells in the design.",
    "Check whether the placement is legal and write the result to outputs/legal.txt.",
    "Run report_checks on the design after detailed placement.",
    "Report the power grid IR drop.",
    "Report the area of the complete floorplan.",
    "Run timing analysis on the globally routed design.",
    "Remove the filler cells.",
    "Report the clock tree latency and skew.",
    "Read the floorplan from platform files and list the routing tracks.",
    "Route the clock tree nets on metal6 and metal7 only.",
    "Replace the buffers on the critical path with stronger ones.",
]


@pytest.mark.parametrize("instruction,expected", POSITIVE_INTENTS)
def test_verifier_detects_requested_operations(instruction, expected):
    assert set(requested_operations(instruction)) == expected


@pytest.mark.parametrize("instruction", NEGATIVE_INTENTS)
def test_verifier_ignores_report_and_negated_requests(instruction):
    assert requested_operations(instruction) == []


def test_verifier_checks_state_only_when_not_already_satisfied():
    instr = "Run global placement with a target density of 0.6."
    unchanged = verify(instr, fake_result(probe=load_baseline_probe("floorplan")), state("floorplan"),
                       state("floorplan"))
    assert not unchanged.ok and unchanged.expectations == ["cells_placed"]
    assert "place the standard cells" in unchanged.reasons[0] and "0/347" in unchanged.reasons[0]
    done = verify(instr, fake_result(), state("floorplan"), state("gplaced"))
    assert done.ok and done.reasons == []
    already = verify(instr, fake_result(), state("gplaced"), state("gplaced"))  # starting state satisfies it
    assert already.ok and already.expectations == []


def test_verifier_output_files_and_execution():
    instr = "Report the worst setup slack to outputs/wns.rpt and the area to outputs/area.txt."
    assert requested_outputs(instr) == ["outputs/wns.rpt", "outputs/area.txt"]
    placed = state("placed")
    missing = verify(instr, fake_result(artifacts=[{"path": "outputs/wns.rpt", "size": 12}]), placed, placed)
    assert not missing.ok and missing.reasons == ["The requested output file outputs/area.txt was not written."]
    empty = verify(instr, fake_result(artifacts=[{"path": "outputs/wns.rpt", "size": 12},
                                                 {"path": "outputs/area.txt", "size": 0}]), placed, placed)
    assert empty.reasons == ["The requested output file outputs/area.txt is empty."]
    good = verify(instr, fake_result(artifacts=[{"path": "outputs/wns.rpt", "size": 12},
                                                {"path": "outputs/area.txt", "size": 3}]), placed, placed)
    assert good.ok
    failed = verify("Report the slack.", fake_result(error_type="invalid_command", status="error"), placed, placed)
    assert not failed.ok and not failed.execution_clean
    unreadable = verify("Report the slack.", fake_result(), placed, DesignState.from_probe(None))
    assert not unreadable.ok and "could not be read" in unreadable.reasons[0]


# ------------------------------------------------------------------ diagnosis and repair message
def test_command_at_line_reconstructs_multiline_commands():
    script = "puts a\ninitialize_floorplan -utilization 35 \\\n  -bogus 3\nforeach x {1 2} {\n  puts $x\n}\n"
    assert command_at_line(script, 1) == "puts a"
    assert command_at_line(script, 3) == "initialize_floorplan -utilization 35 -bogus 3"
    assert command_at_line(script, 6) == "foreach x {1 2} { puts $x }"
    assert command_at_line(script, 99) is None and command_at_line(script, None) is None


@pytest.mark.parametrize("script,expected,line", [
    ('puts "x\nif {1 {\n  puts y\n', "tcl_syntax", None),
    ("initialize_floorplan -utilization 35 -bogus_flag 3\n", "invalid_argument", 1),
    ("source platform/does_not_exist.tcl\n", "missing_file", 1),
    ("global_placement\n", "missing_prerequisite", 1),
    ("puts ok\nmagic_cmd 1\n", "invalid_command", 2),
])
def test_diagnosis_ignores_probe_messages(executor, run_root, script, expected, line):
    spec = get_state("synth")
    res = executor.run(script, run_root / "diag", preamble=spec.preamble(), links=spec.links())
    verdict = verify("Report something.", res, state("synth"), DesignState.from_probe(res.probe))
    diag = diagnose(res, verdict, script)
    assert diag.error_type == expected and diag.failing_line == line
    assert "DRT-0002" not in diag.message and all("DRT-0002" not in e for e in diag.tool_errors)
    assert diag.hint == HINTS[expected]
    assert diag.retrieval_query.endswith(expected.replace("_", " "))


def test_repair_message_is_bounded_and_complete():
    noisy = "\n".join(f"[WARNING GPL-{i:04d}] warning number {i} " + "x" * 300 for i in range(50))
    output = noisy + "\n" + "\n".join(f"line {i} " + "y" * 250 for i in range(500))
    stdout = ("HARNESS_AGENT_SCRIPT_BEGIN\n" + output + "\n[ERROR GPL-0130] No rows defined in design.\n"
              "HARNESS_AGENT_SCRIPT_END\nHARNESS_SCRIPT_ERROR: Error: agent_script.tcl, 3 GPL-0130\n"
              "HARNESS_SCRIPT_STATUS: error\n[ERROR DRT-0002] Detailed routing has not been run yet.\n")
    res = fake_result(error_type="incorrect_design_context", status="error", stdout=stdout,
                      message="[ERROR DRT-0002] Detailed routing has not been run yet.",
                      probe=load_baseline_probe("synth"))
    script = "puts a\nputs b\nglobal_placement -density 0.6\n"
    verdict = verify("Run global placement.", res, state("synth"), state("synth"))
    diag = diagnose(res, verdict, script)
    assert diag.error_type == "missing_prerequisite" and diag.message == "[ERROR GPL-0130] No rows defined in design."
    msg = build_repair_message(attempt=2, max_attempts=4, result=res, diagnosis=diag, verdict=verdict,
                               before=state("synth"), after=state("synth"), docs="D" * 9000)
    feedback = msg.replace("D" * 9000, "")
    assert len(feedback) <= FEEDBACK_BUDGET + 300
    order = ["EXECUTION RESULT (attempt 2 of 4)", "FAILED: execution error", "Error type: missing_prerequisite",
             "Error: [ERROR GPL-0130] No rows defined in design.",
             "(agent_script.tcl line 3: global_placement -density 0.6)", "Warnings:",
             "Output tail (last 40 lines your script printed):", "Design state after your script",
             "Self-check findings:", "Diagnosis: " + HINTS["missing_prerequisite"], EXTRA_DOCS_HEADER,
             "Your script was run from the original starting state"]
    positions = [msg.index(s) for s in order]
    assert positions == sorted(positions)
    assert msg.count("[WARNING GPL-") == 8 and "DRT-0002" not in msg
    assert msg.endswith("Return the complete corrected script in a single tcl code block.")


# ------------------------------------------------------------------ episodes (real OpenROAD)
def test_mock_episode_repairs_hallucinated_command(task, executor, run_root):
    llm = MockLLM([answer(BAD_SCRIPT), answer(task.reference_tcl())])
    rec = run_episode(task, cfg("C_feedback", feedback=True, max_attempts=4), llm, None, executor, run_root, "t", 1)
    assert rec.error is None and rec.attempts_used == 2 and rec.llm_calls == 2
    a1, a2 = rec.attempts
    assert a1.error_type == "invalid_command" and a1.diagnosed_error_type == "invalid_command"
    assert a1.failing_line == 2 and not a1.exec_success and not a1.validator_passed and a1.agent_verdict_ok is False
    assert a2.error_type is None and a2.validator_passed and a2.agent_verdict_ok
    assert rec.success and not rec.first_attempt_success and rec.agent_declared_success
    assert rec.failed_executions == 1 and rec.final_error_type is None
    assert a1.run_dir.endswith("t/C_feedback/run1/DEV-EX-01/attempt1")
    assert a2.run_dir.endswith("t/C_feedback/run1/DEV-EX-01/attempt2")
    assert [c["purpose"] for c in llm.calls] == ["generate", "repair"]
    assert llm.calls[1]["cache_key"] == "t/C_feedback/run1/DEV-EX-01/attempt2"
    first, second = llm.calls[0]["messages"], llm.calls[1]["messages"]
    assert second[0] == first[0]  # append-only conversation
    assert second[1] == {"role": "assistant", "content": [{"type": "text", "text": answer(BAD_SCRIPT)}]}
    repair = second[2]["content"]
    assert repair.startswith("EXECUTION RESULT (attempt 1 of 4)\nFAILED: execution error\nError type: invalid_command")
    assert 'Error: invalid command name "create_floorplan"' in repair
    assert "(agent_script.tcl line 2: create_floorplan -utilization 35 -aspect_ratio 1.0 -core_space 5)" in repair
    assert HINTS["invalid_command"] in repair and DOCS_HEADER not in all_text(llm)
    assert not (run_root / "t/C_feedback/run1/DEV-EX-01/attempt1/final.odb").exists()  # cleaned after validation


def test_self_check_failure_triggers_repair(task, executor, run_root):
    llm = MockLLM([answer(NOOP_SCRIPT), answer(task.reference_tcl())])
    rec = run_episode(task, cfg("C_feedback", feedback=True, max_attempts=4), llm, None, executor, run_root, "t", 1)
    a1 = rec.attempts[0]
    assert a1.exec_success and a1.error_type is None and a1.diagnosed_error_type == "validation_failure"
    assert rec.success and rec.attempts_used == 2 and rec.failed_executions == 0
    repair = llm.calls[1]["messages"][-1]["content"]
    assert "FAILED: self-check\nError type: validation_failure" in repair
    assert "The task asks to initialize the floorplan" in repair and HINTS["validation_failure"] in repair


def test_single_shot_configurations_never_send_a_repair_message(task, executor, run_root):
    for config in (load_agent_config("A_baseline"), load_agent_config("B_rag")):
        assert not config.feedback and config.max_attempts == 1
        llm = MockLLM([answer(BAD_SCRIPT), answer(task.reference_tcl())])
        rec = run_episode(task, config, llm, doc_retriever(), executor, run_root, "t", 1)
        assert rec.attempts_used == 1 and rec.llm_calls == 1 and not rec.success
        assert rec.final_error_type == "invalid_command" and rec.agent_declared_success is False
        assert [c["purpose"] for c in llm.calls] == ["generate"]
        assert "EXECUTION RESULT" not in all_text(llm)


def test_documentation_sections_only_with_rag(task, executor, run_root):
    results = {}
    for name, rag, feedback, attempts in [("A", "none", False, 1), ("B", "hybrid", False, 1),
                                          ("C", "none", True, 4), ("D", "hybrid", True, 4)]:
        llm = MockLLM([answer(BAD_SCRIPT), answer(task.reference_tcl())])
        retriever = doc_retriever()
        rec = run_episode(task, cfg(name, rag, feedback, attempts), llm, retriever, executor, run_root, "t", 1)
        results[name] = (llm, retriever, rec)
    for name in "AC":
        llm, retriever, _ = results[name]
        assert DOCS_HEADER not in all_text(llm) and EXTRA_DOCS_HEADER not in all_text(llm)
        assert retriever.queries == []
    for name in "BD":
        llm, retriever, rec = results[name]
        first = llm.calls[0]["messages"][0]["content"]
        assert f"\n{DOCS_HEADER}\n" in first and "make_tracks creates routing tracks" in first
        assert retriever.queries[0][0] == " ".join(task.instruction.split())
        assert rec.attempts[0].retrieved_chunk_ids == ["doc-fp", "doc-tracks"]
    repair = results["D"][0].calls[1]["messages"][-1]["content"]
    assert EXTRA_DOCS_HEADER in repair and "doc-error" in repair
    assert "doc-fp" not in repair  # chunks already shown are not repeated
    assert results["D"][2].attempts[1].retrieved_chunk_ids == ["doc-error"]
    assert "invalid command" in results["D"][1].queries[1][0]



# ------------------------------------------------------------------ targeted repair retrieval
def syntax_cards() -> SyntaxCards:
    def card(name: str, text: str) -> SyntaxCard:
        return SyntaxCard(id=f"card-{name}", text=text, source="OpenROAD/src/x.tcl", section=name)
    return SyntaxCards({
        "initialize_floorplan": [card("initialize_floorplan", "initialize_floorplan [-utilization util] "
                                                              "[-aspect_ratio ratio] [-core_space space]")],
        "report_checks": [card("report_checks", "report_checks [-path_delay min|max] [-group_count count]")],
        "get_nets": [card("get_nets", "get_nets [-hierarchical] patterns")],
    })


def diag(error_type: str, message: str, command: str | None = None, tool_errors=()) -> Diagnosis:
    return Diagnosis(error_type=error_type, message=message, failing_line=3 if command else None,
                     failing_command_text=command, hint="", tool_errors=list(tool_errors))


def test_syntax_cards_for_diagnosis():
    cards = syntax_cards()
    missing = cards.for_diagnosis(diag("invalid_command", 'invalid command name "create_floorplan"',
                                       "create_floorplan -utilization 35"))
    assert missing.missing == "create_floorplan" and missing.commands == ["initialize_floorplan"]
    assert missing.text.startswith("`create_floorplan` is not a command in this OpenROAD version. "
                                   "Documented commands with similar names: `initialize_floorplan`.")
    assert TARGETED_HEADER in missing.text and "[-aspect_ratio ratio]" in missing.text
    assert missing.ids == ["card-initialize_floorplan"]
    nested = cards.for_diagnosis(diag("invalid_argument", "get_nets -filter is not a known keyword or flag.",
                                      'set n [get_nets -filter "x"]'))
    assert nested.commands == ["get_nets"] and nested.missing is None and "get_nets [-hierarchical]" in nested.text
    named = cards.for_diagnosis(diag("tool_error", "x", None, ["[ERROR STA-0402] report_checks -foo is not known"]))
    assert named.commands == ["report_checks"]
    unknown = cards.for_diagnosis(diag("invalid_command", 'invalid command name "mkdir"', "mkdir -p outputs"))
    assert unknown.cards == [] and unknown.text == "`mkdir` is not a command in this OpenROAD version."
    for etype in ("validation_failure", "unsafe_command"):
        assert cards.for_diagnosis(diag(etype, "get_nets", "get_nets x")).text == ""


def test_syntax_cards_from_knowledge_base():
    cards = SyntaxCards.load()
    assert len(cards) > 250 and "initialize_floorplan" in cards.by_command
    assert all(c.doc_type == "command_syntax" for cs in cards.by_command.values() for c in cs)


def test_targeted_repair_adds_card_only_to_its_configuration(task, executor, run_root):
    targeted = AgentConfig(name="G", rag="hybrid", feedback=True, max_attempts=4, final_k=2, targeted_repair=True,
                           first_attempt_from="D")
    repairs = {}
    for config in (cfg("D", "hybrid", True, 4), targeted):
        llm = MockLLM([answer(BAD_SCRIPT), answer(task.reference_tcl())])
        rec = run_episode(task, config, llm, doc_retriever(), executor, run_root, "t", 1, cards=syntax_cards())
        assert rec.success and rec.attempts_used == 2
        repairs[config.name] = (llm, rec)
    d_llm, _ = repairs["D"]
    g_llm, g_rec = repairs["G"]
    assert g_llm.calls[0]["cache_key"] == d_llm.calls[0]["cache_key"] == "t/D/run1/DEV-EX-01/attempt1"
    assert g_llm.calls[0]["messages"] == d_llm.calls[0]["messages"]       # identical first prompt -> same sample
    assert g_llm.calls[1]["cache_key"] == "t/G/run1/DEV-EX-01/attempt2"
    assert g_rec.attempts[0].run_dir.endswith("t/G/run1/DEV-EX-01/attempt1")
    d_repair, g_repair = d_llm.calls[1]["messages"][-1]["content"], g_llm.calls[1]["messages"][-1]["content"]
    assert TARGETED_HEADER not in d_repair and "is not a command in this OpenROAD version" not in d_repair
    assert "`create_floorplan` is not a command in this OpenROAD version." in g_repair
    assert g_repair.index(TARGETED_HEADER) < g_repair.index("doc-error")    # card first, then generic retrieval
    assert g_rec.attempts[1].retrieved_chunk_ids == ["card-initialize_floorplan", "doc-error"]
    missing_cards = run_episode(task, targeted, MockLLM([answer(BAD_SCRIPT)]), doc_retriever(), executor, run_root,
                                "t", 2)
    assert not missing_cards.success and "needs syntax cards" in missing_cards.error


def test_targeted_configuration_settings():
    g, d = load_agent_config("G_targeted_repair"), load_agent_config("D_full")
    assert g.targeted_repair and g.first_attempt_from == "D_full"
    assert (g.rag, g.feedback, g.max_attempts) == (d.rag, d.feedback, d.max_attempts)
    assert "targeted_repair" not in d.record() and "first_attempt_from" not in d.record()   # old metadata matches
    assert g.record()["targeted_repair"] is True and g.record()["first_attempt_from"] == "D_full"
    with pytest.raises(ValueError, match="needs retrieval and feedback"):
        AgentConfig(name="x", rag="none", feedback=True, max_attempts=4, targeted_repair=True)

def test_validator_results_never_reach_the_llm_or_control_flow(task, executor, run_root, monkeypatch):
    sentinel = "HIDDEN_VALIDATOR_SENTINEL_7f3a"

    def fake_validate(always: bool):
        def validate(task_, result, executor_):
            return ValidationResult(always, [Check(sentinel, always, f"{sentinel} detail")])
        return validate

    # The validator says PASS for everything: the agent must still repair after a failed self-check.
    monkeypatch.setattr(orchestrator, "validate", fake_validate(True))
    llm = MockLLM([answer(BAD_SCRIPT), answer(NOOP_SCRIPT), answer(task.reference_tcl())])
    rec = run_episode(task, cfg("D", "hybrid", True, 4), llm, doc_retriever(), executor, run_root, "pass", 1)
    assert rec.attempts_used == 3 and all(a.validator_passed for a in rec.attempts)
    assert [a.agent_verdict_ok for a in rec.attempts] == [False, False, True]
    assert sentinel not in all_text(llm) and "PASS (" not in all_text(llm)
    assert all(a.validator_summary.startswith("PASS") for a in rec.attempts)

    # The validator says FAIL for everything: the agent still stops when its self-check passes.
    monkeypatch.setattr(orchestrator, "validate", fake_validate(False))
    llm = MockLLM([answer(task.reference_tcl())])
    rec = run_episode(task, cfg("D", "hybrid", True, 4), llm, doc_retriever(), executor, run_root, "fail", 1)
    assert rec.attempts_used == 1 and rec.agent_declared_success and not rec.success
    assert sentinel in rec.attempts[0].validator_summary and sentinel not in all_text(llm)
    assert rec.final_error_type == "validation_failure"


def test_real_validator_output_never_reaches_the_llm(task, executor, run_root):
    llm = MockLLM([answer(BAD_SCRIPT), answer(NOOP_SCRIPT), answer(task.reference_tcl())])
    rec = run_episode(task, cfg("C", "none", True, 4), llm, None, executor, run_root, "t", 1)
    sent = all_text(llm)
    for a in rec.attempts:
        for part in a.validator_summary.replace("FAIL - ", "").split("; "):
            assert part not in sent
    for check_name in ("core_utilization", "rows_created", "core_to_die_margins", "routing_tracks_all_layers"):
        assert check_name not in sent


def test_llm_errors_are_recorded_and_fatal_errors_propagate(task, executor, run_root):
    def flaky(system, messages, purpose):
        if purpose == "repair":
            raise LLMError("overloaded after retries")
        return answer(BAD_SCRIPT)

    rec = run_episode(task, cfg("C", "none", True, 4), MockLLM(flaky), None, executor, run_root, "t", 1)
    assert rec.error == "LLMError: overloaded after retries" and not rec.success and rec.attempts_used == 1

    def broken(system, messages, purpose):
        raise LLMError("AuthenticationError (401): invalid x-api-key", fatal=True)

    with pytest.raises(LLMError):
        run_episode(task, cfg("C", "none", True, 4), MockLLM(broken), None, executor, run_root, "t", 2)


def test_rag_config_without_retriever_is_an_episode_error(task, executor, run_root):
    rec = run_episode(task, cfg("B", "hybrid"), MockLLM([answer(NOOP_SCRIPT)]), None, executor, run_root, "t", 1)
    assert rec.error and "needs a retriever" in rec.error and rec.attempts_used == 0 and not rec.success


# ------------------------------------------------------------------ LLM layer (no network)
def anthropic_message(content: list[dict], stop_reason: str = "end_turn") -> anthropic.types.Message:
    return anthropic.types.Message.model_validate({
        "id": "msg_test", "type": "message", "role": "assistant", "model": "example-model-1",
        "stop_reason": stop_reason, "stop_sequence": None, "content": content,
        "usage": {"input_tokens": 1000, "output_tokens": 500, "cache_read_input_tokens": 200,
                  "cache_creation_input_tokens": 100}})


class FakeAnthropicSDK:
    def __init__(self, outcome):
        self.outcome = outcome
        self.requests: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def test_anthropic_client_request_and_response():
    blocks = [{"type": "thinking", "thinking": "", "signature": "c2lnbmF0dXJl"},
              {"type": "text", "text": "Assumption.\n```tcl\nputs a\n"}, {"type": "text", "text": "```"}]
    sdk = FakeAnthropicSDK(anthropic_message(blocks))
    client = AnthropicClient("example-model-1", max_tokens=16000, effort="medium", thinking="adaptive", client=sdk)
    msgs = [{"role": "user", "content": "TASK\nx"}]
    resp = client.complete("SYSTEM", msgs, purpose="generate")
    req = sdk.requests[0]
    assert set(req) == {"model", "max_tokens", "messages", "system", "thinking", "output_config"}
    assert req["thinking"] == {"type": "adaptive"} and req["output_config"] == {"effort": "medium"}
    assert req["system"] == [{"type": "text", "text": "SYSTEM", "cache_control": {"type": "ephemeral"}}]
    assert req["messages"] is msgs
    assert resp.assistant_content == blocks  # thinking block included, unchanged
    assert extract_tcl(resp.text) == "puts a\n"
    call = resp.call
    assert (call.provider, call.model_requested, call.model_reported) == ("anthropic", "example-model-1",
                                                                          "example-model-1")
    assert (call.input_tokens, call.output_tokens, call.cache_read_tokens, call.cache_write_tokens) == (1000, 500,
                                                                                                         200, 100)
    assert call.cost_usd == 0.0  # no price configured for the example model
    assert call.stop_reason == "end_turn" and call.effort == "medium" and not call.cached
    assert can_continue(resp)


def test_anthropic_client_refusal_and_errors():
    sdk = FakeAnthropicSDK(anthropic_message([], stop_reason="refusal"))
    client = AnthropicClient("example-model-1", max_tokens=100, effort=None, thinking=None,
                             use_prompt_cache=False, client=sdk)
    resp = client.complete("SYSTEM", [{"role": "user", "content": "x"}], purpose="generate")
    assert resp.call.stop_reason == "refusal" and resp.text == "" and not can_continue(resp)
    assert sdk.requests[0]["system"] == "SYSTEM" and "thinking" not in sdk.requests[0]
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    limited = anthropic.RateLimitError("slow down", response=httpx2.Response(429, request=request), body=None)
    with pytest.raises(LLMError) as err:
        AnthropicClient("m", max_tokens=1, effort=None, thinking=None, client=FakeAnthropicSDK(limited)).complete(
            "s", [], purpose="generate")
    assert not err.value.fatal and "rate limited" in str(err.value)
    denied = anthropic.AuthenticationError("bad key", response=httpx2.Response(401, request=request), body=None)
    with pytest.raises(LLMError) as err:
        AnthropicClient("m", max_tokens=1, effort=None, thinking=None, client=FakeAnthropicSDK(denied)).complete(
            "s", [], purpose="generate")
    assert err.value.fatal
    offline = anthropic.APIConnectionError(request=request)
    with pytest.raises(LLMError) as err:
        AnthropicClient("m", max_tokens=1, effort=None, thinking=None, client=FakeAnthropicSDK(offline)).complete(
            "s", [], purpose="generate")
    assert not err.value.fatal


def test_openai_compatible_client():
    from openai.types.chat import ChatCompletion

    completion = ChatCompletion.model_validate({
        "id": "c1", "object": "chat.completion", "created": 1, "model": "llama-x",
        "choices": [{"index": 0, "finish_reason": "length", "message": {"role": "assistant", "content": "```tcl\n"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 7, "total_tokens": 107,
                  "prompt_tokens_details": {"cached_tokens": 40}}})

    class SDK:
        def __init__(self):
            self.requests = []
            self.chat = self
            self.completions = self

        def create(self, **kwargs):
            self.requests.append(kwargs)
            return completion

    sdk = SDK()
    client = OpenAICompatClient("llama-x", max_tokens=512, client=sdk)
    history = [{"role": "user", "content": "TASK"},
               {"role": "assistant", "content": [{"type": "thinking", "thinking": "t"}, {"type": "text", "text": "A"}]},
               {"role": "user", "content": "REPAIR"}]
    resp = client.complete("SYSTEM", history, purpose="repair")
    req = sdk.requests[0]
    assert req["messages"][0] == {"role": "system", "content": "SYSTEM"}
    assert req["messages"][2] == {"role": "assistant", "content": "A"}
    assert req["max_tokens"] == 512 and "temperature" not in req
    assert resp.assistant_content == [{"type": "text", "text": "```tcl\n"}]
    assert (resp.call.input_tokens, resp.call.cache_read_tokens, resp.call.output_tokens) == (60, 40, 7)
    assert resp.call.stop_reason == "max_tokens"
    assert resp.call.seed is None and resp.call.sampling is None and resp.call.thinking is None


class FakeChatSDK:
    """Stand-in for ``openai.OpenAI`` returning a llama-server style completion."""

    def __init__(self, content: str = "Assumption.\n```tcl\nputs a\n```", model: str = "qwen3.6-35b-a3b-q4_k_m"):
        from openai.types.chat import ChatCompletion

        self.completion = ChatCompletion.model_validate({
            "id": "chatcmpl-1", "object": "chat.completion", "created": 1, "model": model,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content,
                                     "reasoning_content": "SECRET REASONING"}}],
            "usage": {"prompt_tokens": 900, "completion_tokens": 300, "total_tokens": 1200}})
        self.requests: list[dict] = []
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.completion


def test_local_client_sampling_seed_and_thinking():
    sdk = FakeChatSDK()
    sampling = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0, "presence_penalty": 0.0}
    client = OpenAICompatClient("qwen3.6-35b-a3b-q4_k_m", max_tokens=8192, sampling=sampling, enable_thinking=False,
                                seed_per_call=True, provider="local", client=sdk)
    key = "exp/D_full/run1/DEV-EX-01/attempt1"
    resp = client.complete("SYSTEM", [{"role": "user", "content": "TASK"}], purpose="generate", cache_key=key)
    req = sdk.requests[0]
    assert (req["temperature"], req["top_p"], req["presence_penalty"]) == (0.7, 0.8, 0.0)
    assert req["extra_body"] == {"top_k": 20, "min_p": 0.0, "chat_template_kwargs": {"enable_thinking": False}}
    assert "top_k" not in req and "min_p" not in req
    expected_seed = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    assert req["seed"] == expected_seed == call_seed(key)
    assert resp.text == "Assumption.\n```tcl\nputs a\n```" and "SECRET" not in json.dumps(resp.assistant_content)
    call = resp.call
    assert (call.provider, call.thinking, call.seed, call.cost_usd) == ("local", "disabled", expected_seed, 0.0)
    assert call.sampling == sampling and call.stop_reason == "end_turn"
    # other run / attempt -> other seed; no cache_key -> no seed
    client.complete("SYSTEM", [{"role": "user", "content": "TASK"}], purpose="generate",
                    cache_key="exp/D_full/run2/DEV-EX-01/attempt1")
    client.complete("SYSTEM", [{"role": "user", "content": "TASK"}], purpose="generate")
    assert sdk.requests[1]["seed"] != expected_seed and "seed" not in sdk.requests[2]
    thinking = OpenAICompatClient("m", max_tokens=10, enable_thinking=True, client=FakeChatSDK())
    assert thinking.thinking == "enabled" and thinking.request("S", [])["extra_body"] == {
        "chat_template_kwargs": {"enable_thinking": True}}
    with pytest.raises(ValueError):
        OpenAICompatClient("m", max_tokens=10, sampling={"top_a": 1.0}, client=FakeChatSDK())


def test_make_llm_local_provider(caplog):
    from common.config import load_config

    loc = load_config("model_config")["local_llm"]
    assert load_config("model_config")["provider"] == "local"
    llm = make_llm()  # the default provider; constructing the client makes no request
    inner = llm.inner
    assert isinstance(llm, ReplayCache) and llm.enabled and isinstance(inner, OpenAICompatClient)
    assert (inner.provider, inner.model, inner.base_url, inner.max_tokens) == (
        "local", loc["model"], loc["base_url"], loc["max_tokens"])
    assert inner.thinking == "disabled" and inner.seed_per_call and inner.sampling == loc["sampling"]
    assert inner.client.api_key == "local"
    settings = llm.settings()
    assert settings["sampling"] == loc["sampling"] and settings["seed"] == "per_call"
    with caplog.at_level(logging.WARNING):
        assert cost_usd(loc["model"], 10_000, 10_000) == 0.0
    assert "no pricing" not in caplog.text
    with pytest.raises(ValueError, match="unknown LLM provider"):
        make_llm({"provider": "nope"})


def test_replay_cache_separates_sampling_settings(run_root):
    msgs = [{"role": "user", "content": "hello"}]
    key = "exp/A/run1/T/attempt1"
    hot = ReplayCache(OpenAICompatClient("m", max_tokens=10, sampling={"temperature": 0.7},
                                         client=FakeChatSDK("```tcl\nputs hot\n```")), run_root / "llm_cache")
    cold = ReplayCache(OpenAICompatClient("m", max_tokens=10, sampling={"temperature": 0.1},
                                          client=FakeChatSDK("```tcl\nputs cold\n```")), run_root / "llm_cache")
    assert hot.complete("S", msgs, purpose="generate", cache_key=key).text.endswith("hot\n```")
    again = hot.complete("S", msgs, purpose="generate", cache_key=key)
    assert again.call.cached and again.call.sampling == {"temperature": 0.7} and again.call.seed is None
    assert not cold.complete("S", msgs, purpose="generate", cache_key=key).call.cached


def test_local_server_metadata_and_defaults(monkeypatch):
    import http.server
    import threading

    from experiments import run_experiment

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = {"/v1/models": {"object": "list", "data": [{"id": "qwen3.6-35b-a3b-q4_k_m"}]},
                    "/props": {"total_slots": 4, "chat_template": "{{ messages }}", "build_info": "b11829"}
                    }.get(self.path)
            self.send_response(200 if body else 404)
            self.end_headers()
            self.wfile.write(json.dumps(body or {}).encode())

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        info = run_experiment.local_server_info(f"http://127.0.0.1:{server.server_address[1]}/v1")
    finally:
        server.shutdown()
        server.server_close()
    assert info["models"]["data"][0]["id"] == "qwen3.6-35b-a3b-q4_k_m"
    assert info["props"] == {"total_slots": 4, "build_info": "b11829"} and info["chat_template_sha256"]
    assert run_experiment.default_parallel("local") == 6
    assert run_experiment.default_parallel("mock") >= 1

    def unreachable(url):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(run_experiment, "local_server_info", unreachable)
    with pytest.raises(SystemExit, match="llm_server.sh start"):
        run_experiment.main(["--config", "A_baseline", "--runs", "1", "--split", "dev", "--provider", "local",
                             "--experiment-id", f"pytest-{uuid.uuid4().hex[:8]}"])


def test_replay_cache(run_root):
    inner = MockLLM(["first", "second", "third"])
    cache = ReplayCache(inner, run_root / "llm_cache")
    msgs = [{"role": "user", "content": "hello"}]
    a = cache.complete("S", msgs, purpose="generate", cache_key="exp/A/run1/T/attempt1")
    b = cache.complete("S", msgs, purpose="generate", cache_key="exp/A/run1/T/attempt1")
    c = cache.complete("S", msgs, purpose="generate", cache_key="exp/A/run2/T/attempt1")  # other run: new sample
    d = cache.complete("S", msgs, purpose="generate", cache_key=None)  # unkeyed calls are never cached
    assert (a.text, b.text, c.text, d.text) == ("first", "first", "second", "third")
    assert not a.call.cached and b.call.cached and not c.call.cached and not d.call.cached
    assert b.assistant_content == a.assistant_content and len(inner.calls) == 3
    assert len(list((run_root / "llm_cache" / "exp").rglob("*.json"))) == 2
    fresh = ReplayCache(MockLLM(["other"]), run_root / "llm_cache")  # e.g. a resumed process
    assert fresh.complete("S", msgs, purpose="generate", cache_key="exp/A/run1/T/attempt1").call.cached
    effortful = ReplayCache(replace_effort(MockLLM(["x"]), "high"), run_root / "llm_cache")
    assert not effortful.complete("S", msgs, purpose="generate", cache_key="exp/A/run1/T/attempt1").call.cached


def replace_effort(llm: MockLLM, effort: str) -> MockLLM:
    llm.effort = effort
    return llm


def test_cost_and_factory(caplog):
    prices = {"m": {"input": 1.0, "output": 2.0, "cache_read": 0.1, "cache_write": 1.25}}
    assert cost_usd("m", 1_000_000, 500_000, 2_000_000, 400_000, pricing=prices) == pytest.approx(2.7)
    with caplog.at_level(logging.WARNING):
        assert cost_usd("unknown-model-xyz", 10, 10) == 0.0
    assert "unknown-model-xyz" in caplog.text
    llm = make_llm({"provider": "mock", "mock_responses": ["```tcl\nputs 1\n```"]})
    assert isinstance(llm, ReplayCache) and not llm.enabled and isinstance(llm.inner, MockLLM)
    assert llm.complete("S", [{"role": "user", "content": "x"}], purpose="generate", cache_key="k").text.startswith(
        "```tcl")
    assert llm.settings()["provider"] == "mock"


# ------------------------------------------------------------------ experiment runner (mock provider)
def test_run_experiment_resumes_and_guards_settings(capsys):
    from experiments import run_experiment

    exp_id = f"pytest-{uuid.uuid4().hex[:8]}"
    out_dir = RESULTS_DIR / exp_id
    argv = ["--config", "A_baseline", "C_feedback", "--runs", "1", "--split", "dev", "--tasks", "DEV-EX-01", "--provider", "mock",
            "--experiment-id", exp_id, "--parallel", "2"]
    try:
        assert run_experiment.main(argv) == 0
        records = [r for name in ("A_baseline", "C_feedback") for r in read_jsonl(out_dir / f"{name}.jsonl")]
        assert len(records) == 2 and all(r["success"] and r["error"] is None for r in records)
        meta = json.loads((out_dir / "metadata.json").read_text())
        assert meta["llm"]["provider"] == "mock" and meta["task_set_hash"] and meta["end"]
        assert meta["openroad"]["version"] and meta["sessions"][0]["status"] == "completed"
        assert run_experiment.main(argv) == 0  # resume: nothing left to run
        assert "0 to run, 2 already recorded" in capsys.readouterr().out
        assert sum(1 for name in ("A_baseline", "C_feedback") for _ in read_jsonl(out_dir / f"{name}.jsonl")) == 2
        with pytest.raises(SystemExit, match="different settings"):
            run_experiment.main(argv + ["--model", "another-model"])
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
        shutil.rmtree(RUNS_DIR / exp_id, ignore_errors=True)
