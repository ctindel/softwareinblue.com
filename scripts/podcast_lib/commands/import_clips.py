"""`podcast import-clips EPISODE` — pull clip data from Google Sheets into metadata YAML.

Reads the Episode_NN_clips spreadsheet, parses clip rows, and updates
the clips section of SIB_ENN_metadata.yaml. Preserves any existing
clip fields that the spreadsheet doesn't cover (e.g. links, overlay_text
added manually).

Usage:
    podcast import-clips Episode40
    podcast import-clips Episode40 --dry-run
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

console = Console()


def _parse_timestamps(raw: str) -> tuple[str, str]:
    """Extract start and end timestamps from the 'Starting / ending with' column.

    The column format varies:
      - '"quote" up through HH:MM:SS "end quote"'
      - '"quote" up until HH:MM:SS "end quote"'
    The start timestamp is in the 'Timestamp in Main Video' column.
    The end timestamp is embedded in the 'Starting / ending with' text.
    """
    # Find HH:MM:SS or MM:SS patterns in the text
    times = re.findall(r'\d{1,2}:\d{2}(?::\d{2})?', raw)
    return times[0] if times else ""


def _parse_quotes(raw: str) -> tuple[str, str]:
    """Extract quote_starts_with and quote_ends_with from the description column."""
    # Find quoted strings
    quotes = re.findall(r'"([^"]*)"', raw)
    if len(quotes) >= 2:
        return quotes[0], quotes[-1]
    elif len(quotes) == 1:
        return quotes[0], ""
    return "", ""


def _normalize_timestamp(ts: str) -> str:
    """Normalize to HH:MM:SS format."""
    parts = ts.split(":")
    if len(parts) == 2:
        return f"00:{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    elif len(parts) == 3:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
    return ts


def _fetch_clips_from_sheets(episode_num: int) -> list[dict]:
    """Fetch clip data from Google Sheets."""
    from ..sheets_clip_ids import CLIP_SHEET_IDS
    from ..youtube_auth import get_credentials
    from googleapiclient.discovery import build

    sheet_id = CLIP_SHEET_IDS.get(episode_num)
    if not sheet_id:
        raise ValueError(f"No clip spreadsheet ID for episode {episode_num}")

    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds)
    result = sheets.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range="Sheet1!A1:Z50",
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return []

    # Row 0 is header, data starts at row 1
    clips = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        try:
            clip_num = int(row[0].strip())
        except ValueError:
            continue

        timestamp_start = _normalize_timestamp(row[1].strip()) if len(row) > 1 and row[1].strip() else ""
        quote_col = row[2] if len(row) > 2 else ""
        notes_col = row[5] if len(row) > 5 else (row[3] if len(row) > 3 else "")

        # Extract end timestamp from the quote column
        timestamp_end = ""
        end_times = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)', quote_col)
        if end_times:
            timestamp_end = _normalize_timestamp(end_times[-1])

        quote_starts, quote_ends = _parse_quotes(quote_col)

        clip = {
            "number": clip_num,
            "timestamp_start": timestamp_start,
            "timestamp_end": timestamp_end,
            "quote_starts_with": quote_starts,
            "quote_ends_with": quote_ends,
            "description": notes_col.strip() if notes_col else "",
            "overlay_text": "",
            "links": {
                "youtube": "",
                "posted_tiktok": "",
                "posted_linkedin": "",
                "posted_twitter": "",
            },
        }
        clips.append(clip)

    return clips


def run(
    episode: str = typer.Argument(..., help="Episode folder (e.g. Episode40)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing clips data"),
):
    """Import clip data from Google Sheets into the episode metadata YAML."""
    # Parse episode number
    m = re.search(r"(\d+)", episode)
    if not m:
        console.print(f"[red]Cannot parse episode number from '{episode}'[/red]")
        raise typer.Exit(1)
    ep_num = int(m.group(1))

    yaml_path = REPO_ROOT / "episodes" / f"Episode{ep_num:02d}" / f"SIB_E{ep_num:02d}_metadata.yaml"
    if not yaml_path.exists():
        console.print(f"[red]Metadata file not found: {yaml_path}[/red]")
        raise typer.Exit(1)

    meta = yaml.safe_load(yaml_path.read_text())

    # Check if clips already exist
    existing_clips = meta.get("clips", [])
    if existing_clips and not force:
        console.print(f"[yellow]Episode {ep_num} already has {len(existing_clips)} clips in YAML.[/yellow]")
        console.print("[yellow]Use --force to overwrite, or clips will be merged.[/yellow]")

    console.print(f"[bold]Fetching clips from Google Sheets for Episode {ep_num}...[/bold]")
    new_clips = _fetch_clips_from_sheets(ep_num)

    if not new_clips:
        console.print("[yellow]No clips found in spreadsheet.[/yellow]")
        raise typer.Exit(0)

    console.print(f"  Found {len(new_clips)} clips in spreadsheet")

    if force or not existing_clips:
        # Replace entirely
        merged = new_clips
    else:
        # Merge: keep existing fields, add new ones from sheets
        existing_by_num = {c["number"]: c for c in existing_clips}
        merged = []
        for new_clip in new_clips:
            num = new_clip["number"]
            if num in existing_by_num:
                # Merge: existing data takes precedence for populated fields
                existing = existing_by_num[num]
                for key, val in new_clip.items():
                    if key not in existing or not existing[key]:
                        existing[key] = val
                merged.append(existing)
            else:
                merged.append(new_clip)
        # Keep any existing clips not in the new set
        new_nums = {c["number"] for c in new_clips}
        for c in existing_clips:
            if c["number"] not in new_nums:
                merged.append(c)
        merged.sort(key=lambda c: c["number"])

    if dry_run:
        console.print("\n[bold]Dry run — would write:[/bold]")
        for clip in merged:
            console.print(f"  Clip {clip['number']}: {clip['timestamp_start']} → {clip['timestamp_end']}")
            console.print(f"    {clip['description'][:80]}...")
        return

    meta["clips"] = merged
    yaml_path.write_text(yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120))
    console.print(f"[green]Wrote {len(merged)} clips to {yaml_path}[/green]")
