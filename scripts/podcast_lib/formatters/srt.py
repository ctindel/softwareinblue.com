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
    cur_end: float | None = None
    cur_words: list[str] = []
    for w in words:
        start = w.get("start")
        end = w.get("end")
        if start is None or end is None:
            continue
        # Check BEFORE appending: would adding this word exceed budget?
        if cur_words and cur_start is not None:
            would_overflow_time = end - cur_start > MAX_CUE_SECONDS
            already_at_word_cap = len(cur_words) >= MAX_CUE_WORDS
            if would_overflow_time or already_at_word_cap:
                cues.append((cur_start, cur_end if cur_end is not None else start,
                             " ".join(cur_words).strip()))
                cur_words = []
                cur_start = None
                cur_end = None
        if cur_start is None:
            cur_start = start
        cur_words.append(w["word"])
        cur_end = end
        if any(w["word"].rstrip().endswith(p) for p in (".", "!", "?")):
            cues.append((cur_start, cur_end, " ".join(cur_words).strip()))
            cur_words = []
            cur_start = None
            cur_end = None
    if cur_words and cur_start is not None and cur_end is not None:
        cues.append((cur_start, cur_end, " ".join(cur_words).strip()))
    # Cap any cue whose duration still exceeds the limit (single word longer than
    # MAX_CUE_SECONDS, e.g. Whisper attaching trailing silence to a word's end).
    return [(s, min(e, s + MAX_CUE_SECONDS), t) for s, e, t in cues]


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
