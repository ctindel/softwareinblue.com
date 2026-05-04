"""AWS Transcribe backend stub.

Will speak the same Protocol as WhisperX once implemented.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import TranscriptionOptions


class AWSTranscribeBackend:
    name = "aws"

    def device_info(self) -> dict[str, str]:
        return {"backend": self.name, "transcribe_device": "cloud"}

    def transcribe(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        raise NotImplementedError(
            "AWS Transcribe backend not yet implemented. Use --backend whisperx."
        )
