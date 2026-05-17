#!/usr/bin/env python3
"""Pure-Pillow SIB thumbnail compositor.

Renders every (variant × size) for one episode using PIL only — no headless
browser. Deterministic, fast, no Chrome version surprises.

Layout primitives (text panels, photo circles, magazine splits, whimsical
balloon backdrops) are implemented directly in Pillow draw calls.

Per-episode artifacts (under hugosite/ so Hugo can serve them directly):
  hugosite/static/img/episode/Episode<N>/
      headshots/<slug>-nobg.png
      illustrations/SIB_E<N>_Balloon_no_overlay.png
      illustrations/SIB_E<N>_Balloon_with_overlay.png
      <variant>/<size>.png

Usage:
  python3 design/gen_sib_exports.py [EPISODE_NUM] [GUEST_SLUG]

Defaults: EPISODE_NUM=45, GUEST_SLUG=robertakang.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------- args + paths -----------------------------------------------

# Episode arg accepts integers (1, 23, 45) AND non-int IDs like "23.5" for
# half-episode interludes. EPISODE_ID is the canonical string used in folder
# and filename slots ("01", "23", "23.5", "45"); EPISODE_DISPLAY is the
# human-facing form rendered onto thumbnails ("EPISODE #1", "#23.5", etc).
# Parse positional args and optional --flags.
# Usage: gen_sib_exports.py EPISODE_NUM GUEST_SLUG [--tagline TEXT]
#                           [--tagline-highlight TEXT] [--out-dir PATH]
import argparse as _ap
_parser = _ap.ArgumentParser(add_help=False)
_parser.add_argument("ep", nargs="?", default="45")
_parser.add_argument("guest", nargs="?", default="robertakang")
_parser.add_argument("--tagline", default=None,
                     help="Override tagline (instead of reading from YAML)")
_parser.add_argument("--tagline-highlight", default=None,
                     help="Override highlight phrases (pipe-delimited)")
_parser.add_argument("--out-dir", default=None,
                     help="Override output directory")
_args = _parser.parse_args()

_ep_arg = _args.ep
try:
    _ep_int = int(_ep_arg)
    EPISODE_ID = f"{_ep_int:02d}"
    EPISODE_DISPLAY = str(_ep_int)
    EPISODE_NUM = _ep_int                 # int for backward-compat / arithmetic
except ValueError:
    EPISODE_ID = _ep_arg                  # e.g. "23.5"
    EPISODE_DISPLAY = _ep_arg
    EPISODE_NUM = _ep_arg                 # str when non-int
GUEST_SLUG = _args.guest

REPO_ROOT = Path(__file__).resolve().parent.parent
EPISODE_DIR = REPO_ROOT / "hugosite" / "static" / "img" / "episode" / f"Episode{EPISODE_ID}"
# Variant subdirectories live directly under EPISODE_DIR (no thumbnails/
# wrapper) so Hugo can reference e.g. img/episode/Episode44/w1/podcast-cover.png
# directly from front-matter and templates.
OUT_DIR = Path(_args.out_dir) if _args.out_dir else EPISODE_DIR

PHOTO_SRC = EPISODE_DIR / "headshots" / f"{GUEST_SLUG}-nobg.png"
BALLOON_NO_SRC = EPISODE_DIR / "illustrations" / f"SIB_E{EPISODE_ID}_Balloon_no_overlay.png"
BALLOON_WITH_SRC = EPISODE_DIR / "illustrations" / f"SIB_E{EPISODE_ID}_Balloon_with_overlay.png"

if not PHOTO_SRC.exists():
    raise SystemExit(f"Missing headshot at {PHOTO_SRC}.")

# ---------------- palette ----------------------------------------------------

NAVY     = (10, 31, 61)
CORN     = (100, 149, 237)
CORN_D   = (59, 108, 192)
CREAM    = (244, 241, 234)
WHITE    = (255, 255, 255)
BLACK    = (0, 0, 0)
SMOKY    = (40, 42, 40)
SLATE_M  = (108, 117, 125)
DIARY_RED = (220, 38, 38)  # #dc2626 — DOAC-style highlight

# ---------------- fonts ------------------------------------------------------
#
# Match what Chrome resolved when the HTML version of this script set
# `font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;` on macOS:
# that maps to **SF Pro** (the macOS system font). SFNS.ttf is the variable
# OpenType font shipped with the OS — we pick weights via named variations.

SFNS_PATH = "/System/Library/Fonts/SFNS.ttf"
# (variation_name, fallback_helvetica_index)
SF_REGULAR = (b"Regular", 0)
SF_MEDIUM  = (b"Medium",  10)
SF_BOLD    = (b"Bold",    1)
SF_HEAVY   = (b"Heavy",   1)
SF_BLACK   = (b"Black",   9)

_FONT_CACHE: dict = {}
def font(face, size):
    """Load SF Pro at the named weight + given pixel size.
    Fails loudly if SF Pro isn't reachable — silent substitution would shift
    every glyph and break the carefully tuned layout."""
    var_name, _ = face
    size = int(size)
    key = (var_name, size)
    f = _FONT_CACHE.get(key)
    if f is None:
        f = ImageFont.truetype(SFNS_PATH, size)
        f.set_variation_by_name(var_name)
        _FONT_CACHE[key] = f
    return f


# Backwards-compat names so the layout code keeps reading.
HN_REGULAR = SF_REGULAR
HN_BOLD    = SF_BOLD
HN_BLACK   = SF_BLACK
HN_MEDIUM  = SF_MEDIUM

# ---------------- assets -----------------------------------------------------

_PHOTO = Image.open(PHOTO_SRC).convert("RGBA")
_BALLOON_NO   = Image.open(BALLOON_NO_SRC).convert("RGBA")   if BALLOON_NO_SRC.exists()   else None
_BALLOON_WITH = Image.open(BALLOON_WITH_SRC).convert("RGBA") if BALLOON_WITH_SRC.exists() else None

# ---------------- guest metadata --------------------------------------------

def _read_guest_meta(slug: str) -> tuple[str, str, str]:
    f = REPO_ROOT / "hugosite" / "content" / "guest" / f"{slug}.md"
    name = title_long = title_short = slug
    if f.exists():
        text = f.read_text()
        m = re.search(r'^Title\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if m:
            name = m.group(1)
    ep_md = REPO_ROOT / "hugosite" / "content" / "episode" / f"episode{EPISODE_DISPLAY}.md"
    if ep_md.exists():
        et = ep_md.read_text()
        tm = re.search(r'^title\s*=\s*"Episode\s*\d+\s*\|\s*[^|]+\|\s*([^"]+)"', et, re.MULTILINE)
        if tm:
            title_long = tm.group(1).strip()
            words = title_long.split()
            title_short = " ".join(words[:4])
    return name, title_long, title_short

GUEST_NAME, GUEST_TITLE, GUEST_TITLE_SHORT = _read_guest_meta(GUEST_SLUG)
print(f"Guest: {GUEST_NAME!r} / {GUEST_TITLE!r}")


def _read_episode_tagline() -> tuple[str, list[str]]:
    """Pull the provocative quote + highlight phrase(s) from the SIB episode
    metadata YAML at episodes/Episode<NN>/SIB_E<NN>_metadata.yaml. This is
    the canonical home of all SIB-internal episode metadata — never the
    Hugo .md frontmatter. Falls back to placeholder if missing so the
    `print` below makes it obvious.

    The `tagline_highlight` field accepts a single phrase ("optionality")
    OR a pipe-delimited list of phrases ("Cloudflare|threats") — every
    case-insensitive whole-phrase match in the tagline is rendered with the
    highlight treatment (red box for diary, color+underline for face-forward,
    etc.). Empty string → no highlights."""
    yaml_path = (
        REPO_ROOT / "episodes"
        / f"Episode{EPISODE_ID}"
        / f"SIB_E{EPISODE_ID}_metadata.yaml"
    )
    # CLI overrides take precedence over YAML.
    if _args.tagline:
        tagline = _args.tagline
        highlights = []
        if _args.tagline_highlight:
            highlights = [p.strip() for p in _args.tagline_highlight.split('|') if p.strip()]
        return tagline, highlights

    tagline = ""
    highlights: list[str] = []
    if yaml_path.exists():
        text = yaml_path.read_text()
        # Match both quoted and unquoted YAML tagline values.
        tm = re.search(r'^\s+tagline:\s*"([^"]+)"', text, re.MULTILINE)
        if not tm:
            tm = re.search(r'^\s+tagline:\s+(.+)$', text, re.MULTILINE)
        hm = re.search(r'^\s+tagline_highlight:\s*"?([^"\n]*)"?', text, re.MULTILINE)
        if tm:
            tagline = tm.group(1).strip()
        if hm:
            raw = hm.group(1).strip()
            highlights = [p.strip() for p in raw.split('|') if p.strip()]
    if not tagline:
        raise SystemExit(
            f"BLOCKED: No tagline found in {yaml_path}. "
            "Every episode/clip must have a tagline — thumbnail generation "
            "cannot proceed without one. Pass --tagline on the CLI or add "
            "'tagline: \"Your quote here\"' to the episode metadata YAML."
        )
    return tagline, highlights

QUOTE_TAGLINE, QUOTE_HIGHLIGHTS = _read_episode_tagline()
QUOTE_FULL_TEXT = f'"{QUOTE_TAGLINE}"'
print(f"Tagline: {QUOTE_FULL_TEXT}   highlights={QUOTE_HIGHLIGHTS!r}")


def _highlight_match_spans() -> list[tuple[int, int]]:
    """Return non-overlapping (start, end) byte spans in QUOTE_TAGLINE for
    every configured highlight, sorted by start. Earlier highlights win when
    spans overlap (later one is dropped)."""
    spans: list[tuple[int, int]] = []
    for phrase in QUOTE_HIGHLIGHTS:
        for m in re.finditer(r'\b' + re.escape(phrase) + r'\b',
                              QUOTE_TAGLINE, re.IGNORECASE):
            spans.append((m.start(), m.end()))
    # Sort by start, drop any overlapping with an earlier kept span.
    spans.sort()
    kept: list[tuple[int, int]] = []
    for s, e in spans:
        if kept and s < kept[-1][1]:
            continue
        kept.append((s, e))
    return kept


def _tagline_segments() -> list[tuple[str, bool]]:
    """Return [(text, is_highlight), ...] segments covering the full quoted
    tagline including the surrounding straight quotes. Non-highlight segments
    are flagged False; highlight segments True. If no highlights match,
    returns a single (full_quoted_text, False)."""
    spans = _highlight_match_spans()
    if not spans:
        return [(QUOTE_FULL_TEXT, False)]
    segs: list[tuple[str, bool]] = []
    cursor = 0
    parts: list[tuple[str, bool]] = []
    for s, e in spans:
        if s > cursor:
            parts.append((QUOTE_TAGLINE[cursor:s], False))
        parts.append((QUOTE_TAGLINE[s:e], True))
        cursor = e
    if cursor < len(QUOTE_TAGLINE):
        parts.append((QUOTE_TAGLINE[cursor:], False))
    # Stitch the surrounding quote marks onto the first/last non-highlight
    # segments. If the very first part is a highlight, prepend an opening
    # quote as its own segment; same for trailing.
    if parts[0][1]:
        segs.append(('"', False))
        segs.extend(parts)
    else:
        first_text, _ = parts[0]
        segs.append(('"' + first_text, False))
        segs.extend(parts[1:])
    if segs[-1][1]:
        segs.append(('"', False))
    else:
        last_text, last_hl = segs[-1]
        segs[-1] = (last_text + '"', last_hl)
    return segs


def quote_segs_for_face_forward(highlight_color: tuple, highlight_underline: bool):
    """3-tuple-style runs (text, color, underline) for the face-forward layouts
    where the quote is freeform inline text with one or more highlighted phrases."""
    segs = _tagline_segments()
    if len(segs) == 1 and not segs[0][1]:
        return [(segs[0][0], WHITE, False)]
    return [
        (text, highlight_color if is_hl else WHITE,
         highlight_underline if is_hl else False)
        for text, is_hl in segs
    ]

# ---------------- text helpers ----------------------------------------------

def text_size(draw, text, fnt):
    """Measure text using the 'lt' (left-top) anchor so width/height match
    the visible glyph extents — y positions then correspond to actual top
    pixels, which keeps inter-element gaps deterministic."""
    bbox = draw.textbbox((0, 0), text, font=fnt, anchor="lt")
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def shrink_to_fit(text, face, max_size, min_size, max_width, draw=None):
    """Return the largest font (≤ max_size, ≥ min_size) where the text fits in max_width."""
    if draw is None:
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    size = max_size
    while size > min_size:
        f = font(face, size)
        if text_size(draw, text, f)[0] <= max_width:
            return f
        size -= 1
    return font(face, min_size)

def wrap_to_width(text, fnt, max_width, draw=None):
    """Word-wrap text to a list of lines, each ≤ max_width wide."""
    if draw is None:
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        trial = w if not cur else f"{cur} {w}"
        if text_size(draw, trial, fnt)[0] <= max_width:
            cur = trial
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines or [text]

def _unpack_run(run):
    """Accept (text, font, color) OR (text, font, color, underline_bool)."""
    if len(run) == 4:
        return run
    text, fnt, color = run
    return text, fnt, color, False

def draw_runs(draw, anchor_xy, runs, anchor="lt"):
    """runs = [(text, font, color [, underline_bool]), ...]. Returns total width, max height.

    The supplied y is the visible TOP of the line (anchor='lt'-equivalent).
    Internally we render each segment via anchor='ls' (left-baseline) at a
    common baseline derived from the first run's font metrics, so segments
    that lack caps (e.g. 'customer') don't visually float above segments that
    have them (e.g. '"The demo is about the '). Each glyph's textbbox top
    differs by content; aligning baselines is what the eye expects."""
    runs = list(runs)
    if not runs:
        return 0, 0
    x, y = anchor_xy

    # Use the first run's font for baseline calculation. In practice all
    # runs in a single line share the same font; if that ever changes,
    # this picks the most likely tallest — fine for the common case.
    _, first_fnt, _, _ = _unpack_run(runs[0])
    ascent, descent = first_fnt.getmetrics()
    baseline_y = y + ascent

    total_w = 0
    for run in runs:
        text, fnt, color, underline = _unpack_run(run)
        draw.text((x + total_w, baseline_y), text, font=fnt, fill=color, anchor="ls")
        # Width measured at the same anchor used for layout (lt) so
        # widths are consistent with measure_runs / text_size.
        bbox = draw.textbbox((0, 0), text, font=fnt, anchor="lt")
        w = bbox[2] - bbox[0]
        if underline:
            # Underline thickness scales with font size; sit at a fixed
            # offset BELOW the common baseline + descent so it clears any
            # descender (g, p, comma, …) and stays at the same depth no
            # matter which segment carries the underline.
            full_h = ascent + descent
            ul_thick = max(2, round(full_h * 0.06))
            ul_y = baseline_y + descent + max(2, round(descent * 0.5))
            draw.rectangle(
                (x + total_w, ul_y, x + total_w + w, ul_y + ul_thick),
                fill=color,
            )
        total_w += w
    return total_w, ascent + descent

def measure_runs(draw, runs):
    runs = list(runs)
    if not runs:
        return 0, 0
    _, first_fnt, _, _ = _unpack_run(runs[0])
    ascent, descent = first_fnt.getmetrics()
    total_w = 0
    for run in runs:
        text, fnt, _, _ = _unpack_run(run)
        bbox = draw.textbbox((0, 0), text, font=fnt, anchor="lt")
        total_w += bbox[2] - bbox[0]
    return total_w, ascent + descent

# ---------------- shape / image helpers --------------------------------------

def linear_gradient(size, c1, c2, angle_deg=90):
    """RGB gradient image. angle 0=L→R, 90=T→B, 135=TL→BR."""
    w, h = size
    rad = np.deg2rad(angle_deg)
    dx, dy = np.cos(rad), np.sin(rad)
    xs = np.arange(w)
    ys = np.arange(h)
    xx, yy = np.meshgrid(xs, ys)
    proj = xx * dx + yy * dy
    proj = (proj - proj.min()) / (proj.max() - proj.min() + 1e-9)
    arr = np.empty((h, w, 3), dtype=np.uint8)
    for i in range(3):
        arr[:, :, i] = c1[i] + (c2[i] - c1[i]) * proj
    return Image.fromarray(arr, "RGB")

def fill_solid(size, color):
    return Image.new("RGB", size, color)

def paste_image(canvas, img, xy):
    """Paste RGBA img onto canvas (RGB or RGBA) using img's alpha."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    canvas.paste(img, xy, img)

def fit_cover(img, box):
    """Return img resized to COVER box (cropping overflow). box=(w,h)."""
    bw, bh = box
    iw, ih = img.size
    scale = max(bw / iw, bh / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    r = img.resize((nw, nh), Image.LANCZOS)
    cx, cy = (nw - bw) // 2, (nh - bh) // 2
    return r.crop((cx, cy, cx + bw, cy + bh))

def fit_contain(img, box):
    """Return img resized to fit INSIDE box maintaining aspect."""
    bw, bh = box
    iw, ih = img.size
    scale = min(bw / iw, bh / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    return img.resize((nw, nh), Image.LANCZOS)

def circle_mask(size):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size, size), fill=255)
    return m

def make_photo_circle(src_img, diameter, ring_color=None, ring_width=0, fill_bg=None):
    """Crop src to a circle of given diameter; optional outer ring + bg fill behind transparent areas."""
    d = int(diameter)
    cropped = fit_cover(src_img.convert("RGBA"), (d, d))
    if fill_bg is not None:
        bg = Image.new("RGBA", (d, d), fill_bg + (255,))
        bg.paste(cropped, (0, 0), cropped)
        cropped = bg
    out = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    out.paste(cropped, (0, 0), circle_mask(d))
    if ring_color is not None and ring_width > 0:
        # Draw ring on a slightly larger canvas
        rw = int(ring_width)
        big = Image.new("RGBA", (d + 2 * rw, d + 2 * rw), (0, 0, 0, 0))
        ring = Image.new("L", big.size, 0)
        ImageDraw.Draw(ring).ellipse((0, 0, big.size[0], big.size[1]), fill=255)
        big.paste(Image.new("RGBA", big.size, ring_color + (255,)), (0, 0), ring)
        big.paste(out, (rw, rw), out)
        return big
    return out

def rounded_rect_outline(canvas, box, radius, color, width):
    ImageDraw.Draw(canvas).rounded_rectangle(box, radius=radius, outline=color, width=width)

def rounded_rect_fill(canvas, box, radius, fill):
    ImageDraw.Draw(canvas).rounded_rectangle(box, radius=radius, fill=fill)

def rounded_translucent_fill(canvas, box, radius, rgba):
    """Alpha-composite a rounded-rectangle translucent fill onto the canvas
    (so the corners match a rounded outline drawn over it)."""
    x0, y0, x1, y1 = box
    w_ = max(1, x1 - x0)
    h_ = max(1, y1 - y0)
    layer = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((0, 0, w_ - 1, h_ - 1),
                                             radius=radius, fill=rgba)
    canvas.alpha_composite(layer, (x0, y0))

# ---------------- aspect classification --------------------------------------

def aspect_kind(w, h):
    r = w / h
    if abs(r - 1.0) < 0.05:
        return "square"
    if 0.5 < r < 0.7:
        return "vertical"
    if r < 2.0:
        return "wide"
    return "banner"

# ---------------- core layout: face-forward (A1, A2, A3, plus *w) -----------

def _bg_for_a(variant_base, size):
    if variant_base == "a2":
        return linear_gradient(size, CORN, CORN_D, angle_deg=135)
    return fill_solid(size, NAVY)

def _photo_for_a(variant):
    return _BALLOON_NO if variant in ("a1w", "a2w", "a3w") else _PHOTO

def _ring_for_a(variant_base):
    return CORN if variant_base in ("a1", "a3") else WHITE

def _ep_blue_color(variant_base):
    return CORN if variant_base in ("a1", "a3") else WHITE

def render_face_forward(variant, w, h):
    """A1, A2 — quote vertically centered, photo circle right (wide/banner) or top-stacked (square/vertical)."""
    base = variant.rstrip("w") if variant in ("a1w", "a2w") else variant
    kind = aspect_kind(w, h)
    s = min(w, h) / 270.0
    canvas = _bg_for_a(base, (w, h)).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    photo_src = _photo_for_a(variant)
    ring = _ring_for_a(base)
    ep_color = _ep_blue_color(base)

    if kind in ("wide", "banner"):
        pad_h = max(round(22 * s), 14)
        pad_v = max(round(14 * s), 10)
        gap = max(round(18 * s), 12)
        photo_d = round(140 * s)
        photo_cx = w - pad_h - photo_d // 2
        photo_cy = h // 2

        # photo circle on right, vertically centered
        ring_w = max(round(4 * s), 2)
        circle = make_photo_circle(photo_src, photo_d, ring_color=ring, ring_width=ring_w,
                                    fill_bg=ring if base != "a2" else WHITE)
        paste_image(canvas, circle, (photo_cx - circle.size[0] // 2, photo_cy - circle.size[1] // 2))

        text_x = pad_h
        text_max_w = photo_cx - photo_d // 2 - gap - text_x

        # brand row at top
        title_size = max(round(15 * s), 12)
        ep_size    = max(round(9 * s),  8)
        f_title = font(HN_BOLD, title_size)
        f_ep    = font(HN_BOLD, ep_size)
        runs_brand = [
            ("Can I get that software ", f_title, WHITE),
            ("in blue?",                  f_title, ep_color),
        ]
        # Shrink-to-fit the brand row to ensure no clipping.
        while measure_runs(draw, runs_brand)[0] > text_max_w and title_size > 10:
            title_size -= 1
            f_title = font(HN_BOLD, title_size)
            runs_brand = [
                ("Can I get that software ", f_title, WHITE),
                ("in blue?",                  f_title, ep_color),
            ]
        draw_runs(draw, (text_x, pad_v), runs_brand)
        ep_y = pad_v + f_title.getmetrics()[0] + max(round(6 * s), 4)
        draw.text((text_x, ep_y), f"EPISODE #{EPISODE_DISPLAY}", font=f_ep, fill=WHITE, anchor="lt")
        brand_bottom = ep_y + f_ep.getmetrics()[0]

        # footer at bottom
        footer_size = max(round(10 * s), 8)
        f_foot = font(HN_REGULAR, footer_size)
        footer_text = "@softwareinblue · softwareinblue.com"
        foot_y = h - pad_v - text_size(draw, footer_text, f_foot)[1]
        draw.text((text_x, foot_y), footer_text, font=f_foot, fill=WHITE, anchor="lt")

        # guest just above footer
        name_size   = max(round(13 * s), 10)
        gtitle_size = max(round(9.5 * s), 8)
        f_name  = font(HN_BOLD, name_size)
        f_gt    = font(HN_REGULAR, gtitle_size)
        # Shrink guest title if too wide
        while text_size(draw, GUEST_TITLE, f_gt)[0] > text_max_w and gtitle_size > 7:
            gtitle_size -= 1
            f_gt = font(HN_REGULAR, gtitle_size)
        gtitle_h = text_size(draw, GUEST_TITLE, f_gt)[1]
        gname_h  = text_size(draw, GUEST_NAME,  f_name)[1]
        gt_y = foot_y - max(round(8 * s), 4) - gtitle_h
        gn_y = gt_y - gname_h - max(round(5 * s), 4)
        draw.text((text_x, gn_y), GUEST_NAME, font=f_name, fill=WHITE, anchor="lt")
        draw.text((text_x, gt_y), GUEST_TITLE, font=f_gt, fill=(220, 220, 230), anchor="lt")

        # quote — vertically centered between brand row and guest block.
        # On a2 (cornflower bg) the highlight word can't be cornflower, so
        # render it white + underlined for emphasis instead.
        quote_top    = brand_bottom + max(round(20 * s), 8)
        quote_bottom = gn_y - max(round(12 * s), 6)
        avail_h = max(40, quote_bottom - quote_top)
        quote_size = max(round(20 * s), 14)
        if base == "a2":
            quote_segs = quote_segs_for_face_forward(WHITE, True)
        else:
            quote_segs = quote_segs_for_face_forward(CORN, False)
        def _bind(rsize):
            qf = font(HN_BLACK, rsize)
            return [(t, qf, c, u) for t, c, u in quote_segs]
        bound = _bind(quote_size)
        while quote_size > 14 and measure_runs(draw, bound)[0] > text_max_w:
            quote_size -= 1
            bound = _bind(quote_size)
        qw, qh = measure_runs(draw, bound)
        qy = quote_top + (avail_h - qh) // 2
        draw_runs(draw, (text_x, qy), bound)
        return canvas

    # ----- square / vertical (single-column stack) -----
    pad = max(round(14 * s), 10)
    if kind == "vertical":
        # 9:16 has lots of vertical real estate — bump everything up.
        title_size  = max(round(22 * s), 14)
        ep_size     = max(round(14 * s), 11)
        name_size   = max(round(17 * s), 12)
        gtitle_size = max(round(13 * s), 10)
        footer_size = max(round(10 * s),  8)
        quote_size  = max(round(20 * s), 14)
        photo_d     = round(135 * s)
    else:  # square
        title_size  = max(round(13 * s), 10)
        ep_size     = max(round(9 * s),  8)
        name_size   = max(round(11 * s), 8)
        gtitle_size = max(round(9 * s),  7)
        footer_size = max(round(9 * s),  7)
        quote_size  = max(round(16 * s), 12)
        photo_d     = round(100 * s)

    f_title = font(HN_BOLD, title_size)
    f_ep    = font(HN_BOLD, ep_size)
    f_name  = font(HN_BOLD, name_size)
    f_gt    = font(HN_REGULAR, gtitle_size)
    f_foot  = font(HN_REGULAR, footer_size)

    avail_w = w - 2 * pad

    runs_brand = [("Can I get that software ", f_title, WHITE), ("in blue?", f_title, ep_color)]
    while measure_runs(draw, runs_brand)[0] > avail_w and title_size > 10:
        title_size -= 1
        f_title = font(HN_BOLD, title_size)
        runs_brand = [("Can I get that software ", f_title, WHITE), ("in blue?", f_title, ep_color)]
    if base == "a2":
        runs_quote_segs = quote_segs_for_face_forward(WHITE, True)
    else:
        runs_quote_segs = quote_segs_for_face_forward(CORN, False)
    def _bind_q(qs):
        qf = font(HN_BLACK, qs)
        return [(t, qf, c, u) for t, c, u in runs_quote_segs]
    runs_quote = _bind_q(quote_size)
    while measure_runs(draw, runs_quote)[0] > avail_w and quote_size > 14:
        quote_size -= 1
        runs_quote = _bind_q(quote_size)

    # Heights
    brand_h = f_title.getmetrics()[0] + max(round(6 * s), 4) + f_ep.getmetrics()[0]
    quote_h = measure_runs(draw, runs_quote)[1]
    name_h  = text_size(draw, GUEST_NAME, f_name)[1]
    gt_h    = text_size(draw, GUEST_TITLE_SHORT, f_gt)[1]
    foot_h  = text_size(draw, "softwareinblue.com", f_foot)[1]

    # Pinned-edges layout: brand pinned to pad-top, footer pinned to pad-bot.
    # Photo / quote / guest distributed with EQUAL gaps between them so the
    # space above and below the photo circle is identical.
    name_gt_gap = max(round(5 * s), 4)
    guest_h = name_h + name_gt_gap + gt_h
    foot_text = "@softwareinblue · softwareinblue.com"

    brand_top = pad
    foot_top  = h - pad - foot_h

    # Brand (centered) at the top
    bw, _ = measure_runs(draw, runs_brand)
    draw_runs(draw, ((w - bw) // 2, brand_top), runs_brand)
    ep_y = brand_top + f_title.getmetrics()[0] + max(round(6 * s), 4)
    ep_text = f"EPISODE #{EPISODE_DISPLAY}"
    ep_w, _ = text_size(draw, ep_text, f_ep)
    draw.text(((w - ep_w) // 2, ep_y), ep_text, font=f_ep, fill=WHITE, anchor="lt")
    brand_bottom = brand_top + brand_h

    # Distribute photo, quote, guest in the middle band
    mid_top = brand_bottom
    mid_bot = foot_top
    mid_rows = [photo_d, quote_h, guest_h]
    mid_leftover = max(0, (mid_bot - mid_top) - sum(mid_rows))
    g = mid_leftover // (len(mid_rows) + 1)
    y = mid_top + g

    # Photo circle (centered) — gap above (g, from brand_bottom) ==
    # gap below (g, to top of quote).
    ring_w = max(round(4 * s), 2)
    circle = make_photo_circle(photo_src, photo_d, ring_color=ring, ring_width=ring_w,
                               fill_bg=ring if base != "a2" else WHITE)
    paste_image(canvas, circle, ((w - circle.size[0]) // 2, y - ring_w))
    y += photo_d + g

    # Quote (centered)
    qw, _ = measure_runs(draw, runs_quote)
    draw_runs(draw, ((w - qw) // 2, y), runs_quote)
    y += quote_h + g

    # Guest (centered)
    nw, _ = text_size(draw, GUEST_NAME, f_name)
    draw.text(((w - nw) // 2, y), GUEST_NAME, font=f_name, fill=WHITE, anchor="lt")
    gtw, _ = text_size(draw, GUEST_TITLE_SHORT, f_gt)
    draw.text(((w - gtw) // 2, y + name_h + name_gt_gap),
              GUEST_TITLE_SHORT, font=f_gt, fill=(220, 220, 230), anchor="lt")

    # Footer pinned to bottom
    fw, _ = text_size(draw, foot_text, f_foot)
    draw.text(((w - fw) // 2, foot_top), foot_text, font=f_foot, fill=WHITE, anchor="lt")

    return canvas


def render_face_forward_bottom(variant, w, h):
    """A3 / A3w — quote → guest → source → footer (source moved to bottom)."""
    base = "a3"
    kind = aspect_kind(w, h)
    s = min(w, h) / 270.0
    canvas = fill_solid((w, h), NAVY).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    photo_src = _BALLOON_NO if variant == "a3w" else _PHOTO
    ring = CORN

    if kind in ("wide", "banner"):
        pad_h = max(round(22 * s), 14)
        pad_v = max(round(14 * s), 10)
        gap   = max(round(18 * s), 12)
        photo_d = round(140 * s)
        photo_cx = w - pad_h - photo_d // 2
        photo_cy = h // 2
        ring_w = max(round(4 * s), 2)
        circle = make_photo_circle(photo_src, photo_d, ring_color=ring, ring_width=ring_w, fill_bg=ring)
        paste_image(canvas, circle, (photo_cx - circle.size[0] // 2, photo_cy - circle.size[1] // 2))

        text_x = pad_h
        text_max_w = photo_cx - photo_d // 2 - gap - text_x

        # quote at top
        quote_size = max(round(20 * s), 14)
        runs_quote_segs = quote_segs_for_face_forward(CORN, False)
        def bind(qs):
            f = font(HN_BLACK, qs)
            return [(t, f, c, u) for t, c, u in runs_quote_segs]
        bq = bind(quote_size)
        while measure_runs(draw, bq)[0] > text_max_w and quote_size > 14:
            quote_size -= 1
            bq = bind(quote_size)
        qw, qh = measure_runs(draw, bq)
        draw_runs(draw, (text_x, pad_v), bq)

        # footer at bottom
        footer_size = max(round(10 * s), 8)
        f_foot = font(HN_REGULAR, footer_size)
        ftext = "@softwareinblue · softwareinblue.com"
        foot_y = h - pad_v - text_size(draw, ftext, f_foot)[1]
        draw.text((text_x, foot_y), ftext, font=f_foot, fill=WHITE, anchor="lt")

        # source = brand title + episode # — sits just above footer
        title_size = max(round(15 * s), 12)
        ep_size    = max(round(9 * s),  8)
        f_title = font(HN_BOLD, title_size)
        f_ep    = font(HN_BOLD, ep_size)
        runs_brand = [("Can I get that software ", f_title, WHITE), ("in blue?", f_title, CORN)]
        while measure_runs(draw, runs_brand)[0] > text_max_w and title_size > 10:
            title_size -= 1
            f_title = font(HN_BOLD, title_size)
            runs_brand = [("Can I get that software ", f_title, WHITE), ("in blue?", f_title, CORN)]
        ep_text = f"EPISODE #{EPISODE_DISPLAY}"
        ep_h    = f_ep.getmetrics()[0]
        title_h = f_title.getmetrics()[0]
        src_block_h = title_h + max(round(6 * s), 4) + ep_h
        src_y = foot_y - max(round(8 * s), 4) - src_block_h
        draw_runs(draw, (text_x, src_y), runs_brand)
        draw.text((text_x, src_y + title_h + max(round(6 * s), 4)), ep_text, font=f_ep, fill=WHITE, anchor="lt")

        # guest centered between quote and source
        name_size   = max(round(13 * s), 10)
        gtitle_size = max(round(9.5 * s), 8)
        f_name = font(HN_BOLD, name_size)
        f_gt   = font(HN_REGULAR, gtitle_size)
        while text_size(draw, GUEST_TITLE, f_gt)[0] > text_max_w and gtitle_size > 7:
            gtitle_size -= 1
            f_gt = font(HN_REGULAR, gtitle_size)
        gname_h = text_size(draw, GUEST_NAME, f_name)[1]
        gt_h    = text_size(draw, GUEST_TITLE, f_gt)[1]
        guest_block_h = gname_h + max(round(5 * s), 4) + gt_h
        avail_top    = pad_v + qh + max(round(12 * s), 6)
        avail_bottom = src_y - max(round(12 * s), 6)
        avail_h      = max(0, avail_bottom - avail_top)
        gn_y = avail_top + (avail_h - guest_block_h) // 2
        draw.text((text_x, gn_y), GUEST_NAME, font=f_name, fill=WHITE, anchor="lt")
        draw.text((text_x, gn_y + gname_h + max(round(5 * s), 4)),
                  GUEST_TITLE, font=f_gt, fill=(220, 220, 230), anchor="lt")
        return canvas

    # ----- square / vertical -----
    pad = max(round(14 * s), 10)
    if kind == "vertical":
        title_size  = max(round(22 * s), 14)
        ep_size     = max(round(14 * s), 11)
        name_size   = max(round(18 * s), 12)
        gtitle_size = max(round(13 * s), 10)
        footer_size = max(round(10 * s),  8)
        quote_size  = max(round(20 * s), 14)
        photo_d     = round(120 * s)
    else:  # square
        title_size  = max(round(13 * s), 10)
        ep_size     = max(round(9 * s),  8)
        name_size   = max(round(12 * s), 9)
        gtitle_size = max(round(9 * s),  7)
        footer_size = max(round(9 * s),  7)
        quote_size  = max(round(16 * s), 12)
        photo_d     = round(90 * s)

    f_title = font(HN_BOLD, title_size)
    f_ep    = font(HN_BOLD, ep_size)
    f_name  = font(HN_BOLD, name_size)
    f_gt    = font(HN_REGULAR, gtitle_size)
    f_foot  = font(HN_REGULAR, footer_size)

    avail_w = w - 2 * pad

    runs_quote_segs = quote_segs_for_face_forward(CORN, False)
    def bind(qs):
        f = font(HN_BLACK, qs)
        return [(t, f, c, u) for t, c, u in runs_quote_segs]
    runs_quote = bind(quote_size)
    while measure_runs(draw, runs_quote)[0] > avail_w and quote_size > 14:
        quote_size -= 1
        runs_quote = bind(quote_size)

    runs_brand = [("Can I get that software ", f_title, WHITE), ("in blue?", f_title, CORN)]
    while measure_runs(draw, runs_brand)[0] > avail_w and title_size > 10:
        title_size -= 1
        f_title = font(HN_BOLD, title_size)
        runs_brand = [("Can I get that software ", f_title, WHITE), ("in blue?", f_title, CORN)]

    quote_h = measure_runs(draw, runs_quote)[1]
    name_h  = text_size(draw, GUEST_NAME, f_name)[1]
    gt_h    = text_size(draw, GUEST_TITLE_SHORT, f_gt)[1]
    title_h = f_title.getmetrics()[0]
    ep_h    = f_ep.getmetrics()[0]
    foot_h  = text_size(draw, "softwareinblue.com", f_foot)[1]

    # Pinned-edges layout: quote pinned to pad-top, footer pinned to pad-bot.
    # Guest / photo / source distributed with EQUAL gaps so the space above
    # and below the photo circle is identical.
    name_gt_gap = max(round(5 * s), 4)
    ep_gap      = max(round(6 * s), 4)
    guest_h = name_h + name_gt_gap + gt_h
    src_h   = title_h + ep_gap + ep_h
    foot_text = "@softwareinblue · softwareinblue.com"

    quote_top = pad
    foot_top  = h - pad - foot_h

    # Quote at top (centered)
    qw, _ = measure_runs(draw, runs_quote)
    draw_runs(draw, ((w - qw) // 2, quote_top), runs_quote)
    quote_bottom = quote_top + quote_h

    mid_top = quote_bottom
    mid_bot = foot_top
    mid_rows = [guest_h, photo_d, src_h]
    mid_leftover = max(0, (mid_bot - mid_top) - sum(mid_rows))
    g = mid_leftover // (len(mid_rows) + 1)
    y = mid_top + g

    # Guest
    nw, _ = text_size(draw, GUEST_NAME, f_name)
    draw.text(((w - nw) // 2, y), GUEST_NAME, font=f_name, fill=WHITE, anchor="lt")
    gtw, _ = text_size(draw, GUEST_TITLE_SHORT, f_gt)
    draw.text(((w - gtw) // 2, y + name_h + name_gt_gap),
              GUEST_TITLE_SHORT, font=f_gt, fill=(220, 220, 230), anchor="lt")
    y += guest_h + g

    # Photo — gap above (g) == gap below (g).
    ring_w = max(round(4 * s), 2)
    circle = make_photo_circle(photo_src, photo_d, ring_color=ring, ring_width=ring_w, fill_bg=ring)
    paste_image(canvas, circle, ((w - circle.size[0]) // 2, y - ring_w))
    y += photo_d + g

    # Source (brand title + episode #)
    bw, _ = measure_runs(draw, runs_brand)
    draw_runs(draw, ((w - bw) // 2, y), runs_brand)
    ep_text = f"EPISODE #{EPISODE_DISPLAY}"
    epw, _ = text_size(draw, ep_text, f_ep)
    draw.text(((w - epw) // 2, y + title_h + ep_gap), ep_text, font=f_ep, fill=WHITE, anchor="lt")

    # Footer pinned to bottom
    fw, _ = text_size(draw, foot_text, f_foot)
    draw.text(((w - fw) // 2, foot_top), foot_text, font=f_foot, fill=WHITE, anchor="lt")

    return canvas

# ---------------- magazine split (C1, C2, C3) --------------------------------

def _c_palette(variant):
    # (text-panel-bg, text-color, ep-blue-color, photo-panel-bg, quote-border, name-color, gtitle-color)
    if variant == "c1":
        return (CREAM, NAVY, CORN, CORN, CORN, NAVY, SLATE_M)
    if variant == "c2":
        return (CORN,  WHITE, WHITE, NAVY, WHITE, WHITE, (235, 235, 240))
    # c3
    return (NAVY, WHITE, CORN, CORN, CORN, WHITE, (220, 220, 230))

def render_magazine(variant, w, h):
    kind = aspect_kind(w, h)
    s = min(w, h) / 270.0
    text_bg, text_color, ep_color, photo_bg, qb_color, name_color, gtitle_color = _c_palette(variant)

    canvas = Image.new("RGB", (w, h), text_bg).convert("RGBA")

    if kind in ("wide", "banner"):
        # text left ~62%, photo right ~38%
        text_w = round(w * 0.62)
        photo_w = w - text_w
        # paint right photo panel
        photo_panel = Image.new("RGB", (photo_w, h), photo_bg)
        photo_img = fit_cover(_PHOTO.convert("RGBA"), (photo_w, h))
        photo_panel.paste(photo_img.convert("RGBA"), (0, 0), photo_img)
        canvas.paste(photo_panel, (text_w, 0))

        pad_h = max(round(22 * s), 14)
        pad_v = max(round(18 * s), 12)

        title_size = max(round(14 * s), 12)
        ep_size    = max(round(9 * s), 8)
        name_size  = max(round(13 * s), 10)
        gtitle_size= max(round(9.5 * s), 8)
        quote_size = max(round(16 * s), 14)
        f_title = font(HN_BOLD, title_size)
        f_ep    = font(HN_BOLD, ep_size)
        f_name  = font(HN_BOLD, name_size)
        f_gt    = font(HN_REGULAR, gtitle_size)
        f_quote = font(HN_BLACK, quote_size)

        text_max_w = text_w - 2 * pad_h
        # brand
        runs_brand = [("Can I get that software ", f_title, text_color), ("in blue?", f_title, ep_color)]
        while measure_runs(ImageDraw.Draw(canvas), runs_brand)[0] > text_max_w and title_size > 10:
            title_size -= 1
            f_title = font(HN_BOLD, title_size)
            runs_brand = [("Can I get that software ", f_title, text_color), ("in blue?", f_title, ep_color)]
        draw = ImageDraw.Draw(canvas)
        draw_runs(draw, (pad_h, pad_v), runs_brand)
        ep_y = pad_v + f_title.getmetrics()[0] + max(round(6*s), 4)
        draw.text((pad_h, ep_y), f"EPISODE #{EPISODE_DISPLAY}", font=f_ep, fill=text_color, anchor="lt")

        # quote box (centered horizontally in text panel)
        quote_text = QUOTE_FULL_TEXT
        # shrink so it fits one line within ~95% of text panel width minus padding
        avail_q = int(text_max_w * 0.95)
        while text_size(draw, quote_text, f_quote)[0] > avail_q and quote_size > 14:
            quote_size -= 1
            f_quote = font(HN_BLACK, quote_size)
        qw, qh = text_size(draw, quote_text, f_quote)
        qpad_v = max(round(10 * s), 6)
        qpad_h = max(round(14 * s), 8)
        radius = max(round(12 * s), 6)
        border = max(round(3 * s), 2)
        box_w = qw + 2 * qpad_h
        box_h = qh + 2 * qpad_v
        box_x = pad_h + (text_max_w - box_w) // 2
        box_y = (h - box_h) // 2
        rounded_rect_outline(canvas, (box_x, box_y, box_x + box_w, box_y + box_h),
                             radius=radius, color=qb_color, width=border)
        draw.text((box_x + qpad_h, box_y + qpad_v), quote_text, font=f_quote, fill=text_color, anchor="lt")

        # guest at bottom
        gtitle_text = GUEST_TITLE
        while text_size(draw, gtitle_text, f_gt)[0] > text_max_w and gtitle_size > 7:
            gtitle_size -= 1
            f_gt = font(HN_REGULAR, gtitle_size)
        name_h = text_size(draw, GUEST_NAME, f_name)[1]
        gt_h   = text_size(draw, gtitle_text, f_gt)[1]
        gn_y = h - pad_v - name_h - max(round(5*s), 4) - gt_h
        draw.text((pad_h, gn_y), GUEST_NAME, font=f_name, fill=name_color, anchor="lt")
        draw.text((pad_h, gn_y + name_h + max(round(5*s), 4)),
                  gtitle_text, font=f_gt, fill=gtitle_color, anchor="lt")
        return canvas

    # ---- square / vertical ----
    # text on top (~62%), photo bottom (~38%)
    text_h = round(h * 0.62)
    photo_h = h - text_h
    photo_panel = Image.new("RGB", (w, photo_h), photo_bg)
    photo_img = fit_contain(_PHOTO.convert("RGBA"), (w, photo_h))
    px = (w - photo_img.size[0]) // 2
    py = (photo_h - photo_img.size[1]) // 2
    panel_canvas = Image.new("RGBA", (w, photo_h), photo_bg + (255,))
    panel_canvas.paste(photo_img, (px, py), photo_img)
    canvas.paste(panel_canvas, (0, text_h))

    pad = max(round(18 * s), 12)
    pad_h = max(round(18 * s), 12)
    title_size = max(round(12 * s), 10)
    ep_size    = max(round(8 * s),  8)
    name_size  = max(round(11 * s), 8)
    gtitle_size= max(round(8.5 * s), 7)
    quote_size = max(round(16 * s), 12)

    f_title = font(HN_BOLD, title_size)
    f_ep    = font(HN_BOLD, ep_size)
    f_name  = font(HN_BOLD, name_size)
    f_gt    = font(HN_REGULAR, gtitle_size)
    f_quote = font(HN_BLACK, quote_size)

    draw = ImageDraw.Draw(canvas)
    text_max_w = w - 2 * pad_h

    # brand at top
    runs_brand = [("Can I get that software ", f_title, text_color), ("in blue?", f_title, ep_color)]
    while measure_runs(draw, runs_brand)[0] > text_max_w and title_size > 10:
        title_size -= 1
        f_title = font(HN_BOLD, title_size)
        runs_brand = [("Can I get that software ", f_title, text_color), ("in blue?", f_title, ep_color)]
    draw_runs(draw, (pad_h, pad), runs_brand)
    title_h = f_title.getmetrics()[0]
    ep_y = pad + title_h + max(round(6*s), 4)
    draw.text((pad_h, ep_y), f"EPISODE #{EPISODE_DISPLAY}", font=f_ep, fill=text_color, anchor="lt")
    brand_bottom = ep_y + f_ep.getmetrics()[0]

    # quote box (centered), nestles in middle of text panel
    quote_text = QUOTE_FULL_TEXT
    avail_q = int(text_max_w * 0.95)
    while text_size(draw, quote_text, f_quote)[0] > avail_q and quote_size > 12:
        quote_size -= 1
        f_quote = font(HN_BLACK, quote_size)
    qw, qh = text_size(draw, quote_text, f_quote)
    qpad_v = max(round(10 * s), 6)
    qpad_h = max(round(14 * s), 8)
    radius = max(round(12 * s), 6)
    border = max(round(2.5 * s), 2)
    box_w = qw + 2 * qpad_h
    box_h = qh + 2 * qpad_v

    # guest sits below quote, before the photo panel
    gtitle_text = GUEST_TITLE_SHORT
    name_h = text_size(draw, GUEST_NAME, f_name)[1]
    gt_h   = text_size(draw, gtitle_text, f_gt)[1]

    # vertically distribute brand/quote/guest in [pad..text_h-pad]
    avail_top = brand_bottom + max(round(8*s), 4)
    avail_bot = text_h - pad
    rows = [box_h, name_h + max(round(2*s),1) + gt_h]
    leftover = max(0, (avail_bot - avail_top) - sum(rows))
    g = leftover // (len(rows) + 1)
    y = avail_top + g
    box_x = (w - box_w) // 2
    rounded_rect_outline(canvas, (box_x, y, box_x + box_w, y + box_h),
                         radius=radius, color=qb_color, width=border)
    draw.text((box_x + qpad_h, y + qpad_v), quote_text, font=f_quote, fill=text_color, anchor="lt")
    y += box_h + g

    nw, _ = text_size(draw, GUEST_NAME, f_name)
    draw.text(((w - nw) // 2, y), GUEST_NAME, font=f_name, fill=name_color, anchor="lt")
    gtw, _ = text_size(draw, gtitle_text, f_gt)
    draw.text(((w - gtw) // 2, y + name_h + max(round(5*s), 4)),
              gtitle_text, font=f_gt, fill=gtitle_color, anchor="lt")

    return canvas

# ---------------- whimsical (W1, W2) ----------------------------------------

def _w_palette(variant):
    if variant == "w2":
        # navy panel, cornflower accent
        return (NAVY, NAVY, CORN, CORN)  # (panel_top, panel_bottom, badge_bg, quote_border)
    return (CORN, CORN_D, NAVY, WHITE)   # cornflower→darker gradient panel, navy badge, white border

def render_whimsical(variant, w, h):
    kind = aspect_kind(w, h)
    s = min(w, h) / 270.0
    panel_top, panel_bot, badge_bg, quote_border = _w_palette(variant)

    if kind in ("wide", "banner"):
        # left: text panel (gradient or solid). right: balloon-with-overlay full bleed.
        canvas = Image.new("RGB", (w, h), panel_top).convert("RGBA")
        if variant == "w2":
            # solid navy panel — gradient is identity here, just fill
            pass
        else:
            grad = linear_gradient((w, h), panel_top, panel_bot, angle_deg=135)
            canvas.paste(grad, (0, 0))
        # right square panel — width == h
        right_w = h
        right_x = w - right_w
        if _BALLOON_WITH is not None:
            cover = fit_cover(_BALLOON_WITH.convert("RGBA"), (right_w, h))
            paste_image(canvas, cover, (right_x, 0))
        else:
            ImageDraw.Draw(canvas).rectangle((right_x, 0, w, h), fill=CORN)

        text_max_w = right_x - 2 * max(round(22 * s), 14)
        pad_h = max(round(22 * s), 14)
        pad_v = max(round(18 * s), 12)

        # episode badge top
        ep_size = max(round(10 * s), 8)
        f_ep = font(HN_BOLD, ep_size)
        ep_text = f"EPISODE #{EPISODE_DISPLAY}"
        ew, eh = text_size(ImageDraw.Draw(canvas), ep_text, f_ep)
        bpad_v = max(round(4 * s), 3)
        bpad_h = max(round(10 * s), 6)
        badge_w = ew + 2 * bpad_h
        badge_h = eh + 2 * bpad_v
        rounded_rect_fill(canvas, (pad_h, pad_v, pad_h + badge_w, pad_v + badge_h),
                          radius=badge_h // 2, fill=badge_bg)
        ImageDraw.Draw(canvas).text((pad_h + bpad_h, pad_v + bpad_v),
                                     ep_text, font=f_ep, fill=WHITE, anchor="lt")

        # quote box vertically centered
        quote_text = QUOTE_FULL_TEXT
        quote_size = max(round(18 * s), 12)
        f_quote = font(HN_BLACK, quote_size)
        draw = ImageDraw.Draw(canvas)
        avail_q = int(text_max_w * 0.95)
        while text_size(draw, quote_text, f_quote)[0] > avail_q and quote_size > 12:
            quote_size -= 1
            f_quote = font(HN_BLACK, quote_size)
        qw, qh = text_size(draw, quote_text, f_quote)
        qpad_v = max(round(10 * s), 6)
        qpad_h = max(round(14 * s), 8)
        radius = max(round(12 * s), 6)
        border = max(round(3 * s), 2)
        box_w = qw + 2 * qpad_h
        box_h = qh + 2 * qpad_v
        box_x = pad_h + (text_max_w - box_w) // 2
        box_y = (h - box_h) // 2
        # navy translucent fill — rounded to match the outline corners
        rounded_translucent_fill(canvas, (box_x, box_y, box_x + box_w, box_y + box_h),
                                 radius=radius, rgba=(10, 31, 61, 200))
        rounded_rect_outline(canvas, (box_x, box_y, box_x + box_w, box_y + box_h),
                             radius=radius, color=quote_border, width=border)
        draw.text((box_x + qpad_h, box_y + qpad_v), quote_text, font=f_quote, fill=WHITE, anchor="lt")

        # guest line + url at bottom
        name_size   = max(round(12 * s), 10)
        gtitle_size = max(round(9.5 * s), 8)
        url_size    = max(round(10 * s),  8)
        f_name = font(HN_BOLD, name_size)
        f_gt   = font(HN_REGULAR, gtitle_size)
        f_url  = font(HN_BOLD, url_size)
        url_text = "softwareinblue.com"
        url_h = text_size(draw, url_text, f_url)[1]
        name_h = text_size(draw, GUEST_NAME, f_name)[1]
        gt_text = GUEST_TITLE
        while text_size(draw, gt_text, f_gt)[0] > text_max_w and gtitle_size > 7:
            gtitle_size -= 1
            f_gt = font(HN_REGULAR, gtitle_size)
        gt_h = text_size(draw, gt_text, f_gt)[1]
        bottom_y = h - pad_v
        # url
        uw, _ = text_size(draw, url_text, f_url)
        draw.text((pad_h + (text_max_w - uw) // 2, bottom_y - url_h),
                  url_text, font=f_url, fill=WHITE, anchor="lt")
        # gtitle above url
        gt_y = bottom_y - url_h - max(round(8 * s), 4) - gt_h
        gtw, _ = text_size(draw, gt_text, f_gt)
        draw.text((pad_h + (text_max_w - gtw) // 2, gt_y),
                  gt_text, font=f_gt, fill=(220, 220, 230), anchor="lt")
        # name above gtitle
        nw, _ = text_size(draw, GUEST_NAME, f_name)
        gn_y = gt_y - max(round(5 * s), 4) - name_h
        draw.text((pad_h + (text_max_w - nw) // 2, gn_y),
                  GUEST_NAME, font=f_name, fill=WHITE, anchor="lt")

        return canvas

    if kind == "square":
        # balloon-no fills canvas; navy scrim on top with episode badge + quote box; smoky guest strip on bottom
        canvas = (
            fit_cover(_BALLOON_NO.convert("RGBA"), (w, h))
            if _BALLOON_NO is not None
            else Image.new("RGBA", (w, h), CORN + (255,))
        )

        # Top scrim (navy fading down)
        scrim_h = round(h * 0.30)
        scrim_arr = np.zeros((scrim_h, w, 4), dtype=np.uint8)
        for y in range(scrim_h):
            t = 1.0 - (y / scrim_h)
            alpha = int(200 * t * t)
            scrim_arr[y, :, 0:3] = NAVY
            scrim_arr[y, :, 3] = alpha
        scrim = Image.fromarray(scrim_arr, "RGBA")
        canvas.paste(scrim, (0, 0), scrim)

        draw = ImageDraw.Draw(canvas)

        # Episode badge top
        ep_size = max(round(9 * s), 8)
        f_ep = font(HN_BOLD, ep_size)
        ep_text = f"EPISODE #{EPISODE_DISPLAY}"
        ew, eh = text_size(draw, ep_text, f_ep)
        bpad_v = max(round(4 * s), 3)
        bpad_h = max(round(9 * s), 6)
        badge_w = ew + 2 * bpad_h
        badge_h = eh + 2 * bpad_v
        bx = (w - badge_w) // 2
        by = max(round(12 * s), 8)
        rounded_rect_fill(canvas, (bx, by, bx + badge_w, by + badge_h),
                          radius=badge_h // 2, fill=badge_bg)
        draw.text((bx + bpad_h, by + bpad_v), ep_text, font=f_ep, fill=WHITE, anchor="lt")

        # Quote box just below badge
        quote_text = QUOTE_FULL_TEXT
        quote_size = max(round(13 * s), 11)
        f_quote = font(HN_BLACK, quote_size)
        avail_q = int(w * 0.85)
        while text_size(draw, quote_text, f_quote)[0] > avail_q and quote_size > 11:
            quote_size -= 1
            f_quote = font(HN_BLACK, quote_size)
        qw, qh = text_size(draw, quote_text, f_quote)
        qpad_v = max(round(7 * s), 5)
        qpad_h = max(round(11 * s), 7)
        radius = max(round(10 * s), 6)
        border = max(round(2.5 * s), 2)
        box_w = qw + 2 * qpad_h
        box_h = qh + 2 * qpad_v
        bx2 = (w - box_w) // 2
        by2 = by + badge_h + max(round(8 * s), 5)
        rounded_translucent_fill(canvas, (bx2, by2, bx2 + box_w, by2 + box_h),
                                 radius=radius, rgba=(10, 31, 61, 200))
        rounded_rect_outline(canvas, (bx2, by2, bx2 + box_w, by2 + box_h),
                             radius=radius, color=quote_border, width=border)
        draw.text((bx2 + qpad_h, by2 + qpad_v), quote_text, font=f_quote, fill=WHITE, anchor="lt")

        # Guest strip pinned to bottom
        name_size   = max(round(14 * s), 10)
        gtitle_size = max(round(9.5 * s), 8)
        f_name = font(HN_BOLD, name_size)
        f_gt   = font(HN_REGULAR, gtitle_size)
        gt_text = GUEST_TITLE
        while text_size(draw, gt_text, f_gt)[0] > w * 0.92 and gtitle_size > 7:
            gtitle_size -= 1
            f_gt = font(HN_REGULAR, gtitle_size)
        name_h = text_size(draw, GUEST_NAME, f_name)[1]
        gt_h   = text_size(draw, gt_text, f_gt)[1]
        strip_pad_v = max(round(10 * s), 6)
        strip_h = name_h + max(round(5*s), 4) + gt_h + 2 * strip_pad_v
        # strip: smoky 92% alpha
        strip = Image.new("RGBA", (w, strip_h), SMOKY + (235,))
        canvas.paste(strip, (0, h - strip_h), strip)
        sy = h - strip_h + strip_pad_v
        nw, _ = text_size(draw, GUEST_NAME, f_name)
        draw.text(((w - nw) // 2, sy), GUEST_NAME, font=f_name, fill=WHITE, anchor="lt")
        gtw, _ = text_size(draw, gt_text, f_gt)
        draw.text(((w - gtw) // 2, sy + name_h + max(round(5*s), 4)),
                  gt_text, font=f_gt, fill=(220, 220, 230), anchor="lt")

        return canvas

    # ---- vertical 9:16: top half balloon-no; below = panel with badge + quote + url ----
    canvas = Image.new("RGB", (w, h), panel_top).convert("RGBA")
    top_h = w  # 1:1 region for the cartoon
    top = (
        fit_cover(_BALLOON_NO.convert("RGBA"), (w, top_h))
        if _BALLOON_NO is not None
        else Image.new("RGBA", (w, top_h), CORN + (255,))
    )
    canvas.paste(top, (0, 0), top)

    # smoky guest strip pinned to bottom of TOP image
    draw = ImageDraw.Draw(canvas)
    name_size   = max(round(9.5 * s), 8)
    gtitle_size = max(round(7 * s),  6)
    f_name = font(HN_BOLD, name_size)
    f_gt   = font(HN_REGULAR, gtitle_size)
    name_h = text_size(draw, GUEST_NAME, f_name)[1]
    gt_h   = text_size(draw, GUEST_TITLE_SHORT, f_gt)[1]
    strip_pad_v = max(round(5 * s), 3)
    strip_h = name_h + max(round(5*s), 4) + gt_h + 2 * strip_pad_v
    strip = Image.new("RGBA", (w, strip_h), SMOKY + (235,))
    canvas.paste(strip, (0, top_h - strip_h), strip)
    sy = top_h - strip_h + strip_pad_v
    nw, _ = text_size(draw, GUEST_NAME, f_name)
    draw.text(((w - nw) // 2, sy), GUEST_NAME, font=f_name, fill=WHITE, anchor="lt")
    gtw, _ = text_size(draw, GUEST_TITLE_SHORT, f_gt)
    draw.text(((w - gtw) // 2, sy + name_h + max(round(5*s), 4)),
              GUEST_TITLE_SHORT, font=f_gt, fill=(220, 220, 230), anchor="lt")

    # bottom panel: episode pill, quote box, url-footer
    pad = max(round(8 * s), 6)
    panel_y = top_h
    panel_h = h - panel_y
    if variant == "w1":
        grad = linear_gradient((w, panel_h), panel_top, panel_bot, angle_deg=135)
        canvas.paste(grad, (0, panel_y))
    # else solid (already filled)

    # Bigger sizes for legibility on phone screens.
    ep_size = max(round(13 * s), 11)
    f_ep = font(HN_BOLD, ep_size)
    ep_text = f"EPISODE #{EPISODE_DISPLAY}"
    ew, eh = text_size(draw, ep_text, f_ep)
    bpad_v = max(round(6 * s), 5)
    bpad_h = max(round(13 * s), 9)
    badge_w = ew + 2 * bpad_h
    badge_h = eh + 2 * bpad_v

    # URL pinned to bottom (slightly bigger).
    url_size = max(round(11 * s), 9)
    f_url = font(HN_BOLD, url_size)
    url_text = "softwareinblue.com"
    uw, uh = text_size(draw, url_text, f_url)
    url_y = h - pad - uh
    draw.text(((w - uw) // 2, url_y), url_text, font=f_url, fill=WHITE, anchor="lt")

    # Quote box (bigger; still must fit on one line).
    quote_text = QUOTE_FULL_TEXT
    quote_size = max(round(15 * s), 12)
    f_quote = font(HN_BLACK, quote_size)
    avail_q = int(w * 0.92)
    while text_size(draw, quote_text, f_quote)[0] > avail_q and quote_size > 10:
        quote_size -= 1
        f_quote = font(HN_BLACK, quote_size)
    qw, qh = text_size(draw, quote_text, f_quote)
    qpad_v = max(round(7 * s), 5)
    qpad_h = max(round(11 * s), 7)
    radius = max(round(9 * s), 6)
    border = max(round(2 * s), 2)
    box_w = qw + 2 * qpad_h
    box_h = qh + 2 * qpad_v
    bx2 = (w - box_w) // 2

    # Position the quote box vertically so the pill above + url below have
    # equal-feeling bands. We center the quote in the available space
    # between (panel_top + pill_height + breathing) and (url_y - breathing).
    breathing = max(round(10 * s), 6)
    quote_band_top = panel_y + badge_h + breathing  # below where the pill will sit
    quote_band_bot = url_y - breathing
    by2 = quote_band_top + max(0, (quote_band_bot - quote_band_top - box_h)) // 2
    rounded_translucent_fill(canvas, (bx2, by2, bx2 + box_w, by2 + box_h),
                             radius=radius, rgba=(10, 31, 61, 200))
    rounded_rect_outline(canvas, (bx2, by2, bx2 + box_w, by2 + box_h),
                         radius=radius, color=quote_border, width=border)
    draw.text((bx2 + qpad_h, by2 + qpad_v), quote_text, font=f_quote, fill=WHITE, anchor="lt")

    # Episode pill: vertically centered between balloon-bottom (panel_y) and
    # quote-top (by2). Width-centered horizontally.
    bx = (w - badge_w) // 2
    by = panel_y + max(0, ((by2 - panel_y) - badge_h) // 2)
    rounded_rect_fill(canvas, (bx, by, bx + badge_w, by + badge_h),
                      radius=badge_h // 2, fill=badge_bg)
    draw.text((bx + bpad_h, by + bpad_v), ep_text, font=f_ep, fill=WHITE, anchor="lt")

    return canvas

# ---------------- core layout: diary (D1, D2) -------------------------------
#
# DOAC-inspired big-text variants. Square + vertical use the face as a full
# backdrop with a dark scrim under the text. Wide + banner use a split
# layout: text-left (~58%), photo cover-fit on the right (~42%). The
# tagline is broken into 3-5 short lines and the configured highlight word
# gets a solid colored block behind it (red for D1, cornflower for D2).

def _diary_palette(variant):
    return DIARY_RED if variant == "d1" else CORN

def _diary_split_lines(text: str, max_lines: int = 4) -> list[str]:
    """Split tagline into short lines for the big-text overlay. Greedy by
    chars-per-line; target balanced across max_lines."""
    text = text.strip().strip('"').strip()
    words = text.split()
    if len(words) <= 2:
        return [text]
    target = max(8, min(22, len(text) // max_lines + 4))
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = word if not cur else f"{cur} {word}"
        if len(trial) <= target or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    while len(lines) > max_lines:
        lines[-2] = lines[-2] + " " + lines[-1]
        lines.pop()
    return lines

def _diary_paint_rect(draw, x, y, line, fnt, start, end, color, pad_x, pad_y):
    """`y` is the ASCENDER line of the font (the anchor='la' position). Rect
    fills the full font cell (ascender → descender) plus optional pad_y on
    each side. Width matches the rendered glyph extent of line[start:end]."""
    before = line[:start]
    hi     = line[start:end]
    bw = text_size(draw, before, fnt)[0]
    hw = text_size(draw, hi, fnt)[0]
    ascent, descent = fnt.getmetrics()
    font_h = ascent + descent
    draw.rectangle((x + bw - pad_x, y - pad_y,
                    x + bw + hw + pad_x, y + font_h + pad_y),
                   fill=color)

def _draw_diary_line(draw, xy, line, fnt, hl_phrases, hl_color, text_color,
                     hl_pad_x=0, hl_pad_y=0):
    """Draw one line; underlay every occurrence of any phrase in hl_phrases
    (each may be a single word OR a space-separated phrase) with a solid
    hl_color rectangle. Position uses anchor='la' (left, ascender) so y refers
    to the font's ascender line — consistent across lines regardless of glyph
    content. Rect uses the full font cell so plain and highlighted lines share
    the same vertical slot.

    `hl_phrases` is a list[str]. Each phrase is matched whole-phrase first;
    if no whole-phrase match on this line, falls back to matching its
    individual words. This lets a multi-word phrase like "stole servers"
    paint a single rect when the line keeps the words together but still
    paint per-word rects when wrapping splits them across lines."""
    x, y = xy
    if hl_phrases:
        painted_spans: list[tuple[int, int]] = []
        def overlaps(s, e):
            return any(not (e <= ps or s >= pe) for ps, pe in painted_spans)
        for phrase in hl_phrases:
            m_full = re.search(r'\b' + re.escape(phrase) + r'\b', line, re.IGNORECASE)
            if m_full and not overlaps(m_full.start(), m_full.end()):
                _diary_paint_rect(draw, x, y, line, fnt,
                                  m_full.start(), m_full.end(),
                                  hl_color, hl_pad_x, hl_pad_y)
                painted_spans.append((m_full.start(), m_full.end()))
            else:
                for word in phrase.split():
                    m = re.search(r'\b' + re.escape(word) + r'\b', line, re.IGNORECASE)
                    if m and not overlaps(m.start(), m.end()):
                        _diary_paint_rect(draw, x, y, line, fnt,
                                          m.start(), m.end(),
                                          hl_color, hl_pad_x, hl_pad_y)
                        painted_spans.append((m.start(), m.end()))
    draw.text((x, y), line, font=fnt, fill=text_color, anchor="la")

def _diary_scrim(w: int, total_h: int, fade_h: int = 0, solid_alpha: int = 240):
    """Navy scrim: alpha goes 0 → solid_alpha over the top `fade_h` rows,
    then stays at solid_alpha for the rest. Drops a fully-opaque panel under
    text while the photo above blends out smoothly."""
    arr = np.zeros((total_h, w, 4), dtype=np.uint8)
    arr[..., 0] = NAVY[0]; arr[..., 1] = NAVY[1]; arr[..., 2] = NAVY[2]
    fade_h = max(0, min(fade_h, total_h))
    if fade_h > 0:
        arr[:fade_h, :, 3] = np.linspace(0, solid_alpha, fade_h, dtype=np.uint8)[:, None]
    arr[fade_h:, :, 3] = solid_alpha
    return Image.fromarray(arr, "RGBA")

def render_diary(variant, w, h):
    """D1 (red highlights) / D2 (cornflower highlights)."""
    kind = aspect_kind(w, h)
    s = min(w, h) / 270.0
    hl_color = _diary_palette(variant)
    hl_phrases = QUOTE_HIGHLIGHTS

    target_lines = 4 if kind in ("vertical", "square") else 4
    lines = _diary_split_lines(QUOTE_TAGLINE, max_lines=target_lines)

    # Brand wordmark + ep# footer fonts (used in both layouts)
    canvas = Image.new("RGB", (w, h), NAVY).convert("RGBA")

    if kind in ("wide", "banner"):
        text_w = round(w * 0.58)
        photo_w = w - text_w
        photo_panel = Image.new("RGB", (photo_w, h), NAVY)
        photo_img = fit_cover(_PHOTO.convert("RGBA"), (photo_w, h))
        photo_panel.paste(photo_img.convert("RGBA"), (0, 0), photo_img)
        canvas.paste(photo_panel, (text_w, 0))

        pad_h = max(round(22 * s), 14)
        pad_v = max(round(18 * s), 12)
        avail_w = text_w - 2 * pad_h
        draw = ImageDraw.Draw(canvas)

        # NEW badge top-left
        badge_size = max(round(11 * s), 9)
        f_badge = font(HN_BLACK, badge_size)
        b_w, b_h = text_size(draw, "NEW", f_badge)
        bpx = max(round(7 * s), 4); bpy = max(round(4 * s), 3)
        rounded_rect_fill(canvas,
                          (pad_h, pad_v, pad_h + b_w + 2*bpx, pad_v + b_h + 2*bpy),
                          radius=max(round(4*s), 3), fill=DIARY_RED)
        draw.text((pad_h + bpx, pad_v + bpy), "NEW", font=f_badge, fill=WHITE, anchor="lt")
        badge_bottom = pad_v + b_h + 2*bpy

        # Footer (small wordmark + ep#) at bottom
        title_size = max(round(11 * s), 9)
        ep_size = max(round(9 * s), 8)
        f_title = font(HN_BOLD, title_size)
        f_ep = font(HN_BOLD, ep_size)
        title_runs = [("Can I get that software ", f_title, WHITE),
                      ("in blue?", f_title, CORN)]
        while measure_runs(draw, title_runs)[0] > avail_w and title_size > 8:
            title_size -= 1
            f_title = font(HN_BOLD, title_size)
            title_runs = [("Can I get that software ", f_title, WHITE),
                          ("in blue?", f_title, CORN)]
        title_h = f_title.getmetrics()[0]
        ep_h = text_size(draw, "EPISODE #", f_ep)[1]
        foot_block_h = title_h + max(round(4*s), 3) + ep_h
        foot_y = h - pad_v - foot_block_h

        avail_v = foot_y - badge_bottom - max(round(24*s), 16)

        # Pick big-line size: largest that fits both the longest line in width
        # and the full block in vertical space. Each line occupies a uniform
        # font cell (ascent+descent) so plain and highlighted lines share the
        # same vertical slot — gaps between any pair are exactly `line_gap`.
        # A small hl_pad_y extends the rect a touch above the ascender line.
        line_size = max(round(40 * s), 22)
        while line_size > 18:
            f_line = font(HN_BLACK, line_size)
            ascent, descent = f_line.getmetrics()
            font_h = ascent + descent
            line_gap = max(round(line_size * 0.10), 3)
            hl_pad_y = max(round(line_size * 0.04), 2)
            block_h = len(lines) * (font_h + 2 * hl_pad_y) + (len(lines) - 1) * line_gap
            longest = max(text_size(draw, ln, f_line)[0] for ln in lines)
            if longest <= avail_w and block_h <= avail_v:
                break
            line_size -= 1
        else:
            f_line = font(HN_BLACK, line_size)
            ascent, descent = f_line.getmetrics()
            font_h = ascent + descent
            line_gap = max(round(line_size * 0.10), 3)
            hl_pad_y = max(round(line_size * 0.04), 2)
            block_h = len(lines) * (font_h + 2 * hl_pad_y) + (len(lines) - 1) * line_gap

        block_y = badge_bottom + (avail_v - block_h) // 2
        hl_pad_x = max(round(line_size * 0.18), 4)
        line_advance = font_h + 2 * hl_pad_y + line_gap
        for i, ln in enumerate(lines):
            _draw_diary_line(draw, (pad_h, block_y + hl_pad_y + i*line_advance),
                             ln, f_line, hl_phrases, hl_color, WHITE,
                             hl_pad_x=hl_pad_x, hl_pad_y=hl_pad_y)

        draw_runs(draw, (pad_h, foot_y), title_runs)
        draw.text((pad_h, foot_y + title_h + max(round(4*s), 3)),
                  f"EPISODE #{EPISODE_DISPLAY}", font=f_ep, fill=(220, 220, 230), anchor="lt")
        return canvas

    # ---- square / vertical: face-as-backdrop ----
    photo_img = fit_cover(_PHOTO.convert("RGBA"), (w, h))
    paste_image(canvas, photo_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    pad_h = max(round(18 * s), 12)
    pad_v = max(round(18 * s), 12)
    avail_w = w - 2 * pad_h

    # NEW badge measurement (paint after scrim so it stays on top of the photo).
    badge_size = max(round(13 * s), 10)
    f_badge = font(HN_BLACK, badge_size)
    b_w, b_h = text_size(draw, "NEW", f_badge)
    bpx = max(round(8 * s), 5); bpy = max(round(5 * s), 3)

    # Footer fonts (compute first so we know how much room is left for text)
    title_size = max(round(13 * s), 10)
    ep_size = max(round(10 * s), 8)
    f_title = font(HN_BOLD, title_size)
    f_ep = font(HN_BOLD, ep_size)
    title_runs = [("Can I get that software ", f_title, WHITE),
                  ("in blue?", f_title, CORN)]
    while measure_runs(draw, title_runs)[0] > avail_w and title_size > 9:
        title_size -= 1
        f_title = font(HN_BOLD, title_size)
        title_runs = [("Can I get that software ", f_title, WHITE),
                      ("in blue?", f_title, CORN)]
    title_h = f_title.getmetrics()[0]
    ep_h = text_size(draw, "EPISODE #", f_ep)[1]
    foot_block_h = title_h + max(round(4*s), 3) + ep_h
    foot_y = h - pad_v - foot_block_h
    text_gap_to_footer = max(round(20 * s), 14)

    max_line_size = round((72 if kind == "vertical" else 58) * s)
    line_size = max(max_line_size, 24)
    avail_v = foot_y - text_gap_to_footer - (pad_v + b_h + 2*bpy + max(round(16*s), 10))
    while line_size > 18:
        f_line = font(HN_BLACK, line_size)
        ascent, descent = f_line.getmetrics()
        font_h = ascent + descent
        line_gap = max(round(line_size * 0.10), 3)
        hl_pad_y = max(round(line_size * 0.04), 2)
        block_h = len(lines) * (font_h + 2 * hl_pad_y) + (len(lines) - 1) * line_gap
        longest = max(text_size(draw, ln, f_line)[0] for ln in lines)
        if longest <= avail_w and block_h <= avail_v:
            break
        line_size -= 1
    else:
        f_line = font(HN_BLACK, line_size)
        ascent, descent = f_line.getmetrics()
        font_h = ascent + descent
        line_gap = max(round(line_size * 0.10), 3)
        hl_pad_y = max(round(line_size * 0.04), 2)
        block_h = len(lines) * (font_h + 2 * hl_pad_y) + (len(lines) - 1) * line_gap

    block_y = foot_y - text_gap_to_footer - block_h

    # Solid navy panel under text + footer, with a short gradient fade above
    # so the photo blends out instead of cutting hard. The solid region starts
    # ~36px above the text block.
    scrim_top_pad = max(round(36 * s), 24)
    fade_h_val = max(round(80 * s), 50)
    solid_top_y = max(round(h * 0.30), block_y - scrim_top_pad)
    scrim_top = max(0, solid_top_y - fade_h_val)
    canvas.alpha_composite(
        _diary_scrim(w, h - scrim_top, fade_h=solid_top_y - scrim_top),
        (0, scrim_top))

    # NEW badge — painted after scrim so it always sits on top.
    rounded_rect_fill(canvas,
                      (pad_h, pad_v, pad_h + b_w + 2*bpx, pad_v + b_h + 2*bpy),
                      radius=max(round(4*s), 3), fill=DIARY_RED)
    draw.text((pad_h + bpx, pad_v + bpy), "NEW", font=f_badge, fill=WHITE, anchor="lt")

    hl_pad_x = max(round(line_size * 0.18), 4)
    line_advance = font_h + 2 * hl_pad_y + line_gap
    for i, ln in enumerate(lines):
        _draw_diary_line(draw, (pad_h, block_y + hl_pad_y + i*line_advance),
                         ln, f_line, hl_phrases, hl_color, WHITE,
                         hl_pad_x=hl_pad_x, hl_pad_y=hl_pad_y)

    draw_runs(draw, (pad_h, foot_y), title_runs)
    draw.text((pad_h, foot_y + title_h + max(round(4*s), 3)),
              f"EPISODE #{EPISODE_DISPLAY}", font=f_ep, fill=(220, 220, 230), anchor="lt")
    return canvas

# ---------------- variant dispatch ------------------------------------------

VARIANTS = (
    "a1", "a2", "a3",
    "a1w", "a2w", "a3w",
    "c1", "c2", "c3",
    "w1", "w2",
    "d1", "d2",
)

def render(variant, w, h):
    if variant in ("a1", "a2", "a1w", "a2w"):
        return render_face_forward(variant, w, h)
    if variant in ("a3", "a3w"):
        return render_face_forward_bottom(variant, w, h)
    if variant in ("c1", "c2", "c3"):
        return render_magazine(variant, w, h)
    if variant in ("w1", "w2"):
        return render_whimsical(variant, w, h)
    if variant in ("d1", "d2"):
        return render_diary(variant, w, h)
    raise ValueError(variant)

# ---------------- main loop --------------------------------------------------

RENDER_TARGETS = [
    ("thumbnail-youtube-1920x1080", 1920, 1080),
    # ("banner-youtube-2560x1440",    2560, 1440),
    # ("banner-twitter-1500x500",     1500,  500),
    # ("banner-facebook-851x315",      851,  315),
    # ("banner-linkedin-1128x191",    1128,  191),
    ("podcast-cover-3000x3000",     3000, 3000),
    ("short-tiktok-1080x1920",      1080, 1920),
]
PROFILE_PIC_SIZES = [
    # ("profilepic-twitter-400x400",   400),
    # ("profilepic-instagram-320x320", 320),
    # ("profilepic-tiktok-200x200",    200),
    # ("profilepic-facebook-170x170",  170),
]
COVER_KEY = "podcast-cover-3000x3000"


def render_one(variant, name, w, h):
    img = render(variant, w, h).convert("RGB")
    if img.size != (w, h):
        raise RuntimeError(f"{variant}/{name}: got {img.size}, expected {(w,h)}")
    out = OUT_DIR / variant / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", optimize=True)
    print(f"  {variant}/{name}.png  ({out.stat().st_size:,} bytes)")


def make_profile_pics(variant):
    cover = OUT_DIR / variant / f"{COVER_KEY}.png"
    if not cover.exists():
        print(f"  SKIP profile pics for {variant}: cover missing")
        return
    with Image.open(cover) as src:
        for name, sz in PROFILE_PIC_SIZES:
            out = OUT_DIR / variant / f"{name}.png"
            src.resize((sz, sz), Image.LANCZOS).save(out, format="PNG")
            print(f"  {variant}/{name}.png  ({out.stat().st_size:,} bytes, downscaled)")


if __name__ == "__main__":
    print(f"Episode {EPISODE_NUM} | guest={GUEST_SLUG}")
    print(f"Output: {OUT_DIR}")
    for variant in VARIANTS:
        if variant in ("w1", "w2") and (_BALLOON_WITH is None or _BALLOON_NO is None):
            print(f"=== {variant.upper()} skipped (balloon assets missing) ===")
            continue
        if variant in ("a1w", "a2w", "a3w") and _BALLOON_NO is None:
            print(f"=== {variant.upper()} skipped (no-overlay balloon missing) ===")
            continue
        print(f"=== {variant.upper()} ===")
        for name, w, h in RENDER_TARGETS:
            render_one(variant, name, w, h)
        make_profile_pics(variant)
    print(f"\nAll variants written to {OUT_DIR}")
