"""`podcast transcribe` subcommand."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

from ..audio import AudioError, extract_audio
from ..config import (
    ArtifactPaths,
    DEFAULT_BACKEND,
    DEFAULT_MAX_SPEAKERS,
    DEFAULT_MIN_SPEAKERS,
    DEFAULT_MODEL,
    PROMPT_TOKEN_BUDGET,
)
from ..correct import correct_transcript
from ..episode import EpisodeError, discover_master_video, resolve_episode_folder
from ..formatters.md import render_md
from ..formatters.srt import render_srt
from ..formatters.txt import render_txt
from ..formatters.vtt import render_vtt
from ..jargon import build_initial_prompt
from ..metadata import load_metadata
from ..speakers import load_speakers
from ..transcribe.aws_backend import AWSTranscribeBackend
from ..transcribe.base import TranscriptionOptions
from ..transcribe.deepgram_backend import DeepgramBackend
from ..transcribe.whisperx_backend import WhisperXBackend


def _backend(name: str):
    if name == "whisperx":
        return WhisperXBackend()
    if name == "deepgram":
        return DeepgramBackend()
    if name == "aws":
        return AWSTranscribeBackend()
    raise typer.BadParameter(f"unknown backend: {name}")


def run(
    episode: str = typer.Argument(..., help="Episode folder (e.g. Episode43)"),
    model: str = typer.Option(DEFAULT_MODEL, "--model"),
    min_speakers: int = typer.Option(DEFAULT_MIN_SPEAKERS, "--min-speakers"),
    max_speakers: int = typer.Option(DEFAULT_MAX_SPEAKERS, "--max-speakers"),
    backend: str = typer.Option(DEFAULT_BACKEND, "--backend"),
    file_override: Optional[Path] = typer.Option(None, "--file", help="Path to a non-standard MP4."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing transcript.json."),
) -> None:
    load_dotenv()
    console = Console()

    try:
        folder = resolve_episode_folder(episode)
        master = discover_master_video(folder, override=file_override)
    except EpisodeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)

    paths = ArtifactPaths(root=folder)
    paths.ensure()

    if paths.transcript_json.exists() and not force:
        console.print(
            f"[yellow]transcript.json already exists at {paths.transcript_json}. "
            "Pass --force to overwrite.[/yellow]"
        )
        raise typer.Exit(0)

    md_state = load_metadata(paths.metadata)
    md_state.set("episode", folder.name)
    md_state.set("master_video", str(master))
    md_state.set("model", model)
    md_state.set("min_speakers", min_speakers)
    md_state.set("max_speakers", max_speakers)

    # Stage 1: audio
    console.print(f"[cyan]Extracting audio[/cyan] {master.name} -> {paths.audio.name}")
    t0 = time.monotonic()
    try:
        extract_audio(master, paths.audio, force=force)
    except AudioError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    md_state.record_stage("audio", duration_s=round(time.monotonic() - t0, 2), ok=True)
    md_state.save()

    # Stage 2: transcribe + align + diarize, with per-stage checkpoints.
    bk = _backend(backend)
    md_state.set("device_info", bk.device_info())
    md_state.save()

    opts = TranscriptionOptions(
        model=model,
        initial_prompt=build_initial_prompt(token_budget=PROMPT_TOKEN_BUDGET),
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        hf_token=os.environ.get("HF_TOKEN"),
    )

    has_staged = all(hasattr(bk, m) for m in ("transcribe_raw", "align_words", "assign_speakers"))

    if not has_staged:
        # Fallback: backend doesn't support stage checkpoints. Run all-in-one.
        console.print(f"[cyan]Transcribing[/cyan] backend={backend} model={model}")
        t0 = time.monotonic()
        try:
            result = bk.transcribe(paths.audio, opts)
        except NotImplementedError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(2)
        except Exception as e:
            console.print(f"[red]Transcription failed: {e}[/red]")
            md_state.record_stage("transcribe", duration_s=round(time.monotonic() - t0, 2), ok=False, error=str(e))
            md_state.save()
            raise typer.Exit(2)
        md_state.record_stage("transcribe", duration_s=round(time.monotonic() - t0, 2), ok=True)
        md_state.save()
    else:
        # Staged path with checkpoints.
        # Stage 2a: raw Whisper transcribe
        if paths.transcript_aligned.exists() and not force:
            console.print(f"[cyan]Reusing[/cyan] {paths.transcript_aligned.name}")
            aligned = json.loads(paths.transcript_aligned.read_text())
        elif paths.transcript_raw.exists() and not force:
            console.print(f"[cyan]Reusing[/cyan] {paths.transcript_raw.name}")
            raw = json.loads(paths.transcript_raw.read_text())
            console.print(f"[cyan]Aligning words[/cyan]")
            t0 = time.monotonic()
            try:
                aligned = bk.align_words(paths.audio, raw)
            except Exception as e:
                console.print(f"[red]Alignment failed: {e}[/red]")
                md_state.record_stage("align", duration_s=round(time.monotonic() - t0, 2), ok=False, error=str(e))
                md_state.save()
                raise typer.Exit(2)
            paths.transcript_aligned.write_text(json.dumps(aligned, indent=2))
            md_state.record_stage("align", duration_s=round(time.monotonic() - t0, 2), ok=True)
            md_state.save()
        else:
            console.print(f"[cyan]Transcribing[/cyan] backend={backend} model={model}")
            t0 = time.monotonic()
            try:
                raw = bk.transcribe_raw(paths.audio, opts)
            except Exception as e:
                console.print(f"[red]Transcription failed: {e}[/red]")
                md_state.record_stage("transcribe", duration_s=round(time.monotonic() - t0, 2), ok=False, error=str(e))
                md_state.save()
                raise typer.Exit(2)
            paths.transcript_raw.write_text(json.dumps(raw, indent=2))
            md_state.record_stage("transcribe", duration_s=round(time.monotonic() - t0, 2), ok=True)
            md_state.save()

            console.print(f"[cyan]Aligning words[/cyan]")
            t0 = time.monotonic()
            try:
                aligned = bk.align_words(paths.audio, raw)
            except Exception as e:
                console.print(f"[red]Alignment failed: {e}[/red]")
                md_state.record_stage("align", duration_s=round(time.monotonic() - t0, 2), ok=False, error=str(e))
                md_state.save()
                raise typer.Exit(2)
            paths.transcript_aligned.write_text(json.dumps(aligned, indent=2))
            md_state.record_stage("align", duration_s=round(time.monotonic() - t0, 2), ok=True)
            md_state.save()

        # Stage 2c: diarize + assign speakers
        console.print(f"[cyan]Diarizing[/cyan]")
        t0 = time.monotonic()
        try:
            result = bk.assign_speakers(paths.audio, aligned, opts)
        except NotImplementedError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(2)
        except Exception as e:
            console.print(f"[red]Diarization failed: {e}[/red]")
            md_state.record_stage("diarize", duration_s=round(time.monotonic() - t0, 2), ok=False, error=str(e))
            md_state.save()
            raise typer.Exit(2)
        md_state.record_stage("diarize", duration_s=round(time.monotonic() - t0, 2), ok=True)
        md_state.save()

    # Stage 3: fuzzy correction
    console.print("[cyan]Applying fuzzy jargon correction[/cyan]")
    t0 = time.monotonic()
    corrected, log = correct_transcript(result)
    for entry in log:
        md_state.add_correction(entry)
    md_state.record_stage("correct", duration_s=round(time.monotonic() - t0, 2), ok=True, replacements=len(log))
    md_state.save()

    paths.transcript_json.write_text(json.dumps(corrected, indent=2))

    # Stage 4: render derivatives
    console.print("[cyan]Rendering SRT/VTT/TXT/MD[/cyan]")
    speakers = load_speakers(paths.speakers)
    paths.transcript_srt.write_text(render_srt(corrected))
    paths.transcript_vtt.write_text(render_vtt(corrected))
    paths.transcript_txt.write_text(render_txt(corrected))
    paths.transcript_md.write_text(render_md(corrected, speakers=speakers))
    md_state.record_stage("render", duration_s=0.0, ok=True)
    md_state.save()

    console.print(f"[green]Done.[/green] Artifacts in {paths.artifacts_dir}")
