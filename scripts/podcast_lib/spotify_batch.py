"""Batch-edit all SIB episodes on Spotify for Creators.

Reuses ONE cloak-browser context across episodes so we don't pay the
login + page-warmup cost 45 times. Records per-episode success/fail in
/tmp/spotify_batch_progress.json so a re-run can skip the ones that
already committed cleanly.
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "scripts" / "podcast_lib"))


from cloakbrowser import launch_persistent_context
from dotenv import load_dotenv
load_dotenv(REPO / "scripts" / "podcast_lib" / ".env", override=False)

from spotify_cloak import edit_episode  # type: ignore

PROFILE = Path.home() / ".cloak-profiles" / "spotify-creators"
PROGRESS = Path("/tmp/spotify_batch_progress.json")
LOG = Path("/tmp/spotify_batch.log")


def load_progress() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text())
    return {}


def save_progress(p: dict) -> None:
    PROGRESS.write_text(json.dumps(p, indent=2))


def log(msg: str) -> None:
    print(msg, flush=True)
    with LOG.open("a") as f:
        f.write(msg + "\n")


def main(start: int, end: int, retry_failures: bool = False) -> int:
    progress = load_progress()
    ctx = launch_persistent_context(str(PROFILE), headless=True, humanize=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    try:
        for n in range(start, end + 1):
            key = str(n)
            status = progress.get(key, "")
            if status == "ok":
                log(f"[ep{n}] skip (already done)")
                continue
            if status.startswith("error:") and not retry_failures:
                log(f"[ep{n}] skip (previously failed; --retry-failures to retry)")
                continue
            log(f"=== [ep{n}] start ===")
            try:
                edit_episode(page, n, set_desc=True, allow_empty_show_notes=False)
                progress[key] = "ok"
                log(f"[ep{n}] OK")
            except Exception as e:
                progress[key] = f"error: {e}"
                log(f"[ep{n}] FAIL: {e}")
            save_progress(progress)
            # Brief pause so we're not pounding Spotify
            time.sleep(8)
    finally:
        ctx.close()
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=int, default=1)
    p.add_argument("--end", type=int, default=45)
    p.add_argument("--retry-failures", action="store_true",
                   help="Re-run episodes marked error in the progress file.")
    args = p.parse_args()
    sys.exit(main(args.start, args.end, retry_failures=args.retry_failures))
