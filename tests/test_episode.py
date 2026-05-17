from __future__ import annotations

from pathlib import Path

import pytest

from scripts.podcast_lib.episode import (
    EpisodeError,
    discover_master_video,
    resolve_episode_folder,
)


def test_resolve_episode_folder_existing(episode_dir: Path) -> None:
    resolved = resolve_episode_folder(str(episode_dir))
    assert resolved == episode_dir.resolve()


def test_resolve_episode_folder_missing(tmp_path: Path) -> None:
    with pytest.raises(EpisodeError, match="does not exist"):
        resolve_episode_folder(str(tmp_path / "Episode404"))


def test_resolve_episode_folder_not_a_dir(tmp_path: Path) -> None:
    f = tmp_path / "not_a_dir.txt"
    f.write_text("hi")
    with pytest.raises(EpisodeError, match="not a directory"):
        resolve_episode_folder(str(f))


def test_discover_master_video_single_match(episode_with_final: Path) -> None:
    result = discover_master_video(episode_with_final)
    assert result.name == "SIB_E99_Final.mp4"


def test_discover_master_video_case_insensitive(episode_dir: Path) -> None:
    (episode_dir / "SIB_e99_FINAL.mp4").write_bytes(b"x")
    result = discover_master_video(episode_dir)
    assert result.name == "SIB_e99_FINAL.mp4"


def test_discover_master_video_no_matches(episode_dir: Path) -> None:
    with pytest.raises(EpisodeError, match="Could not find"):
        discover_master_video(episode_dir)


def test_discover_master_video_multiple_matches(episode_dir: Path) -> None:
    (episode_dir / "SIB_E99_Final.mp4").write_bytes(b"x")
    (episode_dir / "SIB_E99_Final_v2.mp4").write_bytes(b"x")
    with pytest.raises(EpisodeError, match="Multiple"):
        discover_master_video(episode_dir)


def test_discover_master_video_override(episode_dir: Path) -> None:
    custom = episode_dir / "totally_other.mp4"
    custom.write_bytes(b"x")
    result = discover_master_video(episode_dir, override=custom)
    assert result == custom.resolve()


def test_discover_master_video_override_missing(episode_dir: Path) -> None:
    with pytest.raises(EpisodeError, match="does not exist"):
        discover_master_video(episode_dir, override=episode_dir / "missing.mp4")
