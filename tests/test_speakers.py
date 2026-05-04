from __future__ import annotations

from pathlib import Path

import pytest

from scripts.podcast_lib.speakers import (
    SpeakerError,
    apply_overrides,
    load_speakers,
    save_speakers,
)


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    assert load_speakers(tmp_path / "nope.json") == {}


def test_save_and_load(tmp_path: Path) -> None:
    p = tmp_path / "speakers.json"
    save_speakers(p, {"SPEAKER_00": "Chad"})
    assert load_speakers(p) == {"SPEAKER_00": "Chad"}


def test_apply_overrides_parses_pairs() -> None:
    out = apply_overrides({}, ["SPEAKER_00=Chad", "SPEAKER_01=Steve"])
    assert out == {"SPEAKER_00": "Chad", "SPEAKER_01": "Steve"}


def test_apply_overrides_merges() -> None:
    out = apply_overrides({"SPEAKER_00": "Old"}, ["SPEAKER_00=Chad"])
    assert out == {"SPEAKER_00": "Chad"}


def test_apply_overrides_rejects_bad_pair() -> None:
    with pytest.raises(SpeakerError, match="expected KEY=VALUE"):
        apply_overrides({}, ["SPEAKER_00"])
