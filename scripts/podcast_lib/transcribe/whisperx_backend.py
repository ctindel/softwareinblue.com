"""WhisperX transcription backend with auto-detected device.

Device selection:
  - CUDA available → 'cuda', float16
  - Apple MPS available → 'mps' for alignment + diarization, but 'cpu' int8
    for the Whisper transcription pass (CTranslate2 has no Metal support).
  - Otherwise → 'cpu', int8

Stages:
  1. Load Whisper model and transcribe (raw segments, no word ts).
  2. Load alignment model for the detected language and align word-level ts.
  3. Run pyannote diarization, assign speaker labels per word/segment.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import TranscriptionBackend, TranscriptionOptions


def _detect_device() -> tuple[str, str, str]:
    """Return (transcribe_device, transcribe_compute, align_diarize_device)."""
    try:
        import torch  # type: ignore
    except Exception:
        return "cpu", "int8", "cpu"
    if torch.cuda.is_available():
        return "cuda", "float16", "cuda"
    mps_avail = getattr(getattr(torch, "backends", None), "mps", None)
    if mps_avail is not None and torch.backends.mps.is_available():
        return "cpu", "int8", "mps"
    return "cpu", "int8", "cpu"


class WhisperXBackend:
    name = "whisperx"

    def __init__(self) -> None:
        self._tx_dev, self._tx_compute, self._align_dev = _detect_device()

    def device_info(self) -> dict[str, str]:
        return {
            "backend": self.name,
            "transcribe_device": self._tx_dev,
            "transcribe_compute": self._tx_compute,
            "align_diarize_device": self._align_dev,
        }

    def transcribe(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        raw = self.transcribe_raw(audio_path, opts)
        aligned = self.align_words(audio_path, raw)
        return self.assign_speakers(audio_path, aligned, opts)

    def transcribe_raw(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        """Whisper transcription pass. Returns dict with 'language' + 'segments' (no word ts yet)."""
        import whisperx  # type: ignore

        audio = whisperx.load_audio(str(audio_path))
        model = whisperx.load_model(
            opts.model,
            device=self._tx_dev,
            compute_type=self._tx_compute,
            asr_options={"initial_prompt": opts.initial_prompt} if opts.initial_prompt else None,
        )
        result = model.transcribe(audio, batch_size=16)
        del model
        self._free_memory()
        # Stash language at top level for downstream stages.
        return {"language": result["language"], "segments": result["segments"]}

    def align_words(self, audio_path: Path, raw: dict[str, Any]) -> dict[str, Any]:
        """Word-level forced alignment. Returns dict with 'segments' (now with word timestamps)
        and 'language' preserved."""
        import whisperx  # type: ignore

        audio = whisperx.load_audio(str(audio_path))
        align_model, align_meta = whisperx.load_align_model(
            language_code=raw["language"], device=self._align_dev
        )
        aligned = whisperx.align(
            raw["segments"], align_model, align_meta, audio,
            self._align_dev, return_char_alignments=False,
        )
        del align_model
        self._free_memory()
        aligned["language"] = raw["language"]
        return aligned

    def assign_speakers(self, audio_path: Path, aligned: dict[str, Any], opts: TranscriptionOptions) -> dict[str, Any]:
        """Run pyannote diarization and merge speaker labels into aligned segments."""
        import whisperx  # type: ignore

        if not opts.hf_token:
            raise RuntimeError(
                "HF_TOKEN not set. Diarization requires a Hugging Face token "
                "with access to pyannote/speaker-diarization-community-1 and "
                "pyannote/segmentation-community-1. See .env.example for setup."
            )
        try:
            from whisperx.diarize import DiarizationPipeline
            diarize_pipeline = DiarizationPipeline(
                token=opts.hf_token, device=self._align_dev
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load pyannote diarization pipeline: {e}. "
                "Confirm you accepted the gated model terms at BOTH "
                "https://huggingface.co/pyannote/speaker-diarization-community-1 "
                "and https://huggingface.co/pyannote/segmentation-community-1"
            ) from e

        diarize_segments = diarize_pipeline(
            str(audio_path),
            min_speakers=opts.min_speakers,
            max_speakers=opts.max_speakers,
        )
        final = whisperx.assign_word_speakers(diarize_segments, aligned)
        final["language"] = aligned.get("language")
        return final

    def _free_memory(self) -> None:
        try:
            import gc
            gc.collect()
            import torch  # type: ignore
            if self._tx_dev == "cuda":
                torch.cuda.empty_cache()
        except Exception:
            pass
