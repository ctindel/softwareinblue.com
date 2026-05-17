# Podcast Post-Processing Skill — Design

**Date:** 2026-05-04
**Project:** `softwareinblue.com` — "Can I Get That Software in Blue?" podcast
**Status:** Approved design, ready for implementation plan

## Goal

Automate post-production for the SIB podcast. Initial scope: transcription + subtitle generation. Designed to grow into clip-finding, thumbnail copy, show descriptions, LinkedIn posts, YouTube/Spotify publishing.

## Architecture

**Thin skill, fat CLI.**

- `.claude/skills/podcast-postprocessing/SKILL.md` — single-page guide telling Claude when to invoke and what subcommands exist. No business logic.
- `podcast.py` — Typer entrypoint at repo root. Dispatches to subcommand modules.
- `scripts/podcast_lib/` — all real work. Library + per-command modules.

Skill never reimplements logic; it shells out to `podcast.py`.

## Design principles

1. **Stage outputs are durable.** Each stage writes canonical artifacts. Later stages read those, never re-run prior stages. Pipeline resumable.
2. **`transcript.json` is source of truth.** All downstream stages (subtitle, moments, descriptions) read it. Never re-transcribe to regenerate a derivative.
3. **Backend interface for transcription.** `TranscriptionBackend` Protocol. WhisperX is the default. Deepgram + AWS stubs raise `NotImplementedError` from `transcribe()`. Swap without rewriting callers.
4. **Device auto-detect.** Backend probes CUDA → MPS → CPU. Same code path on Mac M-series and Linux GPU box.
5. **Stop and ask on error.** No silent retry, no filename guessing. SKILL.md explicitly tells Claude to surface errors.

## File conventions

- Episode folder: `EpisodeN/` (e.g., `Episode43/`).
- Master video: filename contains `Final`, extension `.mp4`. Discovery glob: `EpisodeN/*Final*.mp4` (case-insensitive).
- Zero matches → exit 2 with clear error.
- Multiple matches → exit 2 listing all matches, ask which.
- Episodes can live on NAS / S3 / network mount. The **SKILL** (not the CLI) asks the user where `EpisodeN` lives before invoking `podcast transcribe`. If non-local, the SKILL stages the file into `/tmp/EpisodeN/` first, then invokes the CLI with that path. The CLI itself only sees a local folder.

## Output layout

Created by the scripts under `EpisodeN/artifacts/`:

```
artifacts/
  audio.wav            # 16kHz mono, ffmpeg-extracted
  transcript.json      # canonical: WhisperX raw output, word-level timestamps, speaker IDs
  transcript.srt
  transcript.vtt
  transcript.txt       # plain text, no timestamps
  transcript.md        # speaker-labeled paragraphs
  speakers.json        # SPEAKER_00 → "Chad" mapping, editable
  metadata.json        # duration, model used, params, per-stage timings, fuzzy correction log
```

## Stage 1: Transcription

1. **Audio extraction** — ffmpeg, 16kHz mono WAV → `artifacts/audio.wav`.
2. **Transcribe** — WhisperX, model `large-v3` default, configurable via `--model`.
3. **Word-level alignment** — WhisperX forced alignment (wav2vec2 via PyTorch, MPS-capable).
4. **Diarization** — pyannote, default `min_speakers=2`, `max_speakers=4`, both overridable.
5. **Custom vocabulary**:
   - Whisper `initial_prompt` built from jargon catalog. Cap ~224 tokens. Sampling deterministic: companies + product names first, then concepts.
6. **Fuzzy post-correction**:
   - After transcription, scan words/short phrases against full jargon catalog with rapidfuzz edit-distance threshold. Replace likely-misheard terms with canonical spellings. Every replacement logged to `metadata.json` for audit.
7. **Outputs**: SRT, VTT, TXT, MD, plus canonical JSON.
   - SRT/VTT cues: break at sentence boundaries when possible, max ~7 words or ~3 seconds, never split mid-word.
   - MD: group consecutive same-speaker segments into paragraphs, prefix `**SPEAKER_00:**` (or `**Chad:**` once `speakers.json` populated).

## Device + backend selection

WhisperX backend auto-detects:

| Platform | Transcription | Alignment | Diarization |
|---|---|---|---|
| Linux + CUDA GPU | CUDA float16 | CUDA float16 | CUDA |
| Mac M-series | CPU int8 (faster-whisper, no Metal in CT2) | MPS | MPS w/ CPU fallback |
| Linux CPU only | CPU int8 | CPU | CPU |

Backend logs detected device + compute type to `metadata.json`. Same code path everywhere.

## CLI surface

```
podcast transcribe EPISODE [--model large-v3] [--min-speakers 2] [--max-speakers 4]
                            [--backend whisperx|deepgram|aws] [--force] [--file PATH]
podcast subtitle EPISODE       # regenerate SRT/VTT from transcript.json
podcast label EPISODE SPEAKER_00=Chad SPEAKER_01=Steve   # update speakers.json + re-render MD
podcast status EPISODE         # show which artifacts exist, which stages have run
```

**Stub subcommands** (print "not implemented yet", exit 0):

```
podcast moments EPISODE
podcast thumbnail EPISODE
podcast describe EPISODE
podcast linkedin EPISODE
podcast chapters EPISODE
podcast publish-youtube EPISODE
podcast publish-spotify EPISODE
```

Each stub is its own module under `scripts/podcast_lib/commands/` so future implementation slots in cleanly.

## Project layout

```
.claude/skills/podcast-postprocessing/
  SKILL.md
podcast.py
scripts/
  podcast_lib/
    __init__.py
    config.py                  # paths, defaults
    jargon.py                  # full catalog
    episode.py                 # discovery, validation
    audio.py                   # ffmpeg extraction
    transcribe/
      __init__.py
      base.py                  # TranscriptionBackend Protocol
      whisperx_backend.py
      deepgram_backend.py      # raises NotImplementedError
      aws_backend.py           # raises NotImplementedError
    diarize.py
    correct.py                 # fuzzy jargon correction
    formatters/
      srt.py
      vtt.py
      txt.py
      md.py
    speakers.py
    metadata.py
    commands/
      transcribe.py
      subtitle.py
      label.py
      status.py
      moments.py               # stub
      thumbnail.py             # stub
      describe.py              # stub
      linkedin.py              # stub
      chapters.py              # stub
      publish_youtube.py       # stub
      publish_spotify.py       # stub
requirements.txt
README.md
.env.example                   # documents HF_TOKEN, never .env itself
```

## Dependencies

`requirements.txt`:

- whisperx
- pyannote.audio
- torch (CUDA wheel on Linux GPU, MPS-capable wheel on Mac, CPU wheel otherwise — driven by platform-specific install instructions in README)
- ffmpeg-python
- typer[all]
- rich
- rapidfuzz
- python-dotenv

System deps:

- ffmpeg (`brew install ffmpeg` Mac, `apt install ffmpeg` Linux)
- HF_TOKEN env var via `.env` (pyannote model gated; user must accept terms on Hugging Face)

## Error handling

- Missing `*Final*.mp4` → exit 2 with: `"Could not find *Final*.mp4 in <EpisodeN>/. Please confirm the file exists and matches the expected pattern, or pass --file to override."`
- Multiple matches → exit 2 listing all paths, ask which.
- Missing ffmpeg → exit 2 with install hint.
- Missing HF_TOKEN → exit 2 with link to pyannote gated model + `.env.example` instructions.
- Model download failure → exit 2 with original error + retry hint.

SKILL.md tells Claude: **on any non-zero exit, surface to user and ask. Never invent filenames, never silently retry.**

## Resumability

- `transcribe` checks for existing `transcript.json`. Present + not stale → exit fast with message. `--force` overrides.
- Each stage's progress + duration logged to `metadata.json` so a long run interrupted partway gives debug info.

## Amplify build-skip

`scripts/` and `.claude/` changes must not trigger Hugo redeploys.

**Approach: Disable Amplify auto-build, drive deploys via GitHub Actions webhook.**

1. AWS Amplify Console → app `softwareinblue.com` → Hosting → Build settings → branch `main` → toggle **Auto build OFF**.
2. Same panel → **Incoming webhooks** → create webhook for `main`. Copy URL.
3. GitHub repo → Settings → Secrets → add `AMPLIFY_WEBHOOK_URL` with the URL.
4. Add `.github/workflows/amplify-deploy.yml`:

   ```yaml
   name: Trigger Amplify deploy
   on:
     push:
       branches: [main]
       paths-ignore:
         - 'scripts/**'
         - '.claude/**'
         - 'docs/**'
         - '*.md'
         - 'podcast.py'
         - 'requirements.txt'
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - run: curl -X POST -d {} "${{ secrets.AMPLIFY_WEBHOOK_URL }}" -H "Content-Type:application/json"
   ```

This is AWS's documented pattern for selective Amplify builds. Walk-through provided alongside the implementation.

## Acceptance test

`podcast transcribe Episode43` on a folder containing `SIB_E43_Final.mp4`:

- Produces all six artifacts under `Episode43/artifacts/`.
- Correctly-spelled "Elasticsearch", "Weaviate", "ClickHouse", "kNN", "RAG", "HNSW" wherever spoken.
- Speaker-labeled paragraphs in `transcript.md` (using `SPEAKER_00` until `podcast label` is run).
- SRT cues never break mid-word, never exceed ~3 seconds.

`podcast moments Episode43` prints "not implemented yet" and exits 0.

## Build order

1. Skeleton: `podcast.py`, `scripts/podcast_lib/`, `requirements.txt`, `README.md`, `.env.example`, `.gitignore` updates.
2. Episode discovery + error handling (`episode.py`).
3. Audio extraction (`audio.py`).
4. Jargon catalog (`jargon.py`) — full catalog before transcription so prompt + correction work end-to-end on first run.
5. Transcription backend Protocol + WhisperX implementation w/ device auto-detect.
6. Diarization (`diarize.py`).
7. Fuzzy correction pass (`correct.py`).
8. Output formatters (SRT, VTT, TXT, MD).
9. `label`, `subtitle`, `status` commands.
10. Stub future subcommands.
11. SKILL.md.
12. Amplify webhook setup + GitHub Action.
13. End-to-end test on `Episode43/`.

## Out of scope (this iteration)

- Moment-finding, thumbnail copy, descriptions, LinkedIn posts, YouTube/Spotify publishing — stubbed only.
- Deepgram + AWS Transcribe backends — interface only, raise NotImplementedError.
- iOS / web UI — none.

## Open risks

- **Pyannote gated model**: user must accept terms on Hugging Face for `pyannote/speaker-diarization-3.1` before first run. README documents.
- **First-run model download**: ~3 GB (large-v3 + alignment + pyannote). README warns.
- **CTranslate2 on Mac**: no Metal support → CPU-only for transcription pass. M4 Max CPU plenty fast (~1-2x realtime for large-v3).
- **Token leak**: HF token pasted in chat is now in transcript. Read-only scope so risk minimal; rotate if concerned.
