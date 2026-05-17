"""`podcast publish-youtube EPISODE` — schedule the main episode video
on YouTube via Postiz.

Reads metadata YAML for title/description, finds the master video file
by glob (`EpisodeN/*Final*.mp4`, excluding audio-only variants), uploads
the video + thumbnail to Postiz, and schedules a YouTube post.

Default thumbnail: `hugosite/static/img/episode/Episode<N>/d2/thumbnail-youtube-1920x1080.png`.
Override with --thumbnail.

Tailnet prereq: must be connected to the EvoGyms Tailscale tailnet
because the Postiz API lives on it.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import typer
import yaml
from rich.console import Console

from scripts.podcast_lib.postiz import PostizClient, youtube_post

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _find_master_video(episode_num: int) -> Path:
    ep_dir = REPO_ROOT / "episodes" / f"Episode{episode_num:02d}"
    if not ep_dir.exists():
        raise FileNotFoundError(f"Episode dir not found: {ep_dir}")
    matches = [
        p for p in ep_dir.iterdir()
        if p.is_file()
        and re.search(r"final", p.name, re.IGNORECASE)
        and p.suffix.lower() == ".mp4"
        and "audio" not in p.name.lower()
    ]
    if not matches:
        raise FileNotFoundError(
            f"No master video matching '*Final*.mp4' in {ep_dir} "
            "(audio-only variants excluded). Pass --video PATH."
        )
    if len(matches) > 1:
        raise FileNotFoundError(
            f"Multiple candidate videos in {ep_dir}: "
            f"{[p.name for p in matches]}. Pass --video PATH."
        )
    return matches[0]


def _load_metadata(episode_num: int) -> dict:
    p = REPO_ROOT / "episodes" / f"Episode{episode_num:02d}" / f"SIB_E{episode_num:02d}_metadata.yaml"
    if not p.exists():
        raise FileNotFoundError(f"Metadata YAML not found: {p}")
    with p.open() as f:
        return yaml.safe_load(f)


def _default_thumbnail(episode_num: int) -> Path:
    return (
        REPO_ROOT / "hugosite" / "static" / "img" / "episode"
        / f"Episode{episode_num:02d}" / "d1" / "thumbnail-youtube-1920x1080.png"
    )


def _build_description(meta: dict) -> str:
    """YouTube description = long_description + chapters + links + footer."""
    ep = meta["episode"]
    parts: list[str] = []
    if ep.get("long_description"):
        parts.append(ep["long_description"].strip())
    chapters = meta.get("chapters") or []
    if chapters:
        parts.append("Chapters:")
        for c in chapters:
            parts.append(f"{c['timestamp']} - {c['title']}")
    links = ep.get("links_mentioned") or []
    if links:
        parts.append("Links mentioned:")
        parts.extend(links)
    footer = (meta.get("templates") or {}).get("footer", "").strip()
    if footer:
        parts.append(footer)
    return "\n\n".join(parts)


def _build_tags(meta: dict) -> list[str]:
    """YouTube tags from the episode topics + a couple show-wide tags."""
    base = ["software in blue", "tech sales", "presales", "solution architecture"]
    topics = meta["episode"].get("topics") or []
    return base + [str(t) for t in topics]


def run(
    episode: int = typer.Argument(..., help="Episode number, e.g. 45"),
    video: Path = typer.Option(None, help="Override master video path."),
    thumbnail: Path = typer.Option(None, help="Override thumbnail path."),
    publish_at: str = typer.Option(
        None, "--publish-at",
        help="Schedule publish (ISO datetime, e.g. 2026-05-15T10:00). "
             "Omit to post immediately.",
    ),
    visibility: str = typer.Option("public", help="public | private | unlisted"),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Build payload + verify integration is connected, but do "
             "not call POST /posts.",
    ),
) -> None:
    console = Console()
    meta = _load_metadata(episode)
    video_path = video or _find_master_video(episode)
    thumb_path = thumbnail or _default_thumbnail(episode)

    if not video_path.exists():
        console.print(f"[red]video not found: {video_path}[/red]")
        raise typer.Exit(2)
    if not thumb_path.exists():
        console.print(f"[red]thumbnail not found: {thumb_path}[/red]")
        raise typer.Exit(2)

    title = meta["episode"]["hugo_title"]
    description = _build_description(meta)
    tags = _build_tags(meta)

    client = PostizClient.from_env()
    yt = client.integration_by(identifier="youtube")
    console.print(f"YouTube channel: [bold]{yt['name']}[/bold] ({yt['profile']})")

    when = None
    if publish_at:
        when = datetime.fromisoformat(publish_at)

    if dry_run:
        console.print("[dim]--dry-run: skipping uploads + post.[/dim]")
        console.print(f"  title: {title}")
        console.print(f"  video: {video_path} ({video_path.stat().st_size:,} bytes)")
        console.print(f"  thumb: {thumb_path}")
        console.print(f"  when:  {when or 'now'}")
        console.print(f"  tags:  {tags}")
        raise typer.Exit(0)

    console.print(f"Uploading video ({video_path.stat().st_size:,} bytes)…")
    video_media = client.upload(video_path)
    console.print(f"  video media id: {video_media['id']}")
    console.print(f"Uploading thumbnail…")
    thumb_media = client.upload(thumb_path)

    post = youtube_post(
        integration_id=yt["id"],
        description=description,
        video=video_media,
        title=title,
        tags=tags,
        thumbnail=thumb_media,
        visibility=visibility,
    )
    console.print("Submitting post to Postiz…")
    resp = client.create_post(integrations=[post], when=when)
    console.print(f"[green]ok[/green]: {resp}")
