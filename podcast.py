#!/usr/bin/env python3
"""Top-level Typer CLI for SIB podcast post-processing."""
from __future__ import annotations

import typer

from scripts.podcast_lib.commands import (
    chapters,
    describe,
    label,
    linkedin,
    moments,
    publish_spotify,
    publish_youtube,
    status,
    subtitle,
    thumbnail,
    transcribe,
)


app = typer.Typer(
    help="Post-production for the 'Can I Get That Software in Blue?' podcast.",
    no_args_is_help=True,
)

app.command("transcribe")(transcribe.run)
app.command("subtitle")(subtitle.run)
app.command("label")(label.run)
app.command("status")(status.run)
app.command("moments")(moments.run)
app.command("thumbnail")(thumbnail.run)
app.command("describe")(describe.run)
app.command("linkedin")(linkedin.run)
app.command("chapters")(chapters.run)
app.command("publish-youtube")(publish_youtube.run)
app.command("publish-spotify")(publish_spotify.run)


if __name__ == "__main__":
    app()
