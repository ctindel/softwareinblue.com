"""Plain-text transcript renderer. No timestamps, no speaker labels."""
from __future__ import annotations

from typing import Any


def render_txt(transcript: dict[str, Any]) -> str:
    lines = []
    for seg in transcript.get("segments", []):
        text = seg.get("text", "").strip()
        if text:
            lines.append(text)
    return "\n".join(lines) + ("\n" if lines else "")
