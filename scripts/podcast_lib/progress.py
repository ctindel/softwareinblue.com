"""Progress reporter for long-running transcribe / align stages.

Whisper and WhisperX expose a `progress_callback(percent_complete: float)`
hook that fires after every internal batch.  We wrap that with a tracker
that:
  - throttles console output to one line per N% increment (so log files
    stay readable, especially when 3 transcribes run in parallel),
  - records the current fraction + elapsed + ETA into metadata.json so
    external observers (e.g. `podcast.py status`) can poll it,
  - atomically rewrites a single-line progress file every callback so
    you can `cat` or `watch -n5 cat …` from another terminal to watch a
    backgrounded run live without touching the running process,
  - prints elapsed and ETA in a human-friendly form.

Both whisperx.transcribe and whisperx.align pass the value as a percent
(0..100), but a stricter fraction (0..1) shape is also supported — the
tracker normalizes either form.
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from rich.console import Console
    from .metadata import Metadata


def _fmt_seconds(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def default_progress_file_path(episode_num: int, pid: Optional[int] = None) -> Path:
    """The convention for backgrounded transcribes: a per-episode + per-PID
    file under /tmp so multiple parallel runs don't clobber each other and
    you can find them at a glance.
    """
    p = pid if pid is not None else os.getpid()
    return Path(f"/tmp/sib_transcribe_progress_episode{episode_num}_{p}.txt")


class ProgressTracker:
    """Callable progress hook. Pass an instance as `progress_callback=` to
    whisperx.transcribe / align."""

    def __init__(
        self,
        label: str,
        console: "Console",
        md_state: "Metadata",
        md_key: str,
        progress_file: Optional[Path] = None,
        emit_every: float = 0.05,
    ) -> None:
        self.label = label
        self.console = console
        self.md_state = md_state
        self.md_key = md_key
        self.progress_file = progress_file
        self.emit_every = emit_every  # fractional units, 0.05 = every 5%
        self.start = time.monotonic()
        # Sentinel below 0 so the first call always emits.
        self._last_emitted = -1.0
        self._first_done = False

    def __call__(self, value: float) -> None:
        # WhisperX feeds percents (0..100); accept fractions too just in case.
        frac = value / 100.0 if value > 1.5 else float(value)
        frac = max(0.0, min(1.0, frac))
        elapsed = time.monotonic() - self.start

        eta = (elapsed * (1.0 - frac) / frac) if frac > 1e-6 else 0.0

        # Throttle console output: emit on first call, every emit_every step,
        # and the final 100%.
        should_print = (
            not self._first_done
            or frac >= self._last_emitted + self.emit_every
            or frac >= 1.0 - 1e-6
        )
        if should_print:
            if frac >= 1.0 - 1e-6:
                self.console.print(
                    f"[cyan]{self.label}[/cyan] 100%  total {_fmt_seconds(elapsed)}"
                )
            else:
                self.console.print(
                    f"[cyan]{self.label}[/cyan] "
                    f"{frac * 100:5.1f}%  elapsed {_fmt_seconds(elapsed)}  "
                    f"ETA {_fmt_seconds(eta)}"
                )
            self._last_emitted = frac
            self._first_done = True

        # Always update the metadata so external pollers see fresh state.
        try:
            self.md_state.set(
                self.md_key,
                {
                    "fraction": round(frac, 4),
                    "elapsed_s": round(elapsed, 1),
                    "eta_s": round(eta, 1) if frac < 1.0 else 0.0,
                    "updated_at": time.time(),
                },
            )
            self.md_state.save()
        except Exception:
            # Don't let a metadata write hiccup take down the whole stage.
            pass

        # If a per-run progress file was requested, atomically overwrite it
        # with a one-line snapshot. `cat` or `watch -n5 cat …` from another
        # terminal will then show the latest state of a backgrounded run.
        if self.progress_file is not None:
            line = (
                f"{self.label}  {frac * 100:5.1f}%  "
                f"elapsed {_fmt_seconds(elapsed)}  ETA {_fmt_seconds(eta)}  "
                f"pid={os.getpid()}  updated={datetime.now().isoformat(timespec='seconds')}\n"
            )
            try:
                tmp = self.progress_file.with_suffix(self.progress_file.suffix + ".tmp")
                tmp.write_text(line)
                os.replace(tmp, self.progress_file)
            except Exception:
                pass


def fmt_progress_line(progress: dict, label: str) -> str:
    """Render a one-line summary of a progress dict for `status` output."""
    if not progress:
        return f"{label}: not started"
    frac = progress.get("fraction", 0.0)
    elapsed = progress.get("elapsed_s", 0.0)
    eta = progress.get("eta_s", 0.0)
    if frac >= 1.0 - 1e-6:
        return f"{label}: 100%  total {_fmt_seconds(elapsed)}"
    return (
        f"{label}: {frac * 100:5.1f}%  elapsed {_fmt_seconds(elapsed)}"
        f"  ETA {_fmt_seconds(eta)}"
    )
