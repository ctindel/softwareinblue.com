"""Walk the Spotify dashboard episode list (paginated) and build a
complete map of episode_number → spotify_id. Writes /tmp/spotify_ids.json."""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "scripts" / "podcast_lib"))
from cloakbrowser import launch_persistent_context
from dotenv import load_dotenv
load_dotenv(REPO / "scripts" / "podcast_lib" / ".env", override=False)

PROFILE = Path.home() / ".cloak-profiles" / "spotify-creators"
SHOW_ID = "25r9ckggqIv6rGU8ca0WP2"
LIST_URL = f"https://creators.spotify.com/pod/show/{SHOW_ID}/episodes"

ctx = launch_persistent_context(str(PROFILE), headless=True, humanize=True)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto(LIST_URL)
page.wait_for_timeout(6000)

mapping = {}


def harvest():
    """Pull all (number, spotify_id) pairs visible right now."""
    found = page.evaluate("""() => {
      return Array.from(document.querySelectorAll('a[href*="/episode/"][href$="/details"]')).map(a => {
        const m = (a.href || '').match(/\\/episode\\/([A-Za-z0-9]+)\\/details/);
        const txt = (a.innerText||'').trim();
        const nm = txt.match(/(?:Episode\\s+|#\\s*)(\\d+(?:\\.\\d+)?)/i);
        return {id: m && m[1], num: nm && nm[1], text: txt.slice(0, 60)};
      }).filter(x => x.id);
    }""")
    for f in found:
        if f.get("num"):
            try:
                num = float(f["num"]) if "." in f["num"] else int(f["num"])
                mapping[num] = f["id"]
            except ValueError:
                pass
    return len(found)


# First page
harvest()

# Look for any pagination button at the bottom and click "next" / arrow.
for i in range(20):
    nav = page.evaluate("""() => {
      // Find pagination buttons. Spotify typically labels them aria-label="Next" or shows arrow icons.
      const candidates = Array.from(document.querySelectorAll('button, a')).filter(b => {
        const lab = (b.getAttribute('aria-label') || '') + ' ' + (b.innerText || '');
        return b.offsetParent !== null && /next|older|page \\d+|→|>/i.test(lab);
      }).slice(0, 6).map(b => ({
        text: (b.innerText||'').trim().slice(0, 30),
        ariaLabel: b.getAttribute('aria-label'),
        disabled: b.disabled,
      }));
      return candidates;
    }""")
    print(f"iter {i}: nav candidates: {nav}")
    # Try clicking "Next" / arrow button
    clicked = page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button')).filter(b =>
        b.offsetParent !== null && !b.disabled
      );
      // Prefer aria-label "Next page"
      let target = btns.find(b => /next\\s*page/i.test(b.getAttribute('aria-label') || ''));
      if (!target) target = btns.find(b => /^next$/i.test((b.innerText||'').trim()));
      if (!target) target = btns.find(b => (b.getAttribute('aria-label')||'').toLowerCase() === 'next');
      if (target) { target.click(); return 'clicked-next'; }
      return 'no-next-button';
    }""")
    print(f"  clicked: {clicked}")
    if clicked == "no-next-button":
        break
    page.wait_for_timeout(3500)
    before = len(mapping)
    harvest()
    after = len(mapping)
    print(f"  mapping: {before} → {after}")
    if before == after:
        break

print(f"\n=== total mapped: {len(mapping)} ===")
print(json.dumps({str(k): v for k, v in sorted(mapping.items(), key=lambda kv: (isinstance(kv[0], float), kv[0]))}, indent=2))
Path("/tmp/spotify_ids.json").write_text(json.dumps({str(k): v for k, v in mapping.items()}, indent=2))
print("saved /tmp/spotify_ids.json")
ctx.close()
