---
name: podcast-postprocessing
description: Post-production tasks for the "Can I Get That Software in Blue?" podcast — transcription, subtitle generation, speaker labeling, plus design-pipeline outputs (BG-removed headshots, AI-balloon scenes with wordmark, full thumbnail variant set A/C/W/D — a1/a2/a3, a1w/a2w/a3w, c1/c2/c3, w1/w2, d1/d2 — across all standard sizes). Use when the user asks to transcribe an episode, regenerate subtitles, label speakers, generate per-episode design assets, or run any other podcast post-production step.
---

# Podcast post-processing

Post-production for the SIB podcast — both the audio pipeline (transcribe → align → diarize → render) and the design pipeline (BG removal → AI balloon scene → wordmark overlay → thumbnail compositor). All real work lives in scripts at the repo root and under `design/`. This skill never reimplements logic — it runs preflight, dispatches to the right script, and surfaces errors verbatim.

## STEP 0 — Preflight (mandatory, every invocation)

Before running any pipeline command, run the preflight check. It verifies: brand assets, fonts (`design/fonts/Futurama-Bold.ttf`), reference cover, host photos, system tools (ffmpeg, headless Chrome), Python packages (Pillow, rembg, etc.), and per-episode inputs (Hugo metadata, guest source photo, BG-removed headshot, AI balloon PNG).

```bash
# Audio pipeline preflight (ffmpeg, whisperx, .env, etc.)
./scripts/setup.sh   # one-time install if not already done

# Design preflight — episode-aware. Pass the episode number you're working on.
python3 design/preflight.py <EPISODE_NUM>
```

If preflight reports any items marked `✗`, **stop and surface the checklist verbatim to the user.** Ask them to provide the missing inputs (e.g., "drop the guest's headshot at `hugosite/static/img/guest/<slug>.jpg`", or "follow `design/balloon-prompt.md` to generate the no-overlay balloon"). Never silently substitute.

### Font requirement (HARD GATE)

All thumbnail generation (episodes AND clips) requires **Apple SF Pro** (`SFNS.ttf`) — the exact variable font used on macOS. The file must exist at `/System/Library/Fonts/SFNS.ttf`. If it is missing, **refuse to run thumbnail generation**. Do NOT substitute Inter, Helvetica, Roboto, or any other font — the layouts are pixel-tuned to SF Pro metrics and any substitution will break glyph placement.

To install on Linux: download SF Pro from Apple's developer site, extract `SF-Pro.ttf` from the package, and copy it to `/System/Library/Fonts/SFNS.ttf`.

Items marked `!` are warnings — pipeline can run but will skip optional steps. Mention them but proceed.

## When to use

Use whenever the user asks to:
- Transcribe a podcast episode
- Regenerate subtitle files (SRT/VTT) from an existing transcript
- Label speakers (`SPEAKER_00` → "Chad")
- Check status of artifacts for an episode
- Generate per-episode design assets (BG-removed headshot, balloon cover, wordmark overlay, thumbnails)
- Generate clip-worthy moments, thumbnail copy, descriptions, LinkedIn posts, chapters, or publish to YouTube/Spotify (stubbed)

## File conventions

- Episodes live in folders named `EpisodeN/` (e.g., `Episode43/`).
- Master video filename contains the word `Final`, extension `.mp4` (e.g., `SIB_E43_Final.mp4`).
- Discovery rule: glob `EpisodeN/*Final*.mp4` (case-insensitive). Zero matches or multiple matches → CLI exits 2 with a clear error.
- Episodes may live locally, on NAS, network mounts, or S3. **Before invoking the CLI, ask the user where the episode lives.** If it's not local, copy/rsync the file into `/tmp/EpisodeN/` first, then point the CLI at that path.

## Subcommands

```
podcast transcribe EPISODE [--model large-v3] [--min-speakers 2] [--max-speakers 4]
                            [--backend whisperx|mlx|deepgram|aws] [--force] [--file PATH]
                            [--progress-file PATH]
podcast subtitle EPISODE       # regenerate SRT/VTT from transcript.json
podcast label EPISODE SPEAKER_00=Chad SPEAKER_01=Steve   # update speakers.json + re-render MD
podcast status EPISODE         # show which artifacts exist
podcast posts EPISODE          # render post bodies from metadata YAML

# Distribution (uses metadata YAML + Postiz/Spotify):
podcast publish-episode-spotify EPISODE [--video PATH] [--cover PATH] [--publish-at ISO] [--test-login]
podcast publish-episode-youtube EPISODE [--video PATH] [--thumbnail PATH] [--publish-at ISO] [--dry-run]
podcast publish-episode-socials EPISODE [--cover PATH] [--publish-at ISO] [--skip PLATFORM] [--allow-tbd] [--dry-run]
podcast publish-clip-youtube    EPISODE CLIP [--video PATH] [--publish-at ISO] [--dry-run]
podcast publish-clip-socials    EPISODE CLIP [--video PATH] [--publish-at ISO] [--skip PLATFORM] [--dry-run]

# Clip post-processing:
podcast import-clips EPISODE [--dry-run] [--force]            # Google Sheets → YAML clips section
podcast transcribe-clip EPISODE --clip N [--all] [--force]    # transcribe + dehallucinate clip
podcast subtitle-clip EPISODE --clip N [--all]                # SRT/VTT from clip transcript
podcast thumbnail-clip EPISODE --clip N [--all]               # full variant set for clip thumbnails

# Batch title management:
podcast batch-titles [EPISODES] [--platform all|hugo|youtube|spotify] [--thumbnails] [--dry-run]

# Still stubbed:
podcast thumbnail EPISODE
podcast describe EPISODE
podcast linkedin EPISODE
podcast chapters EPISODE
```

> **`moments` is intentionally not implemented and never will be.** The
> user always pre-cuts clips outside this pipeline and provides them in
> two formats per clip (see "Source files" below). The CLI is read-only
> with respect to clip generation.

## Source files (user-provided, never generated)

The episode dir (`/Volumes/Public/Backup/Chad/Business/Software_in_Blue/Episode<N>/`
on Joanna's machine; staged into `/tmp/EpisodeN/` for runs that need it
locally) contains:

| File | Format | Purpose |
|------|--------|---------|
| `SIB_E<N>_Final.mp4` | 16:9 H | Master episode video — fed to Spotify + YouTube long-form |
| `SIB_E<N>_clip<I>H.mp4` | 16:9 H | Clip horizontal — backup / archive (not posted by default) |
| `SIB_E<N>_clip<I>V.mp4` | 9:16 V | Clip vertical — posted to YT Shorts + LinkedIn + X + IG Reel + TikTok + FB |

Naming is exact (e.g. `SIB_E38_clip5V.mp4`). The `H`/`V` suffix has no
underscore. Numbers in the filename match `clips[].number` in the
metadata YAML.

## Two-phase publishing

Episode and clips publish on independent schedules. Within each phase,
the upload-the-asset commands are split from the social-announcement
commands so the producer can stagger them as needed.

### Phase A — Episode launch (day 0)

| Step | Command | What it does |
|------|---------|--------------|
| A0 | (manual) | **Reverse-engineer the show notes** — see below |
| A1 | `publish-episode-spotify <N>` | Browser-uploads master video → Spotify for Creators (host). Spotify auto-distributes to Apple/Amazon/iHeart via RSS. |
| A2 | `publish-episode-youtube <N>` | Postiz uploads master video → YouTube long-form with the D1 thumbnail and tags. |
| A3 | `publish-episode-socials <N>` | Postiz fans the announcement (text + cover image) out to LinkedIn / X / IG / FB. TikTok skipped automatically (image-only). Refuses to run if `episode.links.youtube_full` or `.spotify` are unset (unless `--allow-tbd`). |

A typical day-0 flow: A1 first (waits up to 10 min for transcode →
saves Spotify URL into metadata YAML), A2 next (saves YT URL into
metadata YAML), then A3.

### Step A0 — Capture show notes BEFORE editing Spotify (mandatory, automated)

**The Spotify dashboard description field is destructive on save** — the
edit script replaces the entire description with whatever it renders
from the metadata YAML. There is no version history, no undo. If
`episode.show_notes` is empty when the script runs, all existing show
notes / links in Spotify are gone after the save.

`publish-episode-spotify` (and the underlying `spotify_cloak.py`) hard-
**gate on this**: if `episode.show_notes` is empty in the YAML when the
script starts, it:

1. Reads the `youtube` id from the matching Hugo `episode<N>.md` and
   fetches the YouTube video description (extracts
   `ytInitialPlayerResponse.videoDetails.shortDescription`).
2. Parses the description's "Show Notes and Links Mentioned" section
   (or the block after the Stitcher subscribe link, for episodes that
   skipped the header) into `{heading, urls: [...]}` entries.
3. Writes the parsed entries back into the YAML under
   `episode.show_notes:`.
4. If parsing finds **zero** show notes, the script ABORTS with a
   clear error. Every SIB episode is expected to have show notes; an
   empty result is almost always a parser miss, not a real empty.

Library: `scripts/podcast_lib/fetch_show_notes.py` — `populate_show_notes(num)`
is the entry point. CLI for ad-hoc use:

```bash
python3 -m scripts.podcast_lib.fetch_show_notes 2          # auto-populate
python3 -m scripts.podcast_lib.fetch_show_notes 2 --force  # overwrite existing
```

Override (rare): pass `--allow-empty-show-notes` to `publish-episode-spotify`
when an episode genuinely has no links. Default is to refuse.

**Spotify ~4000-char description ceiling.** Spotify rejects saves whose
rendered description exceeds about 4000 chars (the limit isn't exposed
via HTML `maxLength` but the form-Save handler silently no-ops the
commit). The renderer therefore emits raw `<p>URL</p>` paragraphs for
links instead of wrapping them in `<a href="…">…</a>` — Spotify and
Apple Podcasts auto-linkify raw URLs, and the markup savings (~80
chars/link) keep most episodes well under the ceiling. If a render
still goes over, trim show notes manually in the YAML (combine related
links under one heading, drop secondary references, shorten paragraph
prose) until the render fits.

**Episode art (the per-episode square Spotify cover) uses the D2
variant — `hugosite/static/img/episode/Episode<NN>/d2/podcast-cover-3000x3000.png`.**
The script uploads that file as Spotify's "show art" on each episode
to match the D-series (DOAC-style) branding used on YouTube thumbnails.
Hugo's `episode_image` front-matter still points at the W1 variant for
the website — only Spotify gets D2. The video thumbnail (1920×1080) is
the D1 variant: `hugosite/static/img/episode/Episode<NN>/d1/thumbnail-youtube-1920x1080.png`.

### Phase B — Clip drip (6–12 months later, per-clip)

| Step | Command | What it does |
|------|---------|--------------|
| B1 | `publish-clip-youtube <N> <CLIP> --publish-at ISO` | Postiz uploads the 9:16 vertical clip → YouTube Shorts. |
| B2 | `publish-clip-socials <N> <CLIP> --publish-at ISO` | Same vertical clip → LinkedIn (page) / X / IG Reel / TikTok / Facebook in one Postiz call. |

B1 and B2 can run on different `--publish-at` dates — e.g. YT Shorts
Monday, social cross-post Wednesday — or both at the same time. Each
command is independent.

Phase A does **not** require any clip files on disk; the publish-clip-*
commands only check for `SIB_E<N>_clip<I>V.mp4` when they're invoked.
An episode can launch at month 0 even when its clips won't be cut for
half a year.

## Distribution prerequisites (`publish-*`)

Before any `publish-*` command will work:

1. **Tailscale connected**: the EvoGyms Postiz instance is reachable only at
   `http://postiz-tailscale.tailf1ef2f.ts.net` (over the Tailscale tailnet).
   `tailscale status` must show the connection up. Without this every
   Postiz API call will return `httpx.ConnectError`.
2. **`.env` populated**: copy `scripts/podcast_lib/.env.example` →
   `scripts/podcast_lib/.env` and fill `POSTIZ_BASE_URL`, `POSTIZ_TOKEN`,
   `SPOTIFY_EMAIL`, `SPOTIFY_PASSWORD`.
3. **Postiz integrations connected**: in the Postiz UI add the social
   accounts you want to fan out to. SIB ships content to:
   `linkedin` (personal), `linkedin-page` (company), `youtube`, `x`,
   `instagram`, `tiktok`, `facebook`. Verify with
   `python3 -m scripts.podcast_lib.postiz integrations`.
4. **`agent-browser` installed** (Spotify only): `npm i -g agent-browser`
   then `agent-browser install --with-deps`. First run, do
   `python3 podcast.py publish-spotify <N> --test-login` to seed a
   logged-in browser session and clear any 2FA prompts before the real
   upload.
5. **Per-episode metadata YAML** exists at
   `episodes/Episode<NN>/SIB_E<NN>_metadata.yaml` and is filled out (see
   ep45 for the canonical shape — `posting.py` reads from there).

### Postiz API client

`scripts/podcast_lib/postiz.py` is the REST wrapper. It exposes:
- `PostizClient.from_env()` — reads `POSTIZ_BASE_URL` + `POSTIZ_TOKEN`
- `list_integrations()`, `integration_by(identifier=, profile=)`
- `upload(path)` — multipart media upload, returns `{id, path}`
- `create_post(integrations=[…], when=datetime|None)` — schedules or posts now
- Per-platform helpers: `linkedin_post`, `x_post`, `youtube_post`,
  `instagram_post`, `tiktok_post`, `facebook_post`. Each returns the dict
  that `create_post` expects in its `integrations` list.

Auth nuance: Postiz wants the bare token in the `Authorization` header
(NOT `Bearer <token>` — that returns 401). The wrapper handles this.

CLI for ad-hoc use:
```
python3 -m scripts.podcast_lib.postiz integrations
python3 -m scripts.podcast_lib.postiz upload path/to/file.png
```

### Spotify for Creators upload (browser automation)

`scripts/podcast_lib/spotify_browser.py` drives
`https://creators.spotify.com` via `agent-browser`. There is no Spotify
upload API — automation is the only programmatic path. **Spotify ToS
prohibits automated access**; use at your own risk and don't fan out
this script to multiple shows or you'll get account-flagged.

The script:
1. Navigates to the dashboard and detects login state from the snapshot.
2. If logged out, fills email + password on accounts.spotify.com and
   handles 2FA via `SPOTIFY_2FA_CODE` env-var or stdin prompt.
3. Clicks "New episode" → uploads the master video file via
   `agent-browser upload` to the (hidden) `<input type=file>`.
4. Waits up to 10 minutes for Spotify's transcode to finish (form
   fields appearing in the snapshot is the readiness signal).
5. Fills title (from `episode.hugo_title` in the metadata YAML),
   description (rich-text editor — uses `innerHTML` + dispatched
   `input` event so React picks the value up), episode#, season
   (if present), explicit toggle.
6. Either schedules at `--publish-at` or saves as draft.

The selectors are fragile. On first run, expect to refine the
`js_click_button("…")` text matchers and field names — Spotify ships UI
revisions silently. The script always calls `snapshot()` before each
step so the operator (or a Hermes agent) can read the current page and
adjust the next selector. **Do not silently retry with different
selectors** — surface the snapshot to the user and ask.

## How to invoke

Run from repo root with `python3 podcast.py <subcommand> ...` (or `./podcast.py` after `chmod +x`).

Examples:

```bash
# Default backend (whisperx, CPU on Apple Silicon — slow)
python3 podcast.py transcribe Episode43

# GPU-accelerated transcribe on Apple Silicon via mlx-whisper.
# Only the transcribe stage runs on MLX/GPU; alignment + diarization
# fall back to the WhisperX backend (those already use MPS).
python3 podcast.py transcribe Episode43 --backend mlx

# Backgrounded run with explicit progress file (skill polls this path).
python3 podcast.py transcribe Episode43 --backend mlx \
  --progress-file /tmp/sib_transcribe_progress_episode43.txt \
  > /tmp/sib_transcribe_episode43.out 2>&1 &

python3 podcast.py status Episode43
python3 podcast.py label Episode43 SPEAKER_00=Chad SPEAKER_01=Steve
python3 podcast.py subtitle Episode43
```

### Multi-episode batches — RUN SERIALLY

Running multiple `transcribe` jobs in parallel on the same workstation
will exhaust RAM/GPU memory and can hard-lock the box (this has bitten
us — five concurrent runs took the machine down). For a batch like
"transcribe Episodes 41–45":

1. Stage all source MP4s locally first (e.g. into `/tmp/EpisodeN/`).
2. Loop one at a time. Block on each before starting the next:
   ```bash
   for n in 41 42 43 44 45; do
     python3 podcast.py transcribe Episode$n --backend mlx \
       --progress-file /tmp/sib_transcribe_progress_episode$n.txt
   done
   ```
   Or, if backgrounding so you can monitor: launch one, poll the
   progress file until the run exits, then launch the next.
3. Never `&`-fan-out the whole loop. One in flight at a time.

## Watching progress on a backgrounded transcribe

`podcast transcribe` is long-running (≈30 min wall time per hour of audio
on CPU; longer under contention from parallel runs). Whisper itself emits
no per-chunk log output, so when a run is backgrounded the .output file
stays static between stage transitions.

To make progress observable, the CLI auto-creates a single-line progress
file at:

    /tmp/sib_transcribe_progress_episode<N>_<pid>.txt

Override with `--progress-file PATH`. The path is printed at run start so
the user (and the skill) can copy it. Each WhisperX progress callback
atomically rewrites the file with one line of the form:

    transcribe   42.0%  elapsed 20m34s  ETA 28m20s  pid=12345  updated=2026-05-07T19:01:32

When dispatched as a background task, the skill MUST:

1. **Print the progress-file path** to the user immediately after launch
   so they can `cat` or `watch -n5 cat …` it from any other shell.
2. **Poll it periodically** (e.g. every minute or two) and surface the
   current line to the user — `cat /tmp/sib_transcribe_progress_episode<N>_<pid>.txt`
   is enough; one line out, no parsing needed.
3. Treat absence of the file as "stage hasn't reached its first
   progress callback yet" — don't error out; report "warming up" and
   try again shortly.

The same data also lands in `metadata.json` under `transcribe_progress`
and `align_progress` keys (with `fraction`, `elapsed_s`, `eta_s`,
`updated_at`). `python3 podcast.py status <Episode>` reads those keys
and prints a friendly progress line, so it's a higher-level alternative
when you don't have the PID handy.

### MLX backend caveat — progress file stays empty during transcribe

`mlx-whisper` does not expose a per-chunk progress hook, so when running
`--backend mlx` the **progress file remains absent for the entire
transcribe stage**. The progress file *does* get written during the
alignment stage (which runs through WhisperX). For MLX, the live signal
is the tqdm bar mlx-whisper writes to stdout/stderr — capture the run
log and tail-strip carriage returns to read the latest line:

```bash
tail -c 800 /tmp/sib_logs/episodeN.out | tr '\r' '\n' | grep -v '^$' | tail -1
```

Without `tr '\r' '\n'`, plain `tail -1` returns the *first* tqdm line
(everything is one big "line" terminated only by `\r`). Always pipe
through `tr` when surfacing tqdm progress.

### Monitor pattern — polling a backgrounded transcribe

Combine the progress file (when populated), the tqdm log tail
(MLX), and the on-disk artifact state. Drive it with a Monitor task
that ticks every 60s and exits naturally when the worker PID dies:

```bash
PID=<pid_from_launch>
PROG=/tmp/sib_transcribe_progress_episodeN.txt
LOG=/tmp/sib_logs/episodeN.out
ART=/tmp/sib/artifacts/EpisodeN
while kill -0 $PID 2>/dev/null; do
  sleep 60
  ts=$(date +%H:%M:%S)
  if [ -f "$PROG" ]; then p=$(cat "$PROG")
  else p="(progress-file empty — mlx transcribe stage has no callback)"
  fi
  l=$(tail -c 800 "$LOG" 2>/dev/null | tr '\r' '\n' | grep -v '^$' | tail -1 | cut -c1-180)
  stage=$(ls "$ART"/*/transcript*.json 2>/dev/null | xargs -I{} basename {} | tr '\n' ',' | sed 's/,$//')
  echo "[$ts] EPN prog: $p"
  echo "       last_log: $l"
  echo "       artifacts: ${stage:-audio.wav only}"
  grep -E "Traceback|Transcription failed|Alignment failed|Diarization failed|Killed|OOM|Error" \
    "$LOG" 2>/dev/null | tail -1
done
echo "[$(date +%H:%M:%S)] EPN PID $PID exited"
tail -c 1500 "$LOG" | tr '\r' '\n' | tail -8
echo "EPN_DONE"
```

Hand that to the `Monitor` tool with a 1-hour timeout. Each `echo`
becomes a chat notification on its own ~60s schedule. The grep
alternation must cover **failure signatures**, not only success — a
crashed worker should still emit a line. When the loop exits the
sentinel `EPN_DONE` is emitted, signaling "safe to launch the next
episode" for serial batches.

## Error handling — STRICT

**On any non-zero exit code from `podcast.py`:**
1. Surface the full error message to the user verbatim.
2. Ask the user how they want to proceed.
3. **Never invent filenames.** Never silently retry with different paths or arguments.
4. If the error is about a missing `*Final*.mp4`, ask the user to confirm the path or pass `--file`.
5. If the error is about a missing `HF_TOKEN`, point them to `.env.example`.
6. If the error is about ffmpeg, point them to `brew install ffmpeg` (Mac) or `apt install ffmpeg` (Linux).

## Outputs

The CLI writes audio artifacts to `/tmp/sib/artifacts/Episode<N>/<YYYYMMDD-HH:MM:SS>/`:
- `audio.wav` — 16kHz mono extract
- `transcript.json` — canonical source of truth (WhisperX-shaped: language + segments + word-level timestamps + speaker labels)
- `transcript.srt`, `transcript.vtt`, `transcript.txt`, `transcript.md` — derivatives
- `transcript.raw.json`, `transcript.aligned.json` — stage checkpoints (resume-friendly)
- `speakers.json`, `metadata.json`

Design artifacts are committed under `hugosite/static/img/episode/Episode<N>/`
(so Hugo serves them straight off the static path — `episode_image` in the
front matter points at `img/episode/Episode<N>/w1/podcast-cover-3000x3000.png`):
- `headshots/<slug>-nobg.png` — BG-removed guest headshots
- `illustrations/SIB_E<N>_Balloon_no_overlay.png` — AI-generated balloon scene (from ChatGPT)
- `illustrations/SIB_E<N>_Balloon_with_overlay.png` — same with the wordmark added by `design/add_wordmark_overlay.py`
- `<variant>/<size>.png` — final thumbnail exports (variants directly under EpisodeN/, no thumbnails/ subdir)

## Design pipeline scripts

```bash
# Run BG removal on a guest photo (only if rembg-bg-removed PNG missing)
python3 -c "from rembg import remove; \
  open('hugosite/static/img/episode/EpisodeN/headshots/<slug>-nobg.png','wb').write( \
    remove(open('hugosite/static/img/guest/<slug>.jpg','rb').read()))"

# Add wordmark overlay to a no-overlay AI balloon scene
python3 design/add_wordmark_overlay.py <EPISODE_NUM>

# Render every (variant × size) for one episode.
# `gen_sib_exports.py` renders ALL variants in one pass — no flag needed.
# Variants the script always emits (see VARIANTS tuple in the script):
#   A-series face-forward:        a1, a2, a3
#   A-series face-forward + balloon overlay: a1w, a2w, a3w
#   C-series magazine split:      c1, c2, c3
#   W-series whimsical balloon:   w1, w2  (skipped if balloon assets missing)
#   D-series diary:               d1, d2
# All eleven variants are produced unless their inputs are missing — never
# pass a flag to "just generate c1/c3" and skip d1/d2; if the user reports a
# missing variant, check the per-variant skip messages in the script log
# rather than re-running with restricted args.
python3 design/gen_sib_exports.py <EPISODE_NUM> <GUEST_SLUG>
```

The balloon-cartoon recipe (ChatGPT prompt + image attachments) is in `design/balloon-prompt.md`. Surface it to the user when they need to produce the AI scene.
