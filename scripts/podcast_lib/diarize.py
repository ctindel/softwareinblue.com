"""Standalone pyannote diarization for backends that don't include it.

The WhisperX backend handles diarization internally; this module exists
so future backends (Deepgram, AWS) can reuse the same pyannote pipeline.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def diarize(audio_path: Path, *, hf_token: str, min_speakers: int, max_speakers: int,
            device: str = "cpu") -> Any:
    """Run pyannote/speaker-diarization-3.1. Returns the pipeline output."""
    if not hf_token:
        raise RuntimeError(
            "HF_TOKEN not set. Diarization requires a Hugging Face token. "
            "See .env.example."
        )
    try:
        from pyannote.audio import Pipeline  # type: ignore
    except Exception as e:
        raise RuntimeError(f"pyannote.audio unavailable: {e}") from e

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", use_auth_token=hf_token
    )
    try:
        import torch  # type: ignore
        pipeline.to(torch.device(device))
    except Exception:
        pass
    return pipeline(
        str(audio_path),
        min_speakers=min_speakers,
        max_speakers=max_speakers,
    )
