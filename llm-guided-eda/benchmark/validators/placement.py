"""Validators for the placement category (PL-01 ... PL-10, DEV-PL-01).

Ground truth comes from the design-state probe (cell positions and orientations,
legality, IO pins) and from trusted oracle queries that measure what the probe
does not record: pin-based HPWL, bin density, gaps between neighbouring cells
in a row, filler coverage and filler names. All lengths are in microns.
"""
from __future__ import annotations

import math
import re
from typing import Any

from benchmark.task_validator import Check, ValidationContext, register
from benchmark.validators.common import (all_logic_placed, check, moved_cells, netlist_intact,
                                         placement_legal)

# Oracle helpers (namespace ::plv), prepended to every oracle query body.
PLV_TCL = r"""
namespace eval ::plv {
  # F = filler, T = tap cell, L = logic (movable standard cell)
  proc kind {inst} {
    set m [$inst getMaster]
    if {[$m isFiller]} { return F }
    if {[$m getType] eq "CORE_WELLTAP" || [string match TAPCELL* [$m getName]]} { return T }
    return L
  }
  proc placed {inst} { return [expr {[$inst getPlacementStatus] in {PLACED FIRM LOCKED COVER}}] }
  proc site_width {} {
    set rows [[ord::get_db_block] getRows]
    if {![llength $rows]} { return 0 }
    return [[[lindex $rows 0] getSite] getWidth]
  }
  # Pin-based HPWL over signal nets with >= 2 pins: instance pins at the average of their
  # shape centres (getAvgXY, as in the DPL legalization report), IO pins at their shape centre.
  # Returns {total_um io_nets_um net_count}.
  proc hpwl {} {
    set block [ord::get_db_block]
    set dbu [$block getDefUnits]
    set tot 0.0; set io 0.0; set n 0
    foreach net [$block getNets] {
      if {[$net getSigType] in {POWER GROUND}} continue
      set xs {}; set ys {}; set nb 0
      foreach it [$net getITerms] {
        set a [$it getAvgXY]
        if {[lindex $a 0]} {
          lappend xs [lindex $a 1]; lappend ys [lindex $a 2]
        } else {
          set bb [[$it getInst] getBBox]
          lappend xs [expr {([$bb xMin] + [$bb xMax]) / 2.0}]
          lappend ys [expr {([$bb yMin] + [$bb yMax]) / 2.0}]
        }
      }
      foreach bt [$net getBTerms] {
        foreach bp [$bt getBPins] {
          set bb [$bp getBBox]
          lappend xs [expr {([$bb xMin] + [$bb xMax]) / 2.0}]
          lappend ys [expr {([$bb yMin] + [$bb yMax]) / 2.0}]
          incr nb
        }
      }
      if {[llength $xs] < 2} continue
      incr n
      set xs [lsort -real $xs]; set ys [lsort -real $ys]
      set h [expr {([lindex $xs end] - [lindex $xs 0] + [lindex $ys end] - [lindex $ys 0]) / double($dbu)}]
      set tot [expr {$tot + $h}]
      if {$nb} { set io [expr {$io + $h}] }
    }
    return [list $tot $io $n]
  }
  # Area-weighted mean density of the non-empty square bins (aligned to the core origin)
  # over placed logic cells: sum(A_b^2 / binArea) / sum(A_b). -1 when nothing is placed.
  proc density {bin_um} {
    set block [ord::get_db_block]
    set dbu [$block getDefUnits]
    set core [$block getCoreArea]
    set cx0 [$core xMin]; set cy0 [$core yMin]
    set bs [expr {round($bin_um * $dbu)}]
    array set A {}
    set tot 0.0
    foreach inst [$block getInsts] {
      if {[kind $inst] ne "L" || ![placed $inst]} continue
      set bb [$inst getBBox]
      set x0 [$bb xMin]; set y0 [$bb yMin]; set x1 [$bb xMax]; set y1 [$bb yMax]
      set tot [expr {$tot + double($x1 - $x0) * ($y1 - $y0)}]
      set i0 [expr {int(floor(double($x0 - $cx0) / $bs))}]
      set i1 [expr {int(floor(double($x1 - 1 - $cx0) / $bs))}]
      set j0 [expr {int(floor(double($y0 - $cy0) / $bs))}]
      set j1 [expr {int(floor(double($y1 - 1 - $cy0) / $bs))}]
      for {set i $i0} {$i <= $i1} {incr i} {
        for {set j $j0} {$j <= $j1} {incr j} {
          set bx0 [expr {$cx0 + $i * $bs}]; set by0 [expr {$cy0 + $j * $bs}]
          set ox [expr {min($x1, $bx0 + $bs) - max($x0, $bx0)}]
          set oy [expr {min($y1, $by0 + $bs) - max($y0, $by0)}]
          if {$ox > 0 && $oy > 0} {
            if {![info exists A($i,$j)]} { set A($i,$j) 0.0 }
            set A($i,$j) [expr {$A($i,$j) + double($ox) * $oy}]
          }
        }
      }
    }
    if {$tot <= 0} { return -1 }
    set ba [expr {double($bs) * $bs}]
    set w 0.0
    foreach k [array names A] { set w [expr {$w + $A($k) * $A($k) / $ba}] }
    return [expr {$w / $tot}]
  }
  # Placed non-filler instances grouped by row (bbox yMin): {xMin xMax kind master}.
  proc row_lists {} {
    set R [dict create]
    foreach inst [[ord::get_db_block] getInsts] {
      if {![placed $inst]} continue
      set k [kind $inst]
      if {$k eq "F"} continue
      set bb [$inst getBBox]
      dict lappend R [$bb yMin] [list [$bb xMin] [$bb xMax] $k [[$inst getMaster] getName]]
    }
    return $R
  }
  # Minimum gap in sites between horizontal neighbours in a row:
  # {logic-logic logic-tap number_of_logic_logic_pairs}; 1e9 when no such pair exists.
  proc gaps {} {
    set sw [site_width]
    if {$sw <= 0} { return {-1 -1 0} }
    set ll 1e9; set lt 1e9; set nll 0
    dict for {y cells} [row_lists] {
      set cells [lsort -integer -index 0 $cells]
      for {set i 1} {$i < [llength $cells]} {incr i} {
        set a [lindex $cells [expr {$i - 1}]]; set b [lindex $cells $i]
        set g [expr {double([lindex $b 0] - [lindex $a 1]) / $sw}]
        set k "[lindex $a 2][lindex $b 2]"
        if {$k eq "LL"} { incr nll; if {$g < $ll} { set ll $g } }
        if {$k eq "LT" || $k eq "TL"} { if {$g < $lt} { set lt $g } }
      }
    }
    return [list $ll $lt $nll]
  }
  # Minimum gap in sites left and right of instances whose master matches a glob pattern.
  proc master_gaps {pattern} {
    set sw [site_width]
    if {$sw <= 0} { return {-1 -1 0} }
    set lmin 1e9; set rmin 1e9; set n 0
    dict for {y cells} [row_lists] {
      set cells [lsort -integer -index 0 $cells]
      set m [llength $cells]
      for {set i 0} {$i < $m} {incr i} {
        set c [lindex $cells $i]
        if {![string match $pattern [lindex $c 3]]} continue
        incr n
        if {$i > 0} {
          set g [expr {double([lindex $c 0] - [lindex [lindex $cells [expr {$i - 1}]] 1]) / $sw}]
          if {$g < $lmin} { set lmin $g }
        }
        if {$i < $m - 1} {
          set g [expr {double([lindex [lindex $cells [expr {$i + 1}]] 0] - [lindex $c 1]) / $sw}]
          if {$g < $rmin} { set rmin $g }
        }
      }
    }
    return [list $lmin $rmin $n]
  }
  # {filler_count fillers_with_prefix uncovered_row_sites total_row_sites}; coverage is the
  # per-row union of all placed instance boxes.
  proc fill_stats {prefix} {
    set block [ord::get_db_block]
    set nf 0; set np 0
    set iv [dict create]
    foreach inst [$block getInsts] {
      if {[[$inst getMaster] isFiller]} {
        incr nf
        if {[string match "${prefix}*" [$inst getName]]} { incr np }
      }
      if {![placed $inst]} continue
      set bb [$inst getBBox]
      dict lappend iv [$bb yMin] [list [$bb xMin] [$bb xMax]]
    }
    set unc 0; set tot 0
    foreach row [$block getRows] {
      set rb [$row getBBox]
      set sw [[$row getSite] getWidth]
      set y [$rb yMin]; set xe [$rb xMax]
      incr tot [$row getSiteCount]
      set segs {}
      if {[dict exists $iv $y]} { set segs [lsort -integer -index 0 [dict get $iv $y]] }
      set cur [$rb xMin]; set covered 0
      foreach seg $segs {
        lassign $seg a b
        set a [expr {max($a, $cur)}]; set b [expr {min($b, $xe)}]
        if {$b > $a} { incr covered [expr {$b - $a}]; set cur $b }
      }
      incr unc [expr {([$rb xMax] - [$rb xMin] - $covered) / $sw}]
    }
    return [list $nf $np $unc $tot]
  }
  # Placed logic cells whose orientation does not match the row they sit in
  # (R0 rows take R0/MY, MX rows take MX/R180; check_placement does not test this).
  proc bad_orient {} {
    set block [ord::get_db_block]
    set ro [dict create]
    foreach row [$block getRows] { dict set ro [[$row getBBox] yMin] [$row getOrient] }
    set bad 0
    foreach inst [$block getInsts] {
      if {[kind $inst] ne "L" || ![placed $inst]} continue
      set y [[$inst getBBox] yMin]
      if {![dict exists $ro $y]} { incr bad; continue }
      set o [$inst getOrient]; set r [dict get $ro $y]
      if {!(($r eq "R0" && $o in {R0 MY}) || ($r eq "MX" && $o in {MX R180}))} { incr bad }
    }
    return $bad
  }
}
"""

MEASURE_TCL = r"""
set __h [::plv::hpwl]
set __g [::plv::gaps]
set __m [::plv::master_gaps {@MASTER@}]
set __f [::plv::fill_stats {@PREFIX@}]
__oracle_emit_dict [dict create hpwl [lindex $__h 0] io_hpwl [lindex $__h 1] hpwl_nets [lindex $__h 2] \
  density [::plv::density @BIN@] gap_ll [lindex $__g 0] gap_lt [lindex $__g 1] ll_pairs [lindex $__g 2] \
  master_gap_left [lindex $__m 0] master_gap_right [lindex $__m 1] master_count [lindex $__m 2] \
  fillers [lindex $__f 0] fillers_prefixed [lindex $__f 1] uncovered_sites [lindex $__f 2] \
  row_sites [lindex $__f 3] bad_orient [::plv::bad_orient]]
"""

Y_MIRROR = {("R0", "MY"), ("MY", "R0"), ("MX", "R180"), ("R180", "MX")}
NUM = r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"


def _measure(ctx: ValidationContext, params: dict, *, baseline: bool = False, pre: str = "",
             name: str = "pl_measure") -> tuple[dict[str, Any] | None, Check | None]:
    """All oracle measurements in one OpenROAD session, optionally after a reference script ``pre``.

    Failures on the agent's final database become a failing check (the agent may have left
    an unusable design); failures on the starting state are validator bugs and propagate.
    """
    body = (PLV_TCL + "\n" + pre + "\n" + MEASURE_TCL
            .replace("@MASTER@", str(params.get("master_pattern", "DFF_*")))
            .replace("@PREFIX@", str(params.get("prefix", "FILL_")))
            .replace("@BIN@", str(float(params.get("bin_um", 4.0)))))
    if baseline:
        return ctx.query_baseline(body, name=name), None
    try:
        return ctx.query(body, name=name), None
    except Exception as e:  # noqa: BLE001 -- agent output must never crash the validator
        msg = (str(e).strip().splitlines() or [type(e).__name__])[0]
        return None, check("oracle_measurement", False, f"oracle query on final.odb failed: {msg[:200]}")


def _num(d: dict[str, Any] | None, key: str) -> float | None:
    v = (d or {}).get(key)
    return float(v) if isinstance(v, (int, float)) and math.isfinite(v) else None


def _fmt(v: float | None, digits: int = 3) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}"


def _read(ctx: ValidationContext, name: str) -> tuple[str | None, Check]:
    text = ctx.read_output(name)
    if text is None:
        return None, check(f"file:{name}", False, "missing")
    return text, check(f"file:{name}", bool(text.strip()), f"{len(text)} chars")


def _keyed_number(text: str, key: str) -> float | None:
    m = re.search(rf"^\s*{re.escape(key)}\s*[:=]\s*{NUM}", text, re.MULTILINE | re.IGNORECASE)
    return float(m.group(1)) if m else None


def _inside_core(ctx: ValidationContext) -> Check:
    n = ctx.probe.get("logic_outside_core_count")
    return check("cells_inside_core", n == 0, f"{n} placed cells outside the core")


def _row_orientation(m: dict[str, Any]) -> Check:
    bad = m.get("bad_orient")
    return check("row_orientation", bad == 0, f"{bad} cells off-row or with an orientation not matching their row")


def _displacement(ctx: ValidationContext, params: dict) -> Check:
    mv = moved_cells(ctx)
    n = ctx.baseline.get("logic_inst_count", 0)
    ok = (mv["compared"] == n and mv["max_disp"] <= params["max_disp_um"]
          and mv["mean_disp"] <= params["mean_disp_um"])
    return check("near_global_placement", ok,
                 f"{mv['compared']}/{n} cells compared, max {mv['max_disp']:.2f} um "
                 f"(<= {params['max_disp_um']}), mean {mv['mean_disp']:.2f} um (<= {params['mean_disp_um']})")


def _unchanged_positions(ctx: ValidationContext, name: str = "cells_not_moved") -> Check:
    mv = moved_cells(ctx)
    n = len(ctx.baseline.get("positions", {}) or {})
    return check(name, mv["compared"] == n and mv["moved"] == 0,
                 f"{mv['moved']} of {mv['compared']}/{n} cells moved")


def _io_pins_unchanged(ctx: ValidationContext) -> Check:
    """IO pins keep their placement, location and layer (they would otherwise shorten the HPWL)."""
    before = ctx.baseline.get("io_pins", {}) or {}
    after = ctx.probe.get("io_pins", {}) or {}
    changed = 0
    for name, b in before.items():
        a = after.get(name)
        if not isinstance(a, dict) or a.get("placed") != b.get("placed") or a.get("layer") != b.get("layer"):
            changed += 1
            continue
        xy0, xy1 = (b.get("x"), b.get("y")), (a.get("x"), a.get("y"))
        if None in xy0 or None in xy1:
            changed += xy0 != xy1
        elif abs(xy1[0] - xy0[0]) + abs(xy1[1] - xy0[1]) > 1e-3:
            changed += 1
    ok = bool(before) and changed == 0 and len(after) == len(before)
    return check("io_pins_unchanged", ok, f"{changed} of {len(before)} IO pins moved or changed ({len(after)} now)")


def _manhattan(ctx: ValidationContext) -> dict[str, float]:
    before = ctx.baseline.get("positions", {}) or {}
    after = ctx.probe.get("positions", {}) or {}
    return {n: abs(after[n][0] - x0) + abs(after[n][1] - y0)
            for n, (x0, y0, _o) in before.items() if n in after}


# --------------------------------------------------------------------- PL-01, PL-04
@register("pl_global_placement")
def global_placement(ctx: ValidationContext, params: dict) -> list[Check]:
    """Global placement from the floorplan: placed, inside the core, spread, wirelength-driven."""
    p, b = ctx.probe, ctx.baseline
    checks = [all_logic_placed(ctx), _inside_core(ctx), netlist_intact(ctx),
              check("tapcells_kept", p.get("tapcell_count") == b.get("tapcell_count"),
                    f"{p.get('tapcell_count')}/{b.get('tapcell_count')} tap cells")]
    m, err = _measure(ctx, params)
    if err:
        return checks + [err]
    dens = _num(m, "density")
    checks.append(check("cells_spread", dens is not None and 0 < dens <= params["max_bin_density"],
                        f"bin density {_fmt(dens)} (<= {params['max_bin_density']}; stacked cells give > 5)"))
    if "density_min" in params:
        lo, hi = params["density_min"], params["density_max"]
        checks.append(check("target_density", dens is not None and lo <= dens <= hi,
                            f"measured placement density {_fmt(dens)}, expected {lo}..{hi}"))
    ref, _ = _measure(ctx, params, baseline=True, pre=params["reference_script"], name="pl_reference")
    hp, hp_ref = _num(m, "hpwl"), _num(ref, "hpwl")
    limit = params["hpwl_ratio_max"] * (hp_ref or 0.0)
    checks.append(check("wirelength_vs_reference", hp is not None and hp_ref is not None and hp <= limit,
                        f"HPWL {_fmt(hp, 1)} um, limit {limit:.1f} um "
                        f"({params['hpwl_ratio_max']} x reference {_fmt(hp_ref, 1)} um)"))
    return checks


# ------------------------------------------------------------ PL-02, PL-05, DEV-PL-01
@register("pl_legalize")
def legalize(ctx: ValidationContext, params: dict) -> list[Check]:
    """Legalization of the global placement, optionally with padding requirements."""
    checks = [all_logic_placed(ctx), placement_legal(ctx), netlist_intact(ctx), _displacement(ctx, params)]
    m, err = _measure(ctx, params)
    if err:
        return checks + [err]
    checks.append(_row_orientation(m))
    if "min_gap_ll_sites" in params:
        g, n = _num(m, "gap_ll"), m.get("ll_pairs")
        checks.append(check("gap_between_cells", g is not None and g >= params["min_gap_ll_sites"] - 1e-6,
                            f"smallest gap between adjacent standard cells {_fmt(g, 2)} sites over {n} pairs "
                            f"(>= {params['min_gap_ll_sites']})"))
    if "min_gap_lt_sites" in params:
        g = _num(m, "gap_lt")
        checks.append(check("gap_to_tap_cells", g is not None and g >= params["min_gap_lt_sites"] - 1e-6,
                            f"smallest standard-cell to tap-cell gap {_fmt(g, 2)} sites "
                            f"(>= {params['min_gap_lt_sites']})"))
    if "min_master_gap_sites" in params:
        lo, ro, n = _num(m, "master_gap_left"), _num(m, "master_gap_right"), m.get("master_count")
        want = params["min_master_gap_sites"] - 1e-6
        checks.append(check("gap_around_masters", n and lo is not None and ro is not None
                            and lo >= want and ro >= want,
                            f"{n} '{params['master_pattern']}' cells: smallest left gap {_fmt(lo, 2)}, "
                            f"right gap {_fmt(ro, 2)} sites (>= {params['min_master_gap_sites']})"))
    return checks


# ----------------------------------------------------------------------------- PL-03
@register("pl_utilization_report")
def utilization_report(ctx: ValidationContext, params: dict) -> list[Check]:
    """Reported utilization (logic + tap area / core area) and the above-target decision."""
    b, p = ctx.baseline, ctx.probe
    truth = 100.0 * float(b.get("utilization_with_taps") or 0.0)
    text, fcheck = _read(ctx, params["file"])
    checks = [fcheck]
    value = _keyed_number(text or "", "utilization_percent")
    checks.append(check("utilization_value", value is not None and abs(value - truth) <= params["tol_percent"],
                        f"reported {_fmt(value, 3)} %, actual {truth:.3f} % (+/- {params['tol_percent']})"))
    m = re.search(r"^\s*above_target\s*[:=]\s*(yes|no)\b", text or "", re.MULTILINE | re.IGNORECASE)
    expected = "yes" if truth > params["target_percent"] else "no"
    got = m.group(1).lower() if m else None
    checks.append(check("above_target_decision", got == expected,
                        f"reported {got}, expected {expected} ({truth:.2f} % vs target {params['target_percent']} %)"))
    same = (p.get("inst_count") == b.get("inst_count") and p.get("filler_count") == b.get("filler_count"))
    checks.append(check("design_unchanged", same and moved_cells(ctx)["moved"] == 0,
                        f"instances {p.get('inst_count')}/{b.get('inst_count')}, moved {moved_cells(ctx)['moved']}"))
    return checks


# ----------------------------------------------------------------------------- PL-06
@register("pl_fillers")
def fillers(ctx: ValidationContext, params: dict) -> list[Check]:
    """Filler insertion: every row site covered, filler names prefixed, nothing moved."""
    checks = [_unchanged_positions(ctx), placement_legal(ctx), netlist_intact(ctx)]
    m, err = _measure(ctx, params)
    if err:
        return checks + [err]
    unc, tot = m.get("uncovered_sites"), m.get("row_sites")
    rows, rows0 = ctx.probe.get("row_count"), ctx.baseline.get("row_count")
    checks.append(check("no_empty_sites", unc == 0 and rows == rows0 and bool(tot),
                        f"{unc} of {tot} row sites not covered by any cell ({rows}/{rows0} rows)"))
    nf, npref = m.get("fillers") or 0, m.get("fillers_prefixed") or 0
    checks.append(check("fillers_inserted", nf > 0, f"{nf} filler instances"))
    checks.append(check("filler_name_prefix", nf > 0 and npref == nf,
                        f"{npref}/{nf} filler instances named '{params['prefix']}*'"))
    return checks


# ----------------------------------------------------------------------------- PL-07
@register("pl_mirror")
def mirror(ctx: ValidationContext, params: dict) -> list[Check]:
    """Wirelength reduction by Y-axis mirroring only: no movement, legal, HPWL down."""
    before = ctx.baseline.get("positions", {}) or {}
    after = ctx.probe.get("positions", {}) or {}
    moved = flipped = wrong = 0
    for name, (x0, y0, o0) in before.items():
        if name not in after:
            continue
        x1, y1, o1 = after[name]
        if abs(x1 - x0) > 1e-6 or abs(y1 - y0) > 1e-6:
            moved += 1
        elif o1 != o0:
            flipped += 1
            wrong += (o0, o1) not in Y_MIRROR
    compared = sum(1 for n in before if n in after)
    checks = [check("no_cell_moved", compared == len(before) and moved == 0,
                    f"{moved} of {compared}/{len(before)} cells changed location"),
              check("cells_mirrored", flipped >= params["min_flipped"], f"{flipped} cells changed orientation"),
              check("y_axis_mirror_only", wrong == 0, f"{wrong} orientation changes are not Y-axis mirrors"),
              _io_pins_unchanged(ctx), placement_legal(ctx), netlist_intact(ctx)]
    m, err = _measure(ctx, params)
    if err:
        return checks + [err]
    base, _ = _measure(ctx, params, baseline=True, name="pl_start")
    hp, hp0 = _num(m, "hpwl"), _num(base, "hpwl")
    red = (hp0 - hp) / hp0 if hp is not None and hp0 else None
    checks.append(check("hpwl_reduced", red is not None and red >= params["min_hpwl_reduction"],
                        f"HPWL {_fmt(hp0, 1)} -> {_fmt(hp, 1)} um, reduction {_fmt(None if red is None else 100 * red, 2)} % "
                        f"(>= {100 * params['min_hpwl_reduction']:.1f} %)"))
    checks.append(_row_orientation(m))
    return checks


# ----------------------------------------------------------------------------- PL-08
@register("pl_improve_hpwl")
def improve_hpwl(ctx: ValidationContext, params: dict) -> list[Check]:
    """Detailed-placement optimization with an HPWL target, plus a before/after HPWL report."""
    mv = moved_cells(ctx)
    n = ctx.baseline.get("logic_inst_count", 0)
    checks = [all_logic_placed(ctx), placement_legal(ctx), netlist_intact(ctx), _io_pins_unchanged(ctx),
              # detailed-placement optimizers move cells ~2 um on average, a new global placement ~12 um
              check("refines_existing_placement", mv["compared"] == n and mv["mean_disp"] <= params["max_mean_disp_um"],
                    f"{mv['compared']}/{n} cells compared, mean movement {mv['mean_disp']:.2f} um "
                    f"(<= {params['max_mean_disp_um']})")]
    text, fcheck = _read(ctx, params["file"])
    checks.append(fcheck)
    m, err = _measure(ctx, params)
    if err:
        return checks + [err]
    checks.append(_row_orientation(m))
    base, _ = _measure(ctx, params, baseline=True, name="pl_start")
    hp, hp0 = _num(m, "hpwl"), _num(base, "hpwl")
    red = (hp0 - hp) / hp0 if hp is not None and hp0 else None
    checks.append(check("hpwl_reduced", red is not None and red >= params["min_reduction"],
                        f"HPWL {_fmt(hp0, 1)} -> {_fmt(hp, 1)} um, reduction {_fmt(None if red is None else 100 * red, 2)} % "
                        f"(>= {100 * params['min_reduction']:.1f} %)"))
    rtol = params["report_rtol"]
    for key, truth in (("hpwl_before_um", hp0), ("hpwl_after_um", hp)):
        v = _keyed_number(text or "", key)
        ok = v is not None and truth is not None and abs(v - truth) <= rtol * truth
        checks.append(check(f"report_{key}", ok, f"reported {_fmt(v, 2)}, actual {_fmt(truth, 2)} um "
                                                 f"(+/- {100 * rtol:.1f} %)"))
    return checks


# ----------------------------------------------------------------------------- PL-09
@register("pl_displacement_report")
def displacement_report(ctx: ValidationContext, params: dict) -> list[Check]:
    """Legalization plus a report of the N most displaced cells (Manhattan, um)."""
    checks = [all_logic_placed(ctx), placement_legal(ctx), netlist_intact(ctx), _displacement(ctx, params)]
    text, fcheck = _read(ctx, params["file"])
    checks.append(fcheck)
    entries: list[tuple[str, float]] = []
    for line in (text or "").splitlines():
        m = re.match(rf"^\s*\{{?([^\s{{}}:,]+)\}}?[:,]?\s+{NUM}\s*(?:um)?\s*$", line)
        if m:
            entries.append((m.group(1), float(m.group(2))))
    n, tol = params["top_n"], params["value_tol_um"]
    truth = _manhattan(ctx)
    checks.append(check("report_entries", len(entries) == n, f"{len(entries)} '<cell> <value>' lines (expected {n})"))
    names = [e[0] for e in entries]
    unknown = [x for x in names if x not in truth]
    checks.append(check("report_cells_valid", bool(names) and not unknown and len(set(names)) == len(names),
                        f"unknown {unknown[:3]}" if unknown else f"{len(set(names))} distinct cells"))
    bad = [f"{x}: {v:.4f} vs {truth[x]:.4f}" for x, v in entries if x in truth and abs(v - truth[x]) > tol]
    checks.append(check("report_values", bool(entries) and not bad and not unknown,
                        "; ".join(bad[:3]) if bad else f"all values within {tol} um of the actual displacement"))
    ranked = sorted(truth.values(), reverse=True)
    threshold = ranked[n - 1] if len(ranked) >= n else math.inf
    in_top = [x for x in names if x in truth and truth[x] >= threshold - 1e-6]
    checks.append(check("report_is_top_n", len(entries) == n and len(in_top) == n and len(set(names)) == n,
                        f"{len(in_top)}/{n} reported cells among the {n} largest displacements "
                        f"(n-th largest {threshold:.4f} um)"))
    values = [v for _, v in entries]
    checks.append(check("report_sorted", bool(values) and all(a >= b - 1e-9 for a, b in zip(values, values[1:])),
                        "largest first" if values else "no values"))
    return checks


# ----------------------------------------------------------------------------- PL-10
def _pin_checks(ctx: ValidationContext, params: dict) -> list[Check]:
    p, b = ctx.probe, ctx.baseline
    pins, base_pins = p.get("io_pins", {}) or {}, b.get("io_pins", {}) or {}
    die = p.get("die") or b.get("die")
    n = len(base_pins)
    placed = sum(1 for v in pins.values() if v.get("placed"))
    moved = wrong_layer = off_edge = 0
    for name, v in pins.items():
        x, y = v.get("x"), v.get("y")
        if x is None or y is None or not die:
            off_edge += 1
            continue
        b0 = base_pins.get(name, {})
        if b0.get("x") is None or abs(x - b0["x"]) + abs(y - b0["y"]) > 1e-3:
            moved += 1
        dist = {"left": x - die[0], "right": die[2] - x, "bottom": y - die[1], "top": die[3] - y}
        edge = min(dist, key=dist.get)
        if dist[edge] > params["edge_tol_um"]:
            off_edge += 1
            continue
        want = params["hor_layer"] if edge in ("left", "right") else params["ver_layer"]
        wrong_layer += v.get("layer") != want
    frac = moved / n if n else 0.0
    return [check("io_pins_placed", n > 0 and placed == n == len(pins), f"{placed}/{n} IO pins placed"),
            check("io_pins_replaced", frac >= params["min_pins_moved_frac"],
                  f"{moved}/{n} IO pins moved from their starting positions (>= {params['min_pins_moved_frac']:.0%})"),
            check("io_pin_layers", off_edge == 0 and wrong_layer == 0,
                  f"{off_edge} pins off the die boundary, {wrong_layer} on the wrong layer "
                  f"(left/right {params['hor_layer']}, top/bottom {params['ver_layer']})")]


@register("pl_full_placement")
def full_placement(ctx: ValidationContext, params: dict) -> list[Check]:
    """Global placement -> IO pin re-placement -> padded legalization, from the floorplan."""
    checks = [all_logic_placed(ctx), _inside_core(ctx), placement_legal(ctx), netlist_intact(ctx)]
    checks += _pin_checks(ctx, params)
    m, err = _measure(ctx, params)
    if err:
        return checks + [err]
    checks.append(_row_orientation(m))
    g = _num(m, "gap_ll")
    checks.append(check("gap_between_cells", g is not None and g >= params["min_gap_ll_sites"] - 1e-6,
                        f"smallest gap between adjacent standard cells {_fmt(g, 2)} sites "
                        f"(>= {params['min_gap_ll_sites']})"))
    ref, _ = _measure(ctx, params, baseline=True, pre=params["reference_flow"], name="pl_reference")
    for key, label, ratio in (("io_hpwl", "io_net_wirelength", params["io_hpwl_ratio_max"]),
                              ("hpwl", "total_wirelength", params["hpwl_ratio_max"])):
        v, r = _num(m, key), _num(ref, key)
        limit = ratio * (r or 0.0)
        checks.append(check(label, v is not None and r is not None and v <= limit,
                            f"{_fmt(v, 1)} um, limit {limit:.1f} um ({ratio} x reference flow {_fmt(r, 1)} um)"))
    return checks
