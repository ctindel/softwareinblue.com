"""Reverse-engineer show notes from an episode's YouTube description and
write them into `episodes/Episode<NN>/SIB_E<NN>_metadata.yaml` as
`episode.show_notes:` entries.

Why this exists: the Spotify dashboard description field is destructive
on save — `spotify_cloak.py` replaces the entire description with what
we render from the metadata YAML. If `show_notes` is empty in the YAML,
any previously-written notes on Spotify are nuked. The YouTube video's
description is the closest available source-of-truth (same content,
just plain text). This module fetches it and parses the show-notes
section into YAML structure.

The parser is tuned for SIB's description format (Episode #N intro →
guest paragraph → topics paragraph → Contact/Twitter/LinkedIn boilerplate
→ Subscribe links → Stitcher → optional "Show Notes and Links
Mentioned:" header → headings + URLs). Unknown formats fall through
to a `show_notes: []` and log a warning so the operator notices.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Optional

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# Boilerplate paragraph starts — anything beginning with these is the
# follow / subscribe section, NOT a show note.
BOILERPLATE_PREFIXES = (
    "Twitter:", "LinkedIn:", "Youtube:", "Apple Podcasts:",
    "Spotify:", "Stitcher:", "Our website:",
    "Contact us on Twitter",
    "Make sure to subscribe",
)
# Phrases that mark the start of the show-notes section. Case insensitive
# substring match — any of these in a paragraph flips us into show-notes
# mode.
SHOW_NOTES_MARKERS = (
    "show notes and links mentioned",
    "links mentioned in the episode",
    "links mentioned",
    "show notes",
)
# Subscribe-section anchors that signal "show notes follow" when we
# transition from a subscribe paragraph to a non-boilerplate paragraph.
SUBSCRIBE_ANCHORS = (
    "Stitcher:", "Spotify:", "Apple Podcasts:", "Youtube:",
)


def _hugo_youtube_id(episode_num: int) -> Optional[str]:
    md = REPO_ROOT / "hugosite" / "content" / "episode" / f"episode{episode_num}.md"
    if not md.exists():
        return None
    m = re.search(r'^youtube\s*=\s*"([^"]+)"', md.read_text(), re.MULTILINE)
    return m.group(1) if m else None


def fetch_youtube_description(youtube_id: str) -> str:
    """GET the YT watch page and extract the description from the embedded
    `ytInitialPlayerResponse` JSON."""
    req = urllib.request.Request(
        f"https://www.youtube.com/watch?v={youtube_id}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")
    m = re.search(r"var ytInitialPlayerResponse = ({.*?});", html)
    if not m:
        raise RuntimeError("could not find ytInitialPlayerResponse in YT page")
    data = json.loads(m.group(1))
    return data.get("videoDetails", {}).get("shortDescription", "")


def parse_show_notes(description: str) -> list[dict]:
    """Walk the description's blank-line-separated paragraphs and emit
    a list of `{heading, urls: [...]}` entries.

    Strategy:
      1. Strip invisible chars (Spotify wraps URLs in U+2060 word joiners).
      2. Iterate paragraphs in order, skipping intro/follow boilerplate.
      3. Enter show-notes mode after the explicit "Show Notes and Links
         Mentioned:" marker OR after the last subscribe-link paragraph
         (Stitcher).
      4. In show-notes mode:
         - "Heading:"               → start a new section
         - "Heading: https://..."   → new section with the URL
         - "https://..."            → append URL to the current section
    """
    text = description.replace("⁠", "").replace("\xa0", " ")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    show_notes: list[dict] = []
    current: Optional[dict] = None
    in_notes = False
    seen_subscribe_anchor = False

    def flush():
        nonlocal current
        if current is not None and (current.get("urls") or current.get("heading")):
            show_notes.append(current)
        current = None

    for p in paragraphs:
        low = p.lower()
        if any(marker in low for marker in SHOW_NOTES_MARKERS):
            in_notes = True
            continue
        is_boilerplate = any(p.startswith(prefix) for prefix in BOILERPLATE_PREFIXES)
        if is_boilerplate:
            if any(p.startswith(anchor) for anchor in SUBSCRIBE_ANCHORS):
                seen_subscribe_anchor = True
            continue
        if not in_notes:
            # After we've passed the subscribe block (saw Spotify/Stitcher/
            # Apple Podcasts/Youtube link), the next non-boilerplate
            # paragraph kicks off the show notes — handles episodes that
            # don't include an explicit "Show Notes" header.
            if seen_subscribe_anchor:
                in_notes = True
            else:
                # Still in intro/guest paragraphs.
                continue

        # Show-notes paragraph: heading-only, inline heading+url, or url-only.
        if re.match(r"^https?://", p):
            if current is None:
                # Unexpected URL with no preceding heading — start an
                # un-named section so we don't drop it.
                current = {"heading": "", "urls": []}
            # The paragraph might be multiple URLs separated by newlines.
            for line in p.splitlines():
                line = line.strip()
                if line.startswith("http"):
                    current["urls"].append(line)
            continue

        m = re.match(r"^(.+?):\s*\n?\s*(https?://.+)$", p, re.DOTALL)
        if m:
            flush()
            heading = m.group(1).strip()
            urls_text = m.group(2)
            urls = [u.strip() for u in urls_text.splitlines() if u.strip().startswith("http")]
            current = {"heading": heading, "urls": urls}
            continue

        if p.endswith(":"):
            flush()
            current = {"heading": p[:-1].strip(), "urls": []}
            continue

        # Unknown paragraph in show-notes mode — log and skip.
        # (Don't fail; SIB descriptions sometimes have prose tail notes.)
        sys.stderr.write(f"[fetch_show_notes] skipping unrecognised paragraph: {p[:80]}…\n")

    flush()
    # Drop sections that are heading-only with no URLs — usually a parse
    # artefact (e.g., the "Contact us..." sentence picked up as heading).
    return [s for s in show_notes if s.get("urls")]


def yaml_metadata_path(episode_num: int) -> Path:
    return (
        REPO_ROOT / "episodes" / f"Episode{episode_num:02d}"
        / f"SIB_E{episode_num:02d}_metadata.yaml"
    )


def populate_show_notes(episode_num: int, force: bool = False) -> dict:
    """Top-level helper. Returns a summary dict for logging."""
    yaml_path = yaml_metadata_path(episode_num)
    if not yaml_path.exists():
        raise FileNotFoundError(yaml_path)
    meta = yaml.safe_load(yaml_path.read_text())
    ep = meta.setdefault("episode", {})
    existing = ep.get("show_notes") or []
    if existing and not force:
        return {"action": "skip", "reason": "already has show_notes", "count": len(existing)}

    yt_id = _hugo_youtube_id(episode_num)
    if not yt_id:
        return {"action": "fail", "reason": "no youtube id in Hugo md"}

    description = fetch_youtube_description(yt_id)
    parsed = parse_show_notes(description)
    if not parsed:
        return {"action": "fail", "reason": "no show notes parsed from YT description"}

    ep["show_notes"] = parsed
    # Write back preserving comments would require ruamel.yaml; PyYAML is
    # destructive about comments. The auto-generated stubs we ship today
    # already have placeholder comments that are fine to drop here.
    yaml_path.write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True))
    return {"action": "wrote", "count": len(parsed), "headings": [s["heading"] for s in parsed]}


# CLI: `python3 -m scripts.podcast_lib.fetch_show_notes 2`
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fetch_show_notes.py EPISODE_NUM [--force]", file=sys.stderr)
        sys.exit(2)
    n = int(sys.argv[1])
    force = "--force" in sys.argv[2:]
    result = populate_show_notes(n, force=force)
    print(json.dumps(result, indent=2))
