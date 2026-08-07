"""Reusable checks for category validators."""
from __future__ import annotations

import math
from typing import Any

from benchmark.task_validator import Check, ValidationContext

PLACED = {"PLACED", "FIRM", "LOCKED", "COVER"}


def check(name: str, passed: bool, detail: str = "") -> Check:
    return Check(name, bool(passed), detail)


def file_nonempty(ctx: ValidationContext, name: str, min_bytes: int = 1) -> Check:
    p = ctx.output_path(name)
    if not p.is_file():
        return Check(f"file:{name}", False, "missing")
    size = p.stat().st_size
    return Check(f"file:{name}", size >= min_bytes, f"{size} bytes")


def approx(name: str, value: float | None, target: float, rtol: float | None = None,
           atol: float | None = None) -> Check:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return Check(name, False, f"value unavailable (target {target})")
    tol = 0.0
    if rtol is not None:
        tol = max(tol, abs(target) * rtol)
    if atol is not None:
        tol = max(tol, atol)
    ok = abs(value - target) <= tol
    return Check(name, ok, f"value {value:.6g}, target {target:.6g} +/- {tol:.3g}")


def all_logic_placed(ctx: ValidationContext) -> Check:
    p = ctx.probe
    n, placed = p.get("logic_inst_count", 0), p.get("logic_placed_count", 0)
    return Check("all_cells_placed", n > 0 and n == placed, f"{placed}/{n} placed")


def placement_legal(ctx: ValidationContext) -> Check:
    legal = ctx.probe.get("placement_legal")
    return Check("placement_legal", legal is True, f"check_placement legal={legal}")


def moved_cells(ctx: ValidationContext) -> dict[str, float]:
    """Displacement of standard cells relative to the starting state (um)."""
    before = ctx.baseline.get("positions", {}) or {}
    after = ctx.probe.get("positions", {}) or {}
    disp = []
    for name, (x0, y0, _o0) in before.items():
        if name in after:
            x1, y1, _o1 = after[name]
            disp.append(math.hypot(x1 - x0, y1 - y0))
    moved = [d for d in disp if d > 1e-6]
    return {
        "compared": len(disp),
        "moved": len(moved),
        "mean_disp": sum(disp) / len(disp) if disp else 0.0,
        "max_disp": max(disp) if disp else 0.0,
    }


def netlist_intact(ctx: ValidationContext, allow_logic_change: bool = False) -> Check:
    """Guard against destructive 'solutions' (deleting cells or IO ports)."""
    b, p = ctx.baseline, ctx.probe
    ok = p.get("io_pin_count") == b.get("io_pin_count")
    detail = f"io {p.get('io_pin_count')}/{b.get('io_pin_count')}"
    if not allow_logic_change:
        ok = ok and p.get("logic_inst_count", 0) >= b.get("logic_inst_count", 0)
        detail += f", logic cells {p.get('logic_inst_count')}/{b.get('logic_inst_count')}"
    else:
        ok = ok and p.get("sequential_count") == b.get("sequential_count")
        detail += f", registers {p.get('sequential_count')}/{b.get('sequential_count')}"
    return Check("netlist_intact", ok, detail)


def get(ctx: ValidationContext, key: str, default: Any = None) -> Any:
    return ctx.probe.get(key, default)
