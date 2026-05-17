#!/usr/bin/env python3
"""One-shot batch driver: walk every transcript run dir under
/tmp/sib/artifacts/ and apply the dehallucination pass to its
transcript.json, then re-render the SRT/VTT/TXT/MD derivatives so all
formats stay in sync. Idempotent — running twice changes nothing the
second time.

Usage:
    python3 scripts/dehallucinate_all.py [--dry-run] [--episode N]

Without --episode it processes every Episode<N>/<run>/ that contains a
transcript.json; with --episode it limits to that single episode (the
LATEST run for it).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root: `python3 scripts/dehallucinate_all.py`.
_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent))

from podcast_lib.dehallucinate import dehallucinate_transcript
from podcast_lib.formatters.srt import render_srt
from podcast_lib.formatters.vtt import render_vtt
from podcast_lib.formatters.txt import render_txt
from podcast_lib.formatters.md import render_md
from podcast_lib.speakers import load_speakers


ARTIFACTS_ROOT = Path("/tmp/sib/artifacts")


def _latest_run(episode_dir: Path) -> Path | None:
    runs = sorted([p for p in episode_dir.iterdir() if p.is_dir()])
    return runs[-1] if runs else None


def process_run(run_dir: Path, dry_run: bool) -> dict:
    tj = run_dir / "transcript.json"
    if not tj.exists():
        return {"run": str(run_dir), "skipped": "no transcript.json"}
    transcript = json.loads(tj.read_text())
    log = dehallucinate_transcript(transcript)
    summary = {"run": str(run_dir), "fixes": len(log)}
    if dry_run:
        summary["dry_run"] = True
        return summary
    if not log:
        return summary
    tj.write_text(json.dumps(transcript, indent=2))
    speakers_path = run_dir / "speakers.json"
    speakers = load_speakers(speakers_path)
    (run_dir / "transcript.srt").write_text(render_srt(transcript))
    (run_dir / "transcript.vtt").write_text(render_vtt(transcript))
    (run_dir / "transcript.txt").write_text(render_txt(transcript))
    (run_dir / "transcript.md").write_text(render_md(transcript, speakers=speakers))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would change without writing files.")
    ap.add_argument("--episode", type=str,
                    help="Limit to a single Episode<N> (e.g. 23 or 23.5).")
    args = ap.parse_args()

    if not ARTIFACTS_ROOT.exists():
        print(f"No artifacts root at {ARTIFACTS_ROOT}", file=sys.stderr)
        sys.exit(1)

    eps: list[Path]
    if args.episode is not None:
        # Try both Episode<N> and Episode{N:02d}
        cand = ARTIFACTS_ROOT / f"Episode{args.episode}"
        if not cand.exists():
            try:
                n = int(args.episode)
                cand = ARTIFACTS_ROOT / f"Episode{n}"
            except ValueError:
                pass
        if not cand.exists():
            print(f"No artifact dir for Episode{args.episode}", file=sys.stderr)
            sys.exit(1)
        eps = [cand]
    else:
        eps = sorted([p for p in ARTIFACTS_ROOT.iterdir()
                      if p.is_dir() and p.name.startswith("Episode")])

    total_fixes = 0
    processed = 0
    for ep in eps:
        run = _latest_run(ep)
        if run is None:
            print(f"  {ep.name}: no run dir, skipping")
            continue
        result = process_run(run, args.dry_run)
        fixes = result.get("fixes", 0)
        total_fixes += fixes
        processed += 1
        marker = " (DRY)" if args.dry_run else ""
        print(f"  {ep.name}: {fixes} fixes{marker}")

    print(f"\n{processed} episodes processed, {total_fixes} total fixes.")


if __name__ == "__main__":
    main()
