"""Validators for the routing category (RT-01 ... RT-08, DEV-RT-01).

Routing outcomes are measured on the database the agent script left behind:

* global routing   -> route guides (dbGuide) per net. A guide box that spans
  more than one GCell on a layer is a wire on that layer; single-GCell boxes
  are pin-access / via stacks. (Verified to give exactly the per-net layer sets
  of ``report_wire_length -verbose`` on this OpenROAD build.)
* detailed routing -> dbWire per net (probe counts, dbWireDecoder walk).
* parasitics/timing -> trusted re-computation in a fresh oracle session.

Reported numbers are always compared with ground truth, so hard-coded values
written with ``puts`` fail unless they happen to be right.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from benchmark.task_validator import Check, ValidationContext, register
from benchmark.validators.common import approx, check, netlist_intact

# A standalone number (digits inside identifiers such as "metal2" do not count).
_NUM_RE = re.compile(r"(?<![\w.])[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?(?![\d.])")

# ----------------------------------------------------------------- oracle bodies
# All guides of the database in route-guide file format.
GUIDES_TCL = r"""
set lines {}
foreach net [[ord::get_db_block] getNets] {
  set guides [$net getGuides]
  if {![llength $guides]} { continue }
  lappend lines [$net getName] "("
  foreach g $guides {
    set b [$g getBox]
    lappend lines "[$b xMin] [$b yMin] [$b xMax] [$b yMax] [[$g getLayer] getName]"
  }
  lappend lines ")"
}
__oracle_emit_dict [dict create guides [join $lines "\n"]]
"""

# Sum of the per-net global-route wirelength (routes rebuilt from the stored guides).
GR_WIRELENGTH_TCL = r"""
set have [grt::have_routes]
set total 0.0
set nets 0
if {$have} {
  report_wire_length -net * -global_route -file __rt_grwl.txt
  set f [open __rt_grwl.txt r]
  foreach line [lrange [split [read $f] "\n"] 1 end] {
    set t [regexp -all -inline {\S+} $line]
    if {[llength $t] >= 3 && [string is double -strict [lindex $t 2]]} {
      set total [expr {$total + [lindex $t 2]}]
      incr nets
    }
  }
  close $f
}
__oracle_emit_dict [dict create have_routes $have total_um $total nets $nets]
"""

# Per net: kind (S signal, L leaf clock, C non-leaf clock) | routing levels with
# global-route wires | routing levels of the net's IO pins.
GR_LAYERS_TCL = r"""
set block [ord::get_db_block]
set out [dict create]
foreach layer [[ord::get_db_tech] getLayers] {
  if {[$layer getRoutingLevel] > 0} { dict set out "__layer:[$layer getName]" [$layer getRoutingLevel] }
}
set gg [$block getGCellGrid]
if {$gg == "NULL"} {
  dict set out __error "no GCell grid in the database (not globally routed)"
} else {
  set gx [lsort -integer -unique [$gg getGridX]]
  set gy [lsort -integer -unique [$gg getGridY]]
  set leaf [dict create]
  foreach pin [all_registers -clock_pins] {
    foreach n [get_nets -quiet -of_objects $pin] { dict set leaf [[sta::sta_to_db_net $n] getName] 1 }
  }
  foreach net [$block getNets] {
    if {[$net isSpecial] || [$net getSigType] in {POWER GROUND}} { continue }
    set guides [$net getGuides]
    if {![llength $guides]} { continue }
    set wires {}
    foreach g $guides {
      set b [$g getBox]
      set span [expr {[lsearch -sorted -integer -bisect $gx [expr {[$b xMax] - 1}]]
                      - [lsearch -sorted -integer -bisect $gx [$b xMin]]
                      + [lsearch -sorted -integer -bisect $gy [expr {[$b yMax] - 1}]]
                      - [lsearch -sorted -integer -bisect $gy [$b yMin]]}]
      set lv [[$g getLayer] getRoutingLevel]
      if {$span > 0 && $lv ni $wires} { lappend wires $lv }
    }
    set io {}
    foreach bt [$net getBTerms] {
      foreach bp [$bt getBPins] {
        foreach bx [$bp getBoxes] {
          set lv [[$bx getTechLayer] getRoutingLevel]
          if {$lv ni $io} { lappend io $lv }
        }
      }
    }
    set kind S
    if {[$net getSigType] == "CLOCK"} { set kind [expr {[dict exists $leaf [$net getName]] ? "L" : "C"}] }
    dict set out [$net getName] "$kind|[join [lsort -integer $wires] ,]|[join [lsort -integer $io] ,]"
  }
}
__oracle_emit_dict $out
"""

# Worst setup slack with parasitics estimated from the stored global routing.
GRT_SLACK_TCL = r"""
estimate_parasitics -global_routing
__oracle_emit_dict [dict create wns [sta::worst_slack -max] wns_hold [sta::worst_slack -min]]
"""

# Global-route wirelength of every clock net (sigType CLOCK), plus all net names.
CLOCK_GRWL_TCL = r"""
set have [grt::have_routes]
set out [dict create have_routes $have]
set clock_nets {}
set all {}
foreach net [[ord::get_db_block] getNets] {
  lappend all [$net getName]
  if {[$net getSigType] == "CLOCK"} { lappend clock_nets [$net getName] }
}
dict set out all_nets [join $all "\n"]
report_wire_length -net $clock_nets -global_route -file __rt_clkwl.txt
set f [open __rt_clkwl.txt r]
foreach line [lrange [split [read $f] "\n"] 1 end] {
  set t [regexp -all -inline {\S+} $line]
  if {[llength $t] >= 3} { dict set out "wl:[lindex $t 1]" [lindex $t 2] }
}
close $f
__oracle_emit_dict $out
"""

# RC extraction with the platform rules, the SPEF it produces (per-net total cap)
# and the worst setup slack once STA has read that SPEF.
RCX_TCL = r"""
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef __rt_oracle.spef
read_spef __rt_oracle.spef
set out [dict create __wns [sta::worst_slack -max] __wns_hold [sta::worst_slack -min]]
set map [dict create]
set f [open __rt_oracle.spef r]
while {[gets $f line] >= 0} {
  if {[regexp {^\*([0-9]+)\s+(\S+)\s*$} $line -> idx name]} { dict set map $idx $name }
  if {[regexp {^\*D_NET\s+(\S+)\s+(\S+)} $line -> ref cap]} {
    if {[regexp {^\*([0-9]+)$} $ref -> idx] && [dict exists $map $idx]} { set ref [dict get $map $idx] }
    dict set out "cap:$ref" $cap
  }
}
close $f
__oracle_emit_dict $out
"""

# Detailed-route wirelength per layer (um), walking every dbWire path.
DR_LAYER_WL_TCL = r"""
set block [ord::get_db_block]
set dbu [$block getDefUnits]
set out [dict create]
foreach layer [[ord::get_db_tech] getLayers] {
  if {[$layer getRoutingLevel] > 0} { dict set out "__layer:[$layer getName]" [$layer getRoutingLevel] }
}
array set len {}
foreach net [$block getNets] {
  set w [$net getWire]
  if {$w == "NULL"} { continue }
  set dec [odb::dbWireDecoder]
  $dec begin $w
  set layer ""
  set prev {}
  while {1} {
    set op [$dec next]
    if {$op == $odb::dbWireDecoder_END_DECODE} { break }
    if {$op in [list $odb::dbWireDecoder_PATH $odb::dbWireDecoder_JUNCTION $odb::dbWireDecoder_SHORT $odb::dbWireDecoder_VWIRE]} {
      set layer [[$dec getLayer] getName]
      set prev {}
    } elseif {$op == $odb::dbWireDecoder_POINT || $op == $odb::dbWireDecoder_POINT_EXT} {
      set pt [$dec getPoint]
      if {[llength $prev]} {
        if {![info exists len($layer)]} { set len($layer) 0 }
        set len($layer) [expr {$len($layer) + abs([lindex $pt 0] - [lindex $prev 0]) + abs([lindex $pt 1] - [lindex $prev 1])}]
      }
      set prev [lrange $pt 0 1]
    } elseif {$op == $odb::dbWireDecoder_VIA || $op == $odb::dbWireDecoder_TECH_VIA} {
      set l [$dec getLayer]
      if {$l != "NULL"} { set layer [$l getName] }
    }
  }
}
foreach l [array names len] { dict set out "wl:$l" [expr {double($len($l)) / $dbu}] }
__oracle_emit_dict $out
"""


# ----------------------------------------------------------------- helpers
def _numbers(text: str) -> list[float]:
    return [float(x) for x in _NUM_RE.findall(text)]


def _single_number(ctx: ValidationContext, path: str) -> tuple[float | None, Check]:
    """The one number a report file must contain (units/words around it are tolerated)."""
    name = f"report:{path}"
    text = ctx.read_output(path)
    if text is None:
        return None, Check(name, False, "missing")
    nums = _numbers(text)
    if len(nums) != 1:
        return None, Check(name, False, f"expected exactly one number, found {len(nums)}: {text.strip()[:80]!r}")
    return nums[0], Check(name, True, f"reports {nums[0]:g}")


def _oracle(ctx: ValidationContext, body: str, name: str) -> tuple[dict[str, Any] | None, Check | None]:
    """Trusted query on the final database; failure (e.g. a broken design) becomes a failed check."""
    try:
        return ctx.query(body, name=name), None
    except (RuntimeError, ValueError) as e:
        return None, Check(f"oracle:{name}", False, (str(e).splitlines() or ["query failed"])[0][:200])


def _layer_levels(data: dict[str, Any]) -> dict[str, int]:
    return {k.split(":", 1)[1]: int(v) for k, v in data.items() if k.startswith("__layer:")}


def _parse_guides(text: str) -> dict[str, Counter]:
    """Route-guide file -> {net: Counter of (xl, yl, xh, yh, layer)}; ValueError if malformed."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    guides: dict[str, Counter] = {}
    i = 0
    while i < len(lines):
        net = lines[i]
        if i + 1 >= len(lines) or lines[i + 1] != "(":
            raise ValueError(f"expected '(' after net {net[:40]!r}")
        i += 2
        boxes: Counter = Counter()
        while i < len(lines) and lines[i] != ")":
            t = lines[i].split()
            if len(t) != 5:
                raise ValueError(f"bad guide line {lines[i][:60]!r}")
            try:
                boxes[(int(t[0]), int(t[1]), int(t[2]), int(t[3]), t[4])] += 1
            except ValueError:
                raise ValueError(f"bad guide coordinates {lines[i][:60]!r}") from None
            i += 1
        if i >= len(lines):
            raise ValueError(f"unterminated guide block for net {net[:40]!r}")
        i += 1
        guides.setdefault(net, Counter()).update(boxes)
    return guides


def _compare_guides(got: dict[str, Counter], want: dict[str, Counter]) -> tuple[bool, str]:
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    differ = sorted(n for n in set(want) & set(got) if got[n] != want[n])
    ok = not (missing or extra or differ)
    detail = (f"{len(want)} guided nets in the database, {len(got)} compared; "
              f"missing {len(missing)}, extra {len(extra)}, different boxes {len(differ)}")
    examples = (missing + extra + differ)[:3]
    if examples:
        detail += " (e.g. " + ", ".join(examples) + ")"
    return ok, detail


def _all_nets_guided(ctx: ValidationContext) -> Check:
    # Disconnecting nets must not shrink the set of nets that have to be routed.
    p = ctx.probe
    n, g = p.get("routable_net_count", 0), p.get("guided_net_count", 0)
    n0 = ctx.baseline.get("routable_net_count", 0)
    return check("all_nets_globally_routed", n > 0 and n >= n0 and g == n,
                 f"{g}/{n} routable nets have route guides ({n0} in the starting state)")


def _all_nets_detail_routed(ctx: ValidationContext) -> Check:
    p = ctx.probe
    n, r = p.get("routable_net_count", 0), p.get("routed_net_count", 0)
    n0 = ctx.baseline.get("routable_net_count", 0)
    return check("all_nets_detail_routed", n > 0 and n >= n0 and r == n,
                 f"{r}/{n} routable nets have detailed routing ({n0} in the starting state)")


def _guides_unchanged(ctx: ValidationContext) -> Check:
    """The stored global routing is still the one of the starting state."""
    want = _parse_guides(str(ctx.query_baseline(GUIDES_TCL)["guides"]))
    data, fail = _oracle(ctx, GUIDES_TCL, "rt_guides")
    if fail:
        return fail
    try:
        got = _parse_guides(str(data.get("guides", "")))
    except ValueError as e:  # e.g. net names that break the guide format
        return check("existing_global_routing_kept", False, f"cannot read the final guides: {e}")
    ok, detail = _compare_guides(got, want)
    return check("existing_global_routing_kept", ok, detail)


def _unescape(name: str) -> str:
    return name.replace("\\", "")


def _parse_spef_caps(text: str) -> dict[str, float]:
    """Total capacitance of every *D_NET, with *NAME_MAP indices resolved."""
    name_map: dict[str, str] = {}
    caps: dict[str, float] = {}
    for line in text.splitlines():
        m = re.match(r"^\*(\d+)\s+(\S+)\s*$", line)
        if m:
            name_map[m.group(1)] = m.group(2)
            continue
        m = re.match(r"^\*D_NET\s+(\S+)\s+(\S+)", line)
        if m:
            ref = m.group(1)
            if ref.startswith("*") and ref[1:] in name_map:
                ref = name_map[ref[1:]]
            try:
                caps[ref] = float(m.group(2))
            except ValueError:
                continue
    return caps


_WIRING_KEYS = {"ROUTED", "FIXED", "COVER", "NOSHIELD"}


def _wiring_length(tokens: list[str]) -> tuple[bool, int]:
    """(has wiring, total path length in DBU) of one DEF net statement."""
    has_wiring = False
    total = 0
    in_path = False
    prev: tuple[int, int] | None = None
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in _WIRING_KEYS or (t == "NEW" and has_wiring):
            has_wiring = in_path = True
            prev = None
            i += 2  # keyword + layer name
            continue
        if t == "+":
            in_path = False
            i += 1
            continue
        if not in_path:
            i += 1
            continue
        if t in ("RECT", "VIRTUAL"):
            # RECT ( dx1 dy1 dx2 dy2 ) is a patch, VIRTUAL ( x y ) a jump: neither adds length.
            j = tokens.index(")", i) if ")" in tokens[i:] else len(tokens)
            if t == "VIRTUAL" and j - i >= 4:
                prev = _point(tokens[i + 2:j], prev)
            i = j + 1
            continue
        if t in ("MASK", "STYLE", "TAPERRULE", "SHAPE"):
            i += 2
            continue
        if t == "(":
            j = tokens.index(")", i) if ")" in tokens[i:] else len(tokens)
            pt = _point(tokens[i + 1:j], prev)
            if pt is not None and prev is not None:
                total += abs(pt[0] - prev[0]) + abs(pt[1] - prev[1])
            prev = pt
            i = j + 1
            continue
        i += 1  # via name, TAPER, ...
    return has_wiring, total


def _point(fields: list[str], prev: tuple[int, int] | None) -> tuple[int, int] | None:
    if len(fields) < 2:
        return prev
    try:
        x = prev[0] if fields[0] == "*" and prev else int(float(fields[0]))
        y = prev[1] if fields[1] == "*" and prev else int(float(fields[1]))
    except (ValueError, OverflowError):
        return prev
    return x, y


def _parse_def(text: str) -> dict[str, Any]:
    """Minimal DEF reader: header statements, section counts and routed length of every net."""
    out: dict[str, Any] = {"version": None, "design": None, "units": None, "components": None,
                           "pins": None, "routed_nets": 0, "wirelength_dbu": 0}
    for key, rx in (("version", r"^\s*VERSION\s+(\S+)\s*;"), ("design", r"^\s*DESIGN\s+(\S+)\s*;"),
                    ("units", r"^\s*UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;"),
                    ("components", r"^\s*COMPONENTS\s+(\d+)\s*;"), ("pins", r"^\s*PINS\s+(\d+)\s*;")):
        m = re.search(rx, text, re.M)
        if m:
            out[key] = m.group(1)
    for key in ("units", "components", "pins"):
        if out[key] is not None:
            out[key] = int(out[key])
    m = re.search(r"^\s*NETS\s+\d+\s*;(.*?)^\s*END\s+NETS\b", text, re.M | re.S)
    if m:
        for stmt in m.group(1).split(";"):
            tokens = re.findall(r"[()]|[^\s()]+", stmt)
            if len(tokens) < 2 or tokens[0] != "-":
                continue
            wired, length = _wiring_length(tokens[2:])
            if wired:
                out["routed_nets"] += 1
                out["wirelength_dbu"] += length
    return out


# ----------------------------------------------------------------- validators
@register("rt_global_route_guides")
def global_route_guides(ctx: ValidationContext, params: dict) -> list[Check]:
    """RT-01: design globally routed and the guide file holds exactly the stored guides."""
    checks = [netlist_intact(ctx), _all_nets_guided(ctx)]
    path = params["guide_file"]
    text = ctx.read_output(path)
    if text is None or not text.strip():
        checks.append(check(f"file:{path}", False, "missing" if text is None else "empty"))
        return checks
    try:
        got = _parse_guides(text)
    except ValueError as e:
        checks.append(check(f"file:{path}", False, f"not a route-guide file: {e}"))
        return checks
    data, fail = _oracle(ctx, GUIDES_TCL, "rt_guides")
    if fail:
        return checks + [fail]
    try:
        want = _parse_guides(str(data.get("guides", "")))
    except ValueError as e:
        return checks + [check("guide_file_matches_routing", False, f"cannot read the final guides: {e}")]
    ok, detail = _compare_guides(got, want)
    checks.append(check("guide_file_matches_routing", ok and bool(want), detail))
    return checks


@register("rt_global_route_wirelength")
def global_route_wirelength(ctx: ValidationContext, params: dict) -> list[Check]:
    """RT-02: design globally routed and the reported total equals the routed wirelength."""
    checks = [netlist_intact(ctx), _all_nets_guided(ctx)]
    value, c = _single_number(ctx, params["report"])
    checks.append(c)
    data, fail = _oracle(ctx, GR_WIRELENGTH_TCL, "rt_grwl")
    if fail:
        return checks + [fail]
    if not data.get("have_routes") or not data.get("nets"):
        checks.append(check("total_global_route_wirelength", False, "no global routes in the final database"))
    elif value is not None:
        checks.append(approx("total_global_route_wirelength", value, float(data["total_um"]), rtol=params["rtol"]))
    return checks


@register("rt_routing_layers")
def routing_layers(ctx: ValidationContext, params: dict) -> list[Check]:
    """RT-03: global-route wires stay inside the requested signal / clock layer ranges."""
    checks = [netlist_intact(ctx), _all_nets_guided(ctx)]
    data, fail = _oracle(ctx, GR_LAYERS_TCL, "rt_layers")
    if fail:
        return checks + [fail]
    if "__error" in data:
        return checks + [check("route_guides_available", False, str(data["__error"]))]
    levels = _layer_levels(data)
    names = {v: k for k, v in levels.items()}
    s_lo, s_hi = (levels[x] for x in params["signal_layers"])
    c_lo, c_hi = (levels[x] for x in params["clock_layers"])
    bad_signal: list[str] = []
    bad_clock: list[str] = []
    trunk_nets = 0
    for net, value in data.items():
        if net.startswith("__"):
            continue
        kind, wires_s, io_s = (str(value).split("|") + ["", ""])[:3]
        wires = [int(x) for x in wires_s.split(",") if x]
        io = [int(x) for x in io_s.split(",") if x]
        # This build applies the clock range only to non-leaf clock nets (leaf nets
        # follow the signal range) and lets a net with IO pins use the pin's layer.
        # Leaf clock nets are clock nets too, so either range is accepted for them.
        sig = (min([s_lo] + io), s_hi)
        clk = (min([c_lo] + io), c_hi)
        if kind == "C":
            trunk_nets += bool(wires)
        ranges = [clk] if kind == "C" else [sig, clk] if kind == "L" else [sig]
        outside: list[str] = []
        if not any(all(lo <= w <= hi for w in wires) for lo, hi in ranges):
            lo, hi = ranges[0]
            outside = [names.get(w, str(w)) for w in wires if not lo <= w <= hi]
        if outside:
            (bad_clock if kind == "C" else bad_signal).append(f"{net}:{'/'.join(outside)}")
    checks.append(check("signal_routing_layers", not bad_signal,
                        f"{len(bad_signal)} nets with wires outside {'-'.join(params['signal_layers'])}"
                        + (f" (e.g. {', '.join(bad_signal[:3])})" if bad_signal else "")))
    checks.append(check("clock_routing_layers", trunk_nets > 0 and not bad_clock,
                        f"{trunk_nets} clock-tree nets checked; {len(bad_clock)} with wires outside "
                        f"{'-'.join(params['clock_layers'])}" + (f" ({', '.join(bad_clock[:3])})" if bad_clock else "")))
    return checks


@register("rt_grt_parasitics_slack")
def grt_parasitics_slack(ctx: ValidationContext, params: dict) -> list[Check]:
    """RT-04: worst setup slack with parasitics estimated from the existing global routing."""
    checks = [netlist_intact(ctx), _guides_unchanged(ctx)]
    value, c = _single_number(ctx, params["report"])
    checks.append(c)
    if value is not None:
        truth = ctx.query_baseline(GRT_SLACK_TCL)
        checks.append(approx("worst_setup_slack_ns", value, float(truth["wns"]), atol=params["atol_ns"]))
    return checks


@register("rt_detailed_route_drc")
def detailed_route_drc(ctx: ValidationContext, params: dict) -> list[Check]:
    """RT-05: fully detail-routed, DRC clean, and the router's DRC report saved."""
    drv = ctx.probe.get("drv_count")
    checks = [netlist_intact(ctx), _all_nets_detail_routed(ctx),
              check("no_drc_violations", drv == 0, f"detailed router reports {drv} violations")]
    path = params["report"]
    text = ctx.read_output(path)
    if text is None:
        checks.append(check(f"file:{path}", False, "missing"))
    else:
        listed = len(re.findall(r"violation\s+type\s*:", text, re.I))
        checks.append(check("drc_report_matches_router", isinstance(drv, int) and listed == drv,
                            f"{listed} violations listed in the report, router final count {drv}"))
    return checks


@register("rt_clock_net_gr_wirelength")
def clock_net_gr_wirelength(ctx: ValidationContext, params: dict) -> list[Check]:
    """RT-06: per-clock-net global-route wirelength of the existing global routing."""
    checks = [netlist_intact(ctx), _guides_unchanged(ctx)]
    truth = ctx.query_baseline(CLOCK_GRWL_TCL)
    want = {_unescape(k[3:]): float(v) for k, v in truth.items() if k.startswith("wl:")}
    others = {_unescape(n) for n in str(truth.get("all_nets", "")).split("\n") if n} - set(want)
    path = params["report"]
    text = ctx.read_output(path)
    if text is None:
        return checks + [check(f"file:{path}", False, "missing")]
    got: dict[str, float | None] = {}
    extra: set[str] = set()
    for line in text.splitlines():
        tokens = [t.strip("{}\"'") for t in re.split(r"[\s,;:=|]+", line)]
        tokens = [t for t in tokens if t]
        for i, tok in enumerate(tokens):
            name = _unescape(tok)
            if name in want:
                nums = _numbers(" ".join(tokens[i + 1:]))
                got[name] = nums[0] if nums else None
                break
            if name in others:
                extra.add(name)
                break
    missing = sorted(set(want) - set(got))
    checks.append(check("clock_nets_reported", bool(want) and not missing and not extra,
                        f"{len(got)}/{len(want)} clock nets reported; missing {missing[:4]}, "
                        f"non-clock nets {sorted(extra)[:4]}"))
    tol = params["atol_um"]
    wrong = [f"{n}={got[n]} (expected {want[n]:g})" for n in sorted(got)
             if got[n] is None or abs(got[n] - want[n]) > tol]
    checks.append(check("clock_net_wirelengths", bool(got) and not wrong,
                        f"{len(got) - len(wrong)}/{len(got)} values within {tol} um"
                        + (f"; wrong: {', '.join(wrong[:3])}" if wrong else "")))
    return checks


@register("rt_rcx_spef_slack")
def rcx_spef_slack(ctx: ValidationContext, params: dict) -> list[Check]:
    """RT-07: RCX parasitics written as SPEF and used for the worst setup slack."""
    p, b = ctx.probe, ctx.baseline
    unchanged = (p.get("routed_net_count") == b.get("routed_net_count")
                 and abs((p.get("detailed_wirelength_um") or -1.0) - b.get("detailed_wirelength_um", 0.0)) < 1e-3)
    checks = [netlist_intact(ctx),
              check("routing_unchanged", unchanged,
                    f"routed nets {p.get('routed_net_count')}/{b.get('routed_net_count')}, "
                    f"wirelength {p.get('detailed_wirelength_um')}/{b.get('detailed_wirelength_um')} um")]
    truth = ctx.query_baseline(RCX_TCL)
    want = {k[4:]: float(v) for k, v in truth.items() if k.startswith("cap:")}
    path = params["spef"]
    text = ctx.read_output(path)
    if text is None or "*D_NET" not in text:
        checks.append(check(f"file:{path}", False, "missing" if text is None else "no *D_NET entries"))
    else:
        caps = _parse_spef_caps(text)
        missing, extra = set(want) - set(caps), set(caps) - set(want)
        checks.append(check("spef_nets", not missing and not extra,
                            f"{len(caps)} nets in SPEF, {len(want)} in the reference extraction; "
                            f"missing {len(missing)}, extra {len(extra)}"))
        rtol = params["net_cap_rtol"]
        close = sum(1 for n, c in want.items() if n in caps and abs(caps[n] - c) <= rtol * abs(c) + 1e-7)
        total, total_want = sum(caps[n] for n in want if n in caps), sum(want.values())
        ok = close >= params["net_cap_frac"] * len(want) and abs(total - total_want) <= params["cap_rtol"] * total_want
        checks.append(check("spef_capacitance", ok,
                            f"{close}/{len(want)} nets within {rtol:.0%} of the reference; total "
                            f"{total:.6g} vs {total_want:.6g} pF"))
    value, c = _single_number(ctx, params["report"])
    checks.append(c)
    if value is not None:
        checks.append(approx("worst_setup_slack_ns", value, float(truth["__wns"]), atol=params["atol_ns"]))
    return checks


@register("rt_routed_def")
def routed_def(ctx: ValidationContext, params: dict) -> list[Check]:
    """RT-08: DEF whose content matches the routed design of the starting state.

    The DEF is compared with the starting state (not the final probe) so that a
    design modified before export (fillers removed, wiring stripped) is rejected.
    """
    b = ctx.baseline
    checks = [netlist_intact(ctx)]
    path = params["def"]
    text = ctx.read_output(path)
    if text is None:
        return checks + [check(f"file:{path}", False, "missing")]
    d = _parse_def(text)
    checks.append(check("def_header", d["version"] is not None and d["design"] == b.get("top") and bool(d["units"]),
                        f"VERSION {d['version']}, DESIGN {d['design']}, UNITS {d['units']}"))
    checks.append(check("def_components", d["components"] == b.get("inst_count"),
                        f"{d['components']} components in DEF, {b.get('inst_count')} instances in the routed design"))
    checks.append(check("def_pins", d["pins"] == b.get("io_pin_count"),
                        f"{d['pins']} pins in DEF, {b.get('io_pin_count')} IO pins in the routed design"))
    checks.append(check("def_routed_nets", d["routed_nets"] == b.get("routed_net_count") and d["routed_nets"] > 0,
                        f"{d['routed_nets']} nets with routing in DEF, {b.get('routed_net_count')} routed nets "
                        "in the routed design"))
    wl = d["wirelength_dbu"] / d["units"] if d["units"] else None
    checks.append(approx("def_wirelength_um", wl, float(b.get("detailed_wirelength_um") or 0.0), rtol=params["wl_rtol"]))
    return checks


@register("rt_detailed_route_wirelength")
def detailed_route_wirelength(ctx: ValidationContext, params: dict) -> list[Check]:
    """DEV-RT-01: detailed routing inside a layer range and its total wirelength."""
    checks = [netlist_intact(ctx), _all_nets_detail_routed(ctx)]
    data, fail = _oracle(ctx, DR_LAYER_WL_TCL, "rt_drwl")
    if fail:
        checks.append(fail)
    else:
        levels = _layer_levels(data)
        lo, hi = levels[params["bottom_layer"]], levels[params["top_layer"]]
        outside = {k[3:]: float(v) for k, v in data.items()
                   if k.startswith("wl:") and float(v) > 0 and not lo <= levels.get(k[3:], 0) <= hi}
        span = f"{params['bottom_layer']}-{params['top_layer']}"
        checks.append(check("routing_layer_range", not outside,
                            f"wires outside {span}: " + (", ".join(f"{k} {v:.1f} um" for k, v in outside.items())
                                                         or "none")))
    value, c = _single_number(ctx, params["report"])
    checks.append(c)
    if value is not None:
        checks.append(approx("total_detailed_route_wirelength", value,
                             float(ctx.probe.get("detailed_wirelength_um") or 0.0), rtol=params["rtol"]))
    return checks
