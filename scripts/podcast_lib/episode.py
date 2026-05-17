"""Episode folder discovery and master-video lookup."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


class EpisodeError(Exception):
    """Raised when episode discovery or validation fails. Exit code 2."""


def resolve_episode_folder(folder: str | Path) -> Path:
    """Validate the given episode folder exists and is a directory.

    Returns the absolute, resolved path.
    """
    p = Path(folder).expanduser()
    if not p.exists():
        raise EpisodeError(
            f"Episode folder does not exist: {p}. "
            "Confirm the path or stage the episode locally first."
        )
    if not p.is_dir():
        raise EpisodeError(f"Path is not a directory: {p}")
    return p.resolve()


def discover_master_video(folder: Path, override: Optional[Path] = None) -> Path:
    """Find the master *Final*.mp4 in the given folder, case-insensitive.

    If `override` is given, it must be an existing file and is returned directly.
    Zero matches → raise. Multiple matches → raise listing all.
    """
    if override is not None:
        op = Path(override).expanduser()
        if not op.exists() or not op.is_file():
            raise EpisodeError(f"--file override does not exist: {op}")
        return op.resolve()

    folder = resolve_episode_folder(folder)
    matches = sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".mp4"
        and "final" in p.stem.lower()
    )
    if not matches:
        raise EpisodeError(
            f"Could not find *Final*.mp4 in {folder}. "
            "Please confirm the file exists and matches the expected pattern, "
            "or pass --file to override."
        )
    if len(matches) > 1:
        listing = "\n  ".join(str(m) for m in matches)
        raise EpisodeError(
            f"Multiple *Final*.mp4 candidates in {folder}:\n  {listing}\n"
            "Pass --file to choose explicitly."
        )
    return matches[0].resolve()
