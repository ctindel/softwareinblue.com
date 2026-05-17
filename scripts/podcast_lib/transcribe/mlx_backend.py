"""MLX Whisper transcription backend (Apple Silicon GPU-accelerated).

CTranslate2 — the engine WhisperX wraps — has no Metal/MPS support, which
pins the WhisperX backend to CPU on Apple Silicon. mlx-whisper is Apple's
own Whisper port targeting MLX (Metal) and reaches ~8–12× realtime on M-class
GPUs vs ~1.7× realtime CPU-int8.

This backend uses mlx-whisper for the transcribe stage only. Alignment and
diarization fall through to the WhisperX backend (those already run on MPS
via pyannote.audio + WhisperX's wav2vec2 alignment models, so no change).

Output shape is normalized back to the WhisperX-compatible dict:
    {"language": "en", "segments": [{"start": ..., "end": ..., "text": ...}, ...]}
so the rest of the pipeline (alignment, diarization, fuzzy correction,
SRT/VTT/MD render) is untouched.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .base import TranscriptionOptions
from .whisperx_backend import WhisperXBackend


# MLX hub repo for the large-v3 weights. mlx-community pre-converts the
# original OpenAI weights to MLX format. Pinning to a specific repo so a
# rename can't silently switch us to a different model.
_DEFAULT_MLX_REPO = "mlx-community/whisper-large-v3-mlx"
# Other options:
#   "mlx-community/whisper-large-v3-turbo"            (faster, slightly less accurate)
#   "mlx-community/whisper-large-v3-mlx-q4"           (4-bit quantized, lower memory)


class MLXWhisperBackend(WhisperXBackend):
    """Subclasses WhisperXBackend so align_words + assign_speakers come for free."""

    name = "mlx"

    def device_info(self) -> dict[str, str]:
        return {
            "backend": self.name,
            "transcribe_device":     "mps",            # via MLX
            "transcribe_compute":    "fp16",
            "transcribe_model_repo": _DEFAULT_MLX_REPO,
            "align_diarize_device":  self._align_dev,
        }

    def transcribe_raw(
        self,
        audio_path: Path,
        opts: TranscriptionOptions,
        on_progress=None,
    ) -> dict[str, Any]:
        """Transcribe via mlx-whisper. The progress callback is currently a no-op:
        mlx-whisper doesn't expose per-chunk progress, but the whole stage
        finishes fast enough on M-series GPUs that a meter isn't critical.
        """
        import mlx_whisper  # type: ignore

        # The mlx-whisper model name selection. opts.model is the WhisperX
        # name like 'large-v3'; map it to the MLX hub repo.
        repo = _model_to_mlx_repo(opts.model)

        t0 = time.monotonic()
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=repo,
            initial_prompt=opts.initial_prompt or None,
            # word_timestamps=False — alignment stage will compute these.
            word_timestamps=False,
            verbose=False,
        )
        elapsed = time.monotonic() - t0
        # Best-effort 100% ping so callers can mark the stage complete.
        if on_progress is not None:
            try:
                on_progress(100.0)
            except Exception:
                pass

        # Normalize to whisperx-shape: language + minimal segments
        # (start, end, text). mlx-whisper's segments include extra fields
        # we strip for cleanliness; the alignment stage rebuilds the fields
        # it needs from start/end/text.
        segments = [
            {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
            for s in result.get("segments", [])
        ]
        return {
            "language": result.get("language", "en"),
            "segments": segments,
            "_mlx_elapsed_s": round(elapsed, 2),
        }


def _model_to_mlx_repo(model_name: str) -> str:
    """Translate a WhisperX model name to the matching mlx-community hub repo."""
    table = {
        "large-v3":         "mlx-community/whisper-large-v3-mlx",
        "large-v2":         "mlx-community/whisper-large-v2-mlx",
        "medium":           "mlx-community/whisper-medium-mlx",
        "small":            "mlx-community/whisper-small-mlx",
        "tiny":             "mlx-community/whisper-tiny-mlx",
        "large-v3-turbo":   "mlx-community/whisper-large-v3-turbo",
    }
    return table.get(model_name, _DEFAULT_MLX_REPO)
