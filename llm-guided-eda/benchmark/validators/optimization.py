"""Validators for the optimization category (design / timing repair, port buffering).

Every repair outcome is measured by trusted oracle sessions, never by the
agent's own session: the oracle preamble reloads the original SDC (so relaxed
constraints cannot fake success), re-establishes placement-based parasitics for
the placement being measured, and re-applies any design rules the task states.
Baseline values come from the same queries on the untouched starting state.

Netlist guards use a buffer-transparent connectivity signature: for every
non-buffer driver (cell output pin or input port) the leaf sinks (cell input
pins and output ports) reached through buffer chains, compared per sink cell.
Inserting, removing or resizing buffers, resizing gates, swapping commutative
pins and gate cloning leave it unchanged; disconnecting, re-wiring or tying
off loads and deleting cells do not.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from benchmark.task_validator import Check, ValidationContext, register
from benchmark.validators.common import all_logic_placed, check, netlist_intact, placement_legal

# Connectivity signature of the database (emits a flat dict):
#   M|<inst>                         -> master of every non-buffer logic cell
#   L|<inst>/<pin> or L|PORT:<name>  -> leaf sinks reached through buffers
#   P|<port>                         -> INPUT|<#sinks>|<sink masters> or OUTPUT|<driver inst>:<master>
#   C|<register clock pin>           -> driver chain back to the clock port
#   fanout_max, fanout_max_net       -> largest cell-input fanout of a signal net (clock nets excluded)
SIGNATURE_TCL = r"""
set __blk [ord::get_db_block]
array set ::__sig_clknets {}
proc __sig_is_buf {inst} { return [string match {*BUF_X*} [[$inst getMaster] getName]] }
proc __sig_driver {net} {
  foreach it [$net getITerms] { if {[$it getIoType] == "OUTPUT"} { return $it } }
  return ""
}
proc __sig_leaves {net depth} {
  set out {}
  if {$depth > 64} { return [list "LOOP"] }
  foreach it [$net getITerms] {
    if {[$it getIoType] != "INPUT"} { continue }
    set inst [$it getInst]
    if {[__sig_is_buf $inst]} {
      foreach oit [$inst getITerms] {
        if {[$oit getIoType] == "OUTPUT" && [$oit getNet] != "NULL"} {
          lappend out {*}[__sig_leaves [$oit getNet] [expr {$depth + 1}]]
        }
      }
    } else {
      lappend out "[$inst getName]/[[$it getMTerm] getName]"
    }
  }
  foreach bt [$net getBTerms] { if {[$bt getIoType] == "OUTPUT"} { lappend out "PORT:[$bt getName]" } }
  return $out
}
proc __sig_chain {net} {
  set chain {}
  for {set i 0} {$i < 64} {incr i} {
    set ::__sig_clknets([$net getName]) 1
    set drv [__sig_driver $net]
    if {$drv == ""} {
      set src "UNDRIVEN"
      foreach bt [$net getBTerms] { if {[$bt getIoType] == "INPUT"} { set src "PORT:[$bt getName]" } }
      lappend chain $src
      break
    }
    set inst [$drv getInst]
    lappend chain "[$inst getName]:[[$inst getMaster] getName]"
    set ins {}
    foreach it [$inst getITerms] { if {[$it getIoType] == "INPUT" && [$it getNet] != "NULL"} { lappend ins $it } }
    if {[llength $ins] != 1} { break }
    set net [[lindex $ins 0] getNet]
  }
  return [join $chain ">"]
}
set __d [dict create]
foreach inst [$__blk getInsts] {
  set m [$inst getMaster]
  if {[$m isFiller] || [$m getType] == "CORE_WELLTAP"} { continue }
  set isbuf [__sig_is_buf $inst]
  if {!$isbuf} { dict set __d "M|[$inst getName]" [$m getName] }
  foreach it [$inst getITerms] {
    set net [$it getNet]
    if {[$it getIoType] == "OUTPUT" && !$isbuf && $net != "NULL"} {
      dict set __d "L|[$inst getName]/[[$it getMTerm] getName]" [join [lsort [__sig_leaves $net 0]] " "]
    }
  }
}
foreach bt [$__blk getBTerms] {
  set net [$bt getNet]
  if {$net == "NULL"} { dict set __d "P|[$bt getName]" "[$bt getIoType]|unconnected"; continue }
  if {[$bt getIoType] == "INPUT"} {
    dict set __d "L|PORT:[$bt getName]" [join [lsort [__sig_leaves $net 0]] " "]
    set sinks {}
    foreach it [$net getITerms] { if {[$it getIoType] == "INPUT"} { lappend sinks [[[$it getInst] getMaster] getName] } }
    dict set __d "P|[$bt getName]" "INPUT|[llength $sinks]|[join [lsort $sinks] ,]"
  } else {
    set drv [__sig_driver $net]
    set dn [expr {$drv == "" ? "none" : "[[$drv getInst] getName]:[[[$drv getInst] getMaster] getName]"}]
    dict set __d "P|[$bt getName]" "[$bt getIoType]|$dn"
  }
}
foreach pin [all_registers -clock_pins] {
  set name [get_full_name $pin]
  set it [$__blk findITerm $name]
  if {$it == "NULL" || [$it getNet] == "NULL"} { dict set __d "C|$name" "UNCONNECTED"; continue }
  dict set __d "C|$name" [__sig_chain [$it getNet]]
}
set __fo 0; set __fo_net ""
foreach net [$__blk getNets] {
  if {[$net getSigType] in {POWER GROUND} || [info exists ::__sig_clknets([$net getName])]} { continue }
  set n 0
  foreach it [$net getITerms] { if {[$it getIoType] == "INPUT"} { incr n } }
  if {$n > $__fo} { set __fo $n; set __fo_net [$net getName] }
}
dict set __d fanout_max $__fo
dict set __d fanout_max_net $__fo_net
__oracle_emit_dict $__d
"""

# Timing with the original SDC (preamble) and fresh placement parasitics, plus the
# number of timing endpoints that still have a constrained setup / hold check.
TIMING_TCL = r"""
estimate_parasitics -placement
set __n 0; set __cmax 0; set __cmin 0
foreach p [concat [all_registers -data_pins] [all_outputs]] {
  incr __n
  set s [get_property $p slack_max]
  if {[string is double -strict $s] && abs($s) < 1e20} { incr __cmax }
  set s [get_property $p slack_min]
  if {[string is double -strict $s] && abs($s) < 1e20} { incr __cmin }
}
__oracle_emit_dict [dict create wns [sta::worst_slack -max] tns [sta::total_negative_slack -max] \
  whs [sta::worst_slack -min] ths [sta::total_negative_slack -min] \
  endpoints $__n constrained_max $__cmax constrained_min $__cmin]
"""

# Violating-pin counts under the design rules a task states (same checks as report_check_types).
DRV_TCL = r"""
set_max_transition @SLEW@ [current_design]
set_max_capacitance @CAP@ [current_design]
set_max_fanout @FANOUT@ [current_design]
estimate_parasitics -placement
__oracle_emit_dict [dict create max_slew [llength [sta::check_slew_limits NULL 1 NULL max]] \
  max_capacitance [llength [sta::check_capacitance_limits NULL 1 NULL max]] \
  max_fanout [llength [sta::check_fanout_limits NULL 1 max]]]
"""

DRV_KEYS = ("max_slew", "max_capacitance", "max_fanout")


# ------------------------------------------------------------------ helpers
def _oracle(ctx: ValidationContext, body: str, name: str,
            baseline: bool = False) -> tuple[dict[str, Any] | None, str]:
    """Run an oracle query; never raises (missing final.odb, crashed session, ...)."""
    try:
        data = ctx.query_baseline(body, name=name) if baseline else ctx.query(body, name=name)
        return data, ""
    except Exception as e:  # noqa: BLE001 - any oracle failure is a failed check
        msg = str(e).strip().splitlines()
        return None, f"{type(e).__name__}: {msg[0] if msg else ''}"[:200]


def _pair(ctx: ValidationContext, body: str, name: str) -> tuple[dict | None, dict | None, Check | None]:
    """(final, baseline) results of one oracle body, or a failing Check."""
    final, err = _oracle(ctx, body, name)
    base, berr = _oracle(ctx, body, name, baseline=True)
    if final is None or base is None:
        return None, None, check(f"oracle:{name}", False, err or berr)
    return final, base, None


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return None if math.isnan(v) or math.isinf(v) else float(v)


def _fmt(v: float | None, digits: int = 4) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}"


def _cnt(v: float | None) -> str:
    return "n/a" if v is None else str(int(v))


def _leaves(sig: dict[str, Any]) -> dict[str, list[str]]:
    return {k[2:]: str(v).split() for k, v in sig.items() if k.startswith("L|")}


def _inst(sink: str) -> str:
    return sink if sink.startswith("PORT:") else sink.rsplit("/", 1)[0]


def _port_driver(entry: Any) -> str:
    """Driver instance name of an ``OUTPUT|<inst>:<master>`` port entry."""
    return str(entry).split("|", 1)[-1].split(":", 1)[0]


def _family(master: str) -> str:
    return re.sub(r"_X\d+$", "", master)


def _logic_preserved(base_sig: dict, final_sig: dict) -> Check:
    """Every original driver still reaches the same sink cells; buffers are transparent.

    Sinks are compared per cell with multiplicity, so resizing and swapping commutative
    input pins (repair_timing) pass, while a master swap to another function family is
    rejected. A new non-buffer cell is accepted only as a gate clone (same function family
    and same input drivers as an original cell); the sinks of a cloned gate may then be
    split between the original and its clones. Inverter pairs are not treated as buffers
    (no repair command of this build inserts them).
    """
    base, final = _leaves(base_sig), _leaves(final_sig)
    bm = {k[2:]: str(v) for k, v in base_sig.items() if k.startswith("M|")}
    fm = {k[2:]: str(v) for k, v in final_sig.items() if k.startswith("M|")}
    problems: list[str] = [] if base else ["no drivers in the starting-state signature"]
    removed = sorted(set(bm) - set(fm))
    if removed:
        problems.append(f"{len(removed)} logic cells removed (e.g. {removed[0]})")
    # Connectivity alone cannot see a master swap to another function (e.g. NAND2 -> NOR2).
    swapped = sorted(i for i in set(bm) & set(fm) if _family(bm[i]) != _family(fm[i]))
    if swapped:
        problems.append(f"{len(swapped)} cells changed function (e.g. {swapped[0]}: "
                        f"{bm[swapped[0]]} -> {fm[swapped[0]]})")
    feeds: dict[str, set[str]] = {}
    for d, sinks in final.items():
        for s in sinks:
            feeds.setdefault(_inst(s), set()).add(d)
    clones: dict[str, str] = {}
    foreign: list[str] = []
    for n in sorted(set(fm) - set(bm)):
        orig = [i for i in sorted(bm) if i in fm and _family(fm[i]) == _family(fm[n])
                and feeds.get(i) == feeds.get(n)]
        if orig:
            clones[n] = orig[0]
        else:
            foreign.append(f"{n} ({fm[n]})")
    if foreign:
        problems.append(f"{len(foreign)} new logic cells are neither buffers nor gate clones "
                        f"(e.g. {', '.join(foreign[:3])})")
    clones_of: dict[str, list[str]] = {}
    for n, i in clones.items():
        clones_of.setdefault(i, []).append(n)
    changed = []
    for d, sinks in base.items():
        group = [d]
        if not d.startswith("PORT:"):
            group += [f"{n}/{d.rsplit('/', 1)[1]}" for n in clones_of.get(_inst(d), [])]
        got = Counter(_inst(s) for g in group for s in final.get(g, []) if _inst(s) not in clones)
        if got != Counter(_inst(s) for s in sinks):
            changed.append(d)
    if changed:
        d = changed[0]
        problems.append(f"{len(changed)} drivers reach different sinks (e.g. {d}: "
                        f"{' '.join(base[d][:4])} -> {' '.join(final.get(d, ['(none)'])[:4])})")
    extra = sorted(d for d in set(final) - set(base) if _inst(d) not in clones)
    if extra:
        problems.append(f"{len(extra)} new drivers (e.g. {extra[0]})")
    return check("logic_preserved", not problems,
                 "; ".join(problems) if problems else
                 f"{len(base)} drivers reach their original sink cells ({len(clones)} gate clones)")


def _clock_tree_unchanged(base_sig: dict, final_sig: dict, clock_port: str = "clk") -> Check:
    """Driver chain of every register clock pin (and the clock port's sinks) as in the baseline."""
    keys = [k for k in base_sig if k.startswith("C|")] + [f"P|{clock_port}"]
    diff = [k for k in keys if final_sig.get(k) != base_sig.get(k)]
    diff += [k for k in final_sig if k.startswith("C|") and k not in base_sig]
    if len(keys) < 2:
        return check("clock_tree_unchanged", False, "no register clock pins in the starting state")
    if diff:
        k = diff[0]
        return check("clock_tree_unchanged", False, f"clock network changed at {len(diff)} points "
                     f"(e.g. {k[2:]}: {str(base_sig.get(k))[:80]} -> {str(final_sig.get(k))[:80]})")
    return check("clock_tree_unchanged", True, f"{len(keys) - 1} register clock pins keep their clock path")


def _endpoints_constrained(base_t: dict, final_t: dict, key: str) -> Check:
    b, f = _num(base_t.get(key)), _num(final_t.get(key))
    ok = b is not None and f is not None and f >= b
    kind = "setup" if key.endswith("max") else "hold"
    return check(f"{kind}_endpoints_constrained", ok,
                 f"{f} of {final_t.get('endpoints')} register/output endpoints have a {kind} check (start {b})")


def _placement(ctx: ValidationContext) -> list[Check]:
    return [all_logic_placed(ctx), placement_legal(ctx)]


# --------------------------------------------------------------- validators
@register("op_buffer_inputs")
def buffer_inputs(ctx: ValidationContext, params: dict) -> list[Check]:
    """Every data input port drives exactly one buffer; clock and outputs untouched."""
    clock = params.get("clock_port", "clk")
    checks = [netlist_intact(ctx)]
    sig, base, fail = _pair(ctx, SIGNATURE_TCL, "op_signature")
    if fail:
        return checks + [fail]
    inputs = sorted(k[2:] for k, v in base.items()
                    if k.startswith("P|") and str(v).startswith("INPUT|") and k[2:] != clock)
    bad = []
    for port in inputs:
        parts = str(sig.get(f"P|{port}", "")).split("|")
        if not (len(parts) == 3 and parts[1] == "1" and "BUF_X" in parts[2]):
            bad.append(f"{port} -> {'|'.join(parts[1:]) or 'missing'}")
    checks.append(check("data_inputs_buffered", bool(inputs) and not bad,
                        f"{len(inputs) - len(bad)}/{len(inputs)} data inputs drive a single buffer"
                        + (f"; e.g. {', '.join(bad[:3])}" if bad else "")))
    checks.append(_logic_preserved(base, sig))
    outputs = sorted(k for k, v in base.items() if k.startswith("P|") and str(v).startswith("OUTPUT|"))
    changed = [k[2:] for k in outputs if _port_driver(sig.get(k)) != _port_driver(base.get(k))]
    checks.append(check("outputs_unbuffered", bool(outputs) and not changed,
                        f"{len(outputs) - len(changed)}/{len(outputs)} output ports keep their original driver"
                        + (f"; e.g. {changed[0]} now driven by {_port_driver(sig.get('P|' + changed[0]))}"
                           if changed else "")))
    checks.append(_clock_tree_unchanged(base, sig, clock))
    checks.append(all_logic_placed(ctx))
    outside = ctx.probe.get("logic_outside_core_count")
    checks.append(check("cells_inside_core", outside == 0, f"{outside} cells outside the core"))
    return checks


@register("op_hold_margin")
def hold_margin(ctx: ValidationContext, params: dict) -> list[Check]:
    """Worst hold slack >= margin (oracle), setup not degraded, clock tree and logic intact."""
    checks = [netlist_intact(ctx)] + _placement(ctx)
    t, tb, fail = _pair(ctx, TIMING_TCL, "op_timing")
    if fail:
        return checks + [fail]
    whs, wns, wns0 = _num(t.get("whs")), _num(t.get("wns")), _num(tb.get("wns"))
    need = params["min_hold_slack"]
    checks.append(check("hold_slack_margin", whs is not None and whs >= need - params["hold_tol"],
                        f"worst hold slack {_fmt(whs)} ns (start {_fmt(_num(tb.get('whs')))}, required >= {need})"))
    floor = None if wns0 is None else wns0 - params["max_setup_degradation"]
    checks.append(check("setup_not_degraded", wns is not None and floor is not None and wns >= floor - 1e-6,
                        f"worst setup slack {_fmt(wns)} ns (start {_fmt(wns0)}, allowed >= {_fmt(floor)})"))
    checks.append(_endpoints_constrained(tb, t, "constrained_min"))
    sig, base, fail = _pair(ctx, SIGNATURE_TCL, "op_signature")
    if fail:
        return checks + [fail]
    checks += [_clock_tree_unchanged(base, sig), _logic_preserved(base, sig)]
    return checks


@register("op_setup_repair")
def setup_repair(ctx: ValidationContext, params: dict) -> list[Check]:
    """WNS and TNS targets met (oracle with the original SDC), clock tree and netlist intact."""
    checks = [netlist_intact(ctx)] + _placement(ctx)
    t, tb, fail = _pair(ctx, TIMING_TCL, "op_timing")
    if fail:
        return checks + [fail]
    wns, tns = _num(t.get("wns")), _num(t.get("tns"))
    tol = params.get("slack_tol", 1e-4)
    checks.append(check("worst_setup_slack", wns is not None and wns >= params["min_wns"] - tol,
                        f"WNS {_fmt(wns)} ns (start {_fmt(_num(tb.get('wns')))}, required >= {params['min_wns']})"))
    checks.append(check("total_negative_setup_slack", tns is not None and tns >= params["min_tns"] - tol,
                        f"TNS {_fmt(tns)} ns (start {_fmt(_num(tb.get('tns')))}, required >= {params['min_tns']})"))
    checks.append(_endpoints_constrained(tb, t, "constrained_max"))
    sig, base, fail = _pair(ctx, SIGNATURE_TCL, "op_signature")
    if fail:
        return checks + [fail]
    checks += [_clock_tree_unchanged(base, sig), _logic_preserved(base, sig)]
    return checks


def parse_drv_summary(text: str | None) -> dict[str, tuple[int, int]] | None:
    """``max_slew <before> <after>`` lines -> {key: (before, after)}; None if a key is missing or ambiguous."""
    if text is None:
        return None
    found: dict[str, set[tuple[int, int]]] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*(max_slew|max_capacitance|max_fanout)\s*[:=,]?\s*(\d+)(?:\s*[,;]\s*|\s+)(\d+)\s*$",
                     line, re.IGNORECASE)
        if m:
            found.setdefault(m.group(1).lower(), set()).add((int(m.group(2)), int(m.group(3))))
    if any(len(found.get(k, ())) != 1 for k in DRV_KEYS):
        return None
    return {k: next(iter(found[k])) for k in DRV_KEYS}


@register("op_drv_repair_report")
def drv_repair_report(ctx: ValidationContext, params: dict) -> list[Check]:
    """Tightened slew/cap/fanout rules repaired; before/after counts reported match the oracle."""
    out = params["report"]
    checks = [netlist_intact(ctx)] + _placement(ctx)
    body = (DRV_TCL.replace("@SLEW@", str(params["max_transition"]))
            .replace("@CAP@", str(params["max_capacitance"])).replace("@FANOUT@", str(params["max_fanout"])))
    after, before, fail = _pair(ctx, body, "op_drv")
    if fail:
        return checks + [fail]
    a = {k: _num(after.get(k)) for k in DRV_KEYS}
    b = {k: _num(before.get(k)) for k in DRV_KEYS}
    remaining_ok = (a["max_slew"] == 0 and a["max_fanout"] == 0 and a["max_capacitance"] is not None
                    and a["max_capacitance"] <= params["max_cap_violations_after"])
    checks.append(check("violations_repaired", remaining_ok,
                        "remaining " + ", ".join(f"{k} {_cnt(a[k])}" for k in DRV_KEYS)
                        + " (before " + ", ".join(_cnt(b[k]) for k in DRV_KEYS)
                        + f"; allowed: 0 slew, <= {params['max_cap_violations_after']} capacitance, 0 fanout)"))
    rep = parse_drv_summary(ctx.read_output(out))
    if rep is None:
        checks.append(check(f"report:{out}", False, "missing, or not one 'max_slew/max_capacitance/"
                                                    "max_fanout <before> <after>' line per check"))
    else:
        wrong = [f"{k} reported {rep[k][0]} {rep[k][1]}, actual {_cnt(b[k])} {_cnt(a[k])}" for k in DRV_KEYS
                 if b[k] is None or a[k] is None or rep[k] != (int(b[k]), int(a[k]))]
        checks.append(check("reported_counts_match", not wrong,
                            "; ".join(wrong) if wrong else "before/after counts match the oracle"))
    sig, base, fail = _pair(ctx, SIGNATURE_TCL, "op_signature")
    if fail:
        return checks + [fail]
    checks.append(_logic_preserved(base, sig))
    return checks


@register("op_max_fanout")
def max_fanout(ctx: ValidationContext, params: dict) -> list[Check]:
    """No non-clock signal net drives more cell inputs than allowed; clock net and logic intact."""
    checks = [netlist_intact(ctx)] + _placement(ctx)
    sig, base, fail = _pair(ctx, SIGNATURE_TCL, "op_signature")
    if fail:
        return checks + [fail]
    fo, fo0 = _num(sig.get("fanout_max")), _num(base.get("fanout_max"))
    checks.append(check("max_fanout", fo is not None and fo <= params["max_fanout"],
                        f"largest non-clock fanout {fo} on net {sig.get('fanout_max_net')} "
                        f"(start {fo0}, limit {params['max_fanout']})"))
    checks += [_clock_tree_unchanged(base, sig, params.get("clock_port", "clk")), _logic_preserved(base, sig)]
    return checks
