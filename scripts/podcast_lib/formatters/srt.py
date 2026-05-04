"""SRT subtitle renderer.

Cue strategy: walk a segment's word list, accumulating words into the
current cue. Close the cue when any of these is reached:
- MAX_CUE_SECONDS of duration
- MAX_CUE_WORDS of word count
- a sentence-ending punctuation (`.!?`)

Cues never split a word — the word is the smallest unit.
"""
from __future__ import annotations

from typing import Any

from ..config import MAX_CUE_SECONDS, MAX_CUE_WORDS


def _format_ts(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _cues_for_segment(seg: dict[str, Any]) -> list[tuple[float, float, str]]:
    words = seg.get("words", [])
    if not words:
        text = seg.get("text", "").strip()
        if text:
            return [(seg["start"], seg["end"], text)]
        return []
    cues: list[tuple[float, float, str]] = []
    cur_start: float | None = None
    cur_words: list[str] = []
    for w in words:
        if cur_start is None:
            cur_start = w["start"]
        cur_words.append(w["word"])
        is_sentence_end = any(w["word"].rstrip().endswith(p) for p in (".", "!", "?"))
        too_long = w["end"] - cur_start >= MAX_CUE_SECONDS
        too_many = len(cur_words) >= MAX_CUE_WORDS
        if is_sentence_end or too_long or too_many:
            cues.append((cur_start, w["end"], " ".join(cur_words).strip()))
            cur_words = []
            cur_start = None
    if cur_words and cur_start is not None:
        cues.append((cur_start, words[-1]["end"], " ".join(cur_words).strip()))
    return cues


def render_srt(transcript: dict[str, Any]) -> str:
    blocks: list[str] = []
    idx = 1
    for seg in transcript.get("segments", []):
        for start, end, text in _cues_for_segment(seg):
            blocks.append(
                f"{idx}\n{_format_ts(start)} --> {_format_ts(end)}\n{text}"
            )
            idx += 1
    return "\n\n".join(blocks) + ("\n" if blocks else "")
