#!/usr/bin/env bash
# End-to-end podcast post-processing for one episode.
#   ./scripts/run.sh /path/to/EpisodeN
#
# Runs: transcribe → status. Re-runs are resumable (per-stage checkpoints).
# Pass --force as the second arg to redo every stage.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

EPISODE="${1:-}"
FORCE_FLAG=""
if [ "${2:-}" = "--force" ]; then FORCE_FLAG="--force"; fi

if [ -z "$EPISODE" ]; then
  echo "Usage: $0 /path/to/EpisodeN [--force]" >&2
  exit 2
fi
if [ ! -d "$EPISODE" ]; then
  echo "Not a directory: $EPISODE" >&2
  exit 2
fi

PY="${PYTHON:-python3}"
"$PY" podcast.py transcribe "$EPISODE" $FORCE_FLAG
echo
"$PY" podcast.py status "$EPISODE"
