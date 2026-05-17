#!/usr/bin/env python3
"""Preflight check for the SIB design pipeline.

Verifies that everything the design scripts need is present before they run:
  - committed brand assets (fonts, reference cover, logos)
  - tool deps (Pillow, rembg, headless Chrome)
  - per-episode inputs (Hugo metadata, guest headshot, AI-generated balloon)

Run at the start of any design-skill invocation:

  python3 design/preflight.py [EPISODE_NUM]

Exits 0 if everything is ready. Exits 2 with a checklist of missing items
if anything is unavailable. The skill should surface the checklist to the
user verbatim and ask for the missing inputs — never silently substitute.
"""
from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Fonts the Pillow compositor must load — every glyph layout is tuned to
# these specific faces. Substituting an unknown font shifts every measure
# and corrupts the spacing, so we fail loud here rather than fall back.
SFNS_PATH = "/System/Library/Fonts/SFNS.ttf"
REQUIRED_SF_VARIATIONS = (b"Regular", b"Medium", b"Bold", b"Heavy", b"Black")

# (label, expected_path, what_to_do_if_missing)
GLOBAL_FILE_REQS = [
    ("Futurama-Bold font",
     "design/fonts/Futurama-Bold.ttf",
     "Drop the Futurama-Bold.ttf file into design/fonts/. "
     "Other Futurama weights (SemiBold, Medium, Regular) are also expected here."),
    ("Reference podcast cover (Chad+Steve, no guest)",
     "hugosite/static/img/logos/podcast-cover-3000x3000.png",
     "Should be in the Hugo tree already; restore from git if missing."),
    ("SIB logo 320×320",
     "hugosite/static/img/logos/logo-320x320.png",
     "Should be in the Hugo tree already; restore from git if missing."),
    ("Chad host photo",
     "hugosite/static/img/host/chadtindel.png",
     "Should be in the Hugo tree already; restore from git if missing."),
    ("Steve host photo",
     "hugosite/static/img/host/stevemayzak.jpg",
     "Should be in the Hugo tree already; restore from git if missing."),
    ("Thumbnail spec",
     "design/sib-thumbnail-spec-prompt.md",
     "Spec doc; restore from git if missing."),
    ("Balloon-cartoon prompt",
     "design/balloon-prompt.md",
     "Prompt doc; restore from git if missing."),
]

PYTHON_PKGS = [
    ("Pillow",   "PIL",    "pip install Pillow"),
    ("rembg",    "rembg",  "pip install 'rembg[cpu]'"),
    ("rapidfuzz","rapidfuzz","pip install rapidfuzz"),
]

CMDS = [
    ("ffmpeg",   "brew install ffmpeg  (or apt install ffmpeg)"),
]


def check_files(reqs: list, base: Path) -> list[str]:
    missing: list[str] = []
    for label, rel, fix in reqs:
        p = base / rel
        if not p.exists():
            missing.append(f"  ✗ {label}\n      expected: {p}\n      fix: {fix}")
    return missing


def check_python_pkgs() -> list[str]:
    missing: list[str] = []
    for label, mod, fix in PYTHON_PKGS:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(f"  ✗ Python package: {label}\n      fix: {fix}")
    return missing


def check_cmds() -> list[str]:
    missing: list[str] = []
    for cmd, fix in CMDS:
        if shutil.which(cmd) is None:
            missing.append(f"  ✗ {cmd} on PATH\n      fix: {fix}")
    return missing


def check_chrome() -> list[str]:
    if not Path(CHROME_PATH).exists():
        return [f"  ✗ Google Chrome at {CHROME_PATH}\n      fix: install Google Chrome"]
    return []


def build_balloon_prompt(guest_full_name: str,
                         host_cover: Path, guest_nobg: Path) -> str:
    """Produce the ready-to-paste ChatGPT prompt for generating the per-episode
    balloon cover. Mirrors the recipe in design/balloon-prompt.md, with the
    guest's name + attachment paths inlined."""
    return (
        f"Attach these two images to the ChatGPT message:\n"
        f"  1. {host_cover}\n"
        f"  2. {guest_nobg}\n"
        f"\n"
        f"Then paste this prompt:\n"
        f"\n"
        f"---8<--- prompt ---8<---\n"
        f"Take this podcast cover and add a third caricature based on our guest "
        f"{guest_full_name} whose photo is attached also. The 3 bodies should be "
        f"roughly equivalent in size (don't put one in the background, all 3 are "
        f"equally important) and don't change the look of either of the two "
        f"existing caricatures either, and make the guest's caricature cartoony "
        f"so it matches the look and feel of the two hosts that are already in "
        f"the balloon. Have very low detail in facial lines, eyes / eyebrows / "
        f"facial hair, actual hair etc. so the look and feel matches how Chad "
        f"and Steve are already drawn.\n"
        f"---8<--- end prompt ---8<---"
    )


def check_fonts() -> list[str]:
    """Make sure the Pillow compositor can find the exact fonts it expects.

    SF Pro is the macOS system font and the layout is tuned to its metrics.
    Silent substitution to e.g. Helvetica Neue would visibly shift every
    glyph and break the spacing — we fail loudly instead.
    """
    issues: list[str] = []
    sfns = Path(SFNS_PATH)
    if not sfns.exists():
        issues.append(
            f"  ✗ SF Pro variable font missing\n"
            f"      expected: {sfns}\n"
            f"      fix: macOS ships this font; if it's gone, restore it from "
            f"another mac or reinstall the OS font set."
        )
        return issues

    try:
        from PIL import ImageFont   # type: ignore
    except ImportError:
        issues.append(
            "  ✗ Pillow not importable; can't verify SF Pro variations.\n"
            "      fix: pip install Pillow"
        )
        return issues

    try:
        f = ImageFont.truetype(str(sfns), 60)
        names = set(f.get_variation_names())
    except Exception as e:
        issues.append(
            f"  ✗ Could not enumerate SF Pro variations: {e}\n"
            f"      fix: confirm {sfns} isn't truncated; reinstall macOS fonts."
        )
        return issues

    missing = [v.decode() for v in REQUIRED_SF_VARIATIONS if v not in names]
    if missing:
        issues.append(
            f"  ✗ SF Pro is missing the following named weight(s): "
            f"{', '.join(missing)}\n"
            f"      fix: confirm {sfns} is the real Apple variable font, "
            f"not a stripped copy."
        )

    # Also check that the committed Futurama-Bold loads (used by the
    # wordmark-overlay script that runs before the compositor).
    fb = REPO_ROOT / "design" / "fonts" / "Futurama-Bold.ttf"
    if fb.exists():
        try:
            ImageFont.truetype(str(fb), 60)
        except Exception as e:
            issues.append(
                f"  ✗ design/fonts/Futurama-Bold.ttf failed to load: {e}\n"
                f"      fix: re-fetch the file."
            )

    return issues


def per_episode_checks(episode_num: int) -> list[str]:
    """Look up Hugo metadata for the episode to determine guest slug, then verify."""
    ep_md = REPO_ROOT / "hugosite" / "content" / "episode" / f"episode{episode_num}.md"
    issues: list[str] = []
    if not ep_md.exists():
        issues.append(
            f"  ✗ Hugo episode metadata\n"
            f"      expected: {ep_md}\n"
            f"      fix: create the episode .md (or pick a different EPISODE_NUM)"
        )
        return issues  # without metadata we can't know the guest slug

    # Pull the guest list from the +++ frontmatter.
    text = ep_md.read_text()
    import re, json
    m = re.search(r'^guests\s*=\s*(\[.*?\])', text, re.MULTILINE)
    guests: list[str] = []
    if m:
        try:
            guests = json.loads(m.group(1))
        except Exception:
            guests = []

    if not guests:
        issues.append(
            f"  ! No guests= field in {ep_md}\n"
            f"      fix: add guests = [\"<slug>\"] to the frontmatter"
        )
        return issues

    ep_design = REPO_ROOT / "hugosite" / "static" / "img" / "episode" / f"Episode{episode_num:02d}"
    for slug in guests:
        # Guest content file (Hugo) — needs Title field for the cartoon prompt + thumbnail copy.
        guest_md = REPO_ROOT / "hugosite" / "content" / "guest" / f"{slug}.md"
        if not guest_md.exists():
            issues.append(
                f"  ✗ Guest content file: {slug}\n"
                f"      expected: {guest_md}\n"
                f"      fix: create the guest .md OR ASK THE USER for the guest's full name + title before proceeding"
            )
        else:
            content = guest_md.read_text()
            title_match = re.search(r'^Title\s*=\s*"([^"]+)"', content, re.MULTILINE)
            if not title_match or not title_match.group(1).strip():
                issues.append(
                    f"  ✗ Guest title not set in {guest_md}\n"
                    f"      ASK THE USER explicitly: "
                    f"'What full name and professional title should I use for the guest \"{slug}\"?' "
                    f"Don't guess. The name + title is rendered into thumbnails and the cartoon prompt."
                )
        # Original guest photo (Hugo)
        photo = REPO_ROOT / "hugosite" / "static" / "img" / "guest" / f"{slug}.jpg"
        if not photo.exists():
            issues.append(
                f"  ✗ Guest source photo: {slug}\n"
                f"      expected: {photo}\n"
                f"      fix: drop the guest's headshot (jpg) into hugosite/static/img/guest/"
            )
        # BG-removed headshot
        nobg = ep_design / "headshots" / f"{slug}-nobg.png"
        if not nobg.exists():
            issues.append(
                f"  ✗ BG-removed guest headshot: {slug}\n"
                f"      expected: {nobg}\n"
                f"      fix: python3 -c \"from rembg import remove; "
                f"open('{nobg}','wb').write(remove(open('{photo}','rb').read()))\""
            )
        # AI-generated balloon (no overlay)
        balloon_no = ep_design / "illustrations" / f"SIB_E{episode_num:02d}_Balloon_no_overlay.png"
        if not balloon_no.exists():
            host_cover = REPO_ROOT / "hugosite" / "static" / "img" / "logos" / "podcast-cover-3000x3000.png"
            # Pull the guest's full name from their Hugo .md if we read it above.
            full_name = slug
            if guest_md.exists():
                gm_text = guest_md.read_text()
                tm = re.search(r'^Title\s*=\s*"([^"]+)"', gm_text, re.MULTILINE)
                if tm:
                    full_name = tm.group(1)
            prompt_block = build_balloon_prompt(full_name, host_cover, nobg)
            indented = "\n      ".join(prompt_block.splitlines())
            issues.append(
                f"  ✗ AI-generated balloon scene (no overlay): Episode {episode_num}\n"
                f"      expected: {balloon_no}\n"
                f"      fix: follow design/balloon-prompt.md — paste this directly into ChatGPT:\n"
                f"\n"
                f"      {indented}\n"
                f"\n"
                f"      Save the result to {balloon_no}, then re-run preflight."
            )
        # Wordmark-overlay balloon (auto-generated from no_overlay)
        balloon_with = ep_design / "illustrations" / f"SIB_E{episode_num:02d}_Balloon_with_overlay.png"
        if not balloon_with.exists() and balloon_no.exists():
            issues.append(
                f"  ! Wordmark-overlay cover not yet generated for Episode {episode_num}\n"
                f"      run: python3 design/add_wordmark_overlay.py {episode_num}"
            )
    return issues


def main() -> int:
    target_ep: int | None = None
    if len(sys.argv) > 1:
        try:
            target_ep = int(sys.argv[1])
        except ValueError:
            print(f"Bad EPISODE_NUM: {sys.argv[1]!r}", file=sys.stderr)
            return 2

    print(f"=== SIB design preflight  (repo: {REPO_ROOT}) ===\n")

    sections = [
        ("Brand assets", check_files(GLOBAL_FILE_REQS, REPO_ROOT)),
        ("System tools", check_cmds()),
        ("Headless Chrome", check_chrome()),
        ("Python packages", check_python_pkgs()),
        ("Compositor fonts", check_fonts()),
    ]
    if target_ep is not None:
        sections.append((f"Episode #{target_ep} inputs", per_episode_checks(target_ep)))

    blocking = 0
    warnings = 0
    for name, issues in sections:
        if not issues:
            print(f"[OK] {name}")
            continue
        print(f"[ISSUES] {name}")
        for line in issues:
            print(line)
            if "✗" in line:
                blocking += 1
            elif "!" in line:
                warnings += 1
        print()

    if blocking:
        print(f"\n{blocking} blocking issue(s). Fix the items marked ✗ before running the design pipeline.")
        return 2
    if warnings:
        print(f"\n{warnings} warning(s). Pipeline can run but will skip optional steps.")
    print("\nReady.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
