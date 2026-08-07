"""Validator for the worked example task DEV-EX-01 (dev split)."""
from __future__ import annotations

from benchmark.task_validator import Check, ValidationContext, register
from benchmark.validators.common import approx, check

ALL_METALS = {f"metal{i}" for i in range(1, 11)}


@register("example_floorplan_init")
def floorplan_init(ctx: ValidationContext, params: dict) -> list[Check]:
    p = ctx.probe
    checks = [check("rows_created", p.get("row_count", 0) > 0, f"{p.get('row_count')} rows")]
    checks.append(approx("core_utilization", p.get("utilization"), params["utilization"], atol=params["util_tol"]))
    core, die = p.get("core"), p.get("die")
    if not core or not die:
        checks.append(check("die_and_core_defined", False, "die or core area missing"))
        return checks
    w, h = core[2] - core[0], core[3] - core[1]
    checks.append(approx("core_aspect_ratio", h / w, params["aspect_ratio"], rtol=params["ar_tol"]))
    margins = [core[0] - die[0], core[1] - die[1], die[2] - core[2], die[3] - core[3]]
    lo = params["margin_um"] - params["margin_tol_low"]
    hi = params["margin_um"] + params["margin_tol_high"]
    checks.append(check("core_to_die_margins", all(lo <= m <= hi for m in margins),
                        "margins " + ", ".join(f"{m:.3f}" for m in margins) + f" (allowed {lo}..{hi})"))
    layers = set(p.get("track_grid_layers", []))
    checks.append(check("routing_tracks_all_layers", ALL_METALS <= layers, f"track grids on {sorted(layers)}"))
    return checks
