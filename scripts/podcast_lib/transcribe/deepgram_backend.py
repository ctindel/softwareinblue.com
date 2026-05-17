"""Deepgram backend stub.

Will speak the same Protocol as WhisperX once implemented.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import TranscriptionOptions


class DeepgramBackend:
    name = "deepgram"

    def device_info(self) -> dict[str, str]:
        return {"backend": self.name, "transcribe_device": "cloud"}

    def transcribe(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        raise NotImplementedError(
            "Deepgram backend not yet implemented. Use --backend whisperx."
        )

    def transcribe_raw(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        raise NotImplementedError

    def align_words(self, audio_path: Path, raw: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def assign_speakers(self, audio_path: Path, aligned: dict[str, Any], opts: TranscriptionOptions) -> dict[str, Any]:
        raise NotImplementedError
