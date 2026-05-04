"""`podcast status` — show which artifacts exist."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from ..config import ArtifactPaths
from ..episode import EpisodeError, resolve_episode_folder


def run(episode: str = typer.Argument(...)) -> None:
    console = Console()
    try:
        folder = resolve_episode_folder(episode)
    except EpisodeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    paths = ArtifactPaths(root=folder)

    table = Table(title=f"Status: {folder.name}")
    table.add_column("Artifact")
    table.add_column("Path")
    table.add_column("Exists")
    for label, p in [
        ("audio.wav", paths.audio),
        ("transcript.json", paths.transcript_json),
        ("transcript.srt", paths.transcript_srt),
        ("transcript.vtt", paths.transcript_vtt),
        ("transcript.txt", paths.transcript_txt),
        ("transcript.md", paths.transcript_md),
        ("speakers.json", paths.speakers),
        ("metadata.json", paths.metadata),
    ]:
        marker = "[green]yes[/green]" if p.exists() else "[red]no[/red]"
        table.add_row(label, str(p), marker)
    console.print(table)
