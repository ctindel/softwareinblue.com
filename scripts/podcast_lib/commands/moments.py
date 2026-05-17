"""`podcast <stage>` — not implemented yet."""
from __future__ import annotations

import typer
from rich.console import Console


def run(episode: str = typer.Argument(...)) -> None:
    Console().print("[yellow]not implemented yet[/yellow]")
    raise typer.Exit(0)
