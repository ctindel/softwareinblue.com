"""Fuzzy post-correction of transcripts against the tech-jargon catalog.

For each segment, we slide a window of 1-3 consecutive words over the
segment's words list and compare each window's joined string against
every catalog term using rapidfuzz.  A match above FUZZY_MATCH_THRESHOLD
replaces the window in both the segment-level `text` and the per-word
`word` field of the first word in the window (subsequent words in the
window are blanked, then filtered out).

Cross-size matching is intentional: a 2-word window like "elastic search"
can match the 1-word catalog term "Elasticsearch".  When the catalog term
has fewer words than the window, the extra window slots are dropped and
timestamps are merged onto the surviving first slot.

Windows shorter than MIN_WINDOW_CHARS characters are skipped to prevent
common short English words (e.g. "quick") from false-matching short
jargon abbreviations (e.g. "QUIC") near the fuzzy threshold.

Every replacement is recorded for auditing.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from rapidfuzz import fuzz

from .config import FUZZY_MATCH_THRESHOLD
from .jargon import all_terms


_WINDOW_SIZES = (3, 2, 1)

# Minimum character length of a stripped window string before fuzzy matching
# is attempted.  Prevents short common words from matching short abbreviations.
_MIN_WINDOW_CHARS = 6


def _strip_punct(s: str) -> str:
    return s.rstrip(",.!?;:")


def correct_transcript(transcript: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (corrected_transcript, replacement_log).

    The original transcript is not mutated.
    """
    out = deepcopy(transcript)
    log: list[dict[str, Any]] = []
    catalog = all_terms()

    for seg_idx, seg in enumerate(out.get("segments", [])):
        words = seg.get("words", [])
        if not words:
            continue
        i = 0
        while i < len(words):
            matched = False
            for size in _WINDOW_SIZES:
                if i + size > len(words):
                    continue
                window_tokens = [_strip_punct(words[i + k]["word"]) for k in range(size)]
                window_str = " ".join(window_tokens)
                if not window_str.strip():
                    continue
                # Skip windows that are too short to fuzzy-match reliably.
                if len(window_str) < _MIN_WINDOW_CHARS:
                    continue
                best_term = None
                best_score = 0.0
                # Compare against ALL catalog terms regardless of word count.
                for term in catalog:
                    score = fuzz.ratio(window_str.lower(), term.lower())
                    if score > best_score:
                        best_score = score
                        best_term = term
                if (
                    best_term is not None
                    and best_score >= FUZZY_MATCH_THRESHOLD
                    and window_str != best_term
                    and window_str.lower() != best_term.lower()
                ):
                    last_raw = words[i + size - 1]["word"]
                    trailing = ""
                    for ch in reversed(last_raw):
                        if ch in ",.!?;:":
                            trailing = ch + trailing
                        else:
                            break
                    replacement = best_term + trailing
                    log.append({
                        "segment": seg_idx,
                        "before": " ".join(words[i + k]["word"] for k in range(size)),
                        "after": replacement,
                        "score": round(best_score, 1),
                    })
                    words[i]["word"] = replacement
                    last_end = words[i + size - 1].get("end")
                    if last_end is None:
                        last_end = words[i].get("end") or seg.get("end") or 0.0
                    words[i]["end"] = last_end
                    for k in range(1, size):
                        words[i + k]["_drop"] = True
                    i += size
                    matched = True
                    break
            if not matched:
                i += 1
        seg["words"] = [w for w in words if not w.get("_drop")]
        seg["text"] = " ".join(w["word"] for w in seg["words"]).strip()

    return out, log
