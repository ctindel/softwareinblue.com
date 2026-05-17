"""`podcast publish-spotify EPISODE` — drives Spotify for Creators dashboard.

Spotify has no upload API. This command shells out to
`scripts/podcast_lib/spotify_browser.py`, which uses agent-browser to
fill the dashboard form. See that script for the full flow.

Prereq: `agent-browser` CLI installed (`npm i -g agent-browser`); a
working browser session (run with `--test-login` once to seed it); and
SPOTIFY_EMAIL + SPOTIFY_PASSWORD set in `scripts/podcast_lib/.env`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console


def run(
    episode: int = typer.Argument(..., help="Episode number, e.g. 45"),
    video: Path = typer.Option(None, help="Override master video path."),
    cover: Path = typer.Option(None, help="Override cover-art path."),
    publish_at: str = typer.Option(
        None, "--publish-at",
        help="Schedule publish (ISO datetime, e.g. 2026-05-15T10:00). "
             "Omit to save as draft.",
    ),
    test_login: bool = typer.Option(
        False, "--test-login",
        help="Skip upload — just verify the browser can log in.",
    ),
) -> None:
    console = Console()
    script = Path(__file__).resolve().parent.parent / "spotify_browser.py"
    cmd: list[str] = ["python3", str(script)]
    if test_login:
        cmd.append("--test-login")
    else:
        cmd += ["--upload", str(episode)]
        if video:
            cmd += ["--video", str(video)]
        if cover:
            cmd += ["--cover", str(cover)]
        if publish_at:
            cmd += ["--publish-at", publish_at]
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    proc = subprocess.run(cmd)
    raise typer.Exit(proc.returncode)
