"""Audio extraction from MP4 → 16kHz mono WAV via ffmpeg."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import TARGET_CHANNELS, TARGET_SAMPLE_RATE


class AudioError(Exception):
    """Raised when audio extraction fails. Exit code 2."""


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise AudioError(
            "ffmpeg not found on PATH. Install it: 'brew install ffmpeg' (Mac) "
            "or 'apt install ffmpeg' (Linux)."
        )


def extract_audio(video: Path, dest_wav: Path, *, force: bool = False) -> Path:
    """Extract a 16kHz mono WAV from the given video file.

    Returns the destination path. If `dest_wav` already exists and
    `force` is False, returns immediately.
    """
    ensure_ffmpeg()
    if dest_wav.exists() and not force:
        return dest_wav
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-ac", str(TARGET_CHANNELS),
        "-ar", str(TARGET_SAMPLE_RATE),
        "-vn",
        str(dest_wav),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AudioError(
            f"ffmpeg failed (exit {proc.returncode}):\n{proc.stderr}"
        )
    if not dest_wav.exists():
        raise AudioError(f"ffmpeg succeeded but output missing: {dest_wav}")
    return dest_wav
