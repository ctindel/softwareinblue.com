"""`podcast posts` — render social-media post bodies for an episode."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from ..posting import (
    load_metadata,
    render_all_posts,
    render_clip_post,
    render_full_episode_post,
)


def run(
    episode: int = typer.Argument(..., help="Episode number, e.g. 45"),
    clip: Optional[int] = typer.Option(None, "--clip",
        help="Render only the post for this clip number."),
    full: bool = typer.Option(False, "--full",
        help="Render only the full-episode post body."),
    short: bool = typer.Option(False, "--twitter", "--short",
        help="Render the short Twitter variants instead of the long form."),
) -> None:
    console = Console()
    try:
        meta = load_metadata(episode)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)

    sep = "=" * 78

    if clip is not None:
        body = render_clip_post(meta, clip, short=short)
        console.print(f"[bold cyan]Clip {clip}[/bold cyan]\n{sep}\n{body}\n{sep}")
        return

    if full:
        body = render_full_episode_post(meta, short=short)
        console.print(f"[bold cyan]Full Episode[/bold cyan]\n{sep}\n{body}\n{sep}")
        return

    for label, body in render_all_posts(meta, short=short):
        console.print(f"\n[bold cyan]{label}[/bold cyan]\n{sep}\n{body}\n{sep}")
