"""`podcast subtitle` — regenerate SRT/VTT from transcript.json (no re-transcribe)."""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from ..config import ArtifactPaths, episode_number_from_folder, latest_run_dir
from ..episode import EpisodeError, resolve_episode_folder
from ..formatters.srt import render_srt
from ..formatters.vtt import render_vtt


def run(episode: str = typer.Argument(...)) -> None:
    console = Console()
    try:
        folder = resolve_episode_folder(episode)
        episode_num = episode_number_from_folder(folder)
    except (EpisodeError, ValueError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    run_dir = latest_run_dir(episode_num)
    if run_dir is None:
        console.print(f"[red]No transcribe runs found for Episode {episode_num}. "
                      f"Run `podcast transcribe` first.[/red]")
        raise typer.Exit(2)
    paths = ArtifactPaths.for_run(run_dir)
    if not paths.transcript_json.exists():
        console.print(f"[red]No transcript.json at {paths.transcript_json}. "
                      f"Latest run is incomplete; re-run `podcast transcribe`.[/red]")
        raise typer.Exit(2)
    transcript = json.loads(paths.transcript_json.read_text())
    paths.transcript_srt.write_text(render_srt(transcript))
    paths.transcript_vtt.write_text(render_vtt(transcript))
    console.print(f"[green]Regenerated SRT + VTT in {paths.artifacts_dir}[/green]")
