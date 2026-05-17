"""Spotify for Creators (formerly Anchor) episode upload via headless browser.

Spotify does not expose a public API for hosting/uploading episodes —
the dashboard at https://creators.spotify.com is the only path. This
script drives that dashboard through `agent-browser`, modelled on the
Ramp + Gusto + QBO browser automations in `evogyms-agents/bob/`.

ToS warning: Spotify ToS prohibits automated access. Use at your own
risk. The script keeps a single named browser session so login/2FA only
happens on first run, and persists cookies between invocations to avoid
triggering anti-automation heuristics on every login.

CLI:
    python3 spotify_browser.py --test-login
    python3 spotify_browser.py --upload EPISODE_NUM \
        [--video PATH] [--cover PATH] [--publish-at "YYYY-MM-DDTHH:MM"]
    python3 spotify_browser.py --status EPISODE_NUM

The --upload command reads the same per-episode metadata YAML that
posting.py uses (`episodes/Episode<NN>/SIB_E<NN>_metadata.yaml`), so
title, description, tagline, episode number, etc. all come from one
source of truth.

If --video is omitted, the script discovers the master video file by
glob (matches `EpisodeN/*Final*.mp4` case-insensitive, exits 2 on zero
or multiple matches) — same convention as `podcast.py`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Config + paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = REPO_ROOT / "scripts" / "podcast_lib" / ".env"
load_dotenv(ENV_PATH, override=False)

SESSION_NAME = "spotify-creators"
SPOTIFY_URL = "https://creators.spotify.com"
SPOTIFY_LOGIN_URL = "https://accounts.spotify.com/login"

SPOTIFY_EMAIL = os.environ.get("SPOTIFY_EMAIL", "")
SPOTIFY_PASSWORD = os.environ.get("SPOTIFY_PASSWORD", "")

# Default UA matches a real desktop Chrome to keep us under the radar of
# Spotify's anti-automation heuristics. Bumping this only when Spotify's
# UA-based feature detection actually breaks something.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# agent-browser helpers (same pattern as ramp.py)
# ---------------------------------------------------------------------------

def run_ab(*args: str, timeout: int = 120) -> str:
    cmd = [
        "agent-browser",
        "--session-name", SESSION_NAME,
        "--args", "--disable-blink-features=AutomationControlled",
        "--user-agent", USER_AGENT,
        *args,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"agent-browser failed (rc={result.returncode}):\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  stderr: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def snapshot() -> str:
    return run_ab("snapshot")


def open_url(url: str) -> str:
    run_ab("open", url)
    wait(3000)
    return snapshot()


def wait(ms: int) -> None:
    run_ab("wait", str(ms))


def js_eval(code: str) -> str:
    return run_ab("eval", code)


def js_fill_input_by_name(name: str, value: str) -> str:
    """Fill an input by [name=...] attribute via execCommand (works with
    React-controlled inputs that ignore plain .value=)."""
    safe = json.dumps(value)
    return js_eval(
        f"var i = document.querySelector('input[name={json.dumps(name)}]');"
        "if (!i) { 'no input named " + name + "'; }"
        "else {"
        "  i.focus(); i.select();"
        "  document.execCommand('delete');"
        f"  document.execCommand('insertText', false, {safe});"
        "  i.dispatchEvent(new Event('input', {bubbles: true}));"
        "  i.value;"
        "}"
    )


def js_fill_input_by_index(index: int, value: str) -> str:
    safe = json.dumps(value)
    return js_eval(
        f"var inputs = document.querySelectorAll('input'); var i = inputs[{index}];"
        "if (!i) 'no input at index';"
        "else {"
        "  i.focus(); i.select();"
        "  document.execCommand('delete');"
        f"  document.execCommand('insertText', false, {safe});"
        "  i.dispatchEvent(new Event('input', {bubbles: true}));"
        "  i.value;"
        "}"
    )


def js_click_button(label: str) -> str:
    """Click a <button> whose textContent contains `label` (case-insensitive,
    trimmed). Falls back to <a role=button> for sites using anchors."""
    safe = json.dumps(label.lower())
    return js_eval(
        "(function(){"
        "  var nodes = document.querySelectorAll('button, a[role=button], div[role=button]');"
        "  for (var i = 0; i < nodes.length; i++) {"
        "    if ((nodes[i].textContent || '').trim().toLowerCase().includes(" + safe + ")) {"
        "      nodes[i].click();"
        "      return 'clicked: ' + nodes[i].textContent.trim().slice(0, 60);"
        "    }"
        "  }"
        "  return 'not found';"
        "})()"
    )


def js_set_contenteditable(label_text: str, html: str) -> str:
    """Spotify uses contenteditable rich-text editors for episode
    description. Find the editor that follows a label containing
    `label_text` and set its innerHTML — then dispatch an input event
    so the React state machine picks the value up."""
    safe_label = json.dumps(label_text.lower())
    safe_html = json.dumps(html)
    return js_eval(
        "(function(){"
        "  var labels = document.querySelectorAll('label, span, div');"
        "  var editor = null;"
        "  for (var i = 0; i < labels.length; i++) {"
        "    var t = (labels[i].textContent || '').toLowerCase();"
        f"    if (t.indexOf({safe_label}) === -1) continue;"
        "    var p = labels[i].closest('div');"
        "    if (!p) continue;"
        "    editor = p.querySelector('[contenteditable=\"true\"]');"
        "    if (editor) break;"
        "  }"
        "  if (!editor) {"
        "    editor = document.querySelector('[contenteditable=\"true\"]');"
        "  }"
        "  if (!editor) return 'no contenteditable found';"
        "  editor.focus();"
        f"  editor.innerHTML = {safe_html};"
        "  editor.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));"
        "  return 'set: ' + editor.innerHTML.slice(0, 80);"
        "})()"
    )


# ---------------------------------------------------------------------------
# Login flow
# ---------------------------------------------------------------------------

def _is_logged_in(snap: str) -> bool:
    s = snap.lower()
    # Creators dashboard signals — episode list, "New episode" CTA, etc.
    return (
        "new episode" in s
        or "your episodes" in s
        or "podcast dashboard" in s
        or "episodes" in s and "downloads" in s  # analytics tab also reliable
    )


def _is_login_page(snap: str) -> bool:
    s = snap.lower()
    return ("log in to spotify" in s or "log in" in s) and (
        "email" in s or "username" in s
    )


def _is_2fa_page(snap: str) -> bool:
    s = snap.lower()
    return any(p in s for p in ("verification code", "two-factor", "verify it's you"))


def ensure_session() -> str:
    """Ensure the session is logged into Spotify for Creators.

    Spotify's login is on accounts.spotify.com. The Creators dashboard
    redirects there if not authenticated. After login it redirects back
    to creators.spotify.com.

    2FA: if Spotify prompts for a code (SMS or authenticator), the script
    waits for the operator to provide it via stdin or SPOTIFY_2FA_CODE.
    """
    snap = open_url(f"{SPOTIFY_URL}/dashboard")
    if _is_logged_in(snap):
        return snap

    # Force the login page if we ended up somewhere ambiguous.
    if not _is_login_page(snap):
        snap = open_url(SPOTIFY_LOGIN_URL)

    # Email + password
    if SPOTIFY_EMAIL:
        # Spotify uses input[name=username] for the email/username field.
        js_fill_input_by_name("username", SPOTIFY_EMAIL)
    if SPOTIFY_PASSWORD:
        js_fill_input_by_name("password", SPOTIFY_PASSWORD)
    js_click_button("log in")
    wait(5000)
    snap = snapshot()

    # 2FA — Spotify only prompts for unrecognised devices
    if _is_2fa_page(snap):
        code = (
            os.environ.get("SPOTIFY_2FA_CODE")
            or input("Enter the Spotify verification code: ").strip()
        )
        # Single OTP input on Spotify's 2FA screen
        js_fill_input_by_index(0, code)
        js_click_button("verify")
        wait(5000)
        snap = snapshot()

    # Some accounts hit a "Trust this device?" prompt next
    if "trust this device" in snap.lower() or "remember" in snap.lower():
        js_click_button("yes")
        wait(3000)
        snap = snapshot()

    # We should land back on creators.spotify.com once auth succeeds.
    if not _is_logged_in(snap):
        # Navigate explicitly in case the redirect didn't fire.
        snap = open_url(f"{SPOTIFY_URL}/dashboard")

    if not _is_logged_in(snap):
        raise RuntimeError(
            "Spotify login did not complete. Snapshot follows:\n"
            + snap[:2000]
        )
    return snap


# ---------------------------------------------------------------------------
# Upload-an-episode flow
# ---------------------------------------------------------------------------

def _find_master_video(episode_num: int) -> Path:
    ep_dir = REPO_ROOT / "episodes" / f"Episode{episode_num:02d}"
    if not ep_dir.exists():
        raise FileNotFoundError(f"Episode dir not found: {ep_dir}")
    matches = [
        p for p in ep_dir.iterdir()
        if p.is_file() and re.search(r"final", p.name, re.IGNORECASE)
        and p.suffix.lower() == ".mp4"
        and "audio" not in p.name.lower()
    ]
    if not matches:
        raise FileNotFoundError(
            f"No master video matching '*Final*.mp4' in {ep_dir} (excluded "
            "audio-only files). Pass --video PATH explicitly."
        )
    if len(matches) > 1:
        raise FileNotFoundError(
            f"Multiple candidate videos in {ep_dir}: {[p.name for p in matches]}. "
            "Pass --video PATH to disambiguate."
        )
    return matches[0]


def _load_metadata(episode_num: int) -> dict:
    p = REPO_ROOT / "episodes" / f"Episode{episode_num:02d}" / f"SIB_E{episode_num:02d}_metadata.yaml"
    if not p.exists():
        raise FileNotFoundError(f"Metadata YAML not found: {p}")
    with p.open() as f:
        return yaml.safe_load(f)


def _episode_title(meta: dict) -> str:
    """Mirror what's already used in the Hugo site: the `hugo_title` field
    is the canonical episode title."""
    return meta["episode"]["hugo_title"]


def _episode_description_html(meta: dict) -> str:
    """Spotify accepts limited HTML in the description editor. We feed it
    the long_description with paragraph breaks preserved as <p>...</p>."""
    desc = meta["episode"].get("long_description", "").strip()
    if not desc:
        return ""
    # Split on blank lines into paragraphs.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", desc) if p.strip()]
    body = "".join(f"<p>{_html_escape(p)}</p>" for p in paragraphs)
    # Append "Links mentioned" if present.
    links = meta["episode"].get("links_mentioned") or []
    if links:
        items = "".join(f'<li><a href="{url}">{url}</a></li>' for url in links)
        body += f"<p><b>Links mentioned</b></p><ul>{items}</ul>"
    return body


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace("\n", "<br>")
    )


def upload_episode(episode_num: int, video: Path,
                   cover: Path | None = None,
                   publish_at: str | None = None) -> dict:
    """Drive the dashboard end-to-end: navigate to "New episode", upload
    the video, fill metadata, submit. Returns a dict with the resulting
    Spotify episode URL on success.

    Selectors for the upload form will drift. Each step does
    `snapshot()` first so a Hermes-style agent can inspect the page if
    a selector falls behind."""
    ensure_session()
    meta = _load_metadata(episode_num)
    title = _episode_title(meta)
    description_html = _episode_description_html(meta)

    # Spotify supports 2 entry points: the "Create" button on the
    # left rail, or "New episode" in the episodes table. The rail
    # button is more stable across UI revisions.
    snap = open_url(f"{SPOTIFY_URL}/dashboard")
    if "new episode" in snap.lower():
        js_click_button("new episode")
    else:
        js_click_button("create")
        wait(2000)
        js_click_button("new episode")
    wait(4000)
    snap = snapshot()

    # Upload step — Spotify uses a hidden <input type=file>. Set it via
    # agent-browser's file-upload command (drives the input even when not
    # visible).
    file_input_xpath = "//input[@type='file']"
    run_ab("upload", file_input_xpath, str(video))
    # Spotify shows a progress bar; wait for processing to complete
    # (transcode finish signalled by the form fields appearing).
    _wait_for_form_ready()

    # Title (single-line)
    js_fill_input_by_name("title", title)

    # Description (rich-text contenteditable)
    js_set_contenteditable("description", description_html)

    # Episode number + optional season
    ep = meta["episode"]
    js_fill_input_by_name("episodeNumber", str(ep["number"]))
    if "season" in ep:
        js_fill_input_by_name("seasonNumber", str(ep["season"]))

    # Explicit toggle (rarely on for SIB; flip if metadata says so)
    if ep.get("explicit"):
        js_click_button("explicit")

    # Publish-at: if absent, save as draft. Otherwise schedule.
    if publish_at:
        js_click_button("schedule")
        wait(2000)
        # Datetime input — Spotify renders separate date + time fields.
        date_part, _, time_part = publish_at.partition("T")
        js_fill_input_by_name("publishDate", date_part)
        if time_part:
            js_fill_input_by_name("publishTime", time_part)

    # Cover artwork — optional override. If provided, upload it via the
    # cover-art "edit" flow.
    if cover:
        js_click_button("edit artwork")
        wait(2000)
        run_ab("upload", "(//input[@type='file'])[2]", str(cover))
        wait(2000)
        js_click_button("save")

    # Final submit
    js_click_button("publish" if publish_at else "save as draft")
    wait(5000)
    snap = snapshot()

    # Pull the resulting episode URL from the dashboard
    m = re.search(
        r'https://open\.spotify\.com/episode/[A-Za-z0-9]+',
        snap,
    )
    return {
        "status": "success" if m else "uncertain",
        "episode_url": m.group(0) if m else None,
        "title": title,
        "snapshot_excerpt": snap[:1500],
    }


def _wait_for_form_ready(max_wait_seconds: int = 600) -> None:
    """Poll the page until the upload form fields are present (means
    Spotify has finished receiving + transcoding the file). Spotify can
    take 5–10 minutes for hour-long video transcodes; we cap at 10 min."""
    start = time.time()
    while time.time() - start < max_wait_seconds:
        snap = snapshot()
        if (
            "title" in snap.lower()
            and "description" in snap.lower()
            and "episode number" in snap.lower()
        ):
            return
        wait(15000)
    raise TimeoutError(
        f"Upload form did not become ready within {max_wait_seconds}s. "
        "Check the browser session manually."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--test-login", action="store_true",
                   help="Verify the script can log into Spotify for Creators.")
    p.add_argument("--upload", type=int, metavar="EPISODE_NUM",
                   help="Upload an episode to Spotify (reads metadata YAML).")
    p.add_argument("--video", type=Path,
                   help="Override the master video file path.")
    p.add_argument("--cover", type=Path,
                   help="Override the cover-art file path.")
    p.add_argument("--publish-at", metavar="ISO_DATETIME",
                   help="Schedule publish (e.g. 2026-05-15T10:00). If "
                        "omitted, the episode is saved as a draft.")
    args = p.parse_args(argv)

    if args.test_login:
        snap = ensure_session()
        print("login OK")
        print(snap[:1500])
        return 0

    if args.upload:
        if not SPOTIFY_EMAIL or not SPOTIFY_PASSWORD:
            print("SPOTIFY_EMAIL + SPOTIFY_PASSWORD must be set in .env",
                  file=sys.stderr)
            return 2
        video = args.video or _find_master_video(args.upload)
        result = upload_episode(args.upload, video, args.cover, args.publish_at)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "success" else 1

    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
