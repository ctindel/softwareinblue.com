"""`podcast batch-titles` — update episode titles across Hugo, YouTube, and Spotify.

Reads the canonical title map from scripts/podcast_lib/title_map.py and applies
titles to one or more of: Hugo markdown files, YouTube Data API, Spotify for
Creators (browser automation).

Usage:
    podcast batch-titles                          # all episodes, all platforms
    podcast batch-titles --episodes 40            # single episode
    podcast batch-titles --episodes 1-10          # range
    podcast batch-titles --platform youtube       # YouTube only
    podcast batch-titles --platform hugo          # local files only
    podcast batch-titles --dry-run                # preview changes
"""
from __future__ import annotations

import re
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "podcast_lib"))

console = Console()


class Platform(str, Enum):
    all = "all"
    hugo = "hugo"
    youtube = "youtube"
    spotify = "spotify"


ALL_EPISODES = [*range(0, 24), 23.5, *range(24, 46)]


def _parse_episodes(spec: Optional[str]) -> list:
    if spec is None:
        return ALL_EPISODES
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return [e for e in ALL_EPISODES
                if float(lo) <= (e if isinstance(e, float) else float(e)) <= float(hi)]
    val = spec
    return [float(val) if "." in val else int(val)]


def _hugo_youtube_id(num) -> str | None:
    slug = f"episode{num}"
    md = REPO_ROOT / "hugosite" / "content" / "episode" / f"{slug}.md"
    if not md.exists():
        return None
    m = re.search(r'^youtube\s*=\s*"([^"]+)"', md.read_text(), re.MULTILINE)
    return m.group(1) if m else None


# ── Hugo ──────────────────────────────────────────────────────────────────

def _update_hugo(titles: dict, eps: list, dry_run: bool) -> tuple[int, int]:
    ok, fail = 0, 0
    for num in eps:
        new_title = titles.get(num)
        if not new_title:
            continue
        slug = f"episode{num}"
        md = REPO_ROOT / "hugosite" / "content" / "episode" / f"{slug}.md"
        if not md.exists():
            continue
        text = md.read_text()
        m = re.search(r'^(title\s*=\s*)"([^"]*)"', text, re.MULTILINE)
        if not m:
            continue
        old_title = m.group(2)
        if old_title == new_title:
            console.print(f"  [dim]ep{num}: already set[/dim]")
            ok += 1
            continue
        if dry_run:
            console.print(f"  ep{num}: [red]{old_title}[/red] → [green]{new_title}[/green]")
            ok += 1
            continue
        escaped = new_title.replace('"', "'")
        new_text = text[:m.start()] + f'{m.group(1)}"{escaped}"' + text[m.end():]
        md.write_text(new_text)
        console.print(f"  ep{num}: [green]updated[/green]")
        ok += 1
    return ok, fail


# ── YouTube ───────────────────────────────────────────────────────────────

def _update_youtube(titles: dict, eps: list, dry_run: bool) -> tuple[int, int]:
    from youtube_auth import get_credentials
    from googleapiclient.discovery import build

    creds = get_credentials()
    yt = build("youtube", "v3", credentials=creds)
    ok, fail = 0, 0

    for num in eps:
        new_title = titles.get(num)
        if not new_title:
            continue
        vid = _hugo_youtube_id(num)
        if not vid:
            continue
        try:
            resp = yt.videos().list(part="snippet,localizations", id=vid).execute()
            items = resp.get("items", [])
            if not items:
                console.print(f"  ep{num}: [red]video not found[/red]")
                fail += 1
                continue
            snippet = items[0]["snippet"]
            old_title = snippet["title"]
            if old_title == new_title:
                console.print(f"  [dim]ep{num}: already set[/dim]")
                ok += 1
                continue
            if dry_run:
                console.print(f"  ep{num}: [red]{old_title}[/red] → [green]{new_title}[/green]")
                ok += 1
                continue
            snippet["title"] = new_title
            snippet.setdefault("categoryId", "22")
            # Also update localizations to prevent revert.
            locs = items[0].get("localizations", {})
            for lang in locs:
                locs[lang]["title"] = new_title
            yt.videos().update(
                part="snippet,localizations",
                body={"id": vid, "snippet": snippet, "localizations": locs},
            ).execute()
            console.print(f"  ep{num}: [green]updated[/green]")
            ok += 1
            time.sleep(0.5)
        except Exception as e:
            console.print(f"  ep{num}: [red]FAIL — {e}[/red]")
            fail += 1
    return ok, fail


# ── YouTube Thumbnails ────────────────────────────────────────────────────

def _update_youtube_thumbnails(eps: list, dry_run: bool) -> tuple[int, int]:
    from youtube_auth import get_credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = get_credentials()
    yt = build("youtube", "v3", credentials=creds)
    ok, fail = 0, 0

    for num in eps:
        vid = _hugo_youtube_id(num)
        if not vid:
            continue
        if isinstance(num, float):
            folder = f"Episode{num}"
        else:
            folder = f"Episode{num:02d}"
        thumb = REPO_ROOT / "hugosite" / "static" / "img" / "episode" / folder / "d1" / "thumbnail-youtube-1920x1080.png"
        if not thumb.exists():
            console.print(f"  ep{num}: [yellow]no D1 thumbnail[/yellow]")
            continue
        if dry_run:
            console.print(f"  ep{num}: would update thumbnail for {vid}")
            ok += 1
            continue
        try:
            media = MediaFileUpload(str(thumb), mimetype="image/png", resumable=True)
            yt.thumbnails().set(videoId=vid, media_body=media).execute()
            console.print(f"  ep{num}: [green]thumbnail updated[/green]")
            ok += 1
            time.sleep(1)
        except Exception as e:
            console.print(f"  ep{num}: [red]FAIL — {e}[/red]")
            fail += 1
    return ok, fail


# ── Spotify ───────────────────────────────────────────────────────────────

def _update_spotify(titles: dict, eps: list, dry_run: bool) -> tuple[int, int]:
    from cloakbrowser import launch_persistent_context
    from spotify_cloak import (
        PROFILE, SHOW_ID, _KNOWN_IDS, _inject_cookies, _ensure_logged_in,
        keyboard_fill,
    )

    # Filter to integer episodes only (Spotify doesn't have 23.5).
    int_eps = [e for e in eps if isinstance(e, int)]

    ctx = launch_persistent_context(str(PROFILE), headless=True, humanize=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    ok, fail = 0, 0

    try:
        _inject_cookies(ctx)
        _ensure_logged_in(page)

        for num in int_eps:
            new_title = titles.get(num)
            if not new_title:
                continue
            sid = _KNOWN_IDS.get(num)
            if not sid:
                continue
            label = f"ep{num}"
            details = f"https://creators.spotify.com/pod/show/{SHOW_ID}/episode/{sid}/details"

            if dry_run:
                console.print(f"  {label}: would update on Spotify")
                ok += 1
                continue

            try:
                page.goto(details)
                page.wait_for_timeout(7000)

                if "/login" in page.url:
                    _inject_cookies(page.context)
                    _ensure_logged_in(page)
                    page.goto(details)
                    page.wait_for_timeout(7000)

                # Dismiss cookie banner if present.
                try:
                    cb = page.locator('button#onetrust-accept-btn-handler').first
                    if cb.count() > 0 and cb.is_visible():
                        cb.click()
                        page.wait_for_timeout(1500)
                except Exception:
                    pass

                try:
                    page.wait_for_selector("input#title-input", state="visible", timeout=20000)
                except Exception:
                    page.evaluate("""() => {
                        const el = document.getElementById('onetrust-banner-sdk');
                        if (el) el.remove();
                    }""")
                    page.wait_for_timeout(2000)
                    try:
                        page.wait_for_selector("input#title-input", state="visible", timeout=10000)
                    except Exception:
                        page.reload()
                        page.wait_for_timeout(8000)
                        try:
                            cb = page.locator('button#onetrust-accept-btn-handler').first
                            if cb.count() > 0 and cb.is_visible():
                                cb.click()
                                page.wait_for_timeout(1500)
                        except Exception:
                            pass
                        page.wait_for_selector("input#title-input", state="visible", timeout=20000)

                old_title = page.locator("input#title-input").input_value()
                if old_title == new_title:
                    console.print(f"  [dim]{label}: already set[/dim]")
                    ok += 1
                    continue

                keyboard_fill(page, "input#title-input", new_title, "title")

                # Save.
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(800)
                save_btn = page.locator(
                    'button[data-encore-id="buttonPrimary"]:has-text("Save")'
                ).first
                if save_btn.count() == 0:
                    save_btn = page.locator('button:has-text("Save"):visible').first
                save_btn.focus()
                page.wait_for_timeout(300)
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)

                deadline = time.time() + 30
                while time.time() < deadline:
                    page.wait_for_timeout(2000)
                    s = page.evaluate("""() => {
                        const b = Array.from(document.querySelectorAll('button')).find(b =>
                            /^save$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
                        return b ? {disabled: b.disabled} : {missing: true};
                    }""")
                    if s.get("disabled") or s.get("missing"):
                        break

                console.print(f"  {label}: [green]updated[/green]")
                ok += 1
                time.sleep(1)
            except Exception as e:
                console.print(f"  {label}: [red]FAIL — {e}[/red]")
                fail += 1
    finally:
        ctx.close()

    return ok, fail


# ── CLI Entry Point ───────────────────────────────────────────────────────

def run(
    episodes: Optional[str] = typer.Argument(None, help="Episode number or range (e.g. 40, 1-10)"),
    platform: Platform = typer.Option(Platform.all, help="Platform to update"),
    thumbnails: bool = typer.Option(False, "--thumbnails", help="Update YouTube thumbnails instead of titles"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
):
    """Update episode titles (or thumbnails) across Hugo, YouTube, and Spotify."""
    from title_map import TITLES, HUGO_TITLES

    eps = _parse_episodes(episodes)
    action = "thumbnails" if thumbnails else "titles"
    console.print(f"[bold]Updating {action} for {len(eps)} episodes[/bold]"
                  + (f" on {platform.value}" if platform != Platform.all else "")
                  + (" (dry run)" if dry_run else ""))

    if thumbnails:
        if platform not in (Platform.all, Platform.youtube):
            console.print("[red]--thumbnails only applies to YouTube[/red]")
            raise typer.Exit(1)
        console.print("\n[bold]YouTube Thumbnails:[/bold]")
        ok, fail = _update_youtube_thumbnails(eps, dry_run)
        console.print(f"  → {ok} ok, {fail} failed")
        return

    if platform in (Platform.all, Platform.hugo):
        console.print("\n[bold]Hugo:[/bold]")
        ok, fail = _update_hugo(HUGO_TITLES, eps, dry_run)
        console.print(f"  → {ok} ok, {fail} failed")

    if platform in (Platform.all, Platform.youtube):
        console.print("\n[bold]YouTube:[/bold]")
        ok, fail = _update_youtube(TITLES, eps, dry_run)
        console.print(f"  → {ok} ok, {fail} failed")

    if platform in (Platform.all, Platform.spotify):
        console.print("\n[bold]Spotify:[/bold]")
        ok, fail = _update_spotify(TITLES, eps, dry_run)
        console.print(f"  → {ok} ok, {fail} failed")
