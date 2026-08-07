"""Loading of the YAML configuration files in ``config/``."""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

from common.paths import CONFIG_DIR, ROOT


@functools.lru_cache(maxsize=None)
def load_config(name: str) -> dict[str, Any]:
    """Load ``config/<name>.yaml`` (cached)."""
    with open(CONFIG_DIR / f"{name}.yaml") as f:
        return yaml.safe_load(f) or {}


def resolve(path: str | Path) -> Path:
    """Resolve a config path relative to the repository root."""
    p = Path(path)
    return p if p.is_absolute() else ROOT / p
