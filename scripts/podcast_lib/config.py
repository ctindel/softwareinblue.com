"""Centralized paths and default parameters for the podcast pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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


@dataclass(frozen=True)
class ArtifactPaths:
    """Resolved artifact paths for an episode folder."""
    root: Path

    @property
    def artifacts_dir(self) -> Path:
        return self.root / ARTIFACTS_DIRNAME

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
