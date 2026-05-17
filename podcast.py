#!/usr/bin/env python3
"""Top-level Typer CLI for SIB podcast post-processing."""
from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv

# Load secrets from scripts/podcast_lib/.env (HF_TOKEN, etc.) before
# importing any module that reads from os.environ at import time.
# Existing env vars take precedence — supplying HF_TOKEN at the shell
# always wins over the dotenv file.
_ENV_PATH = Path(__file__).resolve().parent / "scripts" / "podcast_lib" / ".env"
load_dotenv(_ENV_PATH, override=False)

from scripts.podcast_lib.commands import (
    batch_titles,
    chapters,
    describe,
    import_clips,
    label,
    linkedin,
    moments,
    posts,
    publish_clip_socials,
    publish_clip_youtube,
    publish_episode_socials,
    publish_episode_spotify,
    publish_episode_youtube,
    status,
    subtitle,
    subtitle_clip,
    thumbnail,
    thumbnail_clip,
    transcribe,
    transcribe_clip,
    validate,
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
app.command("posts")(posts.run)
app.command("publish-episode-spotify")(publish_episode_spotify.run)
app.command("publish-episode-youtube")(publish_episode_youtube.run)
app.command("publish-episode-socials")(publish_episode_socials.run)
app.command("publish-clip-youtube")(publish_clip_youtube.run)
app.command("publish-clip-socials")(publish_clip_socials.run)
app.command("batch-titles")(batch_titles.run)
app.command("import-clips")(import_clips.run)
app.command("transcribe-clip")(transcribe_clip.run)
app.command("subtitle-clip")(subtitle_clip.run)
app.command("thumbnail-clip")(thumbnail_clip.run)
app.command("validate")(validate.run)


if __name__ == "__main__":
    app()
