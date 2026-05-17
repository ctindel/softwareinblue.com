"""Shared pytest fixtures for podcast post-processing tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def episode_dir(tmp_path: Path) -> Path:
    """Empty Episode99 dir under tmp_path."""
    d = tmp_path / "Episode99"
    d.mkdir()
    return d


@pytest.fixture
def episode_with_final(episode_dir: Path) -> Path:
    """Episode99 with a fake SIB_E99_Final.mp4."""
    (episode_dir / "SIB_E99_Final.mp4").write_bytes(b"fake mp4")
    return episode_dir


@pytest.fixture
def sample_transcript() -> dict:
    """Realistic-shape WhisperX output with two speakers, three segments."""
    return {
        "language": "en",
        "segments": [
            {
                "start": 0.0,
                "end": 2.5,
                "text": "Welcome to Software in Blue.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "Welcome", "start": 0.0, "end": 0.4, "speaker": "SPEAKER_00"},
                    {"word": "to", "start": 0.4, "end": 0.5, "speaker": "SPEAKER_00"},
                    {"word": "Software", "start": 0.5, "end": 1.0, "speaker": "SPEAKER_00"},
                    {"word": "in", "start": 1.0, "end": 1.1, "speaker": "SPEAKER_00"},
                    {"word": "Blue.", "start": 1.1, "end": 1.5, "speaker": "SPEAKER_00"},
                ],
            },
            {
                "start": 2.6,
                "end": 6.0,
                "text": "Today we're talking about Elasticsearch and vector search.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "Today", "start": 2.6, "end": 2.9, "speaker": "SPEAKER_00"},
                    {"word": "we're", "start": 2.9, "end": 3.2, "speaker": "SPEAKER_00"},
                    {"word": "talking", "start": 3.2, "end": 3.6, "speaker": "SPEAKER_00"},
                    {"word": "about", "start": 3.6, "end": 3.9, "speaker": "SPEAKER_00"},
                    {"word": "Elasticsearch", "start": 3.9, "end": 4.6, "speaker": "SPEAKER_00"},
                    {"word": "and", "start": 4.6, "end": 4.8, "speaker": "SPEAKER_00"},
                    {"word": "vector", "start": 4.8, "end": 5.2, "speaker": "SPEAKER_00"},
                    {"word": "search.", "start": 5.2, "end": 5.8, "speaker": "SPEAKER_00"},
                ],
            },
            {
                "start": 6.5,
                "end": 9.0,
                "text": "Great topic. ClickHouse also fits here.",
                "speaker": "SPEAKER_01",
                "words": [
                    {"word": "Great", "start": 6.5, "end": 6.8, "speaker": "SPEAKER_01"},
                    {"word": "topic.", "start": 6.8, "end": 7.2, "speaker": "SPEAKER_01"},
                    {"word": "ClickHouse", "start": 7.4, "end": 8.0, "speaker": "SPEAKER_01"},
                    {"word": "also", "start": 8.0, "end": 8.3, "speaker": "SPEAKER_01"},
                    {"word": "fits", "start": 8.3, "end": 8.6, "speaker": "SPEAKER_01"},
                    {"word": "here.", "start": 8.6, "end": 9.0, "speaker": "SPEAKER_01"},
                ],
            },
        ],
    }


@pytest.fixture
def transcript_json_file(tmp_path: Path, sample_transcript: dict) -> Path:
    p = tmp_path / "transcript.json"
    p.write_text(json.dumps(sample_transcript))
    return p
