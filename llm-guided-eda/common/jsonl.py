"""Append-safe JSON Lines helpers used for experiment records."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Iterator

_lock = threading.Lock()


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True, default=str)
    with _lock, open(path, "a") as f:
        f.write(line + "\n")


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)
