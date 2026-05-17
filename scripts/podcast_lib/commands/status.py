"""`podcast status` — show which artifacts exist."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from ..config import ArtifactPaths, episode_number_from_folder, latest_run_dir
from ..episode import EpisodeError, resolve_episode_folder
from ..progress import fmt_progress_line


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
        console.print(f"[yellow]No transcribe runs yet for Episode {episode_num} "
                      f"(under /tmp/sib/artifacts/Episode{episode_num}/).[/yellow]")
        raise typer.Exit(2)
    paths = ArtifactPaths.for_run(run_dir)

    table = Table(title=f"Status: {folder.name}  ·  run {run_dir.name}")
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

    # Show in-flight progress for the transcribe / align stages, if metadata
    # has been written. Useful for peeking at long-running background jobs.
    if paths.metadata.exists():
        try:
            md = json.loads(paths.metadata.read_text())
        except Exception:
            md = {}
        for label, key in (("transcribe", "transcribe_progress"),
                            ("align",      "align_progress")):
            prog = md.get(key)
            if prog:
                console.print(f"  [cyan]{fmt_progress_line(prog, label)}[/cyan]")
