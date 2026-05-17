"""Shared helpers used across the publish-* command modules.

Pulled out of `commands/publish_clip.py` so episode-level and clip-level
publish flows can share the same path conventions and metadata reads.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Platforms outside YouTube that get cross-posted with the clip / episode
# announcement. YouTube is intentionally absent — `publish-clip` and
# `publish-youtube` cover that target separately.
SOCIAL_PLATFORMS = ("linkedin-page", "x", "instagram", "tiktok", "facebook")


def episode_dir_default(episode_num: int) -> Path:
    """Where the source video files live. Local repo's
    `episodes/Episode<NN>/` wins if it has any .mp4; otherwise fall back
    to the network volume (Joanna's archive). Returns the local path
    even on miss so error messages point at the obvious location."""
    local = REPO_ROOT / "episodes" / f"Episode{episode_num:02d}"
    if any(local.glob("*.mp4")):
        return local
    nas = (
        Path("/Volumes/Public/Backup/Chad/Business/Software_in_Blue")
        / f"Episode{episode_num}"
    )
    if nas.exists():
        return nas
    return local


def clip_paths(ep_dir: Path, episode_num: int, clip_num: int) -> tuple[Path, Path]:
    """(horizontal, vertical) clip paths. SIB_E<N>_clip<I>{H,V}.mp4 —
    Joanna's edit naming, no underscore between 'clip', the number, or
    the orientation suffix."""
    h = ep_dir / f"SIB_E{episode_num}_clip{clip_num}H.mp4"
    v = ep_dir / f"SIB_E{episode_num}_clip{clip_num}V.mp4"
    return h, v


def clip_meta(meta: dict, clip_num: int) -> dict:
    for c in meta.get("clips") or []:
        if c["number"] == clip_num:
            return c
    raise ValueError(f"No clip #{clip_num} in metadata YAML")


def short_tags(meta: dict) -> list[str]:
    base = ["software in blue", "tech sales", "presales", "shorts"]
    return base + (meta["episode"].get("topics") or [])


def episode_cover_default(episode_num: int) -> Path:
    """Default cover image for episode-announcement social posts. The W1
    podcast cover is the canonical SIB image (used in episode_image
    frontmatter too)."""
    return (
        REPO_ROOT / "hugosite" / "static" / "img" / "episode"
        / f"Episode{episode_num:02d}" / "w1" / "podcast-cover-3000x3000.png"
    )
