"""`podcast thumbnail-clip EPISODE --clip N` — generate thumbnails for clips.

Uses the same design pipeline as episodes (gen_sib_exports.py) but with
the clip's overlay_text as the tagline. Output goes to
hugosite/static/img/episode/EpisodeNN/ClipM/<variant>/<size>.png

Usage:
    podcast thumbnail-clip Episode40 --clip 1
    podcast thumbnail-clip Episode40 --all
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

console = Console()


def _get_guest_slug(ep_num: int) -> str:
    """Extract guest slug from the episode markdown frontmatter."""
    md = REPO_ROOT / "hugosite" / "content" / "episode" / f"episode{ep_num}.md"
    if not md.exists():
        return ""
    text = md.read_text()
    # Look for guests = ["slug"] in frontmatter
    m = re.search(r'guests\s*=\s*\["([^"]+)"', text)
    return m.group(1) if m else ""


def _generate_clip_thumbnails(
    ep_num: int,
    clip_num: int,
    overlay_text: str,
    overlay_highlight: str,
    guest_slug: str,
) -> bool:
    """Generate thumbnails for one clip by invoking gen_sib_exports.py
    with a temporarily patched metadata YAML."""
    label = f"ep{ep_num} clip{clip_num}"
    ep_id = f"{ep_num:02d}"

    # Check prerequisites
    episode_dir = REPO_ROOT / "hugosite" / "static" / "img" / "episode" / f"Episode{ep_id}"
    headshot = episode_dir / "headshots" / f"{guest_slug}-nobg.png"
    if not headshot.exists():
        console.print(f"  [{label}] [red]Missing headshot: {headshot}[/red]")
        return False

    if not overlay_text:
        console.print(f"  [{label}] [yellow]Empty overlay_text — skipping[/yellow]")
        return False

    # Create clip output directory
    clip_out = episode_dir / f"Clip{clip_num}"
    clip_out.mkdir(parents=True, exist_ok=True)

    console.print(f"  [{label}] Generating thumbnails (overlay: \"{overlay_text}\")...")

    script = REPO_ROOT / "design" / "gen_sib_exports.py"
    cmd = [
        sys.executable, str(script),
        str(ep_num), guest_slug,
        "--tagline", overlay_text,
        "--out-dir", str(clip_out),
    ]
    if overlay_highlight:
        cmd.extend(["--tagline-highlight", overlay_highlight])

    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        console.print(f"  [{label}] [red]Generator failed:[/red]")
        err = result.stderr or result.stdout
        console.print(err[-500:] if len(err) > 500 else err)
        return False

    generated = sum(1 for _ in clip_out.rglob("*.png"))
    console.print(f"  [{label}] [green]Generated {generated} files → {clip_out}[/green]")
    return True


def run(
    episode: str = typer.Argument(..., help="Episode folder (e.g. Episode40)"),
    clip: Optional[int] = typer.Option(None, "--clip", help="Clip number"),
    all_clips: bool = typer.Option(False, "--all", help="All clips"),
):
    """Generate thumbnail variants for clips using the episode design pipeline."""
    m = re.search(r"(\d+)", episode)
    if not m:
        console.print(f"[red]Cannot parse episode number from '{episode}'[/red]")
        raise typer.Exit(1)
    ep_num = int(m.group(1))

    if not clip and not all_clips:
        console.print("[red]Specify --clip N or --all[/red]")
        raise typer.Exit(1)

    # Load metadata
    yaml_path = REPO_ROOT / "episodes" / f"Episode{ep_num:02d}" / f"SIB_E{ep_num:02d}_metadata.yaml"
    meta = yaml.safe_load(yaml_path.read_text())
    clips = meta.get("clips", [])

    if all_clips:
        clip_list = [c["number"] for c in clips]
    else:
        clip_list = [clip]

    # Hard gate: SF Pro font must be present (no font substitution allowed).
    sfns = Path("/System/Library/Fonts/SFNS.ttf")
    if not sfns.exists():
        console.print("[red]BLOCKED: SF Pro font not found at /System/Library/Fonts/SFNS.ttf[/red]")
        console.print("[red]Thumbnail generation requires the exact Apple SF Pro variable font.[/red]")
        console.print("[red]Do NOT substitute other fonts — layouts are pixel-tuned to SF Pro metrics.[/red]")
        raise typer.Exit(1)

    guest_slug = _get_guest_slug(ep_num)
    if not guest_slug:
        console.print("[red]Cannot determine guest slug from episode markdown[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Generating thumbnails for {len(clip_list)} clip(s), guest={guest_slug}[/bold]")

    ok, fail = 0, 0
    for cn in clip_list:
        clip_data = next((c for c in clips if c["number"] == cn), None)
        if not clip_data:
            console.print(f"  clip{cn}: [red]not found in metadata[/red]")
            fail += 1
            continue

        overlay = clip_data.get("overlay_text", "")
        highlight = clip_data.get("overlay_highlight", "")

        if _generate_clip_thumbnails(ep_num, cn, overlay, highlight, guest_slug):
            ok += 1
        else:
            fail += 1

    console.print(f"\n[bold]Done: {ok} generated, {fail} failed[/bold]")
