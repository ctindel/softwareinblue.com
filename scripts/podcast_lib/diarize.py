"""Standalone pyannote diarization for backends that don't include it.

The WhisperX backend handles diarization internally; this module exists
so future backends (Deepgram, AWS) can reuse the same pyannote pipeline.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def diarize(audio_path: Path, *, hf_token: str, min_speakers: int, max_speakers: int,
            device: str = "cpu") -> Any:
    """Run pyannote/speaker-diarization-community-1. Returns the pipeline output."""
    import os
    offline = os.environ.get("HF_HUB_OFFLINE") in ("1", "true", "True")
    if not hf_token and not offline:
        raise RuntimeError(
            "HF_TOKEN not set. Diarization requires a Hugging Face token. "
            "See .env.example. If the model is already cached locally, "
            "re-run with HF_HUB_OFFLINE=1 to use the cached copy."
        )
    try:
        from pyannote.audio import Pipeline  # type: ignore
    except Exception as e:
        raise RuntimeError(f"pyannote.audio unavailable: {e}") from e

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-community-1", token=hf_token
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
