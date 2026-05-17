"""`podcast transcribe-clip EPISODE --clip N` — transcribe a clip video file.

Runs the same pipeline as episode transcription: audio extraction → whisperx
transcription → alignment → diarization → fuzzy jargon correction →
hallucination removal → format rendering (SRT/VTT/TXT/MD).

Artifacts go to episodes/EpisodeNN/artifacts/clipN/.

Usage:
    podcast transcribe-clip Episode40 --clip 1
    podcast transcribe-clip Episode40 --all
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

from ..audio import AudioError, extract_audio
from ..config import (
    DEFAULT_BACKEND,
    DEFAULT_MAX_SPEAKERS,
    DEFAULT_MIN_SPEAKERS,
    DEFAULT_MODEL,
    PROMPT_TOKEN_BUDGET,
)
from ..correct import correct_transcript
from ..dehallucinate import dehallucinate_transcript
from ..formatters.srt import render_srt
from ..formatters.vtt import render_vtt
from ..formatters.txt import render_txt
from ..jargon import build_initial_prompt
from ..posting import load_metadata
from .._publish_helpers import clip_paths, episode_dir_default
from ..transcribe.base import TranscriptionOptions

console = Console()


def _backend(name: str):
    if name == "whisperx":
        from ..transcribe.whisperx_backend import WhisperXBackend
        return WhisperXBackend()
    if name == "mlx":
        from ..transcribe.mlx_backend import MLXWhisperBackend
        return MLXWhisperBackend()
    raise typer.BadParameter(f"unknown backend: {name}")


def _clip_artifact_dir(episode_num: int, clip_num: int) -> Path:
    d = REPO_ROOT / "episodes" / f"Episode{episode_num:02d}" / "artifacts" / f"clip{clip_num}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _transcribe_one_clip(
    episode_num: int,
    clip_num: int,
    backend_name: str,
    model: str,
    force: bool,
) -> bool:
    """Transcribe a single clip. Returns True on success."""
    label = f"ep{episode_num} clip{clip_num}"
    console.print(f"\n[bold]── {label} ──[/bold]")

    # Find clip video file
    ep_dir = episode_dir_default(episode_num)
    h_path, v_path = clip_paths(ep_dir, episode_num, clip_num)

    # Prefer horizontal for transcription (better audio quality, wider frame)
    video = None
    for candidate in [h_path, v_path]:
        if candidate.exists():
            video = candidate
            break

    if video is None:
        console.print(f"  [red]No video file found at {h_path} or {v_path}[/red]")
        return False

    console.print(f"  Video: {video.name}")

    art_dir = _clip_artifact_dir(episode_num, clip_num)
    audio_path = art_dir / "audio.wav"
    transcript_path = art_dir / "transcript.json"
    raw_path = art_dir / "transcript.raw.json"
    aligned_path = art_dir / "transcript.aligned.json"

    if transcript_path.exists() and not force:
        console.print(f"  [dim]Already transcribed (use --force to redo)[/dim]")
        return True

    # Stage 1: Extract audio
    console.print("  [cyan]Stage 1: Extracting audio...[/cyan]")
    try:
        extract_audio(video, audio_path, force=force)
    except AudioError as e:
        console.print(f"  [red]Audio extraction failed: {e}[/red]")
        return False

    # Stage 2: Transcribe
    bk = _backend(backend_name)
    console.print(f"  [cyan]Stage 2: Transcribing ({bk.name}, {bk.device_info()})...[/cyan]")
    opts = TranscriptionOptions(
        model=model,
        initial_prompt=build_initial_prompt(token_budget=PROMPT_TOKEN_BUDGET),
        min_speakers=DEFAULT_MIN_SPEAKERS,
        max_speakers=DEFAULT_MAX_SPEAKERS,
        hf_token=os.environ.get("HF_TOKEN"),
    )

    try:
        # 2a: Raw transcription
        if raw_path.exists() and not force:
            console.print("  [dim]Using cached raw transcript[/dim]")
            raw = json.loads(raw_path.read_text())
        else:
            raw = bk.transcribe_raw(audio_path, opts)
            raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2))
            console.print(f"  Raw: {len(raw.get('segments', []))} segments")

        # 2b: Alignment
        if aligned_path.exists() and not force:
            console.print("  [dim]Using cached aligned transcript[/dim]")
            aligned = json.loads(aligned_path.read_text())
        else:
            aligned = bk.align_words(audio_path, raw)
            aligned_path.write_text(json.dumps(aligned, ensure_ascii=False, indent=2))
            console.print(f"  Aligned: {len(aligned.get('segments', []))} segments")

        # 2c: Diarization
        result = bk.assign_speakers(audio_path, aligned, opts)
        console.print(f"  Diarized: {len(result.get('segments', []))} segments")

    except Exception as e:
        console.print(f"  [red]Transcription failed: {e}[/red]")
        return False

    # Stage 3: Jargon correction
    console.print("  [cyan]Stage 3: Fuzzy jargon correction...[/cyan]")
    corrected, corrections = correct_transcript(result)
    if corrections:
        console.print(f"  Applied {len(corrections)} corrections")

    # Stage 4: Hallucination removal
    console.print("  [cyan]Stage 4: Hallucination removal...[/cyan]")
    hal_log = dehallucinate_transcript(corrected)
    if hal_log:
        console.print(f"  Removed {len(hal_log)} hallucinations")

    # Stage 5: Save final transcript + derivatives
    console.print("  [cyan]Stage 5: Saving transcript + derivatives...[/cyan]")
    transcript_path.write_text(json.dumps(corrected, ensure_ascii=False, indent=2))

    srt_path = art_dir / "transcript.srt"
    vtt_path = art_dir / "transcript.vtt"
    txt_path = art_dir / "transcript.txt"

    srt_path.write_text(render_srt(corrected))
    vtt_path.write_text(render_vtt(corrected))
    txt_path.write_text(render_txt(corrected))

    # Save correction/hallucination logs
    if corrections:
        (art_dir / "corrections.json").write_text(json.dumps(corrections, indent=2))
    if hal_log:
        (art_dir / "hallucinations.json").write_text(json.dumps(hal_log, indent=2))

    console.print(f"  [green]Done → {art_dir}[/green]")
    return True


def run(
    episode: str = typer.Argument(..., help="Episode folder (e.g. Episode40)"),
    clip: Optional[int] = typer.Option(None, "--clip", help="Clip number to transcribe"),
    all_clips: bool = typer.Option(False, "--all", help="Transcribe all clips"),
    model: str = typer.Option(DEFAULT_MODEL, "--model"),
    backend: str = typer.Option(DEFAULT_BACKEND, "--backend"),
    force: bool = typer.Option(False, "--force", help="Re-transcribe even if transcript exists"),
):
    """Transcribe clip video files with the full episode pipeline."""
    m = re.search(r"(\d+)", episode)
    if not m:
        console.print(f"[red]Cannot parse episode number from '{episode}'[/red]")
        raise typer.Exit(1)
    ep_num = int(m.group(1))

    if not clip and not all_clips:
        console.print("[red]Specify --clip N or --all[/red]")
        raise typer.Exit(1)

    if all_clips:
        meta = load_metadata(ep_num)
        clip_list = [c["number"] for c in meta.get("clips", [])]
        if not clip_list:
            console.print("[yellow]No clips defined in metadata YAML[/yellow]")
            raise typer.Exit(0)
    else:
        clip_list = [clip]

    console.print(f"[bold]Transcribing {len(clip_list)} clip(s) for Episode {ep_num}[/bold]")

    ok, fail = 0, 0
    for cn in clip_list:
        if _transcribe_one_clip(ep_num, cn, backend, model, force):
            ok += 1
        else:
            fail += 1

    console.print(f"\n[bold]Done: {ok} transcribed, {fail} failed[/bold]")
