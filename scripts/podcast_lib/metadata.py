"""Read/write `metadata.json` describing pipeline runs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Metadata:
    path: Path
    data: dict[str, Any] = field(default_factory=lambda: {"stages": {}, "corrections": []})

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def record_stage(self, name: str, *, duration_s: float, ok: bool, **extra: Any) -> None:
        self.data.setdefault("stages", {})[name] = {
            "duration_s": duration_s,
            "ok": ok,
            **extra,
        }

    def add_correction(self, entry: dict[str, Any]) -> None:
        self.data.setdefault("corrections", []).append(entry)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True))


def load_metadata(path: Path) -> Metadata:
    if not path.exists():
        return Metadata(path=path)
    return Metadata(path=path, data=json.loads(path.read_text()))
