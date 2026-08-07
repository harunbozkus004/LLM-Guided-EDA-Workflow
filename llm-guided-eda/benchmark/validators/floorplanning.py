"""Validators for the floorplanning category (FP-01 ... FP-08, DEV-FP-01).

Ground truth comes from the design-state probe, from output files and from
trusted oracle queries on the final database (IO pin shapes, rows and tap
cells, special-net wires). Power-grid tasks are checked against a reference
grid that the oracle rebuilds from the platform PDN configuration on the
agent's own floorplan, so any method that produces the configured grid passes.
"""
from __future__ import annotations

import math
import re
from typing import Any

from benchmark.task_validator import Check, ValidationContext, register
from benchmark.validators.common import approx, check, netlist_intact

_FLOAT = r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?"
ALL_METALS = [f"metal{i}" for i in range(1, 11)]
EDGES = ("left", "right", "bottom", "top")

# Trusted Tcl helpers for oracle queries. Every proc returns a JSON fragment.
_TCL = r"""
proc __fp_q {s} { return "\"[string map [list \\ \\\\ \" \\\" \n { } \t { }] $s]\"" }
proc __fp_die {} {
  set d [[ord::get_db_block] getDieArea]
  return "\[[$d xMin],[$d yMin],[$d xMax],[$d yMax]\]"
}
proc __fp_pins {} {
  set items {}
  foreach bt [[ord::get_db_block] getBTerms] {
    set st NONE
    set boxes {}
    foreach bp [$bt getBPins] {
      set st [$bp getPlacementStatus]
      foreach bx [$bp getBoxes] {
        set l [$bx getTechLayer]
        set ln ""
        if {$l != "NULL" && $l != ""} { set ln [$l getName] }
        lappend boxes "\[[__fp_q $ln],[$bx xMin],[$bx yMin],[$bx xMax],[$bx yMax]\]"
      }
    }
    lappend items "[__fp_q [$bt getName]]:\{\"status\":[__fp_q $st],\"io\":[__fp_q [$bt getIoType]],\"boxes\":\[[join $boxes ,]\]\}"
  }
  return "\{[join $items ,]\}"
}
proc __fp_rows {} {
  set rows {}
  foreach r [[ord::get_db_block] getRows] {
    set bb [$r getBBox]
    lappend rows "\[[$bb xMin],[$bb yMin],[$bb xMax],[$bb yMax]\]"
  }
  return "\[[join $rows ,]\]"
}
proc __fp_cells {master} {
  set items {}
  foreach inst [[ord::get_db_block] getInsts] {
    if {[[$inst getMaster] getName] != $master} { continue }
    set bb [$inst getBBox]
    lappend items "\[[__fp_q [$inst getPlacementStatus]],[$bb xMin],[$bb yMin],[$bb xMax],[$bb yMax]\]"
  }
  return "\[[join $items ,]\]"
}
proc __fp_pdn {nets} {
  set b [ord::get_db_block]
  set out {}
  foreach name $nets {
    set net [$b findNet $name]
    if {$net == "NULL"} { lappend out "[__fp_q $name]:null"; continue }
    set shapes {}
    set nvia 0
    foreach sw [$net getSWires] {
      foreach box [$sw getWires] {
        if {[$box isVia]} { incr nvia; continue }
        lappend shapes "\[[__fp_q [[$box getTechLayer] getName]],[$box xMin],[$box yMin],[$box xMax],[$box yMax]\]"
      }
    }
    lappend out "[__fp_q $name]:\{\"special\":[$net isSpecial],\"sig\":[__fp_q [$net getSigType]],\"vias\":$nvia,\"shapes\":\[[join $shapes ,]\]\}"
  }
  return "\{[join $out ,]\}"
}
proc __fp_pg_conn {} {
  set n 0; set ok 0; set bad {}
  foreach inst [[ord::get_db_block] getInsts] {
    set pins 0; set good 1
    foreach it [$inst getITerms] {
      set st [[$it getMTerm] getSigType]
      if {$st == "POWER"} { set want VDD } elseif {$st == "GROUND"} { set want VSS } else { continue }
      incr pins
      set net [$it getNet]
      if {$net == "NULL" || [$net getName] != $want} { set good 0 }
    }
    if {$pins == 0} { continue }
    incr n
    if {$good} { incr ok } elseif {[llength $bad] < 5} { lappend bad [$inst getName] }
  }
  return "\{\"insts\":$n,\"connected\":$ok,\"examples\":[__fp_q [join $bad { }]]\}"
}
proc __fp_pdn_clear {nets} {
  set b [ord::get_db_block]
  foreach name $nets {
    set net [$b findNet $name]
    if {$net != "NULL"} { foreach sw [$net getSWires] { odb::dbSWire_destroy $sw } }
  }
}
# Rebuild the grid from the platform configuration on this floorplan after
# removing the existing VDD/VSS wires (oracle session only; never saved).
proc __fp_pdn_ref {nets cfg} {
  __fp_pdn_clear $nets
  if {[catch {uplevel #0 [list source $cfg]; pdngen} err]} { return "\{\"error\":[__fp_q $err]\}" }
  return [__fp_pdn $nets]
}
# The same configuration built without trimming (pdngen -skip_trim); call after __fp_pdn_ref.
proc __fp_pdn_ref_untrimmed {nets} {
  __fp_pdn_clear $nets
  if {[catch {pdngen -skip_trim} err]} { return "\{\"error\":[__fp_q $err]\}" }
  return [__fp_pdn $nets]
}
"""


# ----------------------------------------------------------------- helpers
def _oracle(ctx: ValidationContext, emit: str, name: str) -> tuple[dict[str, Any] | None, str]:
    """Run an oracle query; failures (missing final.odb, Tcl errors) become an error string."""
    try:
        data = ctx.query(_TCL + "\n" + emit, name=name)
    except Exception as e:  # the agent's database may be unusable; never raise from a validator
        return None, (str(e).strip().splitlines() or ["oracle query failed"])[0][:200]
    if not isinstance(data, dict):
        return None, "oracle returned no JSON object"
    return data, ""


def _dbu(ctx: ValidationContext) -> float:
    return float(ctx.probe.get("dbu") or ctx.baseline.get("dbu") or 2000)


def _obj(d: Any, key: str) -> dict:
    """``d[key]`` if both are JSON objects, else an empty dict."""
    v = d.get(key) if isinstance(d, dict) else None
    return v if isinstance(v, dict) else {}


def _rows_check(p: dict, site: str | None) -> Check:
    rows = p.get("row_count") or 0
    ok = rows > 0 and (site is None or p.get("site") == site)
    return check("rows_created", ok, f"{rows} rows of site {p.get('site')!r}")


def _geometry_checks(p: dict, params: dict) -> list[Check]:
    """Utilization, aspect ratio and core-to-die margins of a utilization-driven floorplan."""
    checks = [_rows_check(p, params.get("site")),
              approx("core_utilization", p.get("utilization"), params["utilization"], atol=params["util_tol"])]
    core, die = p.get("core"), p.get("die")
    if not core or not die:
        checks.append(check("die_and_core_defined", False, "die or core area missing"))
        return checks
    w, h = core[2] - core[0], core[3] - core[1]
    checks.append(approx("core_aspect_ratio", h / w if w > 0 else None, params["aspect_ratio"], rtol=params["ar_tol"]))
    # Rows snap the core inwards: each margin grows by < 1 site horizontally and < 1 row vertically.
    margins = [core[0] - die[0], core[1] - die[1], die[2] - core[2], die[3] - core[3]]
    lo = params["margin_um"] - params["margin_tol_low"]
    hi_x = params["margin_um"] + params["margin_tol_high_x"]
    hi_y = params["margin_um"] + params["margin_tol_high_y"]
    ok = all(lo <= m <= (hi_x if i in (0, 2) else hi_y) for i, m in enumerate(margins))
    checks.append(check("core_to_die_margins", ok,
                        "margins L/B/R/T " + ", ".join(f"{m:.3f}" for m in margins)
                        + f" (allowed L/R {lo:g}..{hi_x:g}, B/T {lo:g}..{hi_y:g})"))
    return checks


def _tracks_check(p: dict) -> Check:
    layers = set(p.get("track_grid_layers") or [])
    missing = [m for m in ALL_METALS if m not in layers]
    return check("routing_tracks_all_layers", not missing, f"missing track grids: {missing}" if missing else "metal1-metal10")


_DESIGN_KEYS = ("die", "core", "row_count", "track_grid_layers", "inst_count", "master_counts", "status_counts",
                "io_pins", "signal_net_count", "special_net_swires")


def _design_unchanged(ctx: ValidationContext) -> Check:
    """The final database still equals the starting state (floorplan, cells, pins, nets, power grid)."""
    b, p = ctx.baseline, ctx.probe
    changed = [k for k in _DESIGN_KEYS if p.get(k) != b.get(k)]
    return check("design_unchanged", not changed, f"changed: {changed}" if changed else "identical to the starting state")


def _floorplan_unchanged(ctx: ValidationContext) -> Check:
    b, p = ctx.baseline, ctx.probe
    same = (p.get("die") == b.get("die") and p.get("core") == b.get("core")
            and p.get("row_count") == b.get("row_count"))
    return check("floorplan_unchanged", same, f"die {p.get('die')}, core {p.get('core')}, rows {p.get('row_count')}")


# ------------------------------------------------------------------ IO pins
def _pin_table(data: dict, hor: str, ver: str) -> list[dict]:
    """Normalize oracle pin data: edges touched, edge assigned (layer-consistent) and centre."""
    die = data.get("die") if isinstance(data.get("die"), list) and len(data["die"]) == 4 else [0, 0, 0, 0]
    pins = []
    for name, info in sorted((data.get("pins") or {}).items()):
        info = info if isinstance(info, dict) else {}
        boxes = [b for b in info.get("boxes") or [] if isinstance(b, list) and len(b) == 5]
        placed = info.get("status") in {"PLACED", "FIRM", "LOCKED", "COVER"} and bool(boxes)
        row: dict[str, Any] = {"name": name, "io": info.get("io"), "placed": placed,
                               "layer": None, "edges": set(), "edge": None, "cx": None, "cy": None}
        if placed:
            layer, x0, y0, x1, y1 = boxes[0]
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            # the pin shape must straddle or touch the edge from inside, within the span of that edge
            in_y, in_x = die[1] <= cy <= die[3], die[0] <= cx <= die[2]
            edges = set()
            if x0 <= die[0] < x1 and in_y:
                edges.add("left")
            if x0 < die[2] <= x1 and in_y:
                edges.add("right")
            if y0 <= die[1] < y1 and in_x:
                edges.add("bottom")
            if y0 < die[3] <= y1 and in_x:
                edges.add("top")
            # a pin at a die corner touches two edges: assign it to the edge its layer serves
            preferred = edges & ({"left", "right"} if layer == hor else {"bottom", "top"} if layer == ver else set())
            pick = preferred or edges
            row.update(layer=layer, edges=edges, edge=next((e for e in EDGES if e in pick), None), cx=cx, cy=cy)
        pins.append(row)
    return pins


def _basic_pin_checks(ctx: ValidationContext, pins: list[dict], hor: str, ver: str) -> list[Check]:
    want = ctx.baseline.get("io_pin_count") or len(pins)
    placed = [r for r in pins if r["placed"]]
    unplaced = [r["name"] for r in pins if not r["placed"]]
    checks = [check("all_pins_placed", len(pins) == want and not unplaced,
                    f"{len(placed)}/{want} placed" + (f"; unplaced e.g. {unplaced[:4]}" if unplaced else ""))]
    off = [r["name"] for r in placed if not r["edges"]]
    checks.append(check("pins_on_die_boundary", bool(placed) and not off,
                        f"{len(off)} placed pins not touching the die boundary {off[:4]}"))
    expected = {"left": hor, "right": hor, "bottom": ver, "top": ver}
    bad = [f"{r['name']}:{r['layer']}@{'/'.join(sorted(r['edges']))}" for r in placed
           if r["edges"] and not any(expected[e] == r["layer"] for e in r["edges"])]
    checks.append(check("pin_layers", bool(placed) and not bad,
                        f"{len(bad)} pins on the wrong layer for their edge (expect {hor} left/right, {ver} "
                        f"top/bottom) {bad[:4]}"))
    return checks


def _pin_oracle(ctx: ValidationContext, params: dict) -> tuple[list[dict] | None, list[Check]]:
    data, err = _oracle(ctx, '__oracle_emit "\\{\\"die\\":[__fp_die],\\"pins\\":[__fp_pins]\\}"', "fp_pins")
    if data is None:
        return None, [check("pin_query", False, err)]
    pins = _pin_table(data, params["hor_layer"], params["ver_layer"])
    return pins, _basic_pin_checks(ctx, pins, params["hor_layer"], params["ver_layer"])


def _along(r: dict) -> float:
    return r["cy"] if r["edge"] in ("left", "right") else r["cx"]


# --------------------------------------------------------------- tap cells
def _tap_checks(ctx: ValidationContext, rows: list, taps: list, params: dict) -> list[Check]:
    """Endcaps at both row ends plus a checkerboard of tap distance d (row pitch 2d, rows staggered by d)."""
    dbu = _dbu(ctx)
    d = params["tap_distance_um"] * dbu
    tol = params["tap_tol_um"] * dbu
    rows = sorted((r for r in rows if isinstance(r, list) and len(r) == 4), key=lambda r: (r[1], r[0]))
    taps = [t for t in taps if isinstance(t, list) and len(t) == 5]
    checks: list[Check] = []
    if not rows:
        return [check("tap_rows", False, "no placement rows")]
    per_row: list[list[list]] = [[] for _ in rows]
    stray = 0
    for t in taps:
        _st, x0, y0, x1, y1 = t
        idx = next((i for i, r in enumerate(rows) if y0 == r[1] and x0 >= r[0] and x1 <= r[2]), None)
        if idx is None:
            stray += 1
        else:
            per_row[idx].append(t)
    for lst in per_row:
        lst.sort(key=lambda t: t[1])
    checks.append(check("taps_inserted", len(taps) > 0 and stray == 0,
                        f"{len(taps)} {params['tap_master']} cells, {stray} not aligned to a row"))
    new_insts = (ctx.probe.get("inst_count") or 0) - (ctx.baseline.get("inst_count") or 0)
    checks.append(check("no_other_cells_inserted", new_insts == len(taps),
                        f"{new_insts} new instances vs {len(taps)} {params['tap_master']} cells"))

    no_endcap = [i for i, (r, lst) in enumerate(zip(rows, per_row))
                 if not (lst and lst[0][1] == r[0] and lst[-1][3] == r[2])]
    checks.append(check("endcaps_both_row_ends", not no_endcap,
                        f"{len(no_endcap)}/{len(rows)} rows lack an endcap at the start or end (e.g. rows {no_endcap[:5]})"))

    overlaps = sum(1 for lst in per_row for a, b in zip(lst, lst[1:]) if b[1] < a[3])
    checks.append(check("taps_do_not_overlap", overlaps == 0, f"{overlaps} overlapping tap/endcap pairs"))

    max_gap, worst = 0.0, None
    for i, lst in enumerate(per_row):
        for a, b in zip(lst, lst[1:]):
            if b[1] - a[1] > max_gap:
                max_gap, worst = b[1] - a[1], i
    checks.append(check("tap_coverage", bool(taps) and max_gap <= 2 * d + tol,
                        f"largest gap between neighbouring taps in a row {max_gap / dbu:.2f} um (row {worst}); "
                        f"allowed {(2 * d + tol) / dbu:.2f} um"))

    # Interior taps (cells at the row ends excluded). The first and last rows may carry both checkerboard phases.
    interior = [[t for t in lst if t[1] != r[0] and t[3] != r[2]] for r, lst in zip(rows, per_row)]
    last = len(rows) - 1
    dense = []
    for i, lst in enumerate(interior):
        min_pitch = (d if i in (0, last) else 2 * d) - tol
        gaps = [b[1] - a[1] for a, b in zip(lst, lst[1:])]
        if gaps and min(gaps) < min_pitch:
            dense.append((i, min(gaps) / dbu))
    checks.append(check("tap_row_pitch", not dense,
                        f"{len(dense)} rows with taps closer than the checkerboard pitch "
                        f"({2 * params['tap_distance_um']:g} um; {params['tap_distance_um']:g} um in the first/last row)"
                        + (f", e.g. row {dense[0][0]} gap {dense[0][1]:.2f} um" if dense else "")))

    aligned, pairs = [], 0
    for i in range(1, last - 1):
        a, b = interior[i], interior[i + 1]
        if not a or not b:
            continue
        pairs += 1
        nearest = min(min(abs(tb[1] - ta[1]) for ta in a) for tb in b)
        if nearest < d - tol:
            aligned.append((i, nearest / dbu))
    checks.append(check("checkerboard_stagger", pairs > 0 and not aligned,
                        f"{len(aligned)}/{pairs} adjacent row pairs whose taps are not staggered by "
                        f">= {params['tap_distance_um']:g} um" + (f", e.g. rows {aligned[0][0]}/{aligned[0][0] + 1}"
                                                                  f" offset {aligned[0][1]:.2f} um" if aligned else "")))
    return checks


# ------------------------------------------------------------- power grid
def _pdn_checks(ctx: ValidationContext, data: dict, params: dict) -> list[Check]:
    dbu = _dbu(ctx)
    agent, ref = _obj(data, "agent"), _obj(data, "ref")
    if "error" in ref:
        return [check("reference_grid", False,
                      f"platform grid could not be rebuilt on this floorplan: {str(ref['error'])[:150]}")]
    checks: list[Check] = []
    for net, sig in (("VDD", "POWER"), ("VSS", "GROUND")):
        a = _obj(agent, net)
        ok = a.get("special") == 1 and a.get("sig") == sig
        checks.append(check(f"supply_net_{net}", ok,
                            f"special={a.get('special')} sig={a.get('sig')}" if a else "missing"))
    total = present = 0
    missing_by_layer: dict[str, int] = {}
    bad_shapes: list[str] = []
    widths = params["layer_widths_um"]

    def shapes(d: dict) -> list[tuple]:
        return [tuple(s) for s in d.get("shapes") or [] if isinstance(s, list) and len(s) == 5]

    def contains(outer: tuple, inner: tuple) -> bool:
        # same layer and width; untrimmed straps may be longer than trimmed ones
        return (outer[0] == inner[0] and outer[1] <= inner[1] and outer[2] <= inner[2] and outer[3] >= inner[3]
                and outer[4] >= inner[4]
                and min(outer[3] - outer[1], outer[4] - outer[2]) == min(inner[3] - inner[1], inner[4] - inner[2]))

    untrimmed = _obj(data, "ref_untrimmed")
    extra: list[str] = []
    for net in ("VDD", "VSS"):
        rshapes, ashapes = shapes(_obj(ref, net)), shapes(_obj(agent, net))
        allowed = rshapes + shapes(_obj(untrimmed, net))
        total += len(rshapes)
        for s in rshapes:
            if any(contains(a, s) for a in ashapes):
                present += 1
            else:
                missing_by_layer[f"{net}/{s[0]}"] = missing_by_layer.get(f"{net}/{s[0]}", 0) + 1
        # every agent shape must belong to the configured grid (trimmed or untrimmed build)
        extra += [f"{net}/{s[0]}@({s[1] / dbu:g},{s[2] / dbu:g})" for s in ashapes
                  if not any(contains(r, s) for r in allowed)]
        for s in ashapes:
            w = min(s[3] - s[1], s[4] - s[2]) / dbu
            if s[0] not in widths or abs(w - widths[s[0]]) > 0.001:
                bad_shapes.append(f"{net}/{s[0]} w={w:.3f}")
    checks.append(check("grid_matches_config", total > 0 and present == total,
                        f"{present}/{total} shapes of the configured grid present"
                        + (f"; missing {missing_by_layer}" if missing_by_layer else "")))
    checks.append(check("grid_no_unconfigured_shapes", not extra,
                        f"{len(extra)} supply shapes that the configured grid does not contain"
                        + (f", e.g. {extra[:3]}" if extra else "")))
    checks.append(check("grid_layers_and_widths", not bad_shapes,
                        f"{len(bad_shapes)} supply shapes not on a configured layer/width {sorted(widths.items())}"
                        + (f", e.g. {bad_shapes[:3]}" if bad_shapes else "")))
    via_detail = []
    via_ok = True
    for net in ("VDD", "VSS"):
        av, rv = _obj(agent, net).get("vias"), _obj(ref, net).get("vias")
        av, rv = (v if isinstance(v, int) else 0 for v in (av, rv))
        via_ok = via_ok and av > 0 and av >= rv
        via_detail.append(f"{net} {av}/{rv}")
    checks.append(check("grid_vias", via_ok, "vias (agent/configured): " + ", ".join(via_detail)))
    return checks


def _conn_check(ctx: ValidationContext, conn: Any) -> Check:
    conn = conn if isinstance(conn, dict) else {}
    n, ok = conn.get("insts", 0), conn.get("connected", 0)
    total = ctx.probe.get("inst_count", 0)
    good = n > 0 and n == ok == total
    return check("pg_pins_connected", good,
                 f"{ok}/{total} instances with VDD->VDD and VSS->VSS"
                 + (f"; unconnected e.g. {conn.get('examples')}" if not good and conn.get("examples") else ""))


def _pdn_emit(cfg: str, extra: str = "") -> str:
    """Oracle body: the agent's grid and supply connectivity, then the reference grid rebuilt from ``cfg``.

    ``extra`` holds additional JSON members (Tcl-escaped, ending with a comma) evaluated beforehand.
    """
    return ("set __fp_agent [__fp_pdn {VDD VSS}]\n"
            "set __fp_conn [__fp_pg_conn]\n"
            "set __fp_ref [__fp_pdn_ref {VDD VSS} " + cfg + "]\n"
            "set __fp_ref_u [__fp_pdn_ref_untrimmed {VDD VSS}]\n"
            '__oracle_emit "\\{' + extra + '\\"agent\\":$__fp_agent,\\"conn\\":$__fp_conn,\\"ref\\":$__fp_ref,'
            '\\"ref_untrimmed\\":$__fp_ref_u\\}"\n')


# ================================================================ validators
@register("fp_util_init_report")
def util_init_report(ctx: ValidationContext, params: dict) -> list[Check]:
    """FP-01: utilization-driven floorplan plus a die/core/utilization report checked against the database."""
    p = ctx.probe
    checks = _geometry_checks(p, params)
    checks.append(netlist_intact(ctx))
    text = ctx.read_output(params["report"])
    if text is None:
        checks.append(check("report_file", False, f"{params['report']} missing"))
        return checks
    checks.append(check("report_file", True, f"{len(text)} bytes"))

    def numbers(key: str, n: int) -> list[float] | None:
        for line in text.splitlines():
            m = re.match(rf"\s*{key}\w*\b[\s:=]*(.*)$", line, re.I)
            if m:
                nums = [float(x) for x in re.findall(_FLOAT, m.group(1))]
                if len(nums) >= n:
                    return nums[:n]
        return None

    tol = params["coord_tol"]
    for key, actual in (("DIE", p.get("die")), ("CORE", p.get("core"))):
        got = numbers(key, 4)
        ok = got is not None and actual is not None and all(abs(a - b) <= tol for a, b in zip(got, actual))
        checks.append(check(f"report_{key.lower()}", ok, f"reported {got}, database {actual} (+/- {tol} um)"))
    got_util = numbers("UTIL", 1)
    util = p.get("utilization")
    if got_util is None or util is None:
        checks.append(check("report_util", False, f"reported {got_util}, database {util}"))
    else:
        checks.append(approx("report_util", got_util[0], 100.0 * util, atol=params["util_report_tol"]))
    return checks


@register("fp_explicit_die_core")
def explicit_die_core(ctx: ValidationContext, params: dict) -> list[Check]:
    """FP-02: explicit die/core boxes (core snapped inwards by < 1 site / 1 row) and tracks on all layers."""
    p = ctx.probe
    checks = [_rows_check(p, params.get("site"))]
    die, core = p.get("die"), p.get("core")
    want_die, want_core = params["die"], params["core"]
    eps = params["die_tol"]
    if not die or not core:
        checks.append(check("die_and_core_defined", False, "die or core area missing"))
    else:
        checks.append(check("die_area", all(abs(a - b) <= eps for a, b in zip(die, want_die)),
                            f"die {die}, requested {want_die}"))
        sx, sy = params["site_width"] + eps, params["row_height"] + eps
        inside = (core[0] >= want_core[0] - eps and core[1] >= want_core[1] - eps
                  and core[2] <= want_core[2] + eps and core[3] <= want_core[3] + eps)
        close = (core[0] - want_core[0] <= sx and want_core[2] - core[2] <= sx
                 and core[1] - want_core[1] <= sy and want_core[3] - core[3] <= sy)
        checks.append(check("core_area", inside and close,
                            f"core (row bbox) {core}, requested {want_core}; edges may snap inwards by < 1 site "
                            f"({params['site_width']}) / 1 row ({params['row_height']})"))
    checks.append(_tracks_check(p))
    checks.append(netlist_intact(ctx))
    return checks


@register("fp_io_layers_spacing")
def io_layers_spacing(ctx: ValidationContext, params: dict) -> list[Check]:
    """FP-03: every pin on the boundary, on the requested layer for its edge, with a minimum spacing per edge."""
    pins, checks = _pin_oracle(ctx, params)
    if pins is not None:
        dbu = _dbu(ctx)
        min_gap, where = math.inf, None
        for edge in EDGES:
            pos = sorted(_along(r) for r in pins if r["placed"] and r["edge"] == edge)
            for a, b in zip(pos, pos[1:]):
                if b - a < min_gap:
                    min_gap, where = b - a, edge
        need = params["min_distance_um"] - params["spacing_tol_um"]
        ok = math.isfinite(min_gap) and min_gap / dbu >= need
        checks.append(check("min_pin_spacing", ok,
                            f"closest neighbouring pins {min_gap / dbu if math.isfinite(min_gap) else None} um "
                            f"apart ({where} edge); required >= {params['min_distance_um']} um"))
    checks += [_floorplan_unchanged(ctx), netlist_intact(ctx)]
    return checks


@register("fp_io_bus_order")
def io_bus_order(ctx: ValidationContext, params: dict) -> list[Check]:
    """FP-05: all pins placed; one bus on a given edge, strictly ordered by bit index."""
    pins, checks = _pin_oracle(ctx, params)
    if pins is not None:
        bus, width, edge = params["bus"], params["width"], params["edge"]
        by_name = {r["name"]: r for r in pins}
        bits = [by_name.get(f"{bus}[{i}]") for i in range(width)]
        missing = [i for i, r in enumerate(bits) if r is None or not r["placed"]]
        off = [i for i, r in enumerate(bits) if r is not None and r["placed"] and r["edge"] != edge]
        checks.append(check("bus_on_edge", not missing and not off,
                            f"{width - len(missing) - len(off)}/{width} {bus} bits on the {edge} edge"
                            + (f"; elsewhere: bits {off[:6]}" if off else "")
                            + (f"; unplaced: bits {missing[:6]}" if missing else "")))
        pos = [_along(r) if r is not None and r["placed"] else None for r in bits]
        inversions = [i for i in range(1, width)
                      if pos[i] is None or pos[i - 1] is None or not pos[i] > pos[i - 1]]
        checks.append(check("bus_bit_order", not inversions,
                            f"{len(inversions)} bits not after their predecessor along the edge"
                            + (f", first at bit {inversions[0]}" if inversions else "")))
    checks += [_floorplan_unchanged(ctx), netlist_intact(ctx)]
    return checks


@register("fp_io_direction_edges")
def io_direction_edges(ctx: ValidationContext, params: dict) -> list[Check]:
    """DEV-FP-01: input pins on one edge, output pins on another."""
    pins, checks = _pin_oracle(ctx, params)
    if pins is not None:
        for io, edge in (("INPUT", params["input_edge"]), ("OUTPUT", params["output_edge"])):
            group = [r for r in pins if r["io"] == io]
            bad = [r["name"] for r in group if not r["placed"] or r["edge"] != edge]
            checks.append(check(f"{io.lower()}s_on_{edge}", bool(group) and not bad,
                                f"{len(group) - len(bad)}/{len(group)} {io.lower()} pins on the {edge} edge"
                                + (f"; e.g. {bad[:4]}" if bad else "")))
    checks += [_floorplan_unchanged(ctx), netlist_intact(ctx)]
    return checks


@register("fp_def_export")
def def_export(ctx: ValidationContext, params: dict) -> list[Check]:
    """FP-04: DEF file of the given version whose content matches the starting floorplan."""
    b = ctx.baseline
    text = ctx.read_output(params["file"])
    if not text or not text.strip():
        return [check("def_file", False, f"{params['file']} missing or empty"), _design_unchanged(ctx)]
    checks = [check("def_file", True, f"{len(text)} bytes"), _design_unchanged(ctx)]

    def first(pattern: str) -> re.Match | None:
        return re.search(pattern, text, re.M)

    m = first(r"^\s*VERSION\s+([^\s;]+)\s*;")
    checks.append(check("def_version", bool(m) and m.group(1) == params["version"],
                        f"VERSION {m.group(1) if m else None}, required {params['version']}"))
    m = first(r"^\s*DESIGN\s+([^\s;]+)\s*;")
    u = first(r"^\s*UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;")
    units = int(u.group(1)) if u else 0
    checks.append(check("def_design_units", bool(m) and m.group(1) == b.get("top") and units > 0,
                        f"DESIGN {m.group(1) if m else None}, UNITS {units or None}"))
    m = first(r"^\s*DIEAREA\s+([^;]*);")
    die = None
    if m and units:
        pts = [(float(x), float(y)) for x, y in re.findall(rf"\(\s*({_FLOAT})\s+({_FLOAT})\s*\)", m.group(1))]
        if pts:
            die = [min(x for x, _ in pts) / units, min(y for _, y in pts) / units,
                   max(x for x, _ in pts) / units, max(y for _, y in pts) / units]
    want_die = b.get("die") or []
    checks.append(check("def_diearea", die is not None and len(want_die) == 4
                        and all(abs(a - c) <= 1e-3 for a, c in zip(die, want_die)), f"DIEAREA {die}, floorplan {want_die}"))
    n_rows = len(re.findall(r"^\s*ROW\s+\S+", text, re.M))
    checks.append(check("def_rows", n_rows == b.get("row_count"), f"{n_rows} ROW statements, floorplan {b.get('row_count')}"))
    track_layers = set()
    for body in re.findall(r"^\s*TRACKS\s+[XY]\s+[^;]*?\bLAYER\s+([^;]*);", text, re.M):
        track_layers.update(body.split())
    want_tracks = set(b.get("track_grid_layers") or [])
    checks.append(check("def_tracks", bool(want_tracks) and want_tracks <= track_layers,
                        f"TRACKS on {len(track_layers)} layers, floorplan {len(want_tracks)}"))

    def section(name: str) -> tuple[int | None, str]:
        sm = re.search(rf"^\s*{name}\s+(\d+)\s*;(.*?)^\s*END\s+{name}\b", text, re.M | re.S)
        return (int(sm.group(1)), sm.group(2)) if sm else (None, "")

    n_comp, comp = section("COMPONENTS")
    entries = re.findall(r"^\s*-\s+(\S+)\s+(\S+)", comp, re.M)
    taps = sum(1 for _, master in entries if master == params["tap_master"])
    want_taps = (b.get("master_counts") or {}).get(params["tap_master"], 0)
    checks.append(check("def_components", n_comp == b.get("inst_count") == len(entries) and taps == want_taps,
                        f"{len(entries)} components (header {n_comp}), {taps} {params['tap_master']}; "
                        f"floorplan {b.get('inst_count')} / {want_taps}"))
    n_pins, pin_text = section("PINS")
    want_pins = b.get("io_pins") or {}
    found: dict[str, tuple[str, float, float] | None] = {}
    for chunk in re.split(r"^\s*-\s+", pin_text, flags=re.M)[1:]:
        name = chunk.split()[0] if chunk.split() else ""
        lay = re.search(rf"\+\s*LAYER\s+(\S+)\s*\(\s*({_FLOAT})\s+({_FLOAT})\s*\)\s*\(\s*({_FLOAT})\s+({_FLOAT})\s*\)", chunk)
        pl = re.search(rf"\+\s*(?:PLACED|FIXED|COVER)\s*\(\s*({_FLOAT})\s+({_FLOAT})\s*\)\s*(\S+)", chunk)
        if lay and pl and pl.group(3) == "N" and units:
            cx = float(pl.group(1)) + (float(lay.group(2)) + float(lay.group(4))) / 2
            cy = float(pl.group(2)) + (float(lay.group(3)) + float(lay.group(5))) / 2
            found[name] = (lay.group(1), cx / units, cy / units)
        else:
            found[name] = None
    wrong = [n for n, info in want_pins.items() if not info.get("placed") or found.get(n) is None
             or found[n][0] != info.get("layer") or abs(found[n][1] - info["x"]) > 1e-3 or abs(found[n][2] - info["y"]) > 1e-3]
    checks.append(check("def_pins", n_pins == len(want_pins) == len(found) and not wrong,
                        f"{len(found)} pins (header {n_pins}); {len(wrong)} missing/unplaced/moved vs the floorplan"
                        + (f", e.g. {wrong[:3]}" if wrong else "")))
    _, special = section("SPECIALNETS")
    nets_ok = []
    for net in params["supply_nets"]:
        em = re.search(rf"^\s*-\s+{net}\b(.*?)(?=^\s*-\s+|\Z)", special, re.M | re.S)
        nets_ok.append(bool(em) and "ROUTED" in em.group(1))
    followpins = len(re.findall(r"\bFOLLOWPIN\b", special))
    want_fp = (b.get("row_count") or 0) + 1
    checks.append(check("def_power_grid", all(nets_ok) and followpins == want_fp,
                        f"routed special nets {dict(zip(params['supply_nets'], nets_ok))}, {followpins} followpin rails "
                        f"(floorplan {want_fp})"))
    n_nets, _ = section("NETS")
    checks.append(check("def_nets", n_nets == b.get("signal_net_count"),
                        f"NETS {n_nets}, floorplan {b.get('signal_net_count')} signal nets"))
    return checks


@register("fp_tapcells")
def tapcells(ctx: ValidationContext, params: dict) -> list[Check]:
    """FP-06: endcaps on every row end plus a checkerboard of taps with the requested distance."""
    emit = f'__oracle_emit "\\{{\\"rows\\":[__fp_rows],\\"taps\\":[__fp_cells {params["tap_master"]}]\\}}"'
    data, err = _oracle(ctx, emit, "fp_taps")
    checks = [_floorplan_unchanged(ctx), netlist_intact(ctx)]
    if data is None:
        return checks + [check("tap_query", False, err)]
    return checks + _tap_checks(ctx, data.get("rows") or [], data.get("taps") or [], params)


@register("fp_pdn_platform")
def pdn_platform(ctx: ValidationContext, params: dict) -> list[Check]:
    """FP-07: power grid identical to the platform configuration and all cell supply pins connected."""
    data, err = _oracle(ctx, _pdn_emit(params["pdn_config"]), "fp_pdn")
    checks = [_floorplan_unchanged(ctx), netlist_intact(ctx)]
    if data is None:
        return checks + [check("pdn_query", False, err)]
    return checks + _pdn_checks(ctx, data, params) + [_conn_check(ctx, data.get("conn"))]


@register("fp_full_flow")
def full_flow(ctx: ValidationContext, params: dict) -> list[Check]:
    """FP-08: floorplan + tracks + IO pins + tap cells + platform power grid, all in one script."""
    p = ctx.probe
    checks = _geometry_checks(p, params) + [_tracks_check(p), netlist_intact(ctx)]
    # Pins, rows and taps are collected before the oracle rebuilds the reference grid.
    emit = ("set __fp_die_json [__fp_die]\nset __fp_pins_json [__fp_pins]\nset __fp_rows_json [__fp_rows]\n"
            f"set __fp_taps_json [__fp_cells {params['tap_master']}]\n"
            + _pdn_emit(params["pdn_config"], '\\"die\\":$__fp_die_json,\\"pins\\":$__fp_pins_json,'
                                              '\\"rows\\":$__fp_rows_json,\\"taps\\":$__fp_taps_json,'))
    data, err = _oracle(ctx, emit, "fp_full")
    if data is None:
        return checks + [check("floorplan_query", False, err)]
    pins = _pin_table(data, params["hor_layer"], params["ver_layer"])
    checks += _basic_pin_checks(ctx, pins, params["hor_layer"], params["ver_layer"])
    checks += _tap_checks(ctx, data.get("rows") or [], data.get("taps") or [], params)
    checks += _pdn_checks(ctx, data, params)
    checks.append(_conn_check(ctx, data.get("conn")))
    return checks
