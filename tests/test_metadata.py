from __future__ import annotations

from pathlib import Path

from scripts.podcast_lib.metadata import Metadata, load_metadata


def test_metadata_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "metadata.json"
    md = Metadata(path=p)
    md.set("model", "large-v3")
    md.record_stage("transcribe", duration_s=42.0, ok=True)
    md.add_correction({"before": "elastic search", "after": "Elasticsearch", "score": 91.0})
    md.save()

    loaded = load_metadata(p)
    assert loaded.data["model"] == "large-v3"
    assert loaded.data["stages"]["transcribe"]["duration_s"] == 42.0
    assert loaded.data["stages"]["transcribe"]["ok"] is True
    assert len(loaded.data["corrections"]) == 1


def test_metadata_load_missing_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "missing.json"
    md = load_metadata(p)
    assert md.data == {"stages": {}, "corrections": []}
