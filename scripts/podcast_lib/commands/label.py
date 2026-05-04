"""`podcast label` — set speaker names and re-render transcript.md."""
from __future__ import annotations

import json
from typing import List

import typer
from rich.console import Console

from ..config import ArtifactPaths
from ..episode import EpisodeError, resolve_episode_folder
from ..formatters.md import render_md
from ..speakers import SpeakerError, apply_overrides, load_speakers, save_speakers


def run(
    episode: str = typer.Argument(...),
    pairs: List[str] = typer.Argument(..., help="SPEAKER_00=Chad SPEAKER_01=Steve ..."),
) -> None:
    console = Console()
    try:
        folder = resolve_episode_folder(episode)
    except EpisodeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    paths = ArtifactPaths(root=folder)
    if not paths.transcript_json.exists():
        console.print(f"[red]No transcript.json at {paths.transcript_json}. Run `podcast transcribe` first.[/red]")
        raise typer.Exit(2)
    existing = load_speakers(paths.speakers)
    try:
        merged = apply_overrides(existing, pairs)
    except SpeakerError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    save_speakers(paths.speakers, merged)
    transcript = json.loads(paths.transcript_json.read_text())
    paths.transcript_md.write_text(render_md(transcript, speakers=merged))
    console.print(f"[green]Updated speakers.json + transcript.md.[/green] {merged}")
