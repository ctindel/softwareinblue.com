#!/usr/bin/env python3
"""Render an HTML gallery for an episode's thumbnail variants.

Writes  hugosite/static/img/episode/Episode<N>/index.html

Usage:
    python3 design/gen_thumbnail_gallery.py 44
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EP = int(sys.argv[1]) if len(sys.argv) > 1 else 45

THUMB_DIR = REPO_ROOT / "hugosite" / "static" / "img" / "episode" / f"Episode{EP:02d}"
EP_MD = REPO_ROOT / "hugosite" / "content" / "episode" / f"episode{EP}.md"

VARIANTS = [
    ("a1",  "A1",  "Navy + cornflower highlight, face-forward"),
    ("a2",  "A2",  "Full cornflower, face-forward"),
    ("a3",  "A3",  "Face-forward, source-at-bottom"),
    ("a1w", "A1w", "A1 layout, all-three balloon photo"),
    ("a2w", "A2w", "A2 layout, all-three balloon photo"),
    ("a3w", "A3w", "A3 layout, all-three balloon photo"),
    ("c1",  "C1",  "Magazine split — cream + cornflower accent"),
    ("c2",  "C2",  "Magazine split — cornflower left"),
    ("c3",  "C3",  "Magazine split — navy left"),
    ("w1",  "W1",  "Whimsical balloon, cornflower panel"),
    ("w2",  "W2",  "Whimsical balloon, navy panel"),
    ("d1",  "D1",  "Hot Take — DOAC-style big text, red highlight"),
    ("d2",  "D2",  "Hot Take — DOAC-style big text, cornflower highlight"),
]
SIZES = [
    ("thumbnail-youtube-1920x1080",  "1920×1080  YouTube"),
    ("banner-youtube-2560x1440",     "2560×1440  YouTube banner"),
    ("banner-twitter-1500x500",      "1500×500   Twitter banner"),
    ("banner-facebook-851x315",      "851×315    Facebook banner"),
    ("banner-linkedin-1128x191",     "1128×191   LinkedIn banner"),
    ("podcast-cover-3000x3000",      "3000×3000  Podcast cover"),
    ("short-tiktok-1080x1920",       "1080×1920  Short / Reel"),
]
PROFILE_PICS = [
    ("profilepic-twitter-400x400",   "400×400   Twitter PP"),
    ("profilepic-instagram-320x320", "320×320   Instagram PP"),
    ("profilepic-tiktok-200x200",    "200×200   TikTok PP"),
    ("profilepic-facebook-170x170",  "170×170   Facebook PP"),
]


def _ep_meta() -> tuple[str, str]:
    """Return (title-line, tagline) from the episode .md frontmatter."""
    title = f"Episode {EP}"
    tagline = ""
    if EP_MD.exists():
        text = EP_MD.read_text()
        m = re.search(r'^title\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if m:
            title = m.group(1)
        m = re.search(r'^tagline\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if m:
            tagline = m.group(1)
    return title, tagline


def main() -> int:
    if not THUMB_DIR.exists():
        print(f"missing {THUMB_DIR}", file=sys.stderr)
        return 2
    title, tagline = _ep_meta()

    sections_html = []
    for slug, label, desc in VARIANTS:
        figs = []
        for n, lbl in SIZES + PROFILE_PICS:
            p = THUMB_DIR / slug / f"{n}.png"
            if not p.exists():
                continue
            cls = " pp" if (n, lbl) in [(x, y) for x, y in PROFILE_PICS] else ""
            figs.append(
                f'<figure class="cell{cls}"><a href="{slug}/{n}.png" target="_blank">'
                f'<img src="{slug}/{n}.png" loading="lazy" alt="{slug} {n}"></a>'
                f'<figcaption><span class="n">{slug}</span><span>{lbl}</span></figcaption>'
                f'</figure>'
            )
        sections_html.append(
            f'<section data-v="{slug}">'
            f'<h2>{label} <span class="tag">{slug}</span></h2>'
            f'<p class="desc">{desc}</p>'
            f'<div class="grid">{"".join(figs)}</div>'
            f'</section>'
        )

    btns = '<button class="on" data-v="all">all</button>' + "".join(
        f'<button data-v="{s}">{label}</button>' for s, label, _ in VARIANTS
    )

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>SIB · Episode {EP} · Thumbnail variants</title>
<style>
  :root {{ --bg:#0a1f3d; --fg:#f4f1ea; --accent:#6495ED; --muted:#7d8aa3; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:24px 32px 64px; font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;
          background:var(--bg); color:var(--fg); }}
  h1 {{ font-size:22px; margin:0 0 6px; }}
  h1 .b {{ color:var(--accent); }}
  .sub {{ color:var(--muted); font-size:13px; margin:0 0 8px; }}
  .quote {{ color:var(--fg); background:rgba(100,149,237,0.08); border-left:3px solid var(--accent);
            padding:8px 12px; font-style:italic; margin:0 0 24px; max-width:900px; }}
  .nav {{ display:flex; gap:14px; align-items:center; margin:0 0 16px; }}
  .nav a {{ color:var(--accent); text-decoration:none; font-weight:600; }}
  .nav a:hover {{ text-decoration:underline; }}
  .controls {{ display:flex; flex-wrap:wrap; gap:8px; margin:0 0 24px; }}
  .controls button {{ background:#1a3460; color:#fff; border:1px solid #2a4a80; border-radius:999px;
                       padding:6px 12px; font-size:12px; cursor:pointer; }}
  .controls button.on {{ background:var(--accent); border-color:var(--accent); color:var(--bg); font-weight:700; }}
  section {{ margin-bottom:36px; padding:18px 22px; background:rgba(255,255,255,.03); border-radius:12px; }}
  section h2 {{ margin:0 0 4px; font-size:18px; letter-spacing:.04em; }}
  section h2 .tag {{ display:inline-block; background:var(--accent); color:var(--bg);
                      font-size:11px; padding:2px 8px; border-radius:999px; vertical-align:middle;
                      margin-left:8px; font-weight:800; letter-spacing:.06em; }}
  section .desc {{ color:var(--muted); font-size:12px; margin:0 0 14px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
           gap:14px; align-items:start; }}
  figure.cell {{ margin:0; background:#0e2750; border-radius:8px; overflow:hidden; border:1px solid #1c3a6b; }}
  figure.cell img {{ display:block; width:100%; height:auto; background:#000; }}
  figcaption {{ padding:8px 10px; font-size:11px; color:var(--muted);
                 display:flex; justify-content:space-between; gap:10px; }}
  figcaption .n {{ color:var(--fg); font-weight:600; }}
  figure.cell.pp img {{ width:auto; max-width:100%; margin:0 auto; padding:16px; background:#0a1f3d; }}
</style></head>
<body>
<div class="nav"><a href="../">← all episodes</a></div>
<h1>{title}</h1>
<p class="sub">13 base variants × 11 sizes per variant. Click an image to open at full size.</p>
{f'<p class="quote">"{tagline}"</p>' if tagline else ''}
<div class="controls" id="filter">{btns}</div>
{''.join(sections_html)}
<script>
document.getElementById("filter").addEventListener("click", e => {{
  const b = e.target.closest("button"); if (!b) return;
  document.querySelectorAll("#filter button").forEach(x => x.classList.remove("on"));
  b.classList.add("on");
  const v = b.dataset.v;
  document.querySelectorAll("section").forEach(s => {{
    s.style.display = (v === "all" || s.dataset.v === v) ? "" : "none";
  }});
}});
</script>
</body></html>
"""
    out = THUMB_DIR / "index.html"
    out.write_text(html)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
