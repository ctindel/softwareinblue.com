"""`podcast publish-clip-socials EPISODE CLIP_NUM` — cross-post a single
9:16 clip to LinkedIn / X / Instagram Reel / TikTok / Facebook via
Postiz.

Sibling to `publish-clip` (which posts to YouTube Shorts). Split so the
producer can schedule YouTube and the social drip on independent dates.

Per-platform copy: render_clip_post() from posting.py is the canonical
source. X gets the `clip_twitter` short variant; the others get
`clip_long`. Both are filled from the same metadata, so per-clip
content stays in sync across platforms.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from scripts.podcast_lib.postiz import (
    PostizClient,
    facebook_post,
    instagram_post,
    linkedin_post,
    tiktok_post,
    x_post,
)
from scripts.podcast_lib.posting import load_metadata, render_clip_post
from scripts.podcast_lib._publish_helpers import (
    SOCIAL_PLATFORMS,
    clip_meta,
    clip_paths,
    episode_dir_default,
)


def run(
    episode: int = typer.Argument(..., help="Episode number, e.g. 45"),
    clip: int = typer.Argument(..., help="Clip number, e.g. 1"),
    video: Path = typer.Option(None, help="Override 9:16 vertical clip path."),
    publish_at: str = typer.Option(
        None, "--publish-at",
        help="Schedule (ISO datetime). Omit to post immediately.",
    ),
    skip: list[str] = typer.Option(
        [], "--skip",
        help="Platform identifier(s) to skip (e.g. --skip tiktok).",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Build payload, verify integrations, skip uploads + POST.",
    ),
) -> None:
    console = Console()
    meta = load_metadata(episode)
    clip_meta(meta, clip)  # validates clip exists in metadata
    ep_dir = episode_dir_default(episode)
    _, v_path = clip_paths(ep_dir, episode, clip)
    if video:
        v_path = video
    if not v_path.exists():
        console.print(f"[red]9:16 clip not found: {v_path}[/red]")
        console.print(
            "  expected naming: SIB_E<N>_clip<I>V.mp4. "
            "Pass --video PATH to override."
        )
        raise typer.Exit(2)

    client = PostizClient.from_env()
    available = {i["identifier"]: i for i in client.list_integrations()}
    targets = [p for p in SOCIAL_PLATFORMS if p not in skip]
    missing = [p for p in targets if p not in available]
    if missing:
        console.print(
            f"[yellow]not connected in Postiz: {missing} — connect them in "
            "the UI or use --skip to suppress.[/yellow]"
        )

    long_body = render_clip_post(meta, clip)
    tweet_body = render_clip_post(meta, clip, short=True)
    when = datetime.fromisoformat(publish_at) if publish_at else None

    if dry_run:
        console.print(f"[dim]--dry-run: episode {episode}, clip {clip}[/dim]")
        console.print(f"  vertical clip: {v_path} ({v_path.stat().st_size:,} bytes)")
        console.print(f"  scheduled at:  {when or 'now'}")
        console.print(f"  fan out to:    {[p for p in targets if p in available]}")
        console.print("  --- long body ---")
        console.print(long_body)
        console.print("  --- twitter body ---")
        console.print(tweet_body)
        raise typer.Exit(0)

    console.print(f"Uploading vertical clip ({v_path.stat().st_size:,} bytes)…")
    media = client.upload(v_path)

    integrations = []
    for ident in targets:
        if ident not in available:
            continue
        ig = available[ident]
        if ident == "linkedin":
            integrations.append(linkedin_post(ig["id"], long_body, media=[media]))
        elif ident == "linkedin-page":
            integrations.append(linkedin_post(ig["id"], long_body, media=[media], page=True))
        elif ident == "x":
            integrations.append(x_post(ig["id"], tweet_body, media=[media]))
        elif ident == "instagram":
            integrations.append(instagram_post(ig["id"], long_body, media=[media], reel=True))
        elif ident == "tiktok":
            integrations.append(tiktok_post(ig["id"], long_body, video=media))
        elif ident == "facebook":
            integrations.append(facebook_post(ig["id"], long_body, media=[media]))

    if not integrations:
        console.print(
            "[yellow]no connected target platforms — nothing to post.[/yellow]"
        )
        raise typer.Exit(0)

    console.print(f"Submitting {len(integrations)} per-platform posts to Postiz…")
    resp = client.create_post(integrations=integrations, when=when)
    console.print(f"[green]ok[/green]: {resp}")
