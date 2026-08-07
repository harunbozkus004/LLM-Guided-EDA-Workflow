"""Design state as seen by the agent, built ONLY from harness probes (probe.json).

The agent never trusts what the LLM says it did: every fact here is read from
the design database by the harness-owned probe that runs after each script.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# (flag, human-readable label) in flow order
FLAGS: list[tuple[str, str]] = [
    ("design_loaded", "design loaded"),
    ("floorplan_initialized", "floorplan initialized"),
    ("tracks_defined", "routing tracks defined"),
    ("io_pins_placed", "IO pins placed"),
    ("tapcells_inserted", "tap cells inserted"),
    ("power_grid_built", "power grid built"),
    ("cells_placed", "standard cells placed"),
    ("placement_legal", "placement legal"),
    ("cts_completed", "clock tree synthesized"),
    ("global_routing_completed", "global routing done"),
    ("detailed_routing_completed", "detailed routing done"),
    ("fillers_inserted", "filler cells inserted"),
]


def _int(p: dict[str, Any], key: str) -> int:
    v = p.get(key)
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


def _num(p: dict[str, Any], key: str) -> float | None:
    v = p.get(key)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


@dataclass(frozen=True)
class DesignState:
    available: bool = False                  # a usable probe exists
    design_loaded: bool = False
    floorplan_initialized: bool = False
    tracks_defined: bool = False
    io_pins_placed: bool = False
    tapcells_inserted: bool = False
    power_grid_built: bool = False
    cells_placed: bool = False
    placement_legal: bool = False
    cts_completed: bool = False
    global_routing_completed: bool = False
    detailed_routing_completed: bool = False
    fillers_inserted: bool = False
    # numeric facts
    row_count: int = 0
    inst_count: int = 0
    logic_inst_count: int = 0
    logic_placed_count: int = 0
    io_pin_count: int = 0
    io_pins_placed_count: int = 0
    tapcell_count: int = 0
    filler_count: int = 0
    buffer_count: int = 0
    clock_sink_net_count: int = 0
    guided_net_count: int = 0
    routable_net_count: int = 0
    routed_net_count: int = 0
    utilization: float | None = None
    core_area_um2: float | None = None
    die_area_um2: float | None = None
    wns_setup: float | None = None
    tns_setup: float | None = None
    wns_hold: float | None = None
    tns_hold: float | None = None
    probe_error: str | None = None
    clock_drivers: dict[str, int] = field(default_factory=dict, compare=False)

    @classmethod
    def from_probe(cls, probe: dict[str, Any] | None) -> "DesignState":
        if not probe:
            return cls()
        if "probe_error" in probe:
            return cls(probe_error=str(probe["probe_error"])[:300])
        if not probe.get("design_loaded"):
            return cls(available=True)
        p = probe
        logic, placed = _int(p, "logic_inst_count"), _int(p, "logic_placed_count")
        io_total, io_placed = _int(p, "io_pin_count"), _int(p, "io_pins_placed")
        routable, routed = _int(p, "routable_net_count"), _int(p, "routed_net_count")
        swires = p.get("special_net_swires") or {}
        drivers = {str(k): int(v) for k, v in (p.get("clock_sink_net_drivers") or {}).items()}
        return cls(
            available=True,
            design_loaded=True,
            floorplan_initialized=_int(p, "row_count") > 0 and bool(p.get("core")),
            tracks_defined=bool(p.get("track_grid_layers")),
            io_pins_placed=io_total > 0 and io_placed == io_total,
            tapcells_inserted=_int(p, "tapcell_count") > 0,
            power_grid_built=any(isinstance(n, (int, float)) and n > 0 for n in swires.values()),
            cells_placed=logic > 0 and placed == logic,
            placement_legal=p.get("placement_legal") is True,
            cts_completed=_int(p, "clock_sink_net_count") > 1 and bool(set(drivers) - {"PORT"}),
            global_routing_completed=_int(p, "guided_net_count") > 0 or p.get("have_global_routes") is True,
            detailed_routing_completed=routable > 0 and routed == routable,
            fillers_inserted=_int(p, "filler_count") > 0,
            row_count=_int(p, "row_count"), inst_count=_int(p, "inst_count"), logic_inst_count=logic,
            logic_placed_count=placed, io_pin_count=io_total, io_pins_placed_count=io_placed,
            tapcell_count=_int(p, "tapcell_count"), filler_count=_int(p, "filler_count"),
            buffer_count=_int(p, "buffer_count"), clock_sink_net_count=_int(p, "clock_sink_net_count"),
            guided_net_count=_int(p, "guided_net_count"), routable_net_count=routable, routed_net_count=routed,
            utilization=_num(p, "utilization"), core_area_um2=_num(p, "core_area_um2"),
            die_area_um2=_num(p, "die_area_um2"), wns_setup=_num(p, "wns_setup"), tns_setup=_num(p, "tns_setup"),
            wns_hold=_num(p, "wns_hold"), tns_hold=_num(p, "tns_hold"), clock_drivers=drivers,
        )

    def flags(self) -> dict[str, bool]:
        return {name: getattr(self, name) for name, _ in FLAGS}

    def summary(self) -> str:
        """Short description of the design state for prompts."""
        if not self.available:
            return ("unavailable (design-state probe failed: " + self.probe_error + ")") if self.probe_error \
                else "unavailable (no design-state probe was taken)"
        if not self.design_loaded:
            return "no design is loaded in the session"
        yn = lambda b: "yes" if b else "no"  # noqa: E731
        parts = [f"instances: {self.inst_count} ({self.logic_inst_count} standard cells, "
                 f"{self.tapcell_count} tap cells, {self.filler_count} fillers)"]
        if self.floorplan_initialized:
            util = f", utilization {self.utilization * 100:.1f}%" if self.utilization is not None else ""
            parts.append(f"floorplan initialized: yes ({self.row_count} rows, core area "
                         f"{self.core_area_um2 or 0:.1f} um^2{util})")
        else:
            parts.append("floorplan initialized: no")
        parts += [
            f"routing tracks: {yn(self.tracks_defined)}",
            f"IO pins placed: {self.io_pins_placed_count}/{self.io_pin_count}",
            f"power grid: {yn(self.power_grid_built)}",
            f"standard cells placed: {self.logic_placed_count}/{self.logic_inst_count}"
            + (f" (legal: {yn(self.placement_legal)})" if self.cells_placed else ""),
            f"clock tree: {yn(self.cts_completed)}",
            f"global routing: {yn(self.global_routing_completed)}",
            f"detailed routing: {self.routed_net_count}/{self.routable_net_count} nets routed",
        ]
        if self.wns_setup is not None:
            parts.append(f"setup WNS {self.wns_setup:.4f} ns, TNS {self.tns_setup or 0.0:.4f} ns")
        if self.wns_hold is not None:
            parts.append(f"hold WNS {self.wns_hold:.4f} ns")
        return "; ".join(parts)


_NUMERIC = [("inst_count", "instances"), ("logic_inst_count", "standard cells"),
            ("logic_placed_count", "placed standard cells"), ("io_pins_placed_count", "placed IO pins"),
            ("tapcell_count", "tap cells"), ("filler_count", "filler cells"), ("buffer_count", "buffers"),
            ("row_count", "rows"), ("routed_net_count", "routed nets")]
_FLOATS = [("utilization", "utilization", 100.0, "%", 0.05), ("core_area_um2", "core area", 1.0, " um^2", 0.05),
           ("wns_setup", "setup WNS", 1.0, " ns", 1e-4), ("tns_setup", "setup TNS", 1.0, " ns", 1e-4),
           ("wns_hold", "hold WNS", 1.0, " ns", 1e-4)]


def diff(before: DesignState, after: DesignState) -> list[str]:
    """Human-readable changes between two design states."""
    if not (before.available and after.available):
        return []
    out = []
    for name, label in FLAGS:
        b, a = getattr(before, name), getattr(after, name)
        if b != a:
            out.append(f"{label}: {'yes' if b else 'no'} -> {'yes' if a else 'no'}")
    for name, label in _NUMERIC:
        b, a = getattr(before, name), getattr(after, name)
        if b != a:
            out.append(f"{label}: {b} -> {a}")
    for name, label, scale, unit, tol in _FLOATS:
        b, a = getattr(before, name), getattr(after, name)
        if b is None and a is None:
            continue
        if b is None or a is None or abs(a * scale - b * scale) > tol:
            fmt = lambda v: "n/a" if v is None else f"{v * scale:.4g}{unit}"  # noqa: E731
            out.append(f"{label}: {fmt(b)} -> {fmt(a)}")
    return out
