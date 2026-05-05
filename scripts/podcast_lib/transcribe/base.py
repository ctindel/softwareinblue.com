"""Transcription backend protocol.

A backend ingests a path to a 16kHz mono WAV plus options, and returns a
WhisperX-shaped dict with `language` and `segments` (each with words +
optional speaker label).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class TranscriptionOptions:
    model: str
    initial_prompt: str
    min_speakers: int
    max_speakers: int
    hf_token: str | None


class TranscriptionBackend(Protocol):
    """Implementations transcribe + word-align + diarize and return a single dict."""

    name: str

    def transcribe(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        ...

    def device_info(self) -> dict[str, str]:
        ...

    # Optional staged API. Backends implementing these unlock checkpointing.
    # Backends that only implement `transcribe` should raise NotImplementedError
    # from these so the orchestrator falls back to the all-in-one path.
    def transcribe_raw(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        ...

    def align_words(self, audio_path: Path, raw: dict[str, Any]) -> dict[str, Any]:
        ...

    def assign_speakers(self, audio_path: Path, aligned: dict[str, Any], opts: TranscriptionOptions) -> dict[str, Any]:
        ...
