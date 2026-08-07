"""Parsers for OpenROAD/OpenSTA text reports (formats of the pinned build)."""
from __future__ import annotations

import re

_FLOAT = r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?"


def timing_paths(text: str) -> list[dict]:
    """Split a ``report_checks`` (full / full_clock / full_clock_expanded) report into paths."""
    paths = []
    for block in re.split(r"(?m)^(?=Startpoint:)", text):
        if not block.startswith("Startpoint:"):
            continue
        sp = re.search(r"^Startpoint:\s*(\S+)", block, re.M)
        ep = re.search(r"^Endpoint:\s*(\S+)", block, re.M)
        ptype = re.search(r"^Path Type:\s*(\w+)", block, re.M)
        group = re.search(r"^Path Group:\s*(\S+)", block, re.M)
        slack = re.search(rf"^\s*({_FLOAT})\s+slack\s+\((MET|VIOLATED)\)", block, re.M)
        paths.append({
            "startpoint": sp.group(1) if sp else None,
            "endpoint": ep.group(1) if ep else None,
            "path_type": ptype.group(1) if ptype else None,
            "group": group.group(1) if group else None,
            "slack": float(slack.group(1)) if slack else None,
            "text": block,
        })
    return paths


def endpoint_slacks(text: str) -> list[tuple[str, float]]:
    """Rows of ``report_checks -format end`` / ``-format summary`` tables."""
    rows = []
    for m in re.finditer(rf"^(\S+)(?:\s+\([^)]*\))?\s+{_FLOAT}\s+{_FLOAT}\s+({_FLOAT})\s*(?:\((?:MET|VIOLATED)\))?\s*$",
                         text, re.M):
        rows.append((m.group(1), float(m.group(2))))
    return rows


def design_area(text: str) -> tuple[float, float] | None:
    """``report_design_area`` -> (area_um2, utilization_percent)."""
    m = re.search(rf"Design area\s+({_FLOAT})\s+u\^2\s+({_FLOAT})%\s+utilization", text)
    return (float(m.group(1)), float(m.group(2))) if m else None


def labeled_value(text: str, label: str) -> float | None:
    """Value printed as ``<label> <number>`` (e.g. 'worst slack', 'tns', 'wns')."""
    m = re.search(rf"(?mi)^\s*{re.escape(label)}\s+({_FLOAT})\s*$", text)
    return float(m.group(1)) if m else None


def clock_skew(text: str) -> float | None:
    """Skew of the last row printed by ``report_clock_skew``."""
    vals = re.findall(rf"^\s*({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})\s*$", text, re.M)
    return float(vals[-1][2]) if vals else None


def numbers(text: str) -> list[float]:
    return [float(x) for x in re.findall(_FLOAT, text)]
