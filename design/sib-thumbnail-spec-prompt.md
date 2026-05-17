# SIB Podcast Thumbnail Spec — Reusable Prompt (v5, locked)

Use this prompt to recreate the SIB thumbnail system in any tool that can render HTML or be driven by an LLM. Every rule below is a *must*. The compositor follows the visual-QA loop in this document — render → overlay measurement grid → verify alignment → iterate → export.

---

## 1. Show identity

- **Name:** "Can I get that software in blue?"
- **Short name:** SIB
- **Domain:** softwareinblue.com
- **Social handle:** @softwareinblue
- **Hosts (always a list, even when length 2):** `hosts: [chad, steve]`
- **Guests (always a list; sometimes more than one per episode):** `guests: [robertakang, ...]`
- **Topic:** technology sales, presales, solution architecture; conversations with practitioners
- **Reference podcasts the visual style is informed by:** Huberman Lab, The Joe Rogan Experience, Diary of a CEO, Lex Fridman, Acquired, All-In.

## 2. Brand palette

- `--sib-blue` (cornflower): **`#6495ED`** — primary brand color
- `--sib-blue-dark`: `#3b6cc0` — gradient companion
- `--sib-navy`: `#0a1f3d` — dark backdrop
- `--sib-cream`: `#f4f1ea` — warm light backdrop (magazine feel)
- White and pure black sparingly

> **Neutral gray photo backdrops are forbidden.** Photos sit on a brand color (cornflower, navy, or cream) tied to the variant.

## 3. Logo / wordmark treatment

The phrase **"Can I get that software in blue?"** is the show wordmark and appears on every variant. The two words `in blue` are highlighted:
- On a **navy or cream** background: render `in blue` in cornflower (`#6495ED`).
- On a **cornflower** background: render `in blue` in **white with a thin (1px) white underline** (cornflower-on-cornflower would not read).

The "in blue" highlight rule applies *consistently* across A1, A2, C1, C2, C3.

## 4. Output format catalog

The compositor produces an asset for every (variant × size) combo the show needs.

### 4a. Per-episode hero formats

| Format | Aspect | Export size | Use |
|---|---|---|---|
| 16:9 | 1.78 | 1280 × 720 (or 1920 × 1080 HD) | YouTube thumbnail |
| 1:1 | 1.0 | 3000 × 3000 | Apple Podcasts / Spotify cover |
| 9:16 | 0.5625 | 1080 × 1920 | YouTube Shorts, Instagram Reels, TikTok |

### 4b. Standard social / channel sizes

| File name | Pixel size | Aspect | Use |
|---|---|---|---|
| `thumbnail-youtube-1920x1080` | 1920 × 1080 | 16:9 | YouTube video thumbnail (HD) |
| `banner-youtube-2560x1440` | 2560 × 1440 | 16:9 | YouTube channel banner |
| `banner-twitter-1500x500` | 1500 × 500 | 3:1 | Twitter/X header |
| `banner-facebook-851x315` | 851 × 315 | 2.7:1 | Facebook page cover |
| `banner-linkedin-1128x191` | 1128 × 191 | 5.9:1 | LinkedIn page cover |
| `podcast-cover-3000x3000` | 3000 × 3000 | 1:1 | Apple Podcasts / Spotify cover |
| `profilepic-twitter-400x400` | 400 × 400 | 1:1 | Twitter profile |
| `profilepic-instagram-320x320` | 320 × 320 | 1:1 | Instagram profile |
| `profilepic-tiktok-200x200` | 200 × 200 | 1:1 | TikTok profile |
| `profilepic-facebook-170x170` | 170 × 170 | 1:1 | Facebook profile |

### 4c. Aspect-ratio dispatch

The compositor picks a layout based on aspect ratio:

```
ratio = width / height
if ratio < 1.05 → SQUARE layout (full magazine cover for ≥ 600 px; simplified profile pic for < 600 px)
if ratio < 2.0  → WIDE-16:9 layout (magazine split: text left ~62%, photo right ~38%)
if ratio ≥ 2.0  → BANNER layout (wide; text left ~70%, photo right ~30%)
```

A 270 × 270 fits SQUARE (simplified). A 3000 × 3000 fits SQUARE (full). A 1920 × 1080 fits WIDE-16:9. A 1500 × 500 (3:1) and a 1128 × 191 (5.9:1) both fit BANNER.

### 4d. Simplified profile-pic layout (< 600 px square)

A 170 × 170 canvas can't legibly fit the full magazine layout. For square exports under 600 px, use the **simplified profile-pic layout**:

- Background: cornflower (`#6495ED`).
- Foreground: BG-removed guest photo as full-bleed, `background-size: cover; background-position: center;`.
- Bottom-right corner: small navy "pill" badge containing the episode number (e.g. `EP #45`). Padding + corner radius + font scale with the canvas width.
- No quote, show title, guest name, or footer at this size.

The compositor falls back to this whenever the canvas's shortest dimension is below 600 px.

## 5. Required elements (full layouts)

For canvases ≥ 600 px in their shortest dimension, every variant must include:

1. **Show title** — `Can I get that software in blue?` with `in blue` highlighted. **First / on top.**
2. **Episode number** — full word, e.g. `Episode #45`. Never `Ep. 45`. Never giant-Impact-font numerals. **Below the show title, smaller and slightly faded (`opacity: 0.8-0.9`).**
3. **Provocative quote** — the **hero element**, biggest type, vertically centered when there's room. On C1, C2, C3: enclosed in a rounded-corner border box.
4. **Guest photo(s)** — BG-removed (rembg), sized so the entire face fits with breathing room.
5. **Guest name + title** — e.g. "Dr. Roberta Lenger Kang" / "Executive Director · Columbia Teachers College CPET".
6. **Footer** — `@softwareinblue` **first** (above or to the left of) `softwareinblue.com`. Two stacked lines on 16:9 / 9:16; one inline line on 1:1.

## 6. Element ordering (locked, every full layout)

```
[ Show title  (Can I get that software in blue?) ]   ← top, larger, one line (white-space: nowrap)
[ Episode #45 ]                                       ← below title, smaller, faded
[ Provocative quote in rounded box (C1/C2/C3) ]       ← hero, centered horizontally + vertically
[ Guest name + title ]                                ← centered between quote and footer
[ @softwareinblue + softwareinblue.com ]              ← footer
```

## 7. Photo handling

1. Run guest / host photo through `rembg` (U²-Net) → transparent PNG. Cache under `EpisodeN/artifacts/headshots/<slug>-nobg.png`. Hosts (Chad, Steve) get the same treatment, cached once and reused across episodes.
   - Chad source: `Downloads/Chad_Tindel_Headshot.jpg`.
   - Steve source: `https://www.softwareinblue.com/img/host/stevemayzak.jpg` (download once).
   - Guest source: `static/img/guest/<slug>.jpg` (Hugo data) or per-episode override.
2. Compute the **subject bounding box** from non-transparent pixels. Pad it on every side by **≥ 8%** of the photo panel before rendering — text panels reflow around the photo's natural aspect, never the other way around.
3. Place the photo with `background-size: contain` (never `cover` — never crop the face) on a brand-color backdrop:
   - C1 photo panel → cornflower (`#6495ED`)
   - C2 photo panel → navy (`#0a1f3d`)
   - C3 photo panel → cornflower (`#6495ED`)
   - A1 photo circle → cornflower fill behind subject (matches the ring border)
   - A2 photo circle → white fill
4. Circular photo treatments (A1/A2) use a 3-4 px ring scaled to format size.
5. **Per-photo subject-aware sizing.** Photos vary in native aspect; panel size adapts so the face fits with margin. Tall portrait → taller panel; wide group photo → wider panel. Text panels reflow around it.

> Exception: simplified profile-pic layout (< 600 px square) uses `background-size: cover` on the canvas itself — face is allowed to crop near the edges since the canvas is too small to honor the contain rule.

## 8. Design directions

Eight base variants plus three emblem variants (suffix `w` = whimsical balloon emblem in lower-right). The compositor renders **every** variant × every standard size for every episode so the producer can pick per-channel.

### A1 — Navy + cornflower highlight (face-forward)
- Background: solid navy (`#0a1f3d`). Text: white.
- One keyword in the quote may be highlighted in cornflower for emphasis.
- Photo: circular, bordered in cornflower, on the right (16:9) or top-center (1:1, 9:16).
- Vibe: face-forward, dramatic, Huberman-Lab adjacent.

### A2 — Full cornflower (face-forward)
- Background: linear gradient `#6495ED → #3b6cc0`. Text: white.
- Quote uses no keyword highlight (already on cornflower).
- Photo: circular, bordered in white.
- Vibe: brand-color-forward, very recognizable.

### A3 — Face-forward, source-at-bottom
- Same palette as A1 (navy + cornflower highlight). Reordered stack: quote → guest name+title → show wordmark + episode # → footer.
- Vibe: A1 with the source attribution moved to the bottom so the quote reads first.

### W1 — Whimsical balloon, cornflower panel
- 16:9: cornflower-gradient text panel left, AI-generated balloon cartoon (with-overlay version) full-bleed right.
- 1:1 / 9:16: balloon (no-overlay version) fills the canvas; navy-gradient scrim across the top hosts episode badge + quote box; smoky guest strip pinned to the bottom.
- Quote box bordered white, navy translucent fill.

### W2 — Whimsical balloon, navy panel (W1 with palette inverted)
- W1 with the navy and cornflower swapped on the text side; quote-box border becomes cornflower; episode-badge becomes cornflower.
- Use when the cornflower pairs better with the guest's wardrobe / cartoon palette than navy does.

### A1w / A2w / A3w — Face-forward + balloon emblem
- Same layout as A1 / A2 / A3 plus a small circular crop of the no-overlay balloon image inset in the lower-right corner (≈12% of canvas height, 4% margin, white ring).
- Use when the producer wants the recognizable brand cartoon to read alongside the photo, without committing to the full whimsical layout.

### D1 — Hot Take (red highlight, DOAC-style)
- **Square + vertical (1:1, 9:16):** face-as-backdrop. The rembg'd guest photo is `cover`-fit on a navy canvas; a bottom-up navy gradient scrim covers ~65% of the canvas for text legibility.
- **Wide + banner (16:9, banners):** split layout. Left ~58% navy text panel; right ~42% photo panel `cover`-fit on navy.
- "NEW" red pill badge top-left.
- Tagline auto-split into 3-5 short lines (greedy word-wrap targeting balanced length per line). Line type is huge SF Pro Black, white, left-aligned.
- The configured `tagline_highlight` word gets a solid **red `#dc2626`** rectangle behind it (no border, no padding rounding). Same word still rendered white on top.
- Footer pinned to bottom-left: small `Can I get that software in blue?` wordmark (cornflower on `in blue`) + `EPISODE #N` faded white.
- Vibe: punchy, signature DOAC look. Best for shorts and per-episode promo art that has to read at thumbnail scale.

### D2 — Hot Take (cornflower highlight, on-brand)
- Identical layout to D1, with the highlight rectangle in **cornflower (`#6495ED`)** instead of red. The "NEW" badge stays red.
- Use when the producer wants the bold-text style without departing from the brand palette.

### C1 — Magazine split, cream + cornflower accent
- Background: cream (`#f4f1ea`) on the text side, **cornflower** on the photo side. Text: navy.
- Quote enclosed in a **cornflower-stroked rounded box**.
- Photo: full-bleed panel on the right (16:9 / banner) or below (1:1, 9:16), `contain`-sized.
- Vibe: editorial, magazine, Diary-of-a-CEO adjacent. Best legibility for cold audiences.

### C2 — Magazine split, cornflower left
- Background: cornflower on the text side, **navy** on the photo side. Text: white.
- `in blue` rendered white-underlined since it's on cornflower.
- Quote enclosed in a **white-stroked rounded box**.
- Vibe: brand-forward magazine. Best for shelf-presence.

### C3 — Magazine split, navy left (C2 with colors flipped)
- Background: **navy** on the text side, **cornflower** on the photo side. Text: white.
- `in blue` rendered in cornflower (visible on navy).
- Quote enclosed in a **cornflower-stroked rounded box**.
- Vibe: same magazine feel as C2, inverted polarity. Pick when a guest's photo reads better on cornflower than navy.

**Generation policy: render every variant for every episode.** All 13 variants (A1, A2, A3, A1w, A2w, A3w, C1, C2, C3, W1, W2, D1, D2) × all 10 standard sizes = 130 assets per episode. The producer picks per-channel from the full set rather than committing to a fixed pair up front.

## 9. Multi-host / multi-guest (16:9 only)

When an episode has >1 guest or hosts on the cover:
- Photo column shows guest faces stacked or side-by-side, each in its own circular ring (A1/A2) or stacked panel (C1/C2/C3).
- Lead guest is the largest; secondary guests smaller.
- 1:1 and 9:16 stay single-guest (lead). Hosts mentioned only via show title at those sizes.

## 10. Quote-box styling (C1, C2, C3)

The quote sits inside a rounded-corner border. Border color and thickness scale with format:

| Format | Border thickness | Border radius | Padding |
|---|---|---|---|
| 16:9 | 3 px (or proportional ≥ h/90) | 12 px | 10 / 14 px |
| 1:1 | 2.5 px | 12 px | 10 / 14 px |
| 9:16 | 2 px | 8 px | 7 / 10 px |
| Banner | 3 px (or proportional) | 12 px | 10 / 14 px |

- Border color: cornflower for C1 + C3, white for C2.
- Quote box: `display: block; width: fit-content; margin-inline: auto;` — horizontally centered.
- `text-align: center` inside.
- 16:9 + banner use `white-space: nowrap`. Drop font size if needed so the quote fits one line. If the LLM-picked tagline is too long for 16 px nowrap on 16:9, the LLM step picks a shorter quote.

## 11. Layout anatomy

### A1 / A2 (face-forward)

**16:9** — text left, photo right (~140 px circle on 480 px-wide preview):
```
┌──────────────────────────────────────────────────┐
│ Can I get that software in blue?       ┌────┐   │
│ Episode #45                            │ ph │   │
│                                        │ oto │   │
│   "Provocative quote"   (hero, ↕)      │ in  │   │
│   Dr. Roberta Lenger Kang              │ ring│   │
│   Executive Director · Columbia ...    └────┘   │
│ @softwareinblue                                  │
│ softwareinblue.com                               │
└──────────────────────────────────────────────────┘
```
- 4-row grid (`auto auto 1fr auto`): brand top, quote, 1fr space (with guest centered), footer bottom.
- Extra ~22 px breathing room between brand row and quote on 480 px preview.
- Photo column spans all rows on the right, vertically centered.

**1:1** — single-column stack: brand → photo → quote → guest → footer.

**9:16** — single-column flow with **multiple 1fr rows** (`auto auto 1fr auto 1fr auto 1fr auto`) so photo, quote, guest, and footer disperse evenly.

### C1 / C2 / C3 (magazine split)

**16:9** — text left (~62%), photo right (~38%):
```
┌────────────────────────────┬───────────────┐
│ Can I get that software in blue?           │
│ Episode #45                │   PHOTO       │
│                            │   PANEL       │
│ ╭────────────────────────╮ │   (cornflower │
│ │ "You can't outsource   │ │    navy or    │
│ │  teaching."  (centered)│ │    cornflower)│
│ ╰────────────────────────╯ │               │
│ Dr. Roberta Kang           │               │
│ Executive Director · ...   │               │
└────────────────────────────┴───────────────┘
```
- Left panel `grid-template-rows: auto 1fr auto` — header top, quote-block centered, guest at bottom.
- Quote box vertically centered (`align-self: center`); horizontally centered (`width: fit-content; margin-inline: auto`).

**Banner (wide aspects, 2.0–6.0:1)** — same anatomy with text left ~70%, photo right ~30%:
- Title + Episode # at top.
- Quote box centered vertically.
- Guest at bottom.
- For very narrow banners (< 250 px tall), shrink fonts and padding aggressively (use h/14 for title, h/8 for quote).

**1:1, 9:16** — text panel on top, photo panel below; same flow.

## 12. Type scale (preview-size references)

For the **480 × 270 preview**. Multiply ~2.67× for 1280 × 720, ~1.05× for 3000 × 3000, ~0.85× for 1080 × 1920.

| Element | A1/A2 16:9 | A1/A2 1:1 | A1/A2 9:16 | C1 16:9 | C1 1:1 | C1 9:16 | C2 16:9 | C2 1:1 | C2 9:16 | C3 16:9 | C3 1:1 | C3 9:16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Show title** (one line, `nowrap`) | 16 | 14 | 9 | 15 | 13 | 9 | 14 | 12 | 9 | 14 | 12 | 9 |
| **Episode #** | 9 | 8 | 7 | 9 | 8 | 7 | 9 | 8 | 7 | 9 | 8 | 7 |
| **Quote** | 25 | 16 | 12 | 16 nowrap | 16 | 12 | 16 nowrap | 16 | 12 | 16 nowrap | 16 | 12 |
| **Guest name** | 13 | 11 | 9 | 12 | 10 | 8.5 | 13 | 11 | 9 | 13 | 11 | 9 |
| **Guest title** | 10 | 9 | 8 | 9.5 | 8.5 | 7.5 | 9.5 | 8.5 | 7.5 | 9.5 | 8.5 | 7.5 |
| **Footer (URL/handle)** | 10 | 9 | 8 | — | — | — | — | — | — | — | — | — |

For other export sizes (3000 × 3000, 1920 × 1080, banners): scale every value linearly by `target_height / preview_height`. The Python generator in section 19 does this automatically.

## 13. Locked composition rules (numbered, every rule mandatory)

1. **Quote is the hero.** Largest type. No element should compete with it.
2. **Show title above Episode #** on every variant.
3. **9:16 + banner title fits one line.** Use the largest font that fits with `white-space: nowrap`. Never wrap the wordmark.
4. **A1/A2 vertical balance.** 16:9 / 1:1: 4-row grid placing the guest on a 1fr row between quote and footer. 9:16: three 1fr rows so photo, quote, guest, and footer disperse evenly.
5. **A1/A2 16:9 breathing room.** Extra ~22 px of margin between brand row and quote.
6. **Every full-layout variant carries:** show title, Episode #, guest name + title, quote, photo, footer.
7. **Per-photo subject-aware sizing.** ≥ 8% padding around the face after BG removal. Re-flow text around the photo, don't crop.
8. **No face cropping.** `contain` only on full layouts. (Simplified profile pics use `cover` with face centered — a deliberate exception for sub-600 px canvases.)
9. **Brand-color photo backdrops only.** Cornflower (C1, C3), navy (C2), cornflower fill (A1 ring), white fill (A2 ring). No gray.
10. **Footer order:** `@softwareinblue` first, `softwareinblue.com` second.
11. **`in blue` highlight color rule:** cornflower on cream/navy; white-underlined on cornflower.
12. **Episode # spelling:** `Episode #N`. Never `Ep. N` or display-type numerals (small "EP #N" pill on profile pics is OK).
13. **Quote box (C1, C2, C3):** rounded border around the quote. Cornflower for C1 + C3, white for C2. Thickness scales. Quote centered horizontally inside; box centered horizontally in the panel.
14. **Text-on-photo readability.** Wherever text sits over a photo region, give it a translucent dark pill (`rgba(10, 31, 61, 0.85)`) or brand-color backdrop.
15. **`hosts` and `guests` are lists** (always). Multi-host / multi-guest scales accordingly.
16. **Sub-600-px squares use the simplified profile-pic layout** (full-bleed photo + EP badge), no full magazine layout.
17. **Bottom-row photo panels in 1:1 and 9:16 use `contain`, not `cover`** — wider-than-tall panels crop the chin off `cover`-fit photos. Use `contain` and fill the cornflower / navy side gap with a vertical `softwareinblue.com` element (`writing-mode: vertical-rl`). 16:9 right-column panels stay on `cover`.
18. **Internal CSS class names must be namespaced.** Brainstorming-wrapper / host pages inject rules for `.header`, `.option`, `.card`, etc. Use `.mag-header`, `.tn-card` style prefixes — never bare `.header`.
19. **After every render, screenshot and verify the guest's face is not cropped.** The compositor reads the PNG back, locates the photo panel, and confirms ≥ 8% padding around the face bbox. If cropped, fall back to `contain` (or shrink the panel) and re-render.

## 14. Visual QA loop (mandatory, every render)

**Every image generation or regeneration produces TWO outputs:**
1. The design with the measurement grid overlay (the QA copy).
2. The same design with the overlay disabled (the export copy).

The grid copy is the source of truth for verification. No render is approved — and no export is shipped — without first reviewing the grid copy.

### The grid CSS

```css
.tn::after {
  content: ''; position: absolute; inset: 0; pointer-events: none; z-index: 999;
  background-image:
    linear-gradient(to right,  rgba(255,0,0,.20) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255,0,0,.20) 1px, transparent 1px),
    linear-gradient(to right,  rgba(255,0,0,.55) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255,0,0,.45) 1px, transparent 1px);
  background-size: 10% 10%, 10% 10%, 50% 100%, 100% 50%;
  background-position: 0 0, 0 0, center top, left center;
}
```

### Verification checklist (run on the grid copy)

- Show title fits inside the safe area (no horizontal overflow). Confirm with `getBoundingClientRect()`.
- Quote is the largest text element on the canvas (compare computed font sizes).
- Photo's non-transparent bbox is fully inside the photo panel with ≥ 8% padding on every side.
- Centered elements actually sit on the 50% vertical line (within ±2 px tolerance).
- No text overlaps a photo without a dark pill backdrop.
- Quote box is horizontally centered (left/right whitespace within the panel matches within ±2 px).
- Element ordering top-to-bottom matches the locked sequence.
- Guest name + title is vertically between the quote and the footer.
- `softwareinblue.com` does not appear before `@softwareinblue` in any footer.

If any check fails, **adjust font size or layout values and re-render**. The new render produces both grid + non-grid outputs again. **Every regeneration repeats the loop.** No silent re-renders without a grid check.

### Final export

Once the grid copy passes all checks, export the non-grid copy at full resolution. Archive the grid copy alongside it under `EpisodeN/artifacts/thumbnails/qa/<variant>-<size>-grid.png` for audit.

## 15. Episode metadata (`episode.yaml` schema)

```yaml
episode:
  number: 45
  recorded_at: 2026-04-28
  duration_seconds: 4127
  youtube_id: A06v1mLmFFQ
hosts:
  - chad
  - steve
guests:
  - name: Dr. Roberta Lenger Kang
    title: Executive Director, Center for the Professional Education of Teachers, Columbia University Teachers College
    title_short: Executive Director · Columbia Teachers College CPET
    bio_short: "World-renowned expert in teacher training and development."
    image: img/guest/robertakang.jpg
    links:
      website: https://cpet.tc.columbia.edu/teaching-today.html
      twitter: https://twitter.com/TCCPET
      linkedin: https://linkedin.com/in/robertakang
sponsor: ~
topics: ["AI in education", "teacher training", "Columbia"]
tagline: "You can't outsource teaching."
description_short: ""
description_long: ""
hashtags: []
```

`tagline` is the **single-string provocative quote** that thumbnails render — short enough to fit at 16 px nowrap on a 16:9 panel (~30 chars max for one line; ~64 if 2 lines acceptable on the variant).

## 16. Quote-source pipeline

The provocative quote is extracted from the transcript by an LLM step. Inputs: `EpisodeN/artifacts/transcript.json`. Output: `EpisodeN/artifacts/tagline.txt` (single line).

Selection criteria:
- A direct guest or host quote, verbatim from the transcript.
- Provocative: states a strong opinion, surprising fact, or contrarian take.
- Self-contained: makes sense without surrounding context.
- ≤ 32 characters when possible (one-line on 16:9); ≤ 64 if 2 lines acceptable.
- Avoids profanity, names of non-public figures, or sensitive topics.

The compositor wraps the tagline in matched smart-quotes ("…").

## 17. Compositor pipeline

1. Read `EpisodeN/episode.yaml`.
2. Pull guest + host photos. Cache `rembg` outputs under `EpisodeN/artifacts/headshots/`.
3. Detect subject bbox from non-transparent pixels.
4. Read tagline from `EpisodeN/artifacts/tagline.txt`.
5. For each (variant × size) in the standard catalog (section 4b), pick the layout (section 4c) and render HTML.
6. **Run the QA loop** with grid overlay; iterate sizes if any rule fails.
7. Final export at full resolution; grid copy archived in `qa/`.
8. Store under `EpisodeN/artifacts/thumbnails/<variant>/<size-name>.png`.

## 18. Headless rendering commands

**Screenshot (single variant × size):**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless --disable-gpu --hide-scrollbars \
  --window-size=WIDTH,HEIGHT \
  --screenshot=/path/to/output.png \
  file:///path/to/variant.html
```

**PNG → PDF (macOS):**
```bash
sips -s format pdf /path/to/output.png --out /path/to/output.pdf
```

**Multi-page PDF**: add `@page { size: WIDTHpx HEIGHTpx; }` and `page-break-after: always;` per variant in CSS, then use `--print-to-pdf`.

## 19. Drop-in Python generator

Saved as `gen_sib_exports.py`. Dispatches each (variant × size) to the right layout, scales fonts/padding by canvas height, runs Chrome headless, writes PNGs.

```python
from __future__ import annotations
import shutil, subprocess
from pathlib import Path

OUT_DIR = Path("/tmp/sib-exports")
TMP_DIR = Path("/tmp/sib-exports-html"); TMP_DIR.mkdir(parents=True, exist_ok=True)
PHOTO_SRC = Path("/path/to/headshot-nobg.png")
shutil.copy2(PHOTO_SRC, TMP_DIR / "robertakang-nobg.png")

TARGETS = [
    ("thumbnail-youtube-1920x1080", 1920, 1080),
    ("banner-youtube-2560x1440",    2560, 1440),
    ("banner-twitter-1500x500",     1500,  500),
    ("banner-facebook-851x315",      851,  315),
    ("banner-linkedin-1128x191",    1128,  191),
    ("podcast-cover-3000x3000",     3000, 3000),
    ("profilepic-twitter-400x400",   400,  400),
    ("profilepic-instagram-320x320", 320,  320),
    ("profilepic-tiktok-200x200",    200,  200),
    ("profilepic-facebook-170x170",  170,  170),
]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PALETTE = """
:root {
  --sib-blue: #6495ED; --sib-blue-dark: #3b6cc0;
  --sib-navy: #0a1f3d; --sib-cream: #f4f1ea;
  --photo: url('robertakang-nobg.png');
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; width: 100%; height: 100%; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; overflow: hidden; }
.tn { position: relative; overflow: hidden; width: 100vw !important; height: 100vh !important; }

.photo-panel-c1, .photo-panel-c3 { background-color: var(--sib-blue); background-image: var(--photo);
                  background-size: contain; background-position: center; background-repeat: no-repeat; }
.photo-panel-c2 { background-color: var(--sib-navy); background-image: var(--photo);
                  background-size: contain; background-position: center; background-repeat: no-repeat; }

.title .blue { font-weight: 800; }
.c1 .title .blue, .c3 .title .blue { color: var(--sib-blue); }

.quote { display: block; width: fit-content; margin-inline: auto; text-align: center;
         font-weight: 900; line-height: 1.1; letter-spacing: -0.02em; }
.c1 .quote, .c3 .quote { border-style: solid; border-color: var(--sib-blue); }
.c2 .quote { border-style: solid; border-color: #fff; }

.brand { line-height: 1.2; }
.brand .ep { font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase; opacity: 0.8; }
.brand .title { font-weight: 700; line-height: 1.15; white-space: nowrap; }
.guest .name { font-weight: 800; line-height: 1.15; }
.guest .gtitle { font-weight: 500; line-height: 1.2; opacity: 0.8; }
.footer .url { font-weight: 700; }
.footer .handle { font-weight: 500; opacity: 0.85; }
"""

def aspect_kind(w, h):
    r = w / h
    if r < 1.05: return "square"
    if r < 2.0:  return "wide-16-9"
    return "banner"

def html_square(variant, w, h):
    if variant == "c1":  bg, color, photo_class = "var(--sib-cream)", "var(--sib-navy)", "photo-panel-c1"
    else:                bg, color, photo_class = "var(--sib-navy)",  "#fff",            "photo-panel-c3"
    if w < 600:
        # Simplified profile pic: photo full-bleed, EP badge bottom-right.
        bs = max(9, w // 12)
        return f"""<!doctype html><html><head><meta charset='utf-8'><style>
{PALETTE}
.tn {{ background-color: var(--sib-blue); background-image: var(--photo);
       background-size: cover; background-position: center; background-repeat: no-repeat; }}
.badge {{ position: absolute; bottom: {max(4, w//22)}px; right: {max(4, w//22)}px;
          font-size: {bs}px; font-weight: 800; line-height: 1;
          background: var(--sib-navy); color: #fff;
          padding: {max(3, w//40)}px {max(5, w//22)}px;
          border-radius: {max(4, w//22)}px; letter-spacing: 0.04em; }}
</style></head><body><div class="tn {variant}">
  <div class="badge">EP #45</div>
</div></body></html>"""
    s = w / 270.0
    title = max(10, round(13*s)); ep = max(8, round(8*s))
    quote = max(12, round(16*s)); name = max(8, round(10*s))
    gt = max(7, round(8.5*s));    pad = round(14*s)
    border = max(2, round(2.5*s));radius = round(12*s)
    qpad = f"{round(10*s)}px {round(14*s)}px"
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
{PALETTE}
.tn {{ background: {bg}; color: {color};
       display: grid; grid-template-rows: auto auto auto 1fr; padding: {pad}px {pad}px 0; }}
.tn .header {{ display: flex; flex-direction: column; gap: {round(2*s)}px; margin-bottom: {round(8*s)}px; }}
.tn .header .title {{ font-size: {title}px; }}
.tn .header .ep {{ font-size: {ep}px; }}
.tn .quote {{ font-size: {quote}px; border-width: {border}px; border-radius: {radius}px;
              padding: {qpad}; margin: {round(6*s)}px auto; max-width: 90%; }}
.tn .guest .name {{ font-size: {name}px; }}
.tn .guest .gtitle {{ font-size: {gt}px; }}
.tn .photo {{ grid-row: 4; }}
</style></head><body><div class="tn {variant}">
  <div class="header">
    <div class="title">Can I get that software <span class="blue">in blue?</span></div>
    <div class="ep">Episode #45</div>
  </div>
  <div class="quote">"You can't outsource teaching."</div>
  <div class="guest">
    <div class="name">Dr. Roberta Lenger Kang</div>
    <div class="gtitle">Executive Director · Columbia Teachers College CPET</div>
  </div>
  <div class="photo {photo_class}"></div>
</div></body></html>"""

def html_16_9(variant, w, h):
    if variant == "c1":  bg, color, photo_class = "var(--sib-cream)", "var(--sib-navy)", "photo-panel-c1"
    else:                bg, color, photo_class = "var(--sib-navy)",  "#fff",            "photo-panel-c3"
    s = h / 270.0
    title = max(12, round(15*s)); ep = max(8, round(9*s))
    quote = max(14, round(20*s)); name = max(10, round(12*s))
    gt = max(8, round(9.5*s));    pad_h = round(22*s); pad_v = round(18*s)
    border = max(2, round(3*s));  radius = round(12*s)
    qpad = f"{round(10*s)}px {round(14*s)}px"
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
{PALETTE}
.tn {{ display: flex; }}
.tn .left {{ flex: 1.55; padding: {pad_v}px {pad_h}px;
             display: grid; grid-template-rows: auto 1fr auto;
             background: {bg}; color: {color}; }}
.tn .right {{ flex: 1; }}
.tn .header .title {{ font-size: {title}px; }}
.tn .header .ep {{ font-size: {ep}px; }}
.tn .quote-block {{ align-self: center; }}
.tn .quote {{ font-size: {quote}px; border-width: {border}px; border-radius: {radius}px;
              padding: {qpad}; max-width: 95%; white-space: nowrap; }}
.tn .guest {{ align-self: end; }}
.tn .guest .name {{ font-size: {name}px; }}
.tn .guest .gtitle {{ font-size: {gt}px; {('color: #6c757d;' if variant=='c1' else 'opacity: .85;')} }}
</style></head><body><div class="tn {variant}">
  <div class="left">
    <div class="header">
      <div class="title">Can I get that software <span class="blue">in blue?</span></div>
      <div class="ep">Episode #45</div>
    </div>
    <div class="quote-block">
      <div class="quote">"You can't outsource teaching."</div>
    </div>
    <div class="guest">
      <div class="name">Dr. Roberta Lenger Kang</div>
      <div class="gtitle">Executive Director · Columbia Teachers College CPET</div>
    </div>
  </div>
  <div class="right {photo_class}"></div>
</div></body></html>"""

def html_banner(variant, w, h):
    if variant == "c1":  bg, color, photo_class = "var(--sib-cream)", "var(--sib-navy)", "photo-panel-c1"
    else:                bg, color, photo_class = "var(--sib-navy)",  "#fff",            "photo-panel-c3"
    s = h / 270.0
    if h < 250:
        title = max(10, h//14); ep = max(7, h//22)
        quote = max(14, h//8);  name = max(8, h//18)
        gt = max(7, h//24); pad_v = max(8, h//18); pad_h = max(14, h//12)
    else:
        title = max(14, round(15*s)); ep = max(9, round(9*s))
        quote = max(18, round(22*s)); name = max(11, round(12*s))
        gt = max(9, round(9.5*s)); pad_h = round(28*s); pad_v = round(20*s)
    border = max(2, round(3*s));  radius = round(12*s)
    qpad = f"{round(10*s)}px {round(14*s)}px"
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
{PALETTE}
.tn {{ display: flex; }}
.tn .left {{ flex: 2.5; padding: {pad_v}px {pad_h}px;
             display: grid; grid-template-rows: auto 1fr auto;
             background: {bg}; color: {color}; }}
.tn .right {{ flex: 1; }}
.tn .header {{ display: flex; flex-direction: column; gap: 2px; }}
.tn .header .title {{ font-size: {title}px; }}
.tn .header .ep {{ font-size: {ep}px; }}
.tn .quote-block {{ align-self: center; }}
.tn .quote {{ font-size: {quote}px; border-width: {border}px; border-radius: {radius}px;
              padding: {qpad}; max-width: 95%; white-space: nowrap; }}
.tn .guest {{ align-self: end; }}
.tn .guest .name {{ font-size: {name}px; }}
.tn .guest .gtitle {{ font-size: {gt}px; {('color: #6c757d;' if variant=='c1' else 'opacity: .85;')} }}
</style></head><body><div class="tn {variant}">
  <div class="left">
    <div class="header">
      <div class="title">Can I get that software <span class="blue">in blue?</span></div>
      <div class="ep">Episode #45</div>
    </div>
    <div class="quote-block">
      <div class="quote">"You can't outsource teaching."</div>
    </div>
    <div class="guest">
      <div class="name">Dr. Roberta Lenger Kang</div>
      <div class="gtitle">Columbia Teachers College CPET</div>
    </div>
  </div>
  <div class="right {photo_class}"></div>
</div></body></html>"""

def render_one(variant, name, w, h):
    kind = aspect_kind(w, h)
    html = (html_square if kind == "square"
            else html_16_9 if kind == "wide-16-9"
            else html_banner)(variant, w, h)
    html_path = TMP_DIR / f"{variant}-{name}.html"
    html_path.write_text(html)
    out = OUT_DIR / variant / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
        f"--window-size={w},{h}",
        f"--screenshot={out}",
        f"file://{html_path}",
    ], capture_output=True, text=True)

if __name__ == "__main__":
    for variant in ("c1", "c3"):
        for name, w, h in TARGETS:
            render_one(variant, name, w, h)
    print("Outputs in", OUT_DIR)
```

## 20. Recreating elsewhere

- **For Figma / Canva:** build templates with the layout anatomy above; per-format text styles use the type scale; `contain`-fit photo placeholders; same color tokens.
- **For Midjourney / Sora:** these tools won't reliably reproduce typography. Use them only for stylized treatments (e.g., illustrated guest portraits as photo replacements).
- **For another LLM-driven build:** paste this entire spec as a system prompt, then ask for HTML for one variant × one format. Iterate from there. The QA loop in section 14 is the verification harness.

---

**File location:** `/Users/ctindel/Downloads/sib-thumbnail-spec-prompt.md`
**Companion exports:** `/Users/ctindel/Downloads/sib-exports/{c1,c3}/<size>.png` (10 sizes × 2 variants = 20 PNGs)
**Companion mockup PDFs:** `/Users/ctindel/Downloads/sib-thumbnails-{clean,with-grid}.pdf`
**Generator script:** `/tmp/gen_sib_exports.py`
