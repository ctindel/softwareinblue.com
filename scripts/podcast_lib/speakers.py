"""Read/write `speakers.json` mapping SPEAKER_NN → human name."""
from __future__ import annotations

import json
from pathlib import Path


class SpeakerError(Exception):
    """Raised on bad speaker override input."""


def load_speakers(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_speakers(path: Path, mapping: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping, indent=2, sort_keys=True))


def apply_overrides(existing: dict[str, str], pairs: list[str]) -> dict[str, str]:
    """Merge `KEY=VALUE` strings into `existing`, returning the new mapping."""
    out = dict(existing)
    for raw in pairs:
        if "=" not in raw:
            raise SpeakerError(f"Bad speaker override '{raw}': expected KEY=VALUE")
        k, v = raw.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k or not v:
            raise SpeakerError(f"Bad speaker override '{raw}': empty key or value")
        out[k] = v
    return out
