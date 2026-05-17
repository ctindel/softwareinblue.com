"""Post-correction pass that strips common WhisperX hallucinations from
transcripts. Operates on the canonical transcript.json shape (segments
with word-level timestamps) and rewrites segment.text from the surviving
words. Idempotent — safe to run repeatedly.

What it removes:

1. **Looped n-grams** — when the same 1-, 2-, or 3-word phrase repeats
   3+ times in a row, collapse to a single occurrence. This is the
   classic Whisper failure mode (`"Yeah. Yeah. Yeah. Yeah. Yeah."`,
   `"I think I think I think"`, `"do this. do this. do this."`).

2. **Phantom speaker / sponsor names** — Whisper sometimes hallucinates
   names from training-data podcast intros into the middle of segments.
   Known offenders (case-insensitive whole-phrase): "Presto Pyshko",
   "Preston Pyshko", "Jason Lowery", "Jeff Booth, CFP®", "Jeff Booth"
   (only when followed by ", CFP" — to avoid false positives).

3. **Decoder-collapse gibberish** — token strings like "ingsings" /
   "ingsingsings" that appear when the decoder gets stuck in a glyph
   loop. Detected via regex: any token containing "ingsings" or 4+
   consecutive identical 3-letter blocks.

The function returns a list of audit entries describing what was
removed so callers can log totals.
"""
from __future__ import annotations

import re
from typing import Any


_PHANTOM_PHRASES = (
    "Presto Pyshko, CFP",
    "Preston Pyshko, CFP",
    "Presto Pyshko",
    "Preston Pyshko",
    "Jason Lowery",
    "Jeff Booth, CFP",
)


def _norm_word(w: str) -> str:
    """Lowercase + strip surrounding punctuation for loop-equality checks."""
    return w.strip().strip(",.!?;:\"'-").lower()


def _is_decoder_collapse(text: str) -> bool:
    """True if a token looks like decoder-collapse gibberish."""
    if "ingsings" in text.lower():
        return True
    # 4+ identical 3-letter blocks back-to-back, e.g. "thethethethe".
    if re.search(r"(.{3,5})\1{3,}", text.lower()):
        return True
    return False


def _drop_phantom_names(words: list[dict[str, Any]], log: list[dict[str, Any]]) -> None:
    """Mark word slots that participate in a phantom name match."""
    if not words:
        return
    # Build a flat string with sentinel markers so we can map regex hits
    # back to word indices. Each word becomes its raw token + a single
    # space; we record the cumulative char offset of each word's start.
    parts: list[str] = []
    starts: list[int] = []
    cursor = 0
    for w in words:
        starts.append(cursor)
        token = w.get("word", "")
        parts.append(token)
        cursor += len(token) + 1
        parts.append(" ")
    flat = "".join(parts)
    for phrase in _PHANTOM_PHRASES:
        for m in re.finditer(re.escape(phrase), flat, re.IGNORECASE):
            ms, me = m.start(), m.end()
            for idx, ws in enumerate(starts):
                we = ws + len(words[idx].get("word", ""))
                if ws < me and we > ms:
                    if not words[idx].get("_drop"):
                        log.append({"kind": "phantom", "word": words[idx].get("word", "")})
                        words[idx]["_drop"] = True


def _collapse_ngram_loops(
    words: list[dict[str, Any]],
    log: list[dict[str, Any]],
    max_n: int = 3,
    min_run: int = 3,
) -> None:
    """Mark all but the first occurrence in any run of >= min_run identical
    n-grams (n in 1..max_n). Compares normalized tokens. Single-token loops
    of articles or filler ("the the the", "uh uh uh") collapse just like
    multi-token ones."""
    if not words:
        return
    norm = [_norm_word(w.get("word", "")) for w in words]
    i = 0
    while i < len(words):
        if words[i].get("_drop"):
            i += 1
            continue
        collapsed_for_i = False
        for n in range(max_n, 0, -1):
            if i + 2 * n > len(words):
                continue
            base = norm[i:i + n]
            if not all(base):
                continue
            # Count consecutive identical n-grams starting at i.
            run = 1
            j = i + n
            while j + n <= len(words):
                if all(not words[k].get("_drop") for k in range(j, j + n)) and \
                   norm[j:j + n] == base and all(base):
                    run += 1
                    j += n
                else:
                    break
            if run >= min_run:
                # Drop everything after the first occurrence (i..i+n-1).
                drop_start = i + n
                drop_end = i + run * n
                for k in range(drop_start, drop_end):
                    words[k]["_drop"] = True
                log.append({
                    "kind": "loop",
                    "ngram": " ".join(words[i + k].get("word", "") for k in range(n)),
                    "n": n,
                    "run": run,
                    "dropped": drop_end - drop_start,
                })
                # Extend first surviving word's end-time to the last
                # dropped word's end-time so playback timing stays sane.
                last_end = words[drop_end - 1].get("end")
                if last_end is not None:
                    words[i + n - 1]["end"] = last_end
                i = drop_end
                collapsed_for_i = True
                break
        if not collapsed_for_i:
            i += 1


def _drop_decoder_collapse(words: list[dict[str, Any]], log: list[dict[str, Any]]) -> None:
    """Mark individual word tokens that are obvious decoder-collapse gibberish."""
    for w in words:
        if w.get("_drop"):
            continue
        text = w.get("word", "")
        if _is_decoder_collapse(text):
            w["_drop"] = True
            log.append({"kind": "gibberish", "word": text})


def _collapse_segment_level_loops(transcript: dict[str, Any], log: list[dict[str, Any]]) -> None:
    """When 3+ consecutive segments by the same speaker collapse to the same
    short normalized text (e.g. each is just "Yeah." or "Right."), keep
    only the first and drop the rest. The MD renderer joins consecutive
    same-speaker segments into one paragraph, so per-segment cleanup
    alone leaves visible "Yeah. Yeah. Yeah." runs across segment
    boundaries — this pass closes that gap.

    Only applies when the normalized text is "short" (≤2 words and ≤12
    chars) to avoid clobbering legitimate repetition like an entire
    sentence being said twice for emphasis."""
    segs = transcript.get("segments", [])
    if not segs:
        return
    # Pre-compute normalized text for each segment.
    norms = [_norm_word(s.get("text", "")) for s in segs]
    drop_flags = [False] * len(segs)
    i = 0
    while i < len(segs):
        cur_norm = norms[i]
        cur_speaker = segs[i].get("speaker")
        if not cur_norm or len(cur_norm) > 12 or len(cur_norm.split()) > 2:
            i += 1
            continue
        # Find the run of consecutive same-speaker, same-normalized-text.
        j = i + 1
        while j < len(segs) and norms[j] == cur_norm and segs[j].get("speaker") == cur_speaker:
            j += 1
        run = j - i
        if run >= 3:
            for k in range(i + 1, j):
                drop_flags[k] = True
            log.append({
                "kind": "segment_loop",
                "text": cur_norm,
                "run": run,
                "dropped": run - 1,
            })
            # Extend first surviving segment's end-time so timing stays sane.
            last_end = segs[j - 1].get("end")
            if last_end is not None:
                segs[i]["end"] = last_end
        i = j
    if any(drop_flags):
        transcript["segments"] = [s for k, s in enumerate(segs) if not drop_flags[k]]


def dehallucinate_transcript(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    """Mutate `transcript` in place. Returns a list of audit entries."""
    log: list[dict[str, Any]] = []
    for seg in transcript.get("segments", []):
        words = seg.get("words", [])
        if not words:
            # No word-level data — fall back to a coarse text-only pass:
            # strip phantom names and gibberish from the raw segment text.
            text = seg.get("text", "")
            new_text = text
            for phrase in _PHANTOM_PHRASES:
                new_text = re.sub(re.escape(phrase) + r"[.,]?\s*", "", new_text, flags=re.IGNORECASE)
            # Decoder collapse — "ingsings..." can be glued onto a real prefix
            # (e.g. "Becauseingsings...") so we can't rely on a leading word
            # boundary. Truncate any token containing 3+ "ings" repeats at
            # the start of the loop, keeping whatever prefix came before.
            new_text = re.sub(r"(ings){3,}\w*", "", new_text, flags=re.IGNORECASE)
            # Generic 3+ character block repeated 4+ times anywhere — covers
            # other decoder-collapse families beyond the "ings" one.
            new_text = re.sub(r"(.{3,6})\1{3,}\w*", "", new_text)
            # Collapse "X. X. X." into "X." (text-level, simpler regex):
            new_text = re.sub(r"\b(\w+)([.,!?])(\s+\1\2){2,}", r"\1\2", new_text)
            if new_text != text:
                seg["text"] = new_text.strip()
                log.append({"kind": "text_only", "segment": seg.get("id")})
            continue
        for w in words:
            w.pop("_drop", None)
        _drop_phantom_names(words, log)
        _drop_decoder_collapse(words, log)
        _collapse_ngram_loops(words, log)
        seg["words"] = [w for w in words if not w.get("_drop")]
        seg["text"] = " ".join(w.get("word", "") for w in seg["words"]).strip()
    # After per-segment cleanup, dedupe consecutive same-speaker single-word
    # segments that the MD renderer would otherwise concatenate into a long
    # "Yeah. Yeah. Yeah." run.
    _collapse_segment_level_loops(transcript, log)
    return log
