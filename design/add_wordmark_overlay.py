#!/usr/bin/env python3
"""Add the SIB wordmark overlay (dark charcoal strip + show title) to a
podcast cover that was generated without one (e.g. an AI-generated
balloon scene).

Reads:
  hugosite/static/img/episode/Episode<N>/illustrations/SIB_E<N>_Balloon_no_overlay.png
Writes:
  hugosite/static/img/episode/Episode<N>/illustrations/SIB_E<N>_Balloon_with_overlay.png

Usage:
  python3 design/add_wordmark_overlay.py [EPISODE_NUM]
  python3 design/add_wordmark_overlay.py [EPISODE_NUM] INPUT.png OUTPUT.png

Defaults: EPISODE_NUM=45 → reads from / writes to the standard repo paths.
Pass explicit INPUT/OUTPUT to override.

The overlay matches the look of the show's reference podcast cover:
  - dark charcoal strip across the bottom (near-opaque #404444 with a
    short fade-in at the top edge so it doesn't clip the artwork)
  - "Can I get that software"  in white
  - "in blue?"                  in cornflower (#6495ED)
  - Futurama-Bold (committed to design/fonts/Futurama-Bold.ttf)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = REPO_ROOT / "design" / "fonts" / "Futurama-Bold.ttf"

# Palette
SIB_BLUE = (100, 149, 237, 255)   # cornflower
WHITE = (255, 255, 255, 255)
STRIP = (64, 68, 67)              # dark charcoal, sampled from SIB_E45_Balloon_with_overlay.png
STRIP_ALPHA = 245                  # near-opaque

# Strip geometry (fractions of image height)
STRIP_HEIGHT = 0.18
FADE_HEIGHT = 0.025                # short fade at top edge of the strip
FONT_HEIGHT = 0.062                # font size as fraction of canvas height


def render_overlay(input_path: Path, output_path: Path) -> None:
    if not FONT_PATH.exists():
        raise SystemExit(
            f"Missing font at {FONT_PATH}. The committed Futurama-Bold.ttf "
            f"should live in design/fonts/."
        )
    img = Image.open(input_path).convert("RGBA")
    W, H = img.size

    strip_h = int(H * STRIP_HEIGHT)
    fade_h = int(H * FADE_HEIGHT)
    strip = Image.new("RGBA", (W, strip_h), (0, 0, 0, 0))
    px = strip.load()
    for y in range(strip_h):
        if y < fade_h:
            alpha = int(STRIP_ALPHA * (y / fade_h))
        else:
            alpha = STRIP_ALPHA
        for x in range(W):
            px[x, y] = (*STRIP, alpha)
    img.alpha_composite(strip, dest=(0, H - strip_h))

    draw = ImageDraw.Draw(img)
    font_size = int(H * FONT_HEIGHT)
    font = ImageFont.truetype(str(FONT_PATH), font_size)

    text_white = "Can I get that software "
    text_blue = "in blue?"

    bbox_w = draw.textbbox((0, 0), text_white, font=font)
    bbox_b = draw.textbbox((0, 0), text_blue, font=font)
    width_w = bbox_w[2] - bbox_w[0]
    width_b = bbox_b[2] - bbox_b[0]
    total_w = width_w + width_b

    # Center the wordmark vertically in the solid (post-fade) part of the strip.
    solid_top = H - strip_h + fade_h
    cx = W // 2
    # Pillow's text() y is the top of the text; compute a baseline that puts
    # the visual center of the line in the center of the solid strip area.
    text_top = (solid_top + (H - solid_top) // 2) - font_size // 2 - int(font_size * 0.1)
    x0 = cx - total_w // 2

    draw.text((x0, text_top), text_white, font=font, fill=WHITE)
    draw.text((x0 + width_w, text_top), text_blue, font=font, fill=SIB_BLUE)

    img.save(output_path, format="PNG")
    print(f"wrote {output_path}  ({output_path.stat().st_size:,} bytes)")


def default_paths(episode_num) -> tuple[Path, Path]:
    """Build the in/out balloon paths for an episode. Accepts int episode
    numbers (zero-padded as Episode01..Episode99 / SIB_E01..SIB_E99) AND
    string episode IDs like "23.5" for half-episode interludes (used
    literally in the path/filename slots so they line up with the rest of
    the design pipeline)."""
    if isinstance(episode_num, int):
        ep_id = f"{episode_num:02d}"
    else:
        ep_id = str(episode_num)
    base = REPO_ROOT / "hugosite" / "static" / "img" / "episode" / f"Episode{ep_id}" / "illustrations"
    return (
        base / f"SIB_E{ep_id}_Balloon_no_overlay.png",
        base / f"SIB_E{ep_id}_Balloon_with_overlay.png",
    )


def main() -> None:
    args = sys.argv[1:]
    if not args:
        ep = 45
        in_path, out_path = default_paths(ep)
    elif len(args) == 1:
        try:
            ep = int(args[0])
        except ValueError:
            ep = args[0]                  # non-int ID like "23.5"
        in_path, out_path = default_paths(ep)
    elif len(args) == 3:
        ep, in_arg, out_arg = args
        in_path = Path(in_arg)
        out_path = Path(out_arg)
    else:
        print("Usage: add_wordmark_overlay.py [EPISODE_NUM] [INPUT.png OUTPUT.png]",
              file=sys.stderr)
        sys.exit(2)

    if not in_path.exists():
        raise SystemExit(f"No input file at {in_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    render_overlay(in_path, out_path)


if __name__ == "__main__":
    main()
