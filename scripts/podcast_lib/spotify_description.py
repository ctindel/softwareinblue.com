"""Render the Spotify episode-description HTML from the per-episode
metadata YAML.

Spotify's episode-details editor accepts simple HTML when the "HTML"
toggle is on: paragraph-per-line `<p>...</p>` blocks plus `<a href="…"
target="_blank" rel="ugc noopener noreferrer">…</a>` for links. That's
the surface area we render.

Layout (matches what ep1 ships with — confirmed working in Spotify +
Apple Podcasts):

    <p>Episode #N of "Can I get that software in blue?", a podcast …</p>
    <p>{description_paragraphs[0]}</p>
    <p>{description_paragraphs[1]}</p>          # zero or more
    <p>Contact us on Twitter or LinkedIn to suggest companies …</p>
    <p>Twitter: <a href="…">…</a></p>
    <p>LinkedIn: <a href="…">…</a></p>
    <p>Make sure to subscribe or follow us …</p>
    <p>Youtube: <a href="…">…</a></p>
    <p>Apple Podcasts: <a href="…">…</a></p>
    <p>Spotify: <a href="…">…</a></p>
    <p>Show Notes and Links Mentioned:</p>
    <p>{heading_1}:</p>
    <p><a href="{url}">{url}</a></p>            # one per URL
    ... etc per show-notes entry

The Stitcher link is intentionally dropped (service defunct).
"""
from __future__ import annotations

from html import escape


# Show-wide constants. If these ever change, update them here once.
INTRO_BOILERPLATE = (
    'Episode #{n} of "Can I get that software in blue?", a podcast by '
    "and for people engaged in technology sales. If you are in the "
    "technology presales, sales, support or professional services "
    "career paths then this show is for you!"
)
CONTACT_PROMPT = (
    "Contact us on Twitter or LinkedIn to suggest companies or tech "
    "news articles worthy of the podcast!"
)
SUBSCRIBE_PROMPT = (
    "Make sure to subscribe or follow us to get notified about our "
    "upcoming episodes:"
)
SHOW_NOTES_HEADER = "Show Notes and Links Mentioned:"

FOLLOW_LINKS = [
    ("Twitter",  "https://twitter.com/softwareinblue"),
    ("LinkedIn", "https://www.linkedin.com/showcase/softwareinblue"),
]
SUBSCRIBE_LINKS = [
    ("Youtube",        "https://www.youtube.com/@softwareinblue"),
    ("Apple Podcasts", "https://podcasts.apple.com/us/podcast/can-i-get-that-software-in-blue/id1561899125"),
    ("Spotify",        "https://open.spotify.com/show/25r9ckggqIv6rGU8ca0WP2"),
]
def _p(s: str) -> str:
    """One paragraph. quote=False keeps `"` literal inside the body —
    Spotify's HTML editor displays the entity-encoded form verbatim."""
    return f"<p>{escape(s, quote=False)}</p>"


def _link_p(label: str, url: str) -> str:
    """`<p>{label}: {url}</p>` — Spotify and Apple Podcasts auto-linkify
    raw URLs in description fields, so we skip the `<a href>` markup
    entirely. Saves ~80 chars per link, which matters because Spotify
    rejects saves over ~4000 chars total."""
    return f"<p>{escape(label, quote=False)}: {escape(url, quote=False)}</p>"


def _link_only_p(url: str) -> str:
    return f"<p>{escape(url, quote=False)}</p>"


def render_description_html(meta: dict) -> str:
    """meta is the parsed `SIB_E<NN>_metadata.yaml`; render the full
    description HTML for the Spotify editor's HTML mode."""
    ep = meta["episode"]
    n = ep["number"]
    long_desc = ep.get("long_description", "").strip()
    show_notes = ep.get("show_notes") or []

    out: list[str] = []
    out.append(_p(INTRO_BOILERPLATE.format(n=n)))
    if long_desc:
        for p in long_desc.split("\n\n"):
            p = p.strip()
            if p:
                out.append(_p(_collapse_ws(p)))
    out.append(_p(CONTACT_PROMPT))
    for label, url in FOLLOW_LINKS:
        out.append(_link_p(label, url))
    out.append(_p(SUBSCRIBE_PROMPT))
    for label, url in SUBSCRIBE_LINKS:
        out.append(_link_p(label, url))
    if show_notes:
        out.append(_p(SHOW_NOTES_HEADER))
        for note in show_notes:
            out.append(_p(f"{note['heading']}:"))
            for url in note.get("urls", []):
                out.append(_link_only_p(url))
    return "".join(out)


def _collapse_ws(s: str) -> str:
    """YAML folded scalars introduce extra spaces and newlines; collapse
    runs of whitespace into single spaces and strip the result."""
    return " ".join(s.split())


# CLI for ad-hoc inspection: print rendered HTML for an episode.
if __name__ == "__main__":
    import sys
    import yaml
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python3 -m scripts.podcast_lib.spotify_description EPISODE_NUM")
        sys.exit(2)
    n = int(sys.argv[1])
    repo = Path(__file__).resolve().parent.parent.parent
    meta_path = repo / "episodes" / f"Episode{n:02d}" / f"SIB_E{n:02d}_metadata.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    print(render_description_html(meta))
