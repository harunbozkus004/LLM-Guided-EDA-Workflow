"""Benchmark starting states (gcd / Nangate45) and how each one is loaded.

States are immutable ODB snapshots built once by ``build_states.tcl``. Every
benchmark attempt runs against a fresh copy of its starting state, so attempts
are independent and failed attempts are rolled back automatically.

    python -m benchmark.states build     # (re)build snapshots + baseline probes
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from common.config import load_config, resolve
from common.paths import STATES_DIR

ODB_DIR = STATES_DIR
PLATFORM_DIR = resolve(load_config("openroad_config")["platform_dir"])
DESIGN_DIR = resolve(load_config("openroad_config")["design_dir"])

COMMON_LOADED = [
    "Liberty timing library platform/Nangate45_typ.lib (typical corner)",
    "SDC constraints design/gcd.sdc (clock core_clock on port clk, period 0.485 ns, 20% IO delays)",
    "Per-layer RC values from platform/Nangate45.rc; set_wire_rc -signal -layer metal3; set_wire_rc -clock -layer metal6",
    "set_dont_use {CLKBUF_* AOI211_X1 OAI211_X1}",
]


@dataclass(frozen=True)
class StateSpec:
    name: str
    stage: str
    description: str
    propagated_clock: bool = False

    @property
    def odb(self) -> Path:
        return ODB_DIR / f"{self.name}.odb"

    @property
    def baseline_probe(self) -> Path:
        return ODB_DIR / f"{self.name}.probe.json"

    def links(self) -> dict[str, Path]:
        return {"platform": PLATFORM_DIR, "design": DESIGN_DIR, f"inputs/{self.name}.odb": self.odb}

    def preamble(self, db_path: str | None = None) -> str:
        db = db_path or f"inputs/{self.name}.odb"
        lines = [
            "read_liberty platform/Nangate45_typ.lib",
            f"read_db {db}",
            "read_sdc design/gcd.sdc",
            "source platform/Nangate45.rc",
            "set_wire_rc -signal -layer metal3",
            "set_wire_rc -clock -layer metal6",
            "set_dont_use {CLKBUF_* AOI211_X1 OAI211_X1}",
        ]
        if self.propagated_clock:
            lines.append("set_propagated_clock [all_clocks]")
        return "\n".join(lines)

    def loaded_items(self) -> list[str]:
        items = [f"Design database for stage '{self.stage}'"] + COMMON_LOADED
        if self.propagated_clock:
            items.append("set_propagated_clock [all_clocks] (clock tree exists)")
        return items


STATES: dict[str, StateSpec] = {s.name: s for s in [
    StateSpec("synth", "synthesized netlist",
              "Synthesized gcd netlist is linked. There is NO floorplan yet: no die/core area, "
              "no placement rows, no routing tracks, no IO pin placement, no cell placement."),
    StateSpec("fp_init", "floorplan initialized",
              "Floorplan initialized: die (0,0)-(100.13,100.8) um, core (10.07,11.2)-(90.25,91) um, "
              "57 placement rows of site FreePDK45_38x28_10R_NP_162NW_34O, routing tracks for metal1-metal10. "
              "IO pins are NOT placed, no tap cells, no power grid, standard cells are unplaced."),
    StateSpec("floorplan", "floorplan complete",
              "Floorplan complete: die/core/rows/tracks defined, synthesis buffers removed, IO pins placed "
              "(random, metal3 horizontal / metal2 vertical), tap/endcap cells (TAPCELL_X1) inserted and the "
              "VDD/VSS power grid built with pdngen. Standard cells are NOT placed yet."),
    StateSpec("gplaced", "global placement done",
              "Floorplan complete and global placement done (routability-driven, target density 0.3); IO pins "
              "re-placed with place_pins. Cells are NOT legalized: detailed placement has not been run."),
    StateSpec("placed", "placement complete (pre-CTS)",
              "Global placement, design repair (repair_design, tie-cell fanout repair) and legal detailed "
              "placement are done. No clock tree has been built (the clock is ideal). Not routed."),
    StateSpec("cts", "clock tree synthesized",
              "Placement complete and clock tree synthesized with clock_tree_synthesis (BUF_X4 buffers), then "
              "legalized. Post-CTS timing repair has NOT been run. The design is not routed.",
              propagated_clock=True),
    StateSpec("grouted", "global routing done",
              "Post-CTS timing repair and detailed placement are done and the design is globally routed "
              "(route guides are stored in the database). Detailed routing has NOT been run; no filler cells.",
              propagated_clock=True),
    StateSpec("routed", "detailed routing done",
              "The design is fully placed, clock-tree synthesized, globally and detailed routed (0 DRC "
              "violations) and filler cells are inserted.",
              propagated_clock=True),
]}


def get_state(name: str) -> StateSpec:
    if name not in STATES:
        raise KeyError(f"unknown starting state '{name}'; known: {sorted(STATES)}")
    return STATES[name]


def load_baseline_probe(name: str) -> dict:
    path = get_state(name).baseline_probe
    return json.loads(path.read_text()) if path.exists() else {}


# ---------------------------------------------------------------- building
def build(force: bool = False) -> None:
    from openroad.executor import OpenROADExecutor

    executor = OpenROADExecutor()
    if force or not all(s.odb.exists() for s in STATES.values()):
        work = STATES_DIR / "_build"
        shutil.rmtree(work, ignore_errors=True)
        (work / "states").mkdir(parents=True)
        (work / "platform").symlink_to(PLATFORM_DIR)
        (work / "design").symlink_to(DESIGN_DIR)
        shutil.copyfile(STATES_DIR / "build_states.tcl", work / "build_states.tcl")
        print("[states] running build_states.tcl ...", flush=True)
        log = open(work / "build.log", "w")
        rc = subprocess.run([str(executor.openroad_bin), "-no_init", "-no_splash", "-exit", "build_states.tcl"],
                            cwd=work, stdout=log, stderr=subprocess.STDOUT,
                            env={"HOME": str(work), "PATH": "/usr/bin:/bin", "LANG": "C"}).returncode
        log.close()
        if rc != 0 or "BUILD_STATES done" not in (work / "build.log").read_text():
            sys.exit(f"build_states.tcl failed; see {work / 'build.log'}")
        for s in STATES.values():
            shutil.copyfile(work / "states" / f"{s.name}.odb", s.odb)
        shutil.copyfile(work / "build.log", STATES_DIR / "build_states.log")
        shutil.rmtree(work)

    # Baseline probes: run the harness with an empty agent script in each state.
    for s in STATES.values():
        run_dir = STATES_DIR / "_probe" / s.name
        shutil.rmtree(run_dir, ignore_errors=True)
        res = executor.run("# empty script: baseline probe\n", run_dir, preamble=s.preamble(), links=s.links())
        if not res.success or res.probe is None:
            sys.exit(f"baseline probe failed for state {s.name}: {res.error_message}\n{res.stdout[-3000:]}")
        s.baseline_probe.write_text(json.dumps(res.probe, indent=1, sort_keys=True))
        p = res.probe
        print(f"[states] {s.name:10s} rows={p['row_count']:3d} insts={p['inst_count']:4d} "
              f"placed={p['logic_placed_count']:4d}/{p['logic_inst_count']:4d} "
              f"io={p['io_pins_placed']}/{p['io_pin_count']} ck_nets={p['clock_sink_net_count']} "
              f"guided={p['guided_net_count']} routed={p['routed_net_count']}/{p['routable_net_count']} "
              f"util={p['utilization']} legal={p['placement_legal']} ({res.execution_time:.1f}s)")
    shutil.rmtree(STATES_DIR / "_probe", ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    build(force=args.force)
