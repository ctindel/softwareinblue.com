# softwareinblue.com
softwareinblue.com

Make sure to clone the theme:

# Using fork branch until upstream PR
# https://github.com/mattstratton/castanet/pull/519 is merged.
# Once merged, revert to:
#   git clone https://github.com/mattstratton/castanet themes/castanet
git clone -b fix/hugo-0.158-deprecations https://github.com/ctindel/castanet themes/castanet

## Podcast post-processing

Automation for "Can I Get That Software in Blue?" episodes — transcription, subtitles, speaker labels, with future stubs for clip-finding, descriptions, LinkedIn posts, and publishing.

### One-time setup

1. Install ffmpeg.
   - Mac: `brew install ffmpeg`
   - Linux: `apt install ffmpeg`
2. Create a virtual environment and install Python deps.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   - On Linux with NVIDIA GPU, install the CUDA wheel of PyTorch first per the official PyTorch site to get GPU acceleration.
   - For Spotify browser automation (`cloakbrowser`), also download the patched Chromium binary:
     ```bash
     python3 -c "from cloakbrowser import ensure_binary; ensure_binary()"
     ```
3. Get a Hugging Face token.
   - Create one (read scope) at https://huggingface.co/settings/tokens
   - Accept gated model terms at BOTH:
     - https://huggingface.co/pyannote/speaker-diarization-community-1
     - https://huggingface.co/pyannote/segmentation-community-1
   - `cp .env.example .env`, paste token into `HF_TOKEN`.
4. First-run model download is ~3 GB (Whisper large-v3 + alignment + pyannote).

### Running

From the repo root (activate the venv first):

```bash
source .venv/bin/activate
python3 podcast.py transcribe Episode43
python3 podcast.py status Episode43
python3 podcast.py label Episode43 SPEAKER_00=Chad SPEAKER_01=Steve
python3 podcast.py subtitle Episode43
```

Outputs land in `Episode43/artifacts/`.

### Selective Amplify deploys

Changes under `scripts/`, `.claude/`, `docs/`, `tests/`, `*.md`, `podcast.py`, and `requirements.txt` should not redeploy the website. To wire this up:

1. AWS Amplify Console → app → Hosting → Build settings → branch `main` → toggle **Auto build OFF**.
2. Same panel → **Incoming webhooks** → create webhook for `main`. Copy the URL.
3. GitHub repo → Settings → Secrets and variables → Actions → add `AMPLIFY_WEBHOOK_URL` = that URL.

Then `.github/workflows/amplify-deploy.yml` triggers a deploy only on web-relevant pushes.
