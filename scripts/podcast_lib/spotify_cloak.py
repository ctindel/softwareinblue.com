"""Drive Spotify for Creators episode-details edit:
title / season / episode-number / cover-art / thumbnail / description / Save.

Usage: python3 spotify_edit_ep.py EPISODE_NUM [--keep-open]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import yaml

# scripts/podcast_lib/spotify_cloak.py → repo root is 2 dirs up.
REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "scripts" / "podcast_lib"))
from cloakbrowser import launch_persistent_context
from dotenv import load_dotenv
from spotify_description import render_description_html

load_dotenv(REPO / "scripts" / "podcast_lib" / ".env", override=False)

PROFILE = Path.home() / ".cloak-profiles" / "spotify-creators"
SHOW_ID = "25r9ckggqIv6rGU8ca0WP2"
LIST_URL = f"https://creators.spotify.com/pod/show/{SHOW_ID}/episodes"
OUT = Path("/tmp/spotify_discover")
OUT.mkdir(exist_ok=True)


def episode_title(num: int) -> str:
    md = REPO / "hugosite" / "content" / "episode" / f"episode{num}.md"
    text = md.read_text()
    m = re.search(r'^title\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1).strip() if m else f"Episode {num}"


def cover_path(num: int) -> Path:
    # Spotify episode art uses the D2 variant (square 3000×3000 cornflower
    # version of the DOAC-style cover). Matches the D-series branding on
    # YouTube thumbnails. Hugo's episode_image still points at w1.
    return REPO / "hugosite" / "static" / "img" / "episode" / f"Episode{num:02d}" / "d2" / "podcast-cover-3000x3000.png"


def thumbnail_path(num: int) -> Path:
    return REPO / "hugosite" / "static" / "img" / "episode" / f"Episode{num:02d}" / "d2" / "thumbnail-youtube-1920x1080.png"


def metadata_yaml(num: int) -> dict:
    p = REPO / "episodes" / f"Episode{num:02d}" / f"SIB_E{num:02d}_metadata.yaml"
    return yaml.safe_load(p.read_text())


_KNOWN_IDS = {
    # Full map populated 2026-05-10 by paginating the Spotify dashboard
    # (see /tmp/spotify_id_map.py). Refresh by running that script again
    # if Spotify ever reissues episode IDs (rare).
    0: "2J39lRIxPUjUI4cIzaJEgG",
    1: "2E549w9rrRDyMbIj2j3TA7",
    2: "0uKpul9ezNBkp36zCjE11L",
    3: "6c9ZeG1U66kILHadJiWCsF",
    4: "1yB7oUIzV43xatcVnudSlL",
    5: "691yhBTMiOA35lbtUkDvg9",
    6: "2PVDGCa0hLzKAKZ3qlIlkP",
    7: "3ENEYGEIGrT8402E07R61b",
    8: "0yQVVJym12E9dPZYtant6g",
    9: "1AIlM4NV6U19vAVQ4wIJxa",
    10: "58DsafGqkQ67p2GHqyrkxb",
    11: "5ytI0oz83mYganuQ7TI110",
    12: "5rXsTV04zfGGTZHHbhWjWV",
    13: "2b2srDOgtbfStdeSpdpBN1",
    14: "1gAAbjziXaw4gnBTKIzZ1O",
    15: "5VbMfpxyzQag087lotKWOt",
    16: "70peF3WyIZUxCqHOOqwDFN",
    17: "68EYFoCU1U3cVxAFph29HT",
    18: "17FDGdtzYWXc7iTrM80FAq",
    19: "7t0gJjSUQXPE7qXpDd04OJ",
    20: "3otUHoc108N5ZNxmLjlNWc",
    21: "36Ke20wQYquqvnZw40MLBS",
    22: "32ffp7ckxhby9hQAL8w75C",
    23: "1LYa75EomzfiCHD8SCWipH",
    24: "1K1zumEVtm0V4fSlVXk5R8",
    25: "2sRv23C3ExcltpIR2c6wLn",
    26: "5HiJKq2r7M94fPhPhsBJvi",
    27: "7d9EpKo5NWsBOee1M571g5",
    28: "3Q0vA5v2Ra79gNNnoz36ap",
    29: "3T26odvbg0wxGTsuQaf9mW",
    30: "2XBvq59XjDXP86583zgM7u",
    31: "1iBwi1Y1NyVXwIPE2SCjOW",
    32: "329IQf790g2aj7XfW1Z0mC",
    33: "4RtwZGCdX8Q3JrTRdL8Goe",
    34: "2xmllvDun0TeNmZRzVSe0e",
    35: "7IFlbp62KDBIQUAz9n8kBf",
    36: "5i1gqmPpCuVCN41WdSEcVp",
    37: "5cMakhvLcvLpgHTMa9aiDO",
    38: "3NsRIyqe3doxvcvQXImTs0",
    39: "2aVOYVI0rEpckxDv8za3nD",
    40: "3yXhlQNZ0eGjlWyZZLigHk",
    41: "5O3D5wTJMQtp0I2KHiMifG",
    42: "7pt8exiwuNhRtbqh7Q813d",
    43: "2nGrR5NoQYmVmcIVIixC8s",
    44: "1nBi1O7PYFPvPKSYKsQfDp",
    45: "1gT8U3JHXYqVVh1Xaj0wpp",
}


def find_spotify_episode_id(page, num: int) -> str:
    if num in _KNOWN_IDS:
        return _KNOWN_IDS[num]
    page.goto(LIST_URL)
    page.wait_for_timeout(6000)
    page.locator('button:has-text("Search")').first.click()
    page.wait_for_timeout(2000)
    inp = page.locator('input[placeholder="Search episode titles"]')
    inp.click()
    page.wait_for_timeout(300)
    inp.fill("")
    page.wait_for_timeout(200)
    # Use a unique-enough query — many old titles use #N format vs "Episode N".
    inp.fill(str(num))
    inp.press("Enter")
    page.wait_for_timeout(5000)
    target = re.compile(rf'(?:^|\s)(?:Episode\s+{num}\s*\||#\s*{num}\b)', re.IGNORECASE)
    for el in page.locator('a[href*="/episode/"][href$="/details"]').all():
        txt = (el.inner_text(timeout=400) or "").strip()
        if target.search(txt):
            href = el.get_attribute("href") or ""
            m = re.search(r"/episode/([A-Za-z0-9]+)/details", href)
            if m:
                return m.group(1)
    raise RuntimeError(f"could not find episode {num}")


def _confirm_dialog(page, label: str) -> None:
    """Click the primary action button inside an open Spotify confirmation
    dialog. The crop modal's confirm button is labeled 'Finish'; older /
    other modals use 'Save' or 'Apply'. Match either by text or by the
    primary-button class within the dialog footer."""
    result = page.evaluate("""() => {
      // Find any visible button inside an element with class
      // dialog-confirmation__footer; prefer the legacy-button-primary one,
      // fallback to any button matching common confirm verbs.
      const footers = Array.from(document.querySelectorAll('*')).filter(el => {
        const cls = (el.className||'').toString();
        return /dialog-confirmation__footer/.test(cls);
      });
      for (const f of footers) {
        const buttons = Array.from(f.querySelectorAll('button')).filter(b => b.offsetParent !== null);
        if (buttons.length === 0) continue;
        const primary = buttons.find(b => /legacy-button-primary/.test((b.className||'').toString()));
        const verb = buttons.find(b => /^(finish|save|apply|confirm|done|continue|use|ok)$/i.test((b.innerText||'').trim()));
        const target = primary || verb;
        if (target) {
          target.click();
          return 'clicked: ' + (target.innerText||'').trim();
        }
      }
      return 'no dialog button found';
    }""")
    print(f"[{label}] modal confirm: {result}")
    page.wait_for_timeout(4000)


def keyboard_fill(page, sel: str, value: str, label: str) -> None:
    """Replace the value of a form input by simulating real keyboard input.

    Spotify's form Save button is disabled until React detects the form
    is "dirty"; only true `input` events from typed-key sequences trigger
    that flag.

    Use HTMLInputElement.select() for reliable select-all (works on both
    text and number inputs and ignores cursor position). Then keyboard.type
    overwrites the selection — that fires real input events so React picks
    up the dirty state."""
    el = page.locator(sel)
    before = el.input_value()
    el.scroll_into_view_if_needed()
    el.click()
    page.wait_for_timeout(200)
    el.evaluate("el => el.select()")
    page.wait_for_timeout(150)
    page.keyboard.press("Backspace")
    page.wait_for_timeout(200)
    page.keyboard.type(value, delay=30)
    page.wait_for_timeout(400)
    page.keyboard.press("Tab")
    page.wait_for_timeout(200)
    after = el.input_value()
    print(f"[{label}] {before!r} → {after!r}")
    if after != value:
        print(f"[{label}] WARNING: value mismatch (expected {value!r})")


def _inject_cookies(ctx) -> bool:
    """Load exported cookies from /tmp/spotify_cookies.json if present."""
    cookie_file = Path("/tmp/spotify_cookies.json")
    if not cookie_file.exists():
        return False
    import json as _json
    cookies = _json.loads(cookie_file.read_text())
    if not cookies:
        return False
    # Playwright expects sameSite to be capitalized properly.
    for c in cookies:
        ss = c.get("sameSite", "None")
        c["sameSite"] = {"none": "None", "lax": "Lax", "strict": "Strict"}.get(
            ss.lower(), "None") if ss else "None"
    ctx.add_cookies(cookies)
    print(f"[login] injected {len(cookies)} cookies from {cookie_file}")
    return True


def _ensure_logged_in(page) -> None:
    """Navigate to the Spotify creators dashboard and log in if needed.

    Uses SPOTIFY_EMAIL / SPOTIFY_PASSWORD from the environment. The persistent
    CloakBrowser profile caches the session, so subsequent runs skip login.
    """
    # Inject exported cookies before the first navigation.
    _inject_cookies(page.context)

    page.goto(LIST_URL)
    page.wait_for_timeout(5000)
    url = page.url
    # Already on the dashboard — session is valid.
    if "creators.spotify.com" in url and "/episodes" in url:
        print("[login] session valid — already on dashboard")
        return
    # Spotify redirects to creators.spotify.com/pod/login for login.
    print(f"[login] redirected to {url[:120]} — logging in")
    email = os.environ.get("SPOTIFY_EMAIL", "")
    password = os.environ.get("SPOTIFY_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("SPOTIFY_EMAIL / SPOTIFY_PASSWORD not set in .env")

    # Click "Continue with Spotify" on the Creators login page to go
    # through the proper OAuth redirect chain to accounts.spotify.com.
    page.wait_for_timeout(3000)
    continue_btn = page.locator('button:has-text("Continue with Spotify")').first
    if continue_btn.count() > 0:
        print("[login] clicking 'Continue with Spotify'")
        continue_btn.click()
    else:
        # Fall back to the link version.
        continue_link = page.locator('a:has-text("Continue with Spotify")').first
        if continue_link.count() > 0:
            href = continue_link.get_attribute("href") or ""
            print(f"[login] navigating to Continue link: {href[:120]}")
            page.goto(href)
        else:
            raise RuntimeError("[login] no 'Continue with Spotify' button or link found")
    page.wait_for_timeout(8000)
    print(f"[login] accounts page: {page.url[:150]}")

    # Dump the page content for diagnostics.
    all_inputs = page.evaluate("""() => Array.from(document.querySelectorAll('input,button,a,h1,h2,p'))
        .map(e => ({tag: e.tagName, type: e.type||'', id: e.id||'', name: e.name||'',
                     text: (e.innerText||e.value||e.placeholder||'').trim().slice(0,80),
                     visible: e.offsetParent !== null}))
        .filter(e => e.text.length > 0 || e.id.length > 0)""")
    print(f"[login] all page elements: {all_inputs}")

    # Fill email — Spotify's current login page uses input#username (not #login-username).
    email_input = page.locator('input#username, input#login-username, input[name="username"], input[type="email"]').first
    email_input.wait_for(state="visible", timeout=15000)
    email_input.fill(email)
    page.wait_for_timeout(500)

    # Spotify's current login is two-step:
    # Step 1: Email + "Continue" button.
    # Step 2: Either password field or OTC (one-time code).
    # After step 2, there may be a "Log in with a password" link on OTC pages.
    pw_input = page.locator('input#password, input#login-password, input[type="password"]').first
    if pw_input.count() > 0 and pw_input.is_visible():
        print("[login] password field visible (classic flow)")
        pw_input.fill(password)
        page.wait_for_timeout(500)
        page.locator('button[type="submit"]').first.click()
    else:
        # Click Continue to advance past the email step.
        print("[login] clicking Continue")
        page.locator('button[type="submit"]').first.click()
        page.wait_for_timeout(5000)
        print(f"[login] after Continue: {page.url[:150]}")

        # Dump what's on the page now.
        elems = page.evaluate("""() => Array.from(document.querySelectorAll('input,button,a,h1,h2,p'))
            .map(e => ({tag: e.tagName, type: e.type||'', id: e.id||'',
                         text: (e.innerText||e.value||e.placeholder||'').trim().slice(0,80),
                         visible: e.offsetParent !== null}))
            .filter(e => (e.text.length > 0 || e.id.length > 0) && e.visible)""")
        print(f"[login] elements after Continue: {elems}")

        # Check for password field first.
        pw_input = page.locator('input#password, input#login-password, input[type="password"]').first
        if pw_input.count() > 0 and pw_input.is_visible():
            print("[login] password field appeared")
            pw_input.fill(password)
            page.wait_for_timeout(500)
            page.locator('button[type="submit"]').first.click()
        else:
            # Look for "Log in with a password" or similar link.
            pw_link = page.locator('a:has-text("password"), button:has-text("password")').first
            if pw_link.count() > 0:
                print(f"[login] clicking password link: {pw_link.inner_text()}")
                pw_link.click()
                page.wait_for_timeout(3000)
                pw_input = page.locator('input#password, input#login-password, input[type="password"]').first
                pw_input.wait_for(state="visible", timeout=15000)
                pw_input.fill(password)
                page.wait_for_timeout(500)
                page.locator('button[type="submit"]').first.click()
            else:
                raise RuntimeError(
                    "[login] BLOCKED: Spotify is using OTC (one-time code) login "
                    "and no 'Log in with password' option is available. "
                    "You may need to scp the cloak profile from your laptop."
                )

    page.wait_for_timeout(10000)
    print(f"[login] after login submit: {page.url[:150]}")

    # Handle 2FA if prompted.
    otp_input = page.locator('input[aria-label*="digit"], input[name*="otp"], input[name*="code"], input[inputmode="numeric"]').first
    if otp_input.count() > 0:
        print("[login] 2FA code requested — waiting up to 90s for push approval")
        for _ in range(18):
            page.wait_for_timeout(5000)
            if "creators.spotify.com" in page.url:
                print("[login] 2FA approved (push/auto)")
                return

    if "creators.spotify.com" in page.url and "/login" not in page.url:
        print("[login] logged in successfully")
    else:
        print(f"[login] WARNING: unexpected URL: {page.url[:200]}")
        print("[login] proceeding — session may still be establishing")


def set_description_html(page, html: str) -> None:
    """Toggle HTML mode then replace the textarea contents with the rendered HTML.

    React-controlled textareas ignore plain `el.value=` because React
    overrides the property descriptor. We use the prototype's native
    setter (`Object.getOwnPropertyDescriptor(...).set.call(el, v)`) +
    dispatch an `input` event so React picks up the new value."""
    clicked = page.evaluate("""() => {
      const cb = Array.from(document.querySelectorAll('input[type=checkbox]'))
        .find(el => (el.parentElement && el.parentElement.innerText.trim() === 'HTML'));
      if (!cb) return 'not found';
      const checked = cb.checked;
      cb.parentElement.click();
      return checked ? 'was-on' : 'turned-on';
    }""")
    print(f"[description] HTML toggle: {clicked}")
    page.wait_for_timeout(2500)

    ta = page.locator('textarea[name="description"]')
    if ta.count() == 0:
        raise RuntimeError("description textarea did not appear after HTML toggle")
    before = ta.input_value()
    print(f"[description] before length: {len(before)}")

    # React-friendly write: native value setter + input event.
    page.evaluate(
        """(html) => {
          const el = document.querySelector('textarea[name="description"]');
          if (!el) return 'no-textarea';
          const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
          setter.call(el, html);
          el.dispatchEvent(new Event('input', {bubbles: true}));
          el.dispatchEvent(new Event('change', {bubbles: true}));
          return 'ok';
        }""",
        html,
    )
    page.wait_for_timeout(800)
    after = ta.input_value()
    print(f"[description] after length:  {len(after)}")
    if after != html:
        # Diagnostic dump if it's still off.
        out = OUT / "description_after.txt"
        out.write_text(after)
        print(f"[description] WARNING: textarea contents differ from sent HTML; dumped {out}")

    # The React-setter doesn't mark Spotify's form as "dirty" — type a
    # real character then immediately delete it so the form's onChange
    # fires and the Save button enables.
    ta.click()
    page.keyboard.press("End")
    page.keyboard.type(" ")
    page.wait_for_timeout(200)
    page.keyboard.press("Backspace")
    page.wait_for_timeout(300)


def edit_episode(page, num: int, set_desc: bool = True,
                 allow_empty_show_notes: bool = False) -> None:
    title = episode_title(num)
    cover = cover_path(num)
    thumb = thumbnail_path(num)
    if not cover.exists():
        raise FileNotFoundError(cover)
    if not thumb.exists():
        raise FileNotFoundError(thumb)

    # Pre-flight: make sure show_notes are populated. If the YAML has
    # none, auto-fetch from YouTube. If even YouTube has none, BLOCK
    # — every SIB episode is expected to have show notes, and silently
    # blanking Spotify's description would be destructive.
    if set_desc:
        from fetch_show_notes import populate_show_notes
        result = populate_show_notes(num, force=False)
        print(f"[show_notes] {result}")
        meta_check = metadata_yaml(num)
        if not (meta_check.get("episode", {}).get("show_notes") or []):
            if not allow_empty_show_notes:
                raise RuntimeError(
                    f"ep{num}: no show notes found (YAML empty + couldn't "
                    "parse any from the YouTube description). Every SIB "
                    "episode should have show notes — if this one truly "
                    "doesn't, re-run with --allow-empty-show-notes. "
                    "Otherwise add the show notes to "
                    f"episodes/Episode{num:02d}/SIB_E{num:02d}_metadata.yaml "
                    "under episode.show_notes: and re-run."
                )
            print(f"[show_notes] WARNING: proceeding with empty show notes (--allow-empty-show-notes)")

    meta = metadata_yaml(num)
    description_html = render_description_html(meta) if set_desc else None

    sid = find_spotify_episode_id(page, num)
    print(f"[ep{num}] spotify_id={sid}")
    details = f"https://creators.spotify.com/pod/show/{SHOW_ID}/episode/{sid}/details"
    page.goto(details)
    page.wait_for_timeout(7000)
    print(f"[ep{num}] current URL after goto: {page.url[:200]}")

    # If we got redirected to login, try re-authenticating and navigating back.
    if "/login" in page.url or "accounts.spotify.com" in page.url:
        print(f"[ep{num}] got redirected to login — re-authenticating")
        _ensure_logged_in(page)
        page.goto(details)
        page.wait_for_timeout(10000)
        print(f"[ep{num}] current URL after re-login: {page.url[:200]}")

    # Wait for the title input to appear (SPA may take a moment).
    page.wait_for_selector("input#title-input", state="visible", timeout=20000)

    # Title — keyboard-driven so React marks the form dirty.
    keyboard_fill(page, "input#title-input", title, "title")
    # Season + Episode #
    keyboard_fill(page, "input#season-number", "1", "season")
    keyboard_fill(page, "input#episode-number", str(num), "epnum")

    # Cover
    print(f"[cover] uploading {cover}")
    page.locator("input#show-art-upload").set_input_files(str(cover))
    page.wait_for_timeout(8000)
    _confirm_dialog(page, "cover")
    page.wait_for_timeout(3000)          # let cover modal fully dismiss

    # Thumbnails: hover the leftmost tile, click the X, confirm Delete in
    # the modal, then upload the new 1920×1080. Spotify's X overlay is
    # opacity:0 by CSS until the parent tile is hovered, so we MUST do a
    # real Playwright `locator.hover()` (which dispatches mouseover events)
    # before clicking — synthetic .click() alone hits the thumbnail behind.
    page.evaluate("""() => {
      const all = Array.from(document.querySelectorAll('h1,h2,h3,h4,strong'));
      const t = all.find(el => (el.innerText||'').trim() === 'Thumbnails');
      if (t) t.scrollIntoView({block:'center'});
    }""")
    page.wait_for_timeout(1500)
    delete_btn = page.locator('button[aria-label="Delete"]').first
    if delete_btn.count() > 0:
        print("[thumb] hovering tile, clicking Delete X")
        # Hover parent of Delete (the thumbnail tile itself).
        tile = page.locator('button[aria-label="Delete"]').locator('xpath=ancestor::div[2]').first
        tile.hover()
        page.wait_for_timeout(800)
        delete_btn.click()
        page.wait_for_timeout(2500)
        # Confirm modal: locate the Delete button inside the dialog footer
        # and click via Playwright (JS .click() doesn't reach React handlers).
        # The footer has Cancel + Delete; we want Delete.
        confirm_btn = page.locator(
            '[class*="dialog-confirmation__footer"] button:has-text("Delete")'
        ).first
        if confirm_btn.count() > 0:
            confirm_btn.click()
            print("[thumb] confirm Delete clicked")
        else:
            print("[thumb] WARNING: confirm dialog Delete button not found")
        page.wait_for_timeout(3500)
        # Re-check that the custom thumbnail is gone
        remaining = page.evaluate("""() => ({
          delete: !!document.querySelector('button[aria-label="Delete"]'),
          thumbs: Array.from(document.querySelectorAll('button[aria-label*="Thumbnail"]'))
            .map(b => b.getAttribute('aria-label')),
        })""")
        print(f"[thumb] after delete: {remaining}")

    # The thumbnail upload input only materialises AFTER the existing
    # custom thumbnail is deleted; its id is `uploadAreaInput` (vs the
    # cover's `show-art-upload`).
    page.wait_for_selector("input#uploadAreaInput", state="attached", timeout=10000)
    thumb_input = page.locator("input#uploadAreaInput")
    print(f"[thumb] uploading {thumb}")
    thumb_input.set_input_files(str(thumb))
    page.wait_for_timeout(8000)
    _confirm_dialog(page, "thumb")
    # Re-check what custom thumbnail is now in slot 1
    new_thumb = page.evaluate("""() => {
      const t1 = document.querySelector('button[aria-label="Thumbnail 1"]');
      if (!t1) return null;
      let p = t1; for (let i = 0; i < 6; i++) p = p.parentElement;
      const img = p.querySelector('img[alt*="Uploaded"]');
      return img ? {src: img.src, w: img.naturalWidth, h: img.naturalHeight} : null;
    }""")
    print(f"[thumb] new uploaded thumbnail: {new_thumb}")

    # Description
    if description_html:
        set_description_html(page, description_html)

    # Save (form-bar Save, outside any dialog)
    page.screenshot(path=str(OUT / f"ep{num}_before_save.png"), full_page=True)
    save_state = page.evaluate("""() => {
      const b = Array.from(document.querySelectorAll('button')).find(b =>
        /^save$/i.test((b.innerText||'').trim()) && b.offsetParent !== null &&
        !(/dialog-confirmation/.test((b.closest('*[class*=dialog-confirmation]')||{}).className||'')));
      if (!b) return {error: 'no save button'};
      return {disabled: b.disabled, ariaDisabled: b.getAttribute('aria-disabled'),
              text: (b.innerText||'').trim()};
    }""")
    print(f"[save] button state: {save_state}")
    if save_state.get("disabled"):
        raise RuntimeError(
            "form Save button is DISABLED — no field-level dirty state "
            "was triggered; aborting before reload reverts everything."
        )
    print("[save] clicking final Save")
    # Scroll to top so the sticky Save button is in view + clickable.
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(800)

    save_locator = page.locator(
        'button[data-encore-id="buttonPrimary"]:has-text("Save")'
    ).first
    if save_locator.count() == 0:
        save_locator = page.locator('button:has-text("Save"):visible').first
    btn_text = save_locator.text_content() or ""
    print(f"[save] target button text: {btn_text.strip()!r}")

    # Try focus + Enter — Spotify's button is type=submit with onClick
    # handler. Real keyboard activation triggers React's click semantics
    # (this is what assistive tech does too).
    save_locator.focus()
    page.wait_for_timeout(300)
    page.keyboard.press("Enter")
    page.wait_for_timeout(2000)

    state_after_click = page.evaluate("""() => {
      const b = Array.from(document.querySelectorAll('button')).find(b =>
        /^save$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
      return b ? {text: (b.innerText||'').trim(), disabled: b.disabled} : {missing: true};
    }""")
    print(f"[save] state 2s after click: {state_after_click}")
    # Poll until the Save button is either disabled (committed) or
    # remains enabled past a hard timeout (failed). Spotify can take
    # ~15-25s to commit a save with media re-uploads.
    import time as _t
    deadline = _t.time() + 60
    while _t.time() < deadline:
        page.wait_for_timeout(2000)
        s = page.evaluate("""() => {
          const b = Array.from(document.querySelectorAll('button')).find(b =>
            /^save$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
          return b ? {disabled: b.disabled} : {disabled: null, missing: true};
        }""")
        if s.get("disabled") is True:
            print(f"[save] commit detected (Save now disabled) after ~{int(60 - (deadline - _t.time()))}s")
            break
    else:
        print("[save] WARNING: Save button never went disabled within 60s — save likely did not commit")
    page.screenshot(path=str(OUT / f"ep{num}_after_save.png"), full_page=True)
    print(f"[ep{num}] final url={page.url}")

    # Verification — open the same details URL in a fresh tab and read
    # back the persisted values. Anything still off is reported here.
    print(f"[verify] re-loading details to confirm save")
    page.goto(details, wait_until="domcontentloaded")
    page.wait_for_timeout(7000)
    state = page.evaluate("""() => ({
      title: document.querySelector('input#title-input')?.value,
      season: document.querySelector('input#season-number')?.value,
      epnum: document.querySelector('input#episode-number')?.value,
      coverSrc: document.querySelector('.header__container__imageContainer img')?.src,
      thumbButtons: Array.from(document.querySelectorAll('button[aria-label*="Thumbnail"], button[aria-label="Delete"]'))
        .map(b => b.getAttribute('aria-label')),
    })""")
    import json
    print("[verify] persisted state:")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("episode", type=int)
    p.add_argument("--keep-open", action="store_true")
    p.add_argument("--no-description", action="store_true",
                   help="Skip description set (debugging)")
    p.add_argument("--allow-empty-show-notes", action="store_true",
                   help="Proceed even when no show notes can be parsed. "
                        "Use only when an episode legitimately has no "
                        "links — every SIB episode is otherwise expected "
                        "to have show notes.")
    args = p.parse_args()

    ctx = launch_persistent_context(str(PROFILE), headless=True, humanize=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    # Surface anything Spotify's API rejects so silent save failures
    # don't look like the script worked.
    _NOISY = ("google", "doubleclick", "sentry.io", "tiktok", "snapchat",
              "branch.io", "stripe.com", "liveperson", "gabo-receiver",
              "remote-config", "pixels.spotify")
    page.on("request", lambda r: (
        print(f"[req] {r.method} {r.url[:140]}")
        if r.method in ("POST", "PUT", "PATCH", "DELETE")
        and not any(n in r.url for n in _NOISY)
        else None
    ))
    page.on("response", lambda r: (
        print(f"[res] {r.status} {r.request.method} {r.url[:140]}")
        if r.request.method in ("POST", "PUT", "PATCH", "DELETE")
        and not any(n in r.url for n in _NOISY)
        else None
    ))
    page.on("pageerror", lambda e: print(f"[pageerror] {e}"))
    try:
        _ensure_logged_in(page)
        edit_episode(page, args.episode, set_desc=not args.no_description,
                     allow_empty_show_notes=args.allow_empty_show_notes)
        if args.keep_open:
            print("[keep-open] press Ctrl-C to close")
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                pass
    finally:
        if not args.keep_open:
            ctx.close()
