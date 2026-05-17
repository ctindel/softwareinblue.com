"""Speaker-labeled Markdown transcript.

Consecutive segments by the same speaker are merged into one paragraph.
Speaker label uses `speakers[id]` if available, else the raw id.
"""
from __future__ import annotations

from typing import Any


def _label(speaker_id: str, mapping: dict[str, str]) -> str:
    return mapping.get(speaker_id, speaker_id)


def render_md(transcript: dict[str, Any], speakers: dict[str, str]) -> str:
    paragraphs: list[str] = []
    current_speaker: str | None = None
    current_text: list[str] = []

    def flush() -> None:
        if current_speaker is not None and current_text:
            text = " ".join(s.strip() for s in current_text).strip()
            paragraphs.append(f"**{_label(current_speaker, speakers)}:** {text}")

    for seg in transcript.get("segments", []):
        sp = seg.get("speaker", "SPEAKER_??")
        if sp != current_speaker:
            flush()
            current_speaker = sp
            current_text = []
        text = seg.get("text", "").strip()
        if text:
            current_text.append(text)
    flush()
    return "\n\n".join(paragraphs) + ("\n" if paragraphs else "")
