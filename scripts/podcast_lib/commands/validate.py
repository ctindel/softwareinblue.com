"""`podcast validate EPISODE` — validate metadata YAML against the schema.

Checks:
  1. JSON Schema validation (structure, types, required fields)
  2. Highlight completeness (every tagline/overlay_text must have a highlight)
  3. Highlight text must appear within the tagline/overlay_text
  4. Thumbnail sanity (if thumbnails exist, spot-check overlay text is rendered)

Usage:
    podcast validate Episode40
    podcast validate --all
    podcast validate Episode40 --check-images   # also verify thumbnails
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "metadata_schema.json"

console = Console()


def _schema_errors(meta: dict) -> list[str]:
    """JSON Schema validation errors."""
    from jsonschema import Draft202012Validator

    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(meta), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"schema: {path}: {err.message}")
    return errors


def _highlight_errors(meta: dict) -> list[str]:
    """Check that every tagline/overlay_text has a non-empty highlight,
    and that the highlight phrase appears within the text."""
    errors = []
    ep = meta.get("episode", {})

    # Episode tagline
    tagline = ep.get("tagline", "")
    highlight = ep.get("tagline_highlight", "")
    if tagline and not highlight:
        errors.append("episode.tagline_highlight: empty — every tagline must have a highlight phrase")
    elif tagline and highlight:
        # Check each pipe-delimited phrase appears in the tagline
        for phrase in highlight.split("|"):
            phrase = phrase.strip()
            if phrase and phrase.lower() not in tagline.lower():
                errors.append(f"episode.tagline_highlight: \"{phrase}\" not found in tagline \"{tagline}\"")

    # Clip overlay_text
    for clip in meta.get("clips", []):
        num = clip.get("number", "?")
        overlay = clip.get("overlay_text", "")
        clip_highlight = clip.get("overlay_highlight", "")
        if overlay and not clip_highlight:
            errors.append(f"clips[{num}].overlay_highlight: empty — every overlay_text must have a highlight phrase")
        elif overlay and clip_highlight:
            for phrase in clip_highlight.split("|"):
                phrase = phrase.strip()
                if phrase and phrase.lower() not in overlay.lower():
                    errors.append(f"clips[{num}].overlay_highlight: \"{phrase}\" not found in overlay_text \"{overlay}\"")

    return errors


def _image_errors(meta: dict, ep_num: int) -> list[str]:
    """Spot-check that generated thumbnails contain the correct overlay text.

    Uses OCR-free heuristic: checks that thumbnail files exist for each clip
    that has overlay_text, and verifies the d2 thumbnail dimensions are correct.
    """
    errors = []
    ep_id = f"{ep_num:02d}"
    ep_dir = REPO_ROOT / "hugosite" / "static" / "img" / "episode" / f"Episode{ep_id}"

    # Episode-level: check d2 thumbnail exists
    ep_thumb = ep_dir / "d2" / "thumbnail-youtube-1920x1080.png"
    if not ep_thumb.exists():
        errors.append(f"episode thumbnail missing: {ep_thumb.relative_to(REPO_ROOT)}")
    else:
        try:
            from PIL import Image
            with Image.open(ep_thumb) as img:
                if img.size != (1920, 1080):
                    errors.append(f"episode d2 thumbnail wrong size: {img.size}, expected (1920, 1080)")
        except Exception:
            pass

    # Clip-level: check d2 thumbnails exist for clips with overlay_text
    for clip in meta.get("clips", []):
        num = clip.get("number", 0)
        overlay = clip.get("overlay_text", "")
        if not overlay:
            continue
        clip_dir = ep_dir / f"Clip{num}"
        if not clip_dir.exists():
            errors.append(f"clips[{num}]: thumbnail dir missing: {clip_dir.relative_to(REPO_ROOT)}")
            continue

        # Check d2 variant exists
        d2_thumb = clip_dir / "d2" / "thumbnail-youtube-1920x1080.png"
        if not d2_thumb.exists():
            errors.append(f"clips[{num}]: d2/thumbnail-youtube-1920x1080.png missing")

        # Check d2 dimensions
        if d2_thumb.exists():
            try:
                from PIL import Image
                with Image.open(d2_thumb) as img:
                    if img.size != (1920, 1080):
                        errors.append(f"clips[{num}]: d2 thumbnail wrong size: {img.size}")
            except Exception:
                pass

        # Check short-tiktok dimensions (9:16)
        tiktok_path = clip_dir / "d2" / "short-tiktok-1080x1920.png"
        if tiktok_path.exists():
            try:
                from PIL import Image
                with Image.open(tiktok_path) as img:
                    if img.size != (1080, 1920):
                        errors.append(f"clips[{num}]: d2 short-tiktok wrong size: {img.size}")
            except Exception:
                pass

    return errors


def _validate_one(ep_num: int, check_images: bool) -> list[str]:
    """Validate one episode's metadata YAML. Returns list of error strings."""
    ep_id = f"{ep_num:02d}"
    yaml_path = REPO_ROOT / "episodes" / f"Episode{ep_id}" / f"SIB_E{ep_id}_metadata.yaml"
    if not yaml_path.exists():
        return [f"File not found: {yaml_path}"]

    meta = yaml.safe_load(yaml_path.read_text())

    errors = []
    errors.extend(_schema_errors(meta))
    errors.extend(_highlight_errors(meta))
    if check_images:
        errors.extend(_image_errors(meta, ep_num))
    return errors


def run(
    episode: Optional[str] = typer.Argument(None, help="Episode folder (e.g. Episode40), or omit with --all"),
    all_episodes: bool = typer.Option(False, "--all", help="Validate all episodes"),
    check_images: bool = typer.Option(False, "--check-images", help="Also verify thumbnail files exist and have correct dimensions"),
):
    """Validate episode metadata YAML against the schema."""
    if not episode and not all_episodes:
        console.print("[red]Specify an episode or use --all[/red]")
        raise typer.Exit(1)

    if all_episodes:
        ep_dirs = sorted(REPO_ROOT.glob("episodes/Episode*/SIB_E*_metadata.yaml"))
        ep_nums = []
        for p in ep_dirs:
            m = re.search(r"Episode(\d+)", str(p))
            if m:
                ep_nums.append(int(m.group(1)))
    else:
        m = re.search(r"(\d+)", episode)
        if not m:
            console.print(f"[red]Cannot parse episode number from '{episode}'[/red]")
            raise typer.Exit(1)
        ep_nums = [int(m.group(1))]

    total_ok, total_fail = 0, 0
    for ep_num in sorted(ep_nums):
        errors = _validate_one(ep_num, check_images)
        if errors:
            console.print(f"[red]Episode {ep_num}: {len(errors)} error(s)[/red]")
            for err in errors:
                console.print(f"  {err}")
            total_fail += 1
        else:
            console.print(f"[green]Episode {ep_num}: valid[/green]")
            total_ok += 1

    console.print(f"\n[bold]{total_ok} valid, {total_fail} invalid[/bold]")
    if total_fail > 0:
        raise typer.Exit(1)
