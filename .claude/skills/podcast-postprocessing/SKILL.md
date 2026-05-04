---
name: podcast-postprocessing
description: Post-production tasks for the "Can I Get That Software in Blue?" podcast — transcription, subtitle generation, speaker labeling, plus stubbed future stages (moments, thumbnail copy, descriptions, LinkedIn posts, YouTube/Spotify publishing). Use when the user asks to transcribe an episode, regenerate subtitles, label speakers, or run any other podcast post-production step.
---

# Podcast post-processing

Post-production for the SIB podcast. All real work lives in the Python CLI `podcast.py` at the repo root. This skill never reimplements logic — it dispatches to the CLI.

## When to use

Use whenever the user asks to:
- Transcribe a podcast episode
- Regenerate subtitle files (SRT/VTT) from an existing transcript
- Label speakers (`SPEAKER_00` → "Chad")
- Check status of artifacts for an episode
- Generate clip-worthy moments, thumbnail copy, descriptions, LinkedIn posts, chapters, or publish to YouTube/Spotify (stubbed)

## File conventions

- Episodes live in folders named `EpisodeN/` (e.g., `Episode43/`).
- Master video filename contains the word `Final`, extension `.mp4` (e.g., `SIB_E43_Final.mp4`).
- Discovery rule: glob `EpisodeN/*Final*.mp4` (case-insensitive). Zero matches or multiple matches → CLI exits 2 with a clear error.
- Episodes may live locally, on NAS, network mounts, or S3. **Before invoking the CLI, ask the user where the episode lives.** If it's not local, copy/rsync the file into `/tmp/EpisodeN/` first, then point the CLI at that path.

## Subcommands

```
podcast transcribe EPISODE [--model large-v3] [--min-speakers 2] [--max-speakers 4]
                            [--backend whisperx|deepgram|aws] [--force] [--file PATH]
podcast subtitle EPISODE       # regenerate SRT/VTT from transcript.json
podcast label EPISODE SPEAKER_00=Chad SPEAKER_01=Steve   # update speakers.json + re-render MD
podcast status EPISODE         # show which artifacts exist

# Stubs (print "not implemented yet", exit 0):
podcast moments EPISODE
podcast thumbnail EPISODE
podcast describe EPISODE
podcast linkedin EPISODE
podcast chapters EPISODE
podcast publish-youtube EPISODE
podcast publish-spotify EPISODE
```

## How to invoke

Run from repo root with `python3 podcast.py <subcommand> ...` (or `./podcast.py` after `chmod +x`).

Examples:

```bash
python3 podcast.py transcribe Episode43
python3 podcast.py status Episode43
python3 podcast.py label Episode43 SPEAKER_00=Chad SPEAKER_01=Steve
python3 podcast.py subtitle Episode43
```

## Error handling — STRICT

**On any non-zero exit code from `podcast.py`:**
1. Surface the full error message to the user verbatim.
2. Ask the user how they want to proceed.
3. **Never invent filenames.** Never silently retry with different paths or arguments.
4. If the error is about a missing `*Final*.mp4`, ask the user to confirm the path or pass `--file`.
5. If the error is about a missing `HF_TOKEN`, point them to `.env.example`.
6. If the error is about ffmpeg, point them to `brew install ffmpeg` (Mac) or `apt install ffmpeg` (Linux).

## Outputs

The CLI writes artifacts to `EpisodeN/artifacts/`:
- `audio.wav` — 16kHz mono extract
- `transcript.json` — canonical source of truth (WhisperX-shaped: language + segments + word-level timestamps + speaker labels)
- `transcript.srt`, `transcript.vtt`, `transcript.txt`, `transcript.md` — derivatives
- `speakers.json` — SPEAKER_NN → human name mapping
- `metadata.json` — model used, params, per-stage timings, fuzzy correction log
