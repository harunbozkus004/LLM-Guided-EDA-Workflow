"""Validators for the timing-analysis category (TA-*, DEV-TA-*).

Every timing task is analysis-only. Ground truth is recomputed by a trusted
OpenROAD session on the untouched starting state under exactly the analysis
conditions the task states (parasitics source, liberty for max delays,
constraints); the agent's report must match it. Reports are parsed for content
(endpoints, slacks, pin names, labelled values), never for the command that
produced them, so hard-coded or wrong-assumption reports fail. A separate check
rejects scripts that modified the design.

Tolerances: a time printed with d decimals is off by at most 0.5*10^-d from the
tool value, so per-value checks use 0.5*10^-d + 1e-6 (d >= the 4 decimals the
tasks prescribe). Derived quantities (TNS summed from printed endpoint slacks,
period minus WNS) get the small explicit tolerances given in the task params.
"""
from __future__ import annotations

import math
import re
from typing import Any

from benchmark.task_validator import Check, ValidationContext, register
from benchmark.validators.common import check, moved_cells, netlist_intact
from openroad import report_parser

_FLOAT = r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?"
_SLACK_RE = re.compile(rf"^\s*({_FLOAT})\s+slack\s+\((?:MET|VIOLATED)\)", re.M)

# Tcl that establishes each parasitics assumption in a fresh oracle session.
PARASITICS_TCL = {
    "none": "",
    "placement": "estimate_parasitics -placement",
    "global_routing": "estimate_parasitics -global_routing",
    # extract_parasitics only fills the database; STA sees the RC after read_spef.
    "rcx": ("define_process_corner -ext_model_index 0 X\n"
            "extract_parasitics -ext_model_file platform/Nangate45.rcx_rules\n"
            "write_spef ta_oracle.spef\n"
            "read_spef ta_oracle.spef"),
}

_TCL_HELPERS = r"""
proc __ta_jlist {items} {
  set parts {}
  foreach i $items { lappend parts [__oracle_json $i] }
  return "\[[join $parts {, }]\]"
}
"""

_PATHS_BODY = r"""
set __eps {}
set __slacks {}
foreach __pe [find_timing_paths -path_delay @MM@ -group_count 100000 -endpoint_count 1 @FROM@] {
  lappend __eps [get_full_name [[$__pe vertex] pin]]
  lappend __slacks [sta::time_sta_ui [$__pe slack]]
}
__oracle_emit "\{\"endpoints\": [__ta_jlist $__eps], \"slacks\": [__ta_jlist $__slacks]\}"
"""

_SUMMARY_BODY = r"""
set __clk [lindex [all_clocks] 0]
set __d [dict create]
dict set __d worst_setup_slack [worst_slack -max]
dict set __d total_negative_setup_slack [total_negative_slack -max]
dict set __d worst_hold_slack [worst_slack -min]
dict set __d setup_violating_endpoints [sta::endpoint_violation_count max]
dict set __d clock_period [sta::time_sta_ui [$__clk period]]
dict set __d min_period_api [sta::time_sta_ui [sta::find_clk_min_period $__clk 1]]
dict set __d setup_skew [worst_clock_skew -setup]
dict set __d hold_skew [worst_clock_skew -hold]
if {[file exists ta_oracle.spef]} {
  set __f [open ta_oracle.spef r]
  dict set __d spef_dnets [regexp -all -line {^\*D_NET} [read $__f]]
  close $__f
}
__oracle_emit_dict $__d
"""

_DRV_BODY = r"""
set __s {}
foreach __p [sta::check_slew_limits NULL 1 NULL max] { lappend __s [get_full_name $__p] }
set __c {}
foreach __p [sta::check_capacitance_limits NULL 1 NULL max] { lappend __c [get_full_name $__p] }
__oracle_emit "\{\"max_transition\": [__ta_jlist $__s], \"max_capacitance\": [__ta_jlist $__c]\}"
"""


# ------------------------------------------------------------------ oracle
def _setup_tcl(params: dict) -> str:
    """Analysis conditions of a task, in the order a correct script applies them."""
    lines = []
    if params.get("liberty_max"):
        lines.append(f"read_liberty -max {params['liberty_max']}")
    if params.get("clock_period") is not None:
        lines.append(f"create_clock -name core_clock -period {params['clock_period']} [get_ports clk]")
    if params.get("max_transition") is not None:
        lines.append(f"set_max_transition {params['max_transition']} [current_design]")
    if params.get("max_capacitance") is not None:
        lines.append(f"set_max_capacitance {params['max_capacitance']} [current_design]")
    lines.append(PARASITICS_TCL[params.get("parasitics", "none")])
    return "\n".join(line for line in lines if line)


def _gt_path_slacks(ctx: ValidationContext, params: dict) -> dict[str, float]:
    """Worst slack per endpoint (keyed like report endpoints) on the starting state."""
    frm = f"-from [get_ports {{{params['from_port']}}}]" if params.get("from_port") else ""
    body = (_TCL_HELPERS + _setup_tcl(params) + "\n"
            + _PATHS_BODY.replace("@MM@", params["path_delay"]).replace("@FROM@", frm))
    data = ctx.query_baseline(body, name="ta_paths")
    slacks: dict[str, float] = {}
    for ep, s in zip(data.get("endpoints", []), data.get("slacks", [])):
        key = _ep_key(ep)
        slacks[key] = min(float(s), slacks.get(key, math.inf))
    return slacks


def _gt_summary(ctx: ValidationContext, params: dict) -> dict[str, Any]:
    data = ctx.query_baseline(_TCL_HELPERS + _setup_tcl(params) + "\n" + _SUMMARY_BODY, name="ta_summary")
    data["min_clock_period"] = data["clock_period"] - data["worst_setup_slack"]
    return data


# ------------------------------------------------------------------ parsing
def _ep_key(name: str) -> str:
    """Report endpoints/startpoints name the register instance, the oracle names its pin."""
    return name.split("/")[0]


def _decimals(token: str) -> int | None:
    """Digits after the decimal point; None for exponent notation (precision not checked)."""
    if re.search(r"[eE]", token):
        return None
    return len(token.split(".")[1]) if "." in token else 0


def _value_tol(token: str) -> float:
    d = _decimals(token)
    return 1e-6 if d is None else 0.5 * 10.0 ** -d + 1e-6


def _num_tokens(line: str) -> list[str]:
    return [t for t in re.split(r"[\s=:,;()]+", line) if t and re.fullmatch(_FLOAT, t)]


def _detail_rows(block: str, ports: set[str]) -> int:
    """Rows of a path report that give a time at a design pin (instance/pin or port)."""
    n = 0
    for line in block.splitlines():
        if re.match(r"\s*(Startpoint|Endpoint|Path Group|Path Type):", line) or not _num_tokens(line):
            continue
        words = re.split(r"[\s()]+", line)
        if any(re.fullmatch(r"[^/\s]+/[^/\s]+", w) or w in ports for w in words):
            n += 1
    return n


def _fmt(names: list[str] | set[str], limit: int = 6) -> str:
    names = sorted(names)
    more = f" (+{len(names) - limit} more)" if len(names) > limit else ""
    return ", ".join(names[:limit]) + more


# ------------------------------------------------------------------ checks
def design_unchanged(ctx: ValidationContext) -> Check:
    """Analysis tasks must not alter the netlist, placement or routing."""
    b, p = ctx.baseline, ctx.probe
    problems = []
    intact = netlist_intact(ctx)
    if not intact.passed:
        problems.append(intact.detail)
    if p.get("master_counts") != b.get("master_counts"):
        problems.append("cell masters changed")
    mv = moved_cells(ctx)
    if mv["moved"] or mv["compared"] != len(b.get("positions") or {}):
        problems.append(f"{mv['moved']} cells moved, {mv['compared']}/{len(b.get('positions') or {})} cells kept")
    for key in ("io_pins_placed", "routed_net_count", "guided_net_count"):
        if p.get(key) != b.get(key):
            problems.append(f"{key} {p.get(key)} (start {b.get(key)})")
    return check("design_unchanged", not problems,
                 "; ".join(problems) or "netlist, placement and routing as in the starting state")


def _read_nonempty(ctx: ValidationContext, name: str, checks: list[Check]) -> str | None:
    text = ctx.read_output(name)
    ok = text is not None and text.strip() != ""
    checks.append(check(f"file:{name}", ok, "present" if ok else ("missing" if text is None else "empty")))
    return text if ok else None


# ------------------------------------------------------------------ validators
@register("ta_path_report")
def path_report(ctx: ValidationContext, params: dict) -> list[Check]:
    """Full timing-path report: the N worst paths (one per endpoint) with matching slacks."""
    checks = [design_unchanged(ctx)]
    text = _read_nonempty(ctx, params["file"], checks)
    if text is None:
        return checks
    n, mm = int(params["count"]), params["path_delay"]
    min_digits = int(params.get("min_digits", 4))
    paths = report_parser.timing_paths(text)
    checks.append(check("path_count", len(paths) == n, f"{len(paths)} paths reported, {n} required"))
    if not paths:
        return checks

    ports = set(ctx.baseline.get("io_pins") or {})
    shallow = [i + 1 for i, pth in enumerate(paths) if _detail_rows(pth["text"], ports) < 2]
    checks.append(check("full_path_detail", not shallow,
                        f"paths without pin-by-pin detail: {shallow}" if shallow else "all paths detailed"))
    wrong_type = [pth["path_type"] for pth in paths if pth["path_type"] not in (None, mm)]
    checks.append(check("path_type", not wrong_type,
                        f"found Path Type {sorted(set(wrong_type))}, expected {mm}" if wrong_type else f"{mm} paths"))

    slack_tokens = []
    for pth in paths:
        m = _SLACK_RE.search(pth["text"])
        slack_tokens.append(m.group(1) if m else None)
    digits = [_decimals(t) for t in slack_tokens if t is not None]
    low = [d for d in digits if d is not None and d < min_digits]
    shown = sorted({str(d) if d is not None else "exp" for d in digits})
    checks.append(check("report_precision", bool(digits) and not low,
                        f"slack decimals {shown}, need >= {min_digits}"))

    keys = [_ep_key(pth["endpoint"] or "?") for pth in paths]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    checks.append(check("one_path_per_endpoint", not dup, f"repeated endpoints {dup}" if dup else "distinct endpoints"))

    if params.get("from_port"):
        sps = {pth["startpoint"] for pth in paths}
        checks.append(check("startpoint", sps == {params["from_port"]},
                            f"startpoints {_fmt({str(s) for s in sps})}, required {params['from_port']}"))

    gt = _gt_path_slacks(ctx, params)
    ordered = sorted(gt.values())
    if len(ordered) < n:
        checks.append(check("ground_truth", False, f"only {len(ordered)} endpoints in ground truth"))
        return checks
    tie_tol = 0.5 * 10.0 ** -min_digits + 1e-6
    boundary = ordered[n - 1]
    unknown = [k for k in keys if k not in gt]
    not_worst = [k for k in keys if k in gt and gt[k] > boundary + tie_tol]
    missing = sorted(k for k, s in gt.items() if s < boundary - tie_tol and k not in keys)
    problems = [msg for msg, items in ((f"unknown endpoints {_fmt(unknown)}", unknown),
                                       (f"not among the {n} worst: {_fmt(not_worst)}", not_worst),
                                       (f"missing worst endpoints: {_fmt(missing)}", missing)) if items]
    checks.append(check("worst_endpoints", not problems,
                        "; ".join(problems) or f"the {n} worst endpoints (boundary slack {boundary:.4f})"))

    bad = []
    for key, tok in zip(keys, slack_tokens):
        if key not in gt:
            continue
        if tok is None:
            bad.append(f"{key}: no slack")
        elif abs(float(tok) - gt[key]) > _value_tol(tok):
            bad.append(f"{key}: {tok} vs {gt[key]:.5f}")
    if unknown:
        bad.append(f"no ground truth for endpoints {_fmt(unknown)}")
    checks.append(check("slacks_match_ground_truth", not bad,
                        "; ".join(bad[:6]) or f"{len(keys)} slacks match ({params.get('parasitics', 'none')} parasitics)"))
    return checks


@register("ta_clock_skew")
def clock_skew(ctx: ValidationContext, params: dict) -> list[Check]:
    """Clock-skew report stating the skew value of the requested check type."""
    checks = [design_unchanged(ctx)]
    text = _read_nonempty(ctx, params["file"], checks)
    if text is None:
        return checks
    min_digits = int(params.get("min_digits", 4))
    mentions = re.search(r"(?i)skew", text) is not None
    checks.append(check("mentions_skew", mentions, "report names the skew" if mentions else "no skew value in file"))
    # Stated skew values: the last non-integer number of a line naming the skew, or the
    # last number of a native "latency CRPR skew" row (numbers only, under a header naming
    # the skew). Integers (counts, "4 decimals") are never a skew value. Every stated
    # value must be right (no shotgun lists); unrelated rows such as clock properties
    # appended to the report are ignored.
    cands = []
    in_skew_table = False
    for line in text.splitlines():
        toks = [t for t in _num_tokens(line) if re.search(r"[.eE]", t)]
        names_skew = re.search(r"(?i)skew", line) is not None
        if names_skew and not toks:
            in_skew_table = True  # header row, e.g. "Latency  CRPR  Skew"
        elif not line.strip() or line.lstrip().startswith("Clock "):
            in_skew_table = False
        if names_skew and toks:
            cands.append(toks[-1])
        elif in_skew_table and len(toks) >= 3 and len(toks) == len(line.split()):
            cands.append(toks[-1])
    target = _gt_summary(ctx, params)[f"{params.get('check', 'setup')}_skew"]
    good = [t for t in cands if (_decimals(t) is None or _decimals(t) >= min_digits)
            and abs(float(t) - target) <= _value_tol(t)]
    checks.append(check("skew_matches_ground_truth", bool(cands) and len(good) == len(cands),
                        f"stated skew values {cands[:6]} vs ground truth {target:.5f} ns "
                        f"(>= {min_digits} decimals)"))
    return checks


@register("ta_timing_summary")
def timing_summary(ctx: ValidationContext, params: dict) -> list[Check]:
    """Labelled timing numbers in a prescribed layout, compared with the oracle."""
    checks = [design_unchanged(ctx)]
    gt = _gt_summary(ctx, params)
    if params.get("spef"):
        checks.append(_spef_check(ctx, params["spef"], gt, params.get("spef_min_fraction", 0.95)))
    text = _read_nonempty(ctx, params["file"], checks)
    if text is None:
        return checks
    fields = params["fields"]
    min_decimals = int(params.get("min_decimals", 4))
    lines = [line for line in text.splitlines() if line.strip()]
    one_line = params.get("layout") == "one_line"
    want = 1 if one_line else len(fields)
    checks.append(check("layout", len(lines) == want, f"{len(lines)} non-empty lines, {want} required"))
    for f in fields:
        label, key = f["label"], f["gt"]
        if one_line:
            pat = rf"(?i)(?<![A-Za-z0-9_]){re.escape(label)}\s*=\s*({_FLOAT})(?![\w.])"
        else:  # a trailing time unit is tolerated
            pat = rf"(?im)^\s*{re.escape(label)}\s*[=:]?\s*({_FLOAT})(?:\s*ns)?\s*$"
        found = re.findall(pat, text)
        target = gt[key]
        if len(found) != 1:
            checks.append(check(label, False, f"value found {len(found)} times (expected once)"))
            continue
        tok = found[0]
        if f.get("integer"):
            ok = re.fullmatch(r"[-+]?\d+", tok) is not None and int(tok) == int(round(target))
            checks.append(check(label, ok, f"{tok} vs ground truth {int(round(target))}"))
            continue
        d = _decimals(tok)
        ok = abs(float(tok) - target) <= float(f["tol"]) and (d is None or d >= min_decimals)
        checks.append(check(label, ok, f"{tok} vs ground truth {target:.5f} (tol {f['tol']}, "
                                       f">= {min_decimals} decimals)"))
    return checks


def _spef_check(ctx: ValidationContext, name: str, gt: dict, min_fraction: float) -> Check:
    p = ctx.output_path(name)
    if not p.is_file():
        return check(f"spef:{name}", False, "missing")
    text = p.read_text(errors="replace")
    dnets = len(re.findall(r"(?m)^\*D_NET\b", text))
    want = int(gt.get("spef_dnets", 0))
    ok = text.lstrip().startswith("*SPEF") and want > 0 and dnets >= min_fraction * want
    return check(f"spef:{name}", ok, f"{dnets} *D_NET sections (reference extraction {want})")


@register("ta_drv_violations")
def drv_violations(ctx: ValidationContext, params: dict) -> list[Check]:
    """Lists of pins violating design-wide max transition / max capacitance limits."""
    checks = [design_unchanged(ctx)]
    body = _TCL_HELPERS + _setup_tcl(params) + "\n" + _DRV_BODY
    gt = ctx.query_baseline(body, name="ta_drv")
    insts = set(ctx.baseline.get("positions") or {})
    ports = set(ctx.baseline.get("io_pins") or {})
    for kind, name in params["files"].items():
        text = _read_nonempty(ctx, name, checks)
        if text is None:
            continue
        found = _pin_tokens(text, insts, ports)
        expected = set(gt.get(kind, []))
        missing, extra = expected - found, found - expected
        detail = f"{len(found)} pins listed, {len(expected)} violate"
        if missing:
            detail += f"; missing {_fmt(missing)}"
        if extra:
            detail += f"; not violating {_fmt(extra)}"
        checks.append(check(f"{kind}_violators", bool(expected) and not missing and not extra, detail))
    return checks


def _pin_tokens(text: str, insts: set[str], ports: set[str]) -> set[str]:
    """Design pin names (instance/pin of a known instance, or a top-level port) in a report."""
    out = set()
    for tok in re.split(r"[\s,;]+", text):
        tok = tok.strip("'\"{}()")
        if "/" in tok:
            inst, pin = tok.rsplit("/", 1)
            if inst in insts and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", pin):
                out.add(tok)
        elif tok in ports:
            out.add(tok)
    return out
