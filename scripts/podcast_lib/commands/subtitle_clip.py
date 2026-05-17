"""`podcast subtitle-clip EPISODE --clip N` — generate subtitles from clip transcript.

Reads the transcript.json from the clip's artifact directory and
generates SRT and VTT subtitle files.

Usage:
    podcast subtitle-clip Episode40 --clip 1
    podcast subtitle-clip Episode40 --all
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

from ..formatters.srt import render_srt
from ..formatters.vtt import render_vtt
from ..posting import load_metadata

console = Console()


def _clip_artifact_dir(episode_num: int, clip_num: int) -> Path:
    return REPO_ROOT / "episodes" / f"Episode{episode_num:02d}" / "artifacts" / f"clip{clip_num}"


def _subtitle_one_clip(episode_num: int, clip_num: int) -> bool:
    label = f"ep{episode_num} clip{clip_num}"
    art_dir = _clip_artifact_dir(episode_num, clip_num)
    transcript_path = art_dir / "transcript.json"

    if not transcript_path.exists():
        console.print(f"  [{label}] [red]No transcript found — run transcribe-clip first[/red]")
        return False

    transcript = json.loads(transcript_path.read_text())

    srt_path = art_dir / "transcript.srt"
    vtt_path = art_dir / "transcript.vtt"

    srt_path.write_text(render_srt(transcript))
    vtt_path.write_text(render_vtt(transcript))

    console.print(f"  [{label}] [green]Generated SRT + VTT[/green]")
    return True


def run(
    episode: str = typer.Argument(..., help="Episode folder (e.g. Episode40)"),
    clip: Optional[int] = typer.Option(None, "--clip", help="Clip number"),
    all_clips: bool = typer.Option(False, "--all", help="All clips"),
):
    """Generate subtitle files from clip transcripts."""
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
    else:
        clip_list = [clip]

    ok, fail = 0, 0
    for cn in clip_list:
        if _subtitle_one_clip(ep_num, cn):
            ok += 1
        else:
            fail += 1

    console.print(f"\n[bold]Done: {ok} subtitled, {fail} failed[/bold]")
