"""`podcast publish-clip EPISODE CLIP_NUM` — post a single 9:16 clip to
YouTube Shorts via Postiz.

Sibling command `publish-clip-socials` does the cross-post to LinkedIn /
X / Instagram / TikTok / Facebook. The two are split so the producer
can schedule YouTube and the social drip on different dates.

Source convention: `Episode<NN>/SIB_E<N>_clip<I>V.mp4` (Joanna pre-cuts
both H and V; pipeline only consumes V here).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from scripts.podcast_lib.postiz import PostizClient, youtube_post
from scripts.podcast_lib.posting import load_metadata, render_clip_post
from scripts.podcast_lib._publish_helpers import (
    clip_meta,
    clip_paths,
    episode_dir_default,
    short_tags,
)


def run(
    episode: int = typer.Argument(..., help="Episode number, e.g. 45"),
    clip: int = typer.Argument(..., help="Clip number, e.g. 1"),
    video: Path = typer.Option(None, help="Override 9:16 vertical clip path."),
    publish_at: str = typer.Option(
        None, "--publish-at",
        help="Schedule (ISO datetime). Omit to post immediately.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Build payload, verify integration, skip uploads + POST.",
    ),
) -> None:
    console = Console()
    meta = load_metadata(episode)
    info = clip_meta(meta, clip)
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
    yt = client.integration_by(identifier="youtube")
    console.print(f"YouTube channel: [bold]{yt['name']}[/bold] ({yt['profile']})")

    description = render_clip_post(meta, clip)
    title = info["overlay_text"]
    tags = short_tags(meta)
    when = datetime.fromisoformat(publish_at) if publish_at else None

    if dry_run:
        console.print("[dim]--dry-run: skipping upload + post.[/dim]")
        console.print(f"  vertical clip: {v_path} ({v_path.stat().st_size:,} bytes)")
        console.print(f"  scheduled at:  {when or 'now'}")
        console.print(f"  short title:   {title}")
        console.print("  --- description ---")
        console.print(description)
        raise typer.Exit(0)

    console.print(f"Uploading vertical clip ({v_path.stat().st_size:,} bytes)…")
    media = client.upload(v_path)
    post = youtube_post(
        integration_id=yt["id"],
        description=description,
        video=media,
        title=title,
        tags=tags,
        visibility="public",
    )
    console.print("Submitting YouTube Shorts post to Postiz…")
    resp = client.create_post(integrations=[post], when=when)
    console.print(f"[green]ok[/green]: {resp}")
