"""Validators for the clock-tree-synthesis (cts) category.

Ground truth comes from a trusted oracle query on the final database that
traces the clock network from every clock source port down to the register
clock pins (STA ``all_registers -clock_pins``). It never relies on instance
names, on which command built the tree, or on what the agent printed.
Timing quantities (clock skew) are recomputed in the oracle session after
re-establishing placement parasitics, because neither parasitics nor SDC
changes made by the agent are stored in the database.
"""
from __future__ import annotations

import math
import re
from typing import Any

from benchmark.task_validator import Check, ValidationContext, register
from benchmark.validators.common import (
    all_logic_placed, check, moved_cells, netlist_intact, placement_legal,
)

# ----------------------------------------------------------------- oracle
_TREE_TCL = r"""
namespace eval ::ct_oracle {
  proc tree {} {
    set block [ord::get_db_block]
    array set regck {}
    foreach p [all_registers -clock_pins] { set regck([get_full_name $p]) 1 }
    set queue {}
    set root_nets {}
    foreach clk [all_clocks] {
      foreach src [get_property $clk sources] {
        set bt [$block findBTerm [get_full_name $src]]
        if {$bt ne "NULL" && [$bt getNet] ne "NULL"} {
          lappend queue [list [$bt getNet] 0 "PORT:[$bt getName]"]
          lappend root_nets "PORT:[$bt getName]"
        }
      }
    }
    array set seen_net {}; array set seen_inst {}; array set nreg {}; array set ncell {}
    set cells {}; set depths {}; set direct 0; set subnets 0
    while {[llength $queue]} {
      lassign [lindex $queue 0] net lvl parent
      set queue [lrange $queue 1 end]
      if {[info exists seen_net([$net getName])]} { continue }
      set seen_net([$net getName]) 1
      if {$lvl > 0} { incr subnets }
      foreach it [$net getITerms] {
        if {![$it isInputSignal]} { continue }
        set inst [$it getInst]
        set pin "[$inst getName]/[[$it getMTerm] getName]"
        if {[info exists regck($pin)]} {
          lappend depths $lvl
          if {$lvl == 0} { incr direct }
          incr nreg($parent) 0; incr nreg($parent)
          continue
        }
        # Any other load on the clock network is a clock-tree cell.
        incr ncell($parent) 0; incr ncell($parent)
        set iname [$inst getName]
        if {[info exists seen_inst($iname)]} { continue }
        set seen_inst($iname) 1
        lappend cells [list $iname [[$inst getMaster] getName] [expr {$lvl + 1}] $parent]
        foreach ot [$inst getITerms] {
          if {[$ot isOutputSignal] && [$ot getNet] ne "NULL"} {
            lappend queue [list [$ot getNet] [expr {$lvl + 1}] $iname]
          }
        }
      }
    }
    set enc {}
    foreach c $cells {
      lassign $c n m l par
      set r [expr {[info exists nreg($n)] ? $nreg($n) : 0}]
      set k [expr {[info exists ncell($n)] ? $ncell($n) : 0}]
      lappend enc "$n,$m,$l,$r,$k,$par"
    }
    # Clock roots: clock source ports whose net drives at least one clock-tree cell.
    set roots 0
    foreach rn [lsort -unique $root_nets] { if {[info exists ncell($rn)]} { incr roots } }
    return [dict create n_reg_pins [array size regck] n_reached [llength $depths] n_port_direct $direct \
      min_depth [expr {[llength $depths] ? [tcl::mathfunc::min {*}$depths] : 0}] \
      max_depth [expr {[llength $depths] ? [tcl::mathfunc::max {*}$depths] : 0}] \
      n_cells [llength $cells] n_subnets $subnets n_roots $roots cells "[join $enc {;}]"]
  }
}
set __ct [::ct_oracle::tree]
"""

# The clock must be propagated BEFORE estimating: in this build parasitics
# estimated while the clock is ideal leave the clock-tree nets without wire RC
# (the skew then drops from ~0.0032 to ~0.0018 ns on gcd).
_SKEW_TCL = r"""
set_propagated_clock [all_clocks]
estimate_parasitics -placement
dict set __ct skew_setup [sta::worst_clock_skew -setup]
sta::redirect_string_begin
report_clock_skew -setup -digits 6
dict set __ct skew_report [sta::redirect_string_end]
"""


def _oracle(ctx: ValidationContext, skew: bool = False) -> tuple[dict[str, Any] | None, Check | None]:
    """Clock-network ground truth for the final database (and optionally the skew)."""
    body = _TREE_TCL + (_SKEW_TCL if skew else "") + "__oracle_emit_dict $__ct\n"
    try:
        data = ctx.query(body, name="ct_oracle")
    except Exception as e:  # missing final.odb or a broken database
        return None, check("oracle_query", False, str(e).strip().splitlines()[0][:200])
    cells = {}
    data["cells_raw"] = str(data.get("cells", ""))
    for item in data["cells_raw"].split(";"):
        parts = item.split(",")
        if len(parts) == 6:
            name, master, level, nreg, ncell, parent = parts
            cells[name] = {"master": master, "level": int(level), "regs": int(nreg),
                           "cells": int(ncell), "parent": parent}
    data["cells"] = cells
    return data, None


# ----------------------------------------------------------------- helpers
_NUM_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def _numbers(text: str) -> list[float]:
    """Standalone numeric tokens (pin names such as _675_/CK are not numbers).

    "key=5" / "key:5" separators and a trailing "ns" unit ("0.0032ns") are accepted.
    """
    out = []
    for tok in re.split(r"[\s=:,;]+", text):
        tok = tok.strip("()[]").rstrip(".")  # "35." / "0.0032." at the end of a sentence
        if len(tok) > 2 and tok[-2:].lower() == "ns" and tok[-3].isdigit():
            tok = tok[:-2]
        if _NUM_RE.fullmatch(tok):
            out.append(float(tok))
    return out


def _to_float(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _has_pin(text: str, pin: str) -> bool:
    return re.search(r"(?<![\w/\\])" + re.escape(pin) + r"(?![\w/\[])", text) is not None


def _tree_checks(ctx: ValidationContext, t: dict[str, Any]) -> list[Check]:
    """The clock tree exists and drives every register clock pin."""
    base_regs = ctx.baseline.get("register_clock_pin_count")
    regs_ok = t["n_reg_pins"] == base_regs and ctx.probe.get("register_clock_pin_count") == base_regs
    out = [check("registers_intact", regs_ok, f"{t['n_reg_pins']} register clock pins (baseline {base_regs})")]
    built = t["n_cells"] > 0 and t["n_reached"] == t["n_reg_pins"] and t["n_port_direct"] == 0
    out.append(check("clock_tree_built", built,
                     f"{t['n_reached']}/{t['n_reg_pins']} register clock pins reached from the clock port, "
                     f"{t['n_port_direct']} driven directly by the port, {t['n_cells']} clock-tree cells, "
                     f"depth {t['min_depth']}-{t['max_depth']}"))
    return out


def _master_check(t: dict[str, Any], tree_masters: list[str], root_master: str | None) -> Check:
    """Masters of the clock-tree cells: level-1 cell(s) = root, the rest = tree buffers."""
    cells = t["cells"]
    roots = {n: c["master"] for n, c in cells.items() if c["level"] == 1}
    others = {n: c["master"] for n, c in cells.items() if c["level"] > 1}
    allowed_root = {root_master} if root_master else set(tree_masters)
    bad_root = {n: m for n, m in roots.items() if m not in allowed_root}
    bad_other = {n: m for n, m in others.items() if m not in set(tree_masters)}
    ok = bool(cells) and bool(roots) and not bad_root and not bad_other
    if root_master:
        ok = ok and bool(others)  # a root plus at least one level of tree buffers
    used = sorted({c["master"] for c in cells.values()})
    detail = (f"root {sorted(set(roots.values()))}, tree {sorted(set(others.values()))} "
              f"(expected root {sorted(allowed_root)}, tree {sorted(tree_masters)}); masters used {used}")
    if bad_root or bad_other:
        detail += "; wrong: " + ", ".join(f"{n}={m}" for n, m in list({**bad_root, **bad_other}.items())[:6])
    return check("clock_buffer_masters", ok, detail)


def _design_unchanged(ctx: ValidationContext, t: dict[str, Any] | None) -> Check:
    """Same cells, masters, placement status/positions and clock-tree connectivity as the start."""
    b, p = ctx.baseline, ctx.probe
    mv = moved_cells(ctx)
    same = (p.get("master_counts") == b.get("master_counts") and p.get("inst_count") == b.get("inst_count")
            and p.get("io_pin_count") == b.get("io_pin_count") and mv["moved"] == 0
            # moved_cells ignores cells that are no longer placed
            and p.get("status_counts") == b.get("status_counts"))
    tree_same: bool | None = None
    if t is not None:
        try:
            base = ctx.query_baseline(_TREE_TCL + "__oracle_emit_dict $__ct\n", name="ct_oracle_baseline")
            # Order-insensitive: the trace order follows the iterm order of each net.
            tree_same = (sorted(str(base.get("cells", "")).split(";"))
                         == sorted(str(t.get("cells_raw", "")).split(";")))
        except Exception:  # baseline oracle unavailable: fall back to the probe comparison
            tree_same = None
    detail = (f"insts {p.get('inst_count')}/{b.get('inst_count')}, moved cells {mv['moved']}, "
              f"masters {'same' if p.get('master_counts') == b.get('master_counts') else 'changed'}, "
              f"placement status {'same' if p.get('status_counts') == b.get('status_counts') else 'changed'}, "
              f"clock tree {'unknown' if tree_same is None else ('same' if tree_same else 'changed')}")
    return check("design_unchanged", same and tree_same is not False, detail)


# -------------------------------------------------------------- validators
@register("ct_clock_tree")
def clock_tree(ctx: ValidationContext, params: dict) -> list[Check]:
    """CTS with prescribed buffer masters (and optionally legalization)."""
    t, err = _oracle(ctx)
    if err:
        return [err]
    checks = _tree_checks(ctx, t)
    checks.append(_master_check(t, params["tree_masters"], params.get("root_master")))
    checks.append(netlist_intact(ctx))
    if params.get("require_legal"):
        checks += [all_logic_placed(ctx), placement_legal(ctx)]
    return checks


_METRIC_KEYS = (("subnets", "subnet"), ("roots", "root"), ("sinks", "sink"), ("buffers", "buffer"))


def _summary_metrics(text: str) -> dict[str, int]:
    """Metric name -> integer value, one metric per line (last occurrence wins).

    The metric of a line is the keyword that appears first in it, and its value is
    the first number after that keyword, so a remark such as
    "buffers: 5 (1 root + 4 leaf)" still reads as buffers = 5. When no number
    follows the keyword ("5 buffers"), the last number of the line is used.
    """
    found: dict[str, int] = {}
    for line in text.splitlines():
        low = line.lower()
        hits = [(low.find(word), key, word) for key, word in _METRIC_KEYS if word in low]
        if not hits:
            continue
        pos, key, word = min(hits)
        after = _numbers(line[pos + len(word):])
        nums = _numbers(line)
        val = after[0] if after else (nums[-1] if nums else None)
        if val is not None and val.is_integer():
            found[key] = int(val)
    return found


@register("ct_cts_summary")
def cts_summary(ctx: ValidationContext, params: dict) -> list[Check]:
    """CTS with a prescribed buffer plus the CTS summary metrics written to a file."""
    t, err = _oracle(ctx)
    if err:
        return [err]
    checks = _tree_checks(ctx, t)
    checks.append(_master_check(t, params["tree_masters"], params.get("root_master")))
    checks.append(netlist_intact(ctx))
    text = ctx.read_output(params["report"])
    if text is None:
        return checks + [check("summary_report", False, f"{params['report']} missing")]
    got = _summary_metrics(text)
    truth = {"roots": t["n_roots"], "buffers": t["n_cells"], "subnets": t["n_subnets"], "sinks": t["n_reached"]}
    for key, want in truth.items():
        val = got.get(key)
        checks.append(check(f"summary_{key}", val is not None and val == want,
                            f"reported {val if val is not None else 'nothing'}, actual {want}"))
    return checks


@register("ct_skew_report")
def skew_report(ctx: ValidationContext, params: dict) -> list[Check]:
    """Setup clock-skew report with placement parasitics on an unchanged design."""
    t, err = _oracle(ctx, skew=True)
    checks = [_design_unchanged(ctx, t)]
    if err:
        return checks + [err]
    text = ctx.read_output(params["report"])
    if text is None:
        return checks + [check("skew_report", False, f"{params['report']} missing")]
    nums = _numbers(text)
    truth = _to_float(t.get("skew_setup"))
    if truth is None:
        return checks + [check("skew_value", False, f"no finite clock skew in the design ({t.get('skew_setup')})")]
    val = nums[-1] if nums else None
    ok = val is not None and math.isfinite(val) and abs(val - truth) <= params["skew_tol_ns"]
    checks.append(check("skew_value", ok, f"reported {val}, actual {truth:.6f} ns (tol {params['skew_tol_ns']})"))
    pins = re.findall(r"(\S+/\S+)\s+[\^v]", str(t.get("skew_report", "")))[:2]
    pins_ok = len(pins) == 2 and all(_has_pin(text, p) for p in pins)
    checks.append(check("skew_pins", pins_ok, f"worst-skew register clock pins {pins}"))
    return checks


_METRIC_LINE = re.compile(r"^\s*([A-Za-z_]+)\s*[:=]?\s*(\S+)\s*$")


@register("ct_cts_metrics")
def cts_metrics(ctx: ValidationContext, params: dict) -> list[Check]:
    """Blueprint task 5: CTS + legalization + clock-tree metrics (buffer count, skew)."""
    t, err = _oracle(ctx, skew=True)
    if err:
        return [err]
    checks = _tree_checks(ctx, t)
    checks.append(_master_check(t, params["tree_masters"], params.get("root_master")))
    checks.append(netlist_intact(ctx))
    if params.get("require_legal"):
        checks += [all_logic_placed(ctx), placement_legal(ctx)]
    text = ctx.read_output(params["report"])
    if text is None:
        return checks + [check("metrics_file", False, f"{params['report']} missing")]
    vals: dict[str, str] = {}
    for line in text.splitlines():
        m = _METRIC_LINE.match(line)
        if m:
            vals[m.group(1).lower()] = m.group(2)
    nbuf = vals.get("clock_buffers")
    ok = nbuf is not None and re.fullmatch(r"\d+", nbuf) is not None and int(nbuf) == t["n_cells"]
    checks.append(check("metric_clock_buffers", ok, f"reported {nbuf}, actual {t['n_cells']}"))
    skew_txt = vals.get("clock_skew_ns")
    skew = _to_float(skew_txt)
    truth = _to_float(t.get("skew_setup"))
    ok = skew is not None and truth is not None and abs(skew - truth) <= params["skew_tol_ns"]
    actual = f"{truth:.6f}" if truth is not None else str(t.get("skew_setup"))
    checks.append(check("metric_clock_skew", ok,
                        f"reported {skew_txt}, actual {actual} ns (tol {params['skew_tol_ns']})"))
    return checks


@register("ct_tree_structure")
def tree_structure(ctx: ValidationContext, params: dict) -> list[Check]:
    """Per-buffer description of the existing clock tree (cell, level, register fanout)."""
    t, err = _oracle(ctx)
    checks = [_design_unchanged(ctx, t)]
    if err:
        return checks + [err]
    truth = {n: (c["master"], c["level"], c["regs"]) for n, c in t["cells"].items()}
    text = ctx.read_output(params["report"])
    if text is None:
        return checks + [check("tree_report", False, f"{params['report']} missing")]
    got: dict[str, tuple[str, int, int]] = {}
    bad_lines, dups = [], []
    for line in text.splitlines():
        if not line.strip():
            continue
        f = line.split()
        if len(f) != 4 or not re.fullmatch(r"\d+", f[2]) or not re.fullmatch(r"\d+", f[3]):
            bad_lines.append(line.strip()[:60])
            continue
        if f[0] in got:
            dups.append(f[0])
        # A library-qualified master (NangateOpenCellLibrary/BUF_X4) names the same cell.
        got[f[0]] = (f[1].rsplit("/", 1)[-1], int(f[2]), int(f[3]))
    checks.append(check("report_format", not bad_lines and not dups and bool(got),
                        f"{len(got)} buffer lines" + (f", malformed {bad_lines[:3]}" if bad_lines else "")
                        + (f", duplicates {dups[:3]}" if dups else "")))
    missing, extra = sorted(set(truth) - set(got)), sorted(set(got) - set(truth))
    checks.append(check("buffer_set", not missing and not extra,
                        f"{len(truth)} clock buffers; missing {missing[:4]}, not in the clock tree {extra[:4]}"))
    wrong = [f"{n}: {got[n]} vs {truth[n]}" for n in sorted(set(truth) & set(got)) if got[n] != truth[n]]
    checks.append(check("buffer_attributes", not wrong and bool(truth),
                        f"cell/level/register sinks wrong for {len(wrong)}: {wrong[:3]}" if wrong
                        else f"all {len(set(truth) & set(got))} listed buffers correct"))
    return checks
