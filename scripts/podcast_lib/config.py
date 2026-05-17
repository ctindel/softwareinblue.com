"""Centralized paths and default parameters for the podcast pipeline."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


ARTIFACTS_BASE = Path(os.environ.get("SIB_ARTIFACTS_BASE", "/tmp/sib/artifacts"))
RUN_TIMESTAMP_FORMAT = "%Y%m%d-%H:%M:%S"

ARTIFACTS_DIRNAME = "artifacts"
AUDIO_FILENAME = "audio.wav"
TRANSCRIPT_JSON = "transcript.json"
TRANSCRIPT_RAW_JSON = "transcript.raw.json"
TRANSCRIPT_ALIGNED_JSON = "transcript.aligned.json"
TRANSCRIPT_SRT = "transcript.srt"
TRANSCRIPT_VTT = "transcript.vtt"
TRANSCRIPT_TXT = "transcript.txt"
TRANSCRIPT_MD = "transcript.md"
SPEAKERS_JSON = "speakers.json"
METADATA_JSON = "metadata.json"

DEFAULT_MODEL = "large-v3"
DEFAULT_MIN_SPEAKERS = 2
DEFAULT_MAX_SPEAKERS = 4
DEFAULT_BACKEND = "whisperx"

# Audio extraction
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1

# Subtitle cue limits
MAX_CUE_SECONDS = 3.0
MAX_CUE_WORDS = 7

# Whisper initial_prompt token cap. Whisper's prompt is ~224 tokens.
PROMPT_TOKEN_BUDGET = 200

# Fuzzy correction threshold (rapidfuzz ratio, 0-100). Higher = stricter.
FUZZY_MATCH_THRESHOLD = 88


def episode_number_from_folder(folder: Path) -> int:
    """Extract the episode number from a folder name like 'Episode45' → 45."""
    m = re.search(r"(\d+)", folder.name)
    if not m:
        raise ValueError(
            f"Cannot extract episode number from folder '{folder.name}'. "
            f"Expected name like 'Episode45'."
        )
    return int(m.group(1))


def _episode_run_root(episode_num: int) -> Path:
    """The directory containing all timestamped runs for one episode."""
    return ARTIFACTS_BASE / f"Episode{episode_num}"


def latest_run_dir(episode_num: int) -> Optional[Path]:
    """Return the most recent run directory for the episode, or None if no runs."""
    root = _episode_run_root(episode_num)
    if not root.exists():
        return None
    runs = sorted(p for p in root.iterdir() if p.is_dir())
    return runs[-1] if runs else None


def new_run_dir(episode_num: int, *, when: Optional[datetime] = None) -> Path:
    """Allocate a new timestamped run dir under /tmp/sib/artifacts/EpisodeNN/."""
    when = when or datetime.now()
    return _episode_run_root(episode_num) / when.strftime(RUN_TIMESTAMP_FORMAT)


@dataclass(frozen=True)
class ArtifactPaths:
    """Resolved artifact paths for one transcribe run.

    `artifacts_dir` is the timestamped run directory under
    `/tmp/sib/artifacts/Episode<N>/<YYYYMMDD-HH:MM:SS>/`.
    """
    artifacts_dir: Path

    @classmethod
    def for_run(cls, run_dir: Path) -> "ArtifactPaths":
        return cls(artifacts_dir=run_dir)

    @classmethod
    def latest_or_new(cls, episode_num: int, *, force_new: bool = False) -> "ArtifactPaths":
        """If a previous run dir exists and has no final transcript.json,
        resume into it. Otherwise allocate a new timestamped dir.
        Pass force_new=True to always allocate a new dir.
        """
        if not force_new:
            latest = latest_run_dir(episode_num)
            if latest is not None and not (latest / TRANSCRIPT_JSON).exists():
                return cls(artifacts_dir=latest)
        return cls(artifacts_dir=new_run_dir(episode_num))

    @property
    def audio(self) -> Path:
        return self.artifacts_dir / AUDIO_FILENAME

    @property
    def transcript_json(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_JSON

    @property
    def transcript_raw(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_RAW_JSON

    @property
    def transcript_aligned(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_ALIGNED_JSON

    @property
    def transcript_srt(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_SRT

    @property
    def transcript_vtt(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_VTT

    @property
    def transcript_txt(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_TXT

    @property
    def transcript_md(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_MD

    @property
    def speakers(self) -> Path:
        return self.artifacts_dir / SPEAKERS_JSON

    @property
    def metadata(self) -> Path:
        return self.artifacts_dir / METADATA_JSON

    def ensure(self) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
