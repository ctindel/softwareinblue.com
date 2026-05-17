"""WebVTT renderer. Reuses SRT cue logic, swaps timestamp format and header."""
from __future__ import annotations

from typing import Any

from .srt import _cues_for_segment


def _format_ts(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def render_vtt(transcript: dict[str, Any]) -> str:
    out = ["WEBVTT", ""]
    for seg in transcript.get("segments", []):
        for start, end, text in _cues_for_segment(seg):
            out.append(f"{_format_ts(start)} --> {_format_ts(end)}")
            out.append(text)
            out.append("")
    return "\n".join(out)
