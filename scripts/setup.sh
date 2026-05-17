#!/usr/bin/env bash
# Install everything the podcast post-processing pipeline needs.
# Idempotent — safe to re-run.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

say() { printf '\n\033[1;36m▶\033[0m %s\n' "$*"; }

# --- 1. ffmpeg ---------------------------------------------------------------
if ! command -v ffmpeg >/dev/null 2>&1; then
  say "Installing ffmpeg"
  case "$(uname -s)" in
    Darwin)
      command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh"; exit 1; }
      brew install ffmpeg
      ;;
    Linux)
      sudo apt-get update && sudo apt-get install -y ffmpeg
      ;;
    *)
      echo "Unsupported OS. Install ffmpeg manually." >&2; exit 1;;
  esac
else
  say "ffmpeg already installed: $(ffmpeg -version | head -n 1)"
fi

# --- 2. Python deps ----------------------------------------------------------
say "Installing Python deps from requirements.txt"
PY="${PYTHON:-python3}"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt

# --- 3. .env -----------------------------------------------------------------
ENV_DIR="scripts/podcast_lib"
if [ ! -f "$ENV_DIR/.env" ]; then
  say "Creating $ENV_DIR/.env from $ENV_DIR/.env.example (you must paste your HF token before first transcribe run)"
  cp "$ENV_DIR/.env.example" "$ENV_DIR/.env"
  echo "  Edit $(pwd)/$ENV_DIR/.env and set HF_TOKEN=hf_xxx (read scope is enough)."
  echo "  Accept gated model terms at https://huggingface.co/pyannote/speaker-diarization-community-1"
fi

# --- 4. Pre-warm the rembg U²-Net model (used by the thumbnail BG remover) ---
if "$PY" -c "import rembg" 2>/dev/null; then
  say "Pre-warming rembg U²-Net model"
  "$PY" -c "from rembg import new_session; new_session('u2net')" || true
fi

# --- 5. Smoke test -----------------------------------------------------------
say "Smoke test: importing the podcast library"
"$PY" -c "from scripts.podcast_lib.commands.transcribe import run; print('podcast pipeline import OK')"

say "Setup complete."
echo
echo "Next steps:"
echo "  1. Edit $ENV_DIR/.env to set HF_TOKEN."
echo "  2. Place an episode video at EpisodeN/SIB_E<N>_Final.mp4 (or anywhere; pass the path)."
echo "  3. Run: $PY podcast.py transcribe /path/to/EpisodeN"
echo "     ...or: ./scripts/run.sh /path/to/EpisodeN"
