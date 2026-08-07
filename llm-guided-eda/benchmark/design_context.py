"""Agent-facing description of the execution environment and design state.

The same context is given to every experimental configuration; only the
retrieved documentation and execution feedback differ between configurations.
"""
from __future__ import annotations

from common.config import load_config
from benchmark.states import StateSpec, get_state

PLATFORM_FACTS = """\
- Technology: Nangate45 (FreePDK45); 10 routing layers metal1 ... metal10.
- Standard-cell site: FreePDK45_38x28_10R_NP_162NW_34O (row height 1.4 um, site width 0.19 um).
- Tap/endcap cell: TAPCELL_X1. Filler cells: FILLCELL_X1 ... FILLCELL_X32 (pattern FILLCELL*).
- Tie cells: LOGIC0_X1 (output pin Z), LOGIC1_X1 (output pin Z). Buffers BUF_X1 ... BUF_X32,
  inverters INV_X1 ... INV_X32, clock buffers CLKBUF_X1 ... CLKBUF_X3.
- Platform flow defaults: IO pins on metal3 (horizontal) and metal2 (vertical); signal routing on
  metal2-metal10 and clock routing on metal6-metal10 with a 0.5 global-routing layer adjustment;
  CTS buffer BUF_X4; global placement density 0.3.
- Platform files (relative to the working directory):
    platform/Nangate45_tech.lef, platform/Nangate45_stdcell.lef,
    platform/Nangate45_typ.lib, platform/Nangate45_fast.lib, platform/Nangate45_slow.lib,
    platform/Nangate45.rc (set_layer_rc commands), platform/Nangate45.tracks (make_tracks commands),
    platform/Nangate45.pdn.tcl (pdngen configuration), platform/Nangate45.rcx_rules (RC extraction rules)
- Design files: design/gcd.v (synthesized gate-level netlist), design/gcd.sdc (timing constraints)."""


def design_context(state: StateSpec | str) -> str:
    st = get_state(state) if isinstance(state, str) else state
    version = load_config("openroad_config")["openroad_version"]
    loaded = "\n".join(f"- {item}" for item in st.loaded_items())
    return f"""\
ENVIRONMENT
- Tool: OpenROAD {version} (a November 2023 build) with its Tcl command interpreter.
- Your Tcl script is executed with `source` inside an OpenROAD session that has ALREADY loaded the
  design and libraries listed below. Do not reload them unless the task explicitly requires it.
- The working directory is a scratch run directory. Use relative paths. Write every requested output
  file into the outputs/ directory using exactly the file name given in the task.
- The script runs non-interactively (no GUI). External programs, sockets and `cd` are not allowed.

DESIGN
- gcd (greatest-common-divisor accelerator), top module `gcd`, about 350 standard cells,
  54 IO ports, single clock port `clk`.

CURRENT DESIGN STATE: {st.stage}
{st.description}

ALREADY LOADED IN THE SESSION
{loaded}

PLATFORM
{PLATFORM_FACTS}
"""
