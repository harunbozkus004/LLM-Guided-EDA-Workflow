"""Validators for the design-inspection category (IN-*, DEV-IN-*).

Every inspection task asks for a report file whose content is compared with
ground truth taken from the *starting* database (baseline probe or trusted
``query_baseline`` oracles), plus a ``design_unchanged`` guard: the requests
are read-only, so a script that edits the design (re-reading the netlist,
removing buffers, re-placing cells ...) fails even if its report looks right.

Report parsing is deliberately lenient about whitespace, separators
(``name: 41``, ``key = value``), the letter case of keywords (directions,
``total``, line keys; design object names stay case-sensitive), blank lines,
``#`` comment lines and Tcl quoting artifacts (``{name}``, ``\\[``), but every prescribed value is
compared exactly (names, counts) or within a tolerance justified by the
requested precision.
"""
from __future__ import annotations

import re
from typing import Any

from benchmark.task_validator import Check, ValidationContext, register
from benchmark.validators.common import approx, check

DIRECTIONS = ("input", "output", "inout")
_PUNCT = "()[]{}:,;=\"'"

# Minimal JSON helpers shared by the oracle bodies (a fresh session only has __oracle_*).
# Physical-only cells: fillers or master class WELLTAP / SPACER / ANTENNACELL / ENDCAP.
_TCL_JSON = r"""
proc in_js {s} {
  set s [string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t] $s]
  return "\"$s\""
}
proc in_jobj {pairs} {
  set parts {}
  foreach {k v} $pairs { lappend parts "[in_js $k]: $v" }
  return "\{[join $parts {, }]\}"
}
proc in_jcounts {d} {
  set parts {}
  dict for {k v} $d { lappend parts "[in_js $k]: $v" }
  return "\{[join $parts {, }]\}"
}
proc in_physical {master} {
  if {[$master isFiller]} { return 1 }
  set t [$master getType]
  foreach p {CORE_WELLTAP CORE_SPACER CORE_ANTENNACELL ENDCAP} {
    if {[string match ${p}* $t]} { return 1 }
  }
  return 0
}
"""


# ------------------------------------------------------------------ helpers
def norm_name(s: str) -> str:
    """Strip Tcl/Verilog quoting: ``{a[0]}``, ``a\\[0\\]`` and ``\\a[0] `` all become ``a[0]``."""
    s = s.strip().strip(",;:")
    if len(s) >= 2 and s[0] == "{" and s[-1] == "}":
        s = s[1:-1]
    return s.replace("\\", "").strip()


def report_lines(text: str) -> list[str]:
    """Non-empty lines that are not ``#`` comments."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def split_fields(line: str) -> list[str]:
    """Whitespace/comma separated fields; a braced Tcl element counts as one field."""
    return re.findall(r"\{[^{}]*\}|[^\s,]+", line)


def to_int(s: str) -> int | None:
    try:
        return int(s)
    except ValueError:
        f = to_float(s)
        return int(f) if f is not None and f.is_integer() else None


def to_float(s: str) -> float | None:
    try:
        f = float(s)
    except ValueError:
        return None
    return f if f == f and abs(f) != float("inf") else None


def numbers_in(text: str) -> list[float]:
    """Plain numbers among the tokens of ``text`` (braces, parentheses and ``%`` ignored; ``um^2`` is not a number)."""
    out = []
    for tok in re.split(r"[\s,;(){}\[\]]+", text):
        v = to_float(tok.rstrip("%"))
        if v is not None:
            out.append(v)
    return out


def count_rows(text: str) -> tuple[list[tuple[str, int]], list[str]]:
    """``<name> <int>`` rows: the name is the first field, the count the first integer after it."""
    rows: list[tuple[str, int]] = []
    bad: list[str] = []
    for line in report_lines(text):
        f = split_fields(line)
        n = next((v for v in (to_int(t.strip(_PUNCT)) for t in f[1:]) if v is not None), None)
        if n is None:
            bad.append(line)
        else:
            rows.append((norm_name(f[0]), n))
    return rows, bad


def parse_counts(text: str) -> tuple[dict[str, int], int | None, list[str], list[str]]:
    """Count rows plus an optional ``total <int>`` row -> (counts, total, bad_lines, duplicates)."""
    counts: dict[str, int] = {}
    total = None
    dup: list[str] = []
    rows, bad = count_rows(text)
    for name, n in rows:
        if name.lower() == "total":
            total = n
        elif name in counts:
            dup.append(name)
        else:
            counts[name] = n
    return counts, total, bad, dup


def read_report(ctx: ValidationContext, name: str) -> tuple[str | None, Check]:
    text = ctx.read_output(name)
    if text is None:
        return None, check(f"file:{name}", False, "missing")
    if not text.strip():
        return None, check(f"file:{name}", False, "empty")
    return text, check(f"file:{name}", True, f"{len(text)} bytes")


def format_check(bad: list[str], dup: list[str] | None = None, name: str = "report_format") -> Check:
    dup = dup or []
    detail = []
    if bad:
        detail.append(f"{len(bad)} unparseable line(s), e.g. {bad[0][:60]!r}")
    if dup:
        detail.append(f"duplicate entries {dup[:4]}")
    return check(name, not bad and not dup, "; ".join(detail) or "all lines parse")


def compare_counts(label: str, got: dict[str, int], want: dict[str, int]) -> list[Check]:
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    wrong = sorted(k for k in set(got) & set(want) if got[k] != want[k])
    if not got:
        detail = "nothing listed"
    elif wrong:
        detail = "wrong: " + ", ".join(f"{k} {got[k]} (expected {want[k]})" for k in wrong[:6])
    else:
        detail = "all listed counts correct"
    return [
        check(f"{label}_set", not missing and not extra,
              f"{len(got)} listed, {len(want)} expected; missing {missing[:6]}, unexpected {extra[:6]}"),
        check(f"{label}_counts", bool(got) and not wrong, detail),
    ]


# Database-derived probe fields (no timing or session state) that any edit of cells, nets, routing,
# supply wiring or the clock network would change.
_UNCHANGED_KEYS = ("inst_count", "net_count", "io_pin_count", "row_count", "die", "core", "status_counts",
                   "signal_net_count", "routable_net_count", "routed_net_count", "guided_net_count",
                   "detailed_wirelength_um", "special_net_swires", "register_clock_pin_count",
                   "clock_sink_net_count", "clock_sink_net_drivers")


def design_unchanged(ctx: ValidationContext) -> Check:
    """The inspection requests are read-only: the database must match the starting state."""
    b, p = ctx.baseline, ctx.probe
    diffs = []
    for key in _UNCHANGED_KEYS:
        if p.get(key) != b.get(key):
            diffs.append(f"{key} {b.get(key)} -> {p.get(key)}")
    if (p.get("master_counts") or {}) != (b.get("master_counts") or {}):
        diffs.append("cell types/counts changed")
    pos_b, pos_p = b.get("positions") or {}, p.get("positions") or {}
    moved = sum(1 for k, v in pos_b.items() if pos_p.get(k) != v)
    if moved or len(pos_p) != len(pos_b):
        diffs.append(f"{moved} of {len(pos_b)} cell placements changed")
    if (p.get("io_pins") or {}) != (b.get("io_pins") or {}):
        diffs.append("IO pins changed")
    return check("design_unchanged", not diffs, "; ".join(diffs) or "design matches the starting state")


# ------------------------------------------------------------ Verilog reader
_V_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
_V_TOKEN = re.compile(r"\\\S+|[A-Za-z_][\w$]*|\d*'[sS]?[bBoOdDhH][0-9a-fA-FxXzZ_?]+|\d+|\S")
_V_SKIP = {"wire", "reg", "tri", "wand", "wor", "supply0", "supply1", "parameter", "localparam",
           "specify", "endspecify", "defparam", "genvar", "`timescale"}


def _v_name(tok: str) -> str:
    return tok[1:] if tok.startswith("\\") else tok


def _v_expr(toks: list[str]) -> str | None:
    """A connection expression -> normalized net name (None for empty, constants, concatenations)."""
    if not toks or toks[0] == "{" or "'" in toks[0] or toks[0][0].isdigit():
        return None
    name = _v_name(toks[0])
    if len(toks) >= 4 and toks[1] == "[" and toks[3] == "]":
        name = f"{name}[{toks[2]}]"
    return norm_name(name)


def _v_range(toks: list[str], i: int) -> tuple[list[int] | None, int]:
    if i < len(toks) and toks[i] == "[":
        try:
            j = toks.index("]", i)
            msb, lsb = int(toks[i + 1]), int(toks[i + 3])
        except (ValueError, IndexError):
            return None, len(toks)
        step = 1 if lsb >= msb else -1
        return list(range(msb, lsb + step, step)), j + 1
    return None, i


def _v_ports(toks: list[str], ports: dict[str, str]) -> None:
    """Declarations like ``input [3:0] a, b`` (also ANSI-style header lists)."""
    direction, bits = None, None
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in DIRECTIONS:
            direction = t
            i += 1
            while i < len(toks) and toks[i] in ("wire", "reg", "logic", "signed", "tri"):
                i += 1
            bits, i = _v_range(toks, i)
            continue
        if direction and (t[0].isalpha() or t[0] in "_\\"):
            name = norm_name(_v_name(t))
            if bits is None:
                ports[name] = direction
            else:
                for b in bits:
                    ports[f"{name}[{b}]"] = direction
        i += 1


def _v_instance(toks: list[str]) -> tuple[str, str, dict[str, str | None]] | None:
    master = _v_name(toks[0])
    i = 1
    if i < len(toks) and toks[i] == "#":  # parameter overrides
        depth = 0
        i += 1
        while i < len(toks):
            depth += toks[i] == "("
            depth -= toks[i] == ")"
            i += 1
            if depth == 0:
                break
    if i + 1 >= len(toks) or toks[i + 1] != "(":
        return None
    inst = norm_name(_v_name(toks[i]))
    conns: dict[str, str | None] = {}
    j = i + 2
    while j < len(toks):
        if toks[j] == "." and j + 2 < len(toks) and toks[j + 2] == "(":
            pin = _v_name(toks[j + 1])
            k, depth = j + 3, 1
            while k < len(toks) and depth:
                depth += toks[k] == "("
                depth -= toks[k] == ")"
                k += 1
            conns[pin] = _v_expr(toks[j + 3:k - 1])
            j = k
        else:
            j += 1
    return master, inst, conns


def parse_verilog(text: str) -> dict[str, dict[str, Any]]:
    """Minimal structural-Verilog reader; never raises (unparseable statements are skipped).

    Returns ``{module: {"ports": {bit: dir}, "insts": {name: (master, {pin: net})}, "assigns": [(a, b)]}}``.
    """
    modules: dict[str, dict[str, Any]] = {}
    cur: dict[str, Any] | None = None

    def flush(st: list[str]) -> None:
        nonlocal cur
        if not st:
            return
        head = st[0]
        if head in ("module", "macromodule") and len(st) > 1:
            cur = modules.setdefault(norm_name(_v_name(st[1])), {"ports": {}, "insts": {}, "assigns": []})
            if "(" in st:
                _v_ports(st[st.index("(") + 1:], cur["ports"])
            return
        if cur is None or head in _V_SKIP:
            return
        if head in DIRECTIONS:
            _v_ports(st, cur["ports"])
        elif head == "assign":
            if "=" in st:
                k = st.index("=")
                a, b = _v_expr(st[1:k]), _v_expr(st[k + 1:])
                if a and b:
                    cur["assigns"].append((a, b))
        elif head[0].isalpha() or head[0] in "_\\":
            parsed = _v_instance(st)
            if parsed:
                master, inst, conns = parsed
                cur["insts"][inst] = (master, conns)

    try:
        stmt: list[str] = []
        for tok in _V_TOKEN.findall(_V_COMMENT.sub(" ", text)):
            if tok == "endmodule":
                flush(stmt)
                stmt, cur = [], None
            elif tok == ";":
                flush(stmt)
                stmt = []
            else:
                stmt.append(tok)
        flush(stmt)
    except Exception:  # noqa: BLE001  (defensive: never fail the validator on odd input)
        pass
    return modules


# ------------------------------------------------------------- oracles
NETLIST_ORACLE = _TCL_JSON + r"""
set block [ord::get_db_block]
set insts {}; set phys {}; set conns {}; set ports {}; set pg {}
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  lappend insts [$inst getName] [in_js [$m getName]]
  if {[in_physical $m]} { lappend phys [in_js [$inst getName]] }
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    if {[$mt getSigType] in {POWER GROUND}} { lappend pg [in_js [$mt getName]]; continue }
    set net [$it getNet]
    if {$net == "NULL"} { continue }
    lappend conns "\[[in_js [$inst getName]], [in_js [$mt getName]], [in_js [$net getName]]\]"
  }
}
foreach bt [$block getBTerms] {
  set net [$bt getNet]
  lappend ports [$bt getName] [expr {$net == "NULL" ? "null" : [in_js [$net getName]]}]
}
__oracle_emit [in_jobj [list insts [in_jobj $insts] physical "\[[join $phys {, }]\]" \
  conns "\[[join $conns {, }]\]" ports [in_jobj $ports] pg_pins "\[[join [lsort -unique $pg] {, }]\]"]]
"""

CELL_USAGE_ORACLE = _TCL_JSON + r"""
set block [ord::get_db_block]
set logic [dict create]; set phys [dict create]
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  if {[in_physical $m]} { dict incr phys [$m getName] } else { dict incr logic [$m getName] }
}
__oracle_emit [in_jobj [list logic [in_jcounts $logic] physical [in_jcounts $phys]]]
"""

FANOUT_ORACLE = _TCL_JSON + r"""
set block [ord::get_db_block]
set clock_ports {}
foreach clk [all_clocks] {
  foreach src [get_property $clk sources] { lappend clock_ports [get_full_name $src] }
}
set fanout {}; set excluded {}
foreach net [$block getNets] {
  set name [$net getName]
  set sinks 0; set is_clock [expr {[$net getSigType] == "CLOCK"}]
  foreach it [$net getITerms] {
    if {[$it getIoType] in {INPUT INOUT} && [[$it getMTerm] getSigType] ni {POWER GROUND}} { incr sinks }
  }
  foreach bt [$net getBTerms] {
    if {[$bt getIoType] in {OUTPUT INOUT}} { incr sinks }
    if {[$bt getName] in $clock_ports} { set is_clock 1 }
  }
  if {[$net getSigType] in {POWER GROUND} || [$net isSpecial] || $is_clock} {
    lappend excluded [in_js $name]
  }
  lappend fanout $name $sinks
}
__oracle_emit [in_jobj [list fanout [in_jobj $fanout] excluded "\[[join $excluded {, }]\]"]]
"""

AREA_ORACLE = r"""
set block [ord::get_db_block]
set dbu [$block getDefUnits]
set area 0.0; set n 0
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  if {[$m isFiller]} { continue }
  incr n
  set area [expr {$area + double([$m getWidth]) * [$m getHeight] / $dbu / $dbu}]
}
set c [$block getCoreArea]
set core_area [expr {double([$c xMax] - [$c xMin]) * ([$c yMax] - [$c yMin]) / $dbu / $dbu}]
__oracle_emit_dict [dict create cell_area $area core_area $core_area counted_insts $n]
"""

FLOP_ORACLE = _TCL_JSON + r"""
set block [ord::get_db_block]
set types [dict create]; set drivers [dict create]; set n 0
foreach reg [all_registers -edge_triggered -cells] {
  incr n
  dict incr types [get_property $reg ref_name]
}
foreach ck [all_registers -edge_triggered -clock_pins] {
  # clock-pin connectivity from the database itself (independent of the STA network)
  set inst [$block findInst [get_full_name [get_cells -of_objects $ck]]]
  set it [$inst findITerm [get_property $ck lib_pin_name]]
  set net [$it getNet]
  if {$net == "NULL"} { continue }
  set drv ""
  foreach dit [$net getITerms] {
    if {[$dit getIoType] == "OUTPUT"} { set drv [[$dit getInst] getName] }
  }
  if {$drv == ""} { set drv "PORT:[join [lmap b [$net getBTerms] {$b getName}] ,]" }
  dict incr drivers $drv
}
__oracle_emit [in_jobj [list types [in_jcounts $types] drivers [in_jcounts $drivers] count $n]]
"""

UNLOADED_ORACLE = _TCL_JSON + r"""
set block [ord::get_db_block]
set out {}
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND} || [$net isSpecial]} { continue }
  set loads 0; set drivers {}
  foreach it [$net getITerms] {
    switch [$it getIoType] {
      INPUT { incr loads }
      OUTPUT { lappend drivers "[[$it getInst] getName]/[[$it getMTerm] getName]" }
    }
  }
  foreach bt [$net getBTerms] {
    switch [$bt getIoType] {
      OUTPUT { incr loads }
      INPUT { lappend drivers [$bt getName] }
    }
  }
  if {$loads == 0 && [llength $drivers]} { lappend out [$net getName] [in_js [join $drivers ,]] }
}
__oracle_emit [in_jobj $out]
"""


# ---------------------------------------------------------- validators
@register("in_io_ports")
def io_ports(ctx: ValidationContext, params: dict) -> list[Check]:
    """IN-01: every port bit listed exactly once with its direction."""
    text, fc = read_report(ctx, params["file"])
    checks = [fc]
    if text is None:
        return checks + [design_unchanged(ctx)]
    want = {norm_name(k): str(v.get("io", "")).lower() for k, v in (ctx.baseline.get("io_pins") or {}).items()}
    got: dict[str, str] = {}
    bad, dup = [], []
    for line in report_lines(text):
        f = split_fields(line)
        d = next((t.strip(_PUNCT).lower() for t in f[1:] if t.strip(_PUNCT).lower() in DIRECTIONS), None)
        if d is None:
            bad.append(line)
            continue
        name = norm_name(f[0])
        if name in got:
            dup.append(name)
        got[name] = d
    checks.append(format_check(bad, dup))
    missing, extra = sorted(set(want) - set(got)), sorted(set(got) - set(want))
    checks.append(check("port_set", not missing and not extra,
                        f"{len(got)} ports listed, {len(want)} in design; missing {missing[:6]}, unexpected {extra[:6]}"))
    wrong = sorted(k for k in set(got) & set(want) if got[k] != want[k])
    checks.append(check("port_directions", bool(got) and not wrong,
                        "nothing listed" if not got else "all listed directions correct" if not wrong else
                        "wrong: " + ", ".join(f"{k} {got[k]} (is {want[k]})" for k in wrong[:6])))
    checks.append(design_unchanged(ctx))
    return checks


@register("in_verilog_netlist")
def verilog_netlist(ctx: ValidationContext, params: dict) -> list[Check]:
    """IN-02: the written Verilog reproduces the database netlist (ports, instances, cell types, connectivity)."""
    text, fc = read_report(ctx, params["file"])
    checks = [fc]
    if text is None:
        return checks + [design_unchanged(ctx)]
    truth = ctx.query_baseline(NETLIST_ORACLE, name="in_netlist")
    top = params.get("top", "gcd")
    mod = parse_verilog(text).get(top)
    checks.append(check("module_found", mod is not None, f"module {top} {'found' if mod else 'not found'}"))
    if mod is None:
        return checks + [design_unchanged(ctx)]

    want_ports = {norm_name(k): str(v.get("io", "")).lower() for k, v in (ctx.baseline.get("io_pins") or {}).items()}
    got_ports = mod["ports"]
    missing_p = sorted(set(want_ports) - set(got_ports))
    extra_p = sorted(set(got_ports) - set(want_ports))
    wrong_dir = sorted(p for p in set(got_ports) & set(want_ports) if got_ports[p] != want_ports[p])
    checks.append(check("ports", not missing_p and not extra_p and not wrong_dir,
                        f"{len(got_ports)} port bits declared, {len(want_ports)} expected; missing {missing_p[:4]}, "
                        f"unexpected {extra_p[:4]}, wrong direction {wrong_dir[:4]}"))

    db_insts = {norm_name(k): v for k, v in truth["insts"].items()}
    physical = {norm_name(i) for i in truth["physical"]}
    logic = {k: v for k, v in db_insts.items() if k not in physical}
    file_insts = {k: v[0] for k, v in mod["insts"].items()}
    missing = sorted(set(logic) - set(file_insts))
    wrong_master = sorted(k for k in set(logic) & set(file_insts) if file_insts[k] != logic[k])
    extra = sorted(k for k in set(file_insts) - set(logic)
                   if not (k in physical and file_insts[k] == db_insts[k]))
    checks.append(check("instances", not missing and not wrong_master and not extra,
                        f"{len(logic)} standard cells in design; missing {len(missing)} {missing[:3]}, "
                        f"wrong cell type {len(wrong_master)} {wrong_master[:3]}, unexpected {len(extra)} {extra[:3]}"))

    # Connectivity as a partition of instance pins and ports into nets: independent of net names.
    pg = set(truth["pg_pins"])
    db_groups: dict[str, set[str]] = {}
    for inst, pin, net in truth["conns"]:
        inst = norm_name(inst)
        if inst in logic:
            db_groups.setdefault(norm_name(net), set()).add(f"{inst}/{pin}")
    for port, net in truth["ports"].items():
        if net is not None:
            db_groups.setdefault(norm_name(net), set()).add(f"PORT:{norm_name(port)}")

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in mod["assigns"]:
        parent[find(a)] = find(b)
    file_groups: dict[str, set[str]] = {}
    for inst, (_master, conns) in mod["insts"].items():
        if inst in physical:
            continue
        for pin, net in conns.items():
            if net is not None and pin not in pg:
                file_groups.setdefault(find(net), set()).add(f"{inst}/{pin}")
    for port in got_ports:
        file_groups.setdefault(find(port), set()).add(f"PORT:{port}")
    # A net holding a single instance pin (e.g. an unused QN output) connects nothing, so writing
    # that pin as unconnected (.QN()) is equivalent; such singletons are ignored on both sides.
    def partition(groups: dict[str, set[str]]) -> set[frozenset[str]]:
        return {frozenset(g) for g in groups.values() if len(g) > 1 or next(iter(g)).startswith("PORT:")}

    want_part, got_part = partition(db_groups), partition(file_groups)
    checks.append(check("connectivity", bool(want_part) and want_part == got_part,
                        f"{len(want_part)} nets in design; {len(want_part - got_part)} not reproduced, "
                        f"{len(got_part - want_part)} net(s) in file not in design"))
    checks.append(design_unchanged(ctx))
    return checks


@register("in_cell_usage")
def cell_usage(ctx: ValidationContext, params: dict) -> list[Check]:
    """IN-03: instance count per logic cell type (physical-only cells excluded) plus total."""
    text, fc = read_report(ctx, params["file"])
    checks = [fc]
    if text is None:
        return checks + [design_unchanged(ctx)]
    truth = ctx.query_baseline(CELL_USAGE_ORACLE, name="in_cell_usage")
    want = {k: int(v) for k, v in truth["logic"].items()}
    counts, total, bad, dup = parse_counts(text)
    checks.append(format_check(bad, dup))
    checks += compare_counts("cell_types", counts, want)
    want_total = sum(want.values())
    checks.append(check("total", total == want_total, f"total {total}, expected {want_total}"))
    checks.append(design_unchanged(ctx))
    return checks


@register("in_high_fanout_nets")
def high_fanout_nets(ctx: ValidationContext, params: dict) -> list[Check]:
    """IN-04: the N highest-fanout signal nets (clock and supply nets excluded), sorted."""
    text, fc = read_report(ctx, params["file"])
    checks = [fc]
    if text is None:
        return checks + [design_unchanged(ctx)]
    truth = ctx.query_baseline(FANOUT_ORACLE, name="in_fanout")
    n_want = int(params.get("count", 5))
    fanout = {norm_name(k): int(v) for k, v in truth["fanout"].items()}
    excluded = {norm_name(k) for k in truth["excluded"]}
    eligible = {k: v for k, v in fanout.items() if k not in excluded}

    rows, bad = count_rows(text)
    names = [r[0] for r in rows]
    dup = sorted({x for x in names if names.count(x) > 1})
    checks.append(format_check(bad, dup))
    checks.append(check("net_count", len(rows) == n_want, f"{len(rows)} nets listed, {n_want} requested"))
    not_allowed = [n for n in names if n not in eligible]
    checks.append(check("eligible_nets", not not_allowed,
                        "all listed nets are signal nets" if not not_allowed else
                        f"not existing or excluded (clock/supply): {not_allowed[:5]}"))
    wrong = [(n, v, fanout[n]) for n, v in rows if n in fanout and fanout[n] != v]
    checks.append(check("fanout_values", bool(rows) and not wrong,
                        "nothing listed" if not rows else "all fanouts correct" if not wrong else
                        "wrong: " + ", ".join(f"{n} {v} (actual {t})" for n, v, t in wrong[:5])))
    listed = [eligible[n] for n in names if n in eligible]
    best_unlisted = max((v for k, v in eligible.items() if k not in names), default=-1)
    top = sorted(eligible.values(), reverse=True)[:n_want]
    is_top = len(listed) == n_want and not dup and min(listed) >= best_unlisted
    checks.append(check("top_nets", is_top,
                        f"actual fanouts of listed nets {listed}; top {n_want} fanouts in design {top}"))
    vals = [v for _, v in rows]
    checks.append(check("sorted_decreasing", vals == sorted(vals, reverse=True), f"order {vals}"))
    checks.append(design_unchanged(ctx))
    return checks


@register("in_floorplan_summary")
def floorplan_summary(ctx: ValidationContext, params: dict) -> list[Check]:
    """IN-05: die/core boxes, non-filler cell area and utilization."""
    text, fc = read_report(ctx, params["file"])
    checks = [fc]
    if text is None:
        return checks + [design_unchanged(ctx)]
    truth = ctx.query_baseline(AREA_ORACLE, name="in_area")
    values: dict[str, list[float]] = {}
    for line in report_lines(text):
        m = re.match(r"([A-Za-z_]+)\s*[:=]?(.*)$", line)
        if m:
            values.setdefault(m.group(1).lower(), numbers_in(m.group(2)))
    tol_box, tol_val = float(params["box_tol_um"]), float(params["value_tol"])
    for key, want in (("die_area", ctx.baseline.get("die")), ("core_area", ctx.baseline.get("core"))):
        got = values.get(key)
        ok = got is not None and want is not None and len(got) == 4 and all(
            abs(g - w) <= tol_box for g, w in zip(got, want))
        checks.append(check(key, ok, f"reported {got}, expected {want} (+/- {tol_box} um)"))
    cell_area = float(truth["cell_area"])
    util = 100.0 * cell_area / float(truth["core_area"])
    got_area = values.get("cell_area") or [None]
    got_util = values.get("utilization") or [None]
    checks.append(approx("cell_area", got_area[0], cell_area, atol=tol_val))
    checks.append(approx("utilization_percent", got_util[0], util, atol=tol_val))
    checks.append(design_unchanged(ctx))
    return checks


@register("in_flop_report")
def flop_report(ctx: ValidationContext, params: dict) -> list[Check]:
    """IN-06: flip-flops per cell type (+ total) and per cell driving their clock pins."""
    checks: list[Check] = []
    truth = ctx.query_baseline(FLOP_ORACLE, name="in_flops")
    want_types = {k: int(v) for k, v in truth["types"].items()}
    want_drv = {norm_name(k): int(v) for k, v in truth["drivers"].items()}

    text, fc = read_report(ctx, params["types_file"])
    checks.append(fc)
    if text is not None:
        counts, total, bad, dup = parse_counts(text)
        checks.append(format_check(bad, dup))
        checks += compare_counts("flop_types", counts, want_types)
        want_total = sum(want_types.values())
        checks.append(check("flop_total", total == want_total, f"total {total}, expected {want_total}"))

    text, fc = read_report(ctx, params["drivers_file"])
    checks.append(fc)
    if text is not None:
        counts, _total, bad, dup = parse_counts(text)  # a harmless extra total line is ignored
        checks.append(format_check(bad, dup, name="drivers_format"))
        checks += compare_counts("clock_drivers", counts, want_drv)
    checks.append(design_unchanged(ctx))
    return checks


@register("in_unloaded_nets")
def unloaded_nets(ctx: ValidationContext, params: dict) -> list[Check]:
    """DEV-IN-01: driven nets without any load, each with its driver pin."""
    text, fc = read_report(ctx, params["file"])
    checks = [fc]
    if text is None:
        return checks + [design_unchanged(ctx)]
    truth = ctx.query_baseline(UNLOADED_ORACLE, name="in_unloaded")
    want = {norm_name(k): {norm_name(d) for d in str(v).split(",")} for k, v in truth.items()}
    got: dict[str, str] = {}
    bad, dup = [], []
    for line in report_lines(text):
        f = split_fields(line)
        if len(f) < 2:
            bad.append(line)
            continue
        name = norm_name(f[0])
        if name in got:
            dup.append(name)
        got[name] = norm_name(next((t for t in f[1:] if "/" in t), f[1]))
    checks.append(format_check(bad, dup))
    missing, extra = sorted(set(want) - set(got)), sorted(set(got) - set(want))
    checks.append(check("net_set", bool(want) and not missing and not extra,
                        f"{len(got)} nets listed, {len(want)} expected; missing {missing[:5]}, unexpected {extra[:5]}"))
    wrong = sorted(k for k in set(got) & set(want) if got[k] not in want[k])
    checks.append(check("driver_pins", bool(got) and not wrong,
                        "nothing listed" if not got else "all driver pins correct" if not wrong else
                        "wrong: " + ", ".join(f"{k} {got[k]} (is {sorted(want[k])[0]})" for k in wrong[:5])))
    checks.append(design_unchanged(ctx))
    return checks
