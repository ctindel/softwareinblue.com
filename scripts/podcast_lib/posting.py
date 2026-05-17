"""Render social-media posts from per-episode metadata YAML.

Reads `episodes/Episode<NN>/SIB_E<NN>_metadata.yaml` (the private metadata
file the user keeps outside Hugo) and produces the post bodies that go into
the SIB_Posting_Schedule spreadsheet.

Lifecycle: the metadata file is filled out in stages. Episode YouTube + Spotify
URLs land at publish time; per-clip YouTube URLs land as Joanna uploads each
short; `posted_*` URLs land as each platform publishes. Templates use Python
`{key}` placeholders; any key that hasn't been filled in renders as
`<TBD: key>` so the output makes it obvious what's still pending.

CLI:
    python3 podcast.py posts 45                  # all posts (full + 12 clips)
    python3 podcast.py posts 45 --clip 3         # one clip's body
    python3 podcast.py posts 45 --full           # full-episode body only
    python3 podcast.py posts 45 --twitter        # Twitter variants instead of long form
"""
from __future__ import annotations

import string
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class _TBDFormatter(string.Formatter):
    """str.Formatter that renders missing or empty keys as `<TBD: key>`
    instead of raising KeyError. Lets us print partially-filled posts."""

    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            v = kwargs.get(key, _Missing)
            if v is _Missing:
                return f"<TBD: {key}>"
            if v == "":
                return f"<TBD: {key}>"
            return v
        return super().get_value(key, args, kwargs)


_Missing = object()
_FMT = _TBDFormatter()


def metadata_path(episode_num: int) -> Path:
    return REPO_ROOT / "episodes" / f"Episode{episode_num:02d}" / f"SIB_E{episode_num:02d}_metadata.yaml"


def load_metadata(episode_num: int) -> dict[str, Any]:
    p = metadata_path(episode_num)
    if not p.exists():
        raise FileNotFoundError(f"Episode metadata missing: {p}")
    with p.open() as f:
        return yaml.safe_load(f)


def _shared_context(meta: dict[str, Any]) -> dict[str, Any]:
    """Keys available to every template (episode-level)."""
    ep = meta["episode"]
    g = ep["guest"]
    twitter_handle = (g.get("twitter_handle") or "").strip()
    twitter_title  = (g.get("twitter_title")  or g.get("short_title") or g["full_title"]).strip()
    return {
        "guest_name":              g["full_name"],
        "guest_title":             g["full_title"],
        "guest_short_title":       g["short_title"],
        # Twitter form: prefer @handle, fall back to full name.
        "guest_twitter_or_name":   twitter_handle if twitter_handle else g["full_name"],
        "twitter_title":           twitter_title,
        "twitter_topic":           ep.get("twitter_topic", ""),
        "episode_number":          ep["number"],
        "episode_youtube_full":    ep["links"].get("youtube_full", ""),
        "episode_spotify":         ep["links"].get("spotify", ""),
        "long_description":        ep.get("long_description", "").rstrip(),
        "tagline":                 ep.get("tagline", ""),
        "links_mentioned_block":   "\n\n".join(ep.get("links_mentioned", [])),
    }


def render_footer(meta: dict[str, Any]) -> str:
    return _FMT.format(meta["templates"]["footer"]).rstrip()


def render_clip_post(meta: dict[str, Any], clip_number: int, *, short: bool = False) -> str:
    """Render the long YouTube/TikTok/LinkedIn post body for one clip
    (or the Twitter version when short=True)."""
    clip = next((c for c in meta["clips"] if c["number"] == clip_number), None)
    if clip is None:
        raise ValueError(f"No clip #{clip_number} in metadata")
    ctx = _shared_context(meta)
    ctx.update({
        "clip_number":      clip["number"],
        "clip_description": clip["description"],
        "clip_overlay":     clip["overlay_text"],
        "clip_youtube":     clip.get("links", {}).get("youtube", ""),
        "footer":           render_footer(meta),
    })
    template_key = "clip_twitter" if short else "clip_long"
    return _FMT.format(meta["templates"][template_key], **ctx).rstrip()


def render_full_episode_post(meta: dict[str, Any], *, short: bool = False) -> str:
    ctx = _shared_context(meta)
    ctx["footer"] = render_footer(meta)
    template_key = "episode_twitter" if short else "episode_long"
    return _FMT.format(meta["templates"][template_key], **ctx).rstrip()


def render_all_posts(meta: dict[str, Any], *, short: bool = False) -> Iterable[tuple[str, str]]:
    """Yield (label, body) for the full episode + every clip in order."""
    yield ("Full Episode", render_full_episode_post(meta, short=short))
    for clip in meta["clips"]:
        yield (f"Clip {clip['number']}", render_clip_post(meta, clip["number"], short=short))
