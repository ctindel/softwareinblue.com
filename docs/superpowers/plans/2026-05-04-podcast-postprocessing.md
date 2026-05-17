# Podcast Post-Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Typer-based Python CLI (`podcast.py`) plus a thin Claude Code skill (`.claude/skills/podcast-postprocessing/SKILL.md`) that automates SIB podcast post-production. Initial scope: extract audio, transcribe with WhisperX (large-v3 default), align word-level timestamps, diarize with pyannote, fuzzy-correct against a tech-jargon catalog, and emit SRT/VTT/TXT/MD subtitle/transcript artifacts. Future stages (moments, thumbnail copy, descriptions, LinkedIn, YouTube/Spotify publishing) scaffolded as no-op stubs.

**Architecture:** Thin skill, fat CLI. SKILL.md tells Claude when to invoke and what subcommands exist; all logic lives in `scripts/podcast_lib/`. Each pipeline stage writes durable artifacts under `EpisodeN/artifacts/`; downstream stages read those, never re-run prior stages. `transcript.json` is the canonical source of truth. Transcription backend is abstracted behind a `TranscriptionBackend` Protocol with WhisperX as the default and `deepgram_backend.py` / `aws_backend.py` as `NotImplementedError` stubs. WhisperX backend auto-detects device (CUDA → MPS → CPU) so the same code runs on Mac M-series and Linux GPU box.

**Tech Stack:** Python 3.13, Typer (CLI), Rich (progress + output), WhisperX (faster-whisper + wav2vec2 alignment + pyannote), rapidfuzz (jargon correction), python-dotenv (env), ffmpeg-python (audio), pytest (tests). Hugo unchanged. Amplify auto-build disabled in console; deploys driven by GitHub Actions webhook.

---

## File Structure

**New files:**

- `podcast.py` — Typer entrypoint, registers subcommands.
- `requirements.txt` — Python deps (top-level for user `pip install -r`).
- `README.md` already exists; will be **modified**, not created.
- `.env.example` — documents required env vars (HF_TOKEN), checked into repo.
- `.github/workflows/amplify-deploy.yml` — selective Amplify webhook trigger.
- `scripts/podcast_lib/__init__.py` — empty marker.
- `scripts/podcast_lib/config.py` — paths + defaults (model, speaker bounds).
- `scripts/podcast_lib/jargon.py` — full tech jargon catalog organized by category.
- `scripts/podcast_lib/episode.py` — folder discovery, `*Final*.mp4` glob, validation.
- `scripts/podcast_lib/audio.py` — ffmpeg extraction to 16kHz mono WAV.
- `scripts/podcast_lib/metadata.py` — read/write `metadata.json` artifact.
- `scripts/podcast_lib/speakers.py` — read/write `speakers.json` mapping.
- `scripts/podcast_lib/correct.py` — fuzzy jargon post-correction with rapidfuzz.
- `scripts/podcast_lib/diarize.py` — pyannote diarization wrapper, MPS-aware.
- `scripts/podcast_lib/transcribe/__init__.py` — empty marker.
- `scripts/podcast_lib/transcribe/base.py` — `TranscriptionBackend` Protocol.
- `scripts/podcast_lib/transcribe/whisperx_backend.py` — WhisperX impl, auto-detect device.
- `scripts/podcast_lib/transcribe/deepgram_backend.py` — `NotImplementedError` stub.
- `scripts/podcast_lib/transcribe/aws_backend.py` — `NotImplementedError` stub.
- `scripts/podcast_lib/formatters/__init__.py` — empty marker.
- `scripts/podcast_lib/formatters/srt.py` — SRT cue formatter, no mid-word breaks, ≤3s/cue.
- `scripts/podcast_lib/formatters/vtt.py` — VTT formatter, shares cue logic with SRT.
- `scripts/podcast_lib/formatters/txt.py` — plain text, no timestamps.
- `scripts/podcast_lib/formatters/md.py` — speaker-grouped paragraphs.
- `scripts/podcast_lib/commands/__init__.py` — empty marker.
- `scripts/podcast_lib/commands/transcribe.py` — `transcribe` subcommand.
- `scripts/podcast_lib/commands/subtitle.py` — `subtitle` subcommand (regen from JSON).
- `scripts/podcast_lib/commands/label.py` — `label` subcommand (set speaker names).
- `scripts/podcast_lib/commands/status.py` — `status` subcommand (show artifact state).
- `scripts/podcast_lib/commands/moments.py` — stub.
- `scripts/podcast_lib/commands/thumbnail.py` — stub.
- `scripts/podcast_lib/commands/describe.py` — stub.
- `scripts/podcast_lib/commands/linkedin.py` — stub.
- `scripts/podcast_lib/commands/chapters.py` — stub.
- `scripts/podcast_lib/commands/publish_youtube.py` — stub.
- `scripts/podcast_lib/commands/publish_spotify.py` — stub.
- `.claude/skills/podcast-postprocessing/SKILL.md` — skill descriptor.
- `tests/__init__.py` — empty marker.
- `tests/test_episode.py` — episode discovery tests.
- `tests/test_jargon.py` — jargon catalog + sampling tests.
- `tests/test_correct.py` — fuzzy correction tests.
- `tests/test_formatters.py` — SRT/VTT/TXT/MD tests.
- `tests/test_speakers.py` — speakers.json read/write tests.
- `tests/test_metadata.py` — metadata.json read/write tests.
- `tests/test_cli.py` — Typer CLI registration / stub-command tests.
- `tests/conftest.py` — pytest fixtures (sample transcript JSON, tmp episode dirs).

**Modified files:**

- `.gitignore` — add `.env`, `Episode*/artifacts/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`.
- `README.md` — add a "Podcast post-processing" section with setup + run instructions.

---

## Task Order

Tasks build bottom-up: configuration → pure logic (jargon, correction, formatters) → I/O (audio, episode discovery, metadata, speakers) → external integrations (transcription backend, diarization) → CLI commands wiring it all → SKILL.md → Amplify webhook → end-to-end test.

---

### Task 1: Repository scaffolding + .gitignore

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`
- Create: `scripts/podcast_lib/__init__.py` (empty)
- Create: `scripts/podcast_lib/transcribe/__init__.py` (empty)
- Create: `scripts/podcast_lib/formatters/__init__.py` (empty)
- Create: `scripts/podcast_lib/commands/__init__.py` (empty)
- Modify: `.gitignore`

- [ ] **Step 1: Update .gitignore**

Read current `.gitignore`, append:

```
# Python
__pycache__/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Environment
.env

# Episode artifacts (audio + transcripts; large + per-machine)
Episode*/artifacts/
```

- [ ] **Step 2: Create `requirements.txt`**

```
# Core
typer[all]>=0.12
rich>=13
python-dotenv>=1.0

# Audio
ffmpeg-python>=0.2

# Transcription
whisperx>=3.1
torch>=2.2
pyannote.audio>=3.1

# Fuzzy correction
rapidfuzz>=3.6

# Tests
pytest>=8.0
```

- [ ] **Step 3: Create `.env.example`**

```
# Hugging Face token for pyannote diarization model.
# 1. Create a token: https://huggingface.co/settings/tokens (read scope is enough)
# 2. Accept gated model terms: https://huggingface.co/pyannote/speaker-diarization-3.1
# 3. Copy this file to .env and paste your token below.
HF_TOKEN=
```

- [ ] **Step 4: Create empty `__init__.py` markers**

Touch `tests/__init__.py`, `scripts/podcast_lib/__init__.py`, `scripts/podcast_lib/transcribe/__init__.py`, `scripts/podcast_lib/formatters/__init__.py`, `scripts/podcast_lib/commands/__init__.py`. Each is empty.

- [ ] **Step 5: Create `tests/conftest.py`**

```python
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
```

- [ ] **Step 6: Verify pytest discovers the tree**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/ --collect-only`
Expected: zero tests collected (no test files yet), no errors.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore tests/__init__.py tests/conftest.py scripts/podcast_lib/__init__.py scripts/podcast_lib/transcribe/__init__.py scripts/podcast_lib/formatters/__init__.py scripts/podcast_lib/commands/__init__.py
git commit -m "scaffold: podcast post-processing package skeleton + test fixtures"
```

---

### Task 2: `config.py` — paths and defaults

**Files:**
- Create: `scripts/podcast_lib/config.py`

- [ ] **Step 1: Create `scripts/podcast_lib/config.py`**

```python
"""Centralized paths and default parameters for the podcast pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ARTIFACTS_DIRNAME = "artifacts"
AUDIO_FILENAME = "audio.wav"
TRANSCRIPT_JSON = "transcript.json"
TRANSCRIPT_SRT = "transcript.srt"
TRANSCRIPT_VTT = "transcript.vtt"
TRANSCRIPT_TXT = "transcript.txt"
TRANSCRIPT_MD = "transcript.md"
SPEAKERS_JSON = "speakers.json"
METADATA_JSON = "metadata.json"

DEFAULT_MODEL = "large-v3"
DEFAULT_MIN_SPEAKERS = 2
DEFAULT_MAX_SPEAKERS = 4
DEFAULT_BACKEND = "whisperx"

# Audio extraction
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1

# Subtitle cue limits
MAX_CUE_SECONDS = 3.0
MAX_CUE_WORDS = 7

# Whisper initial_prompt token cap. Whisper's prompt is ~224 tokens.
PROMPT_TOKEN_BUDGET = 200

# Fuzzy correction threshold (rapidfuzz ratio, 0-100). Higher = stricter.
FUZZY_MATCH_THRESHOLD = 88


@dataclass(frozen=True)
class ArtifactPaths:
    """Resolved artifact paths for an episode folder."""
    root: Path

    @property
    def artifacts_dir(self) -> Path:
        return self.root / ARTIFACTS_DIRNAME

    @property
    def audio(self) -> Path:
        return self.artifacts_dir / AUDIO_FILENAME

    @property
    def transcript_json(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_JSON

    @property
    def transcript_srt(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_SRT

    @property
    def transcript_vtt(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_VTT

    @property
    def transcript_txt(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_TXT

    @property
    def transcript_md(self) -> Path:
        return self.artifacts_dir / TRANSCRIPT_MD

    @property
    def speakers(self) -> Path:
        return self.artifacts_dir / SPEAKERS_JSON

    @property
    def metadata(self) -> Path:
        return self.artifacts_dir / METADATA_JSON

    def ensure(self) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 2: Sanity-import**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -c "from scripts.podcast_lib.config import ArtifactPaths; print(ArtifactPaths.__name__)"`
Expected: `ArtifactPaths`

- [ ] **Step 3: Commit**

```bash
git add scripts/podcast_lib/config.py
git commit -m "feat(podcast): config module with paths and defaults"
```

---

### Task 3: `episode.py` — folder discovery + validation

**Files:**
- Create: `scripts/podcast_lib/episode.py`
- Test: `tests/test_episode.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_episode.py`:

```python
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
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_episode.py -v`
Expected: collection error or import error — module not yet defined.

- [ ] **Step 3: Implement `episode.py`**

```python
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
```

- [ ] **Step 4: Run tests, confirm they pass**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_episode.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/podcast_lib/episode.py tests/test_episode.py
git commit -m "feat(podcast): episode folder + master-video discovery"
```

---

### Task 4: `jargon.py` — full catalog + sampling

**Files:**
- Create: `scripts/podcast_lib/jargon.py`
- Test: `tests/test_jargon.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_jargon.py`:

```python
from __future__ import annotations

from scripts.podcast_lib.jargon import (
    CATEGORIES,
    all_terms,
    build_initial_prompt,
)


def test_categories_nonempty() -> None:
    assert len(CATEGORIES) >= 20  # 20+ topical buckets in spec
    for name, terms in CATEGORIES.items():
        assert isinstance(name, str)
        assert len(terms) > 0


def test_all_terms_includes_show_critical() -> None:
    terms = set(all_terms())
    for must in ["Elasticsearch", "Weaviate", "ClickHouse", "kNN", "RAG", "HNSW",
                 "Steve Mayzak", "Software in Blue", "Chad"]:
        assert must in terms, f"Missing: {must}"


def test_all_terms_dedupes() -> None:
    terms = all_terms()
    assert len(terms) == len(set(terms))


def test_build_initial_prompt_under_token_cap() -> None:
    prompt = build_initial_prompt(token_budget=200)
    # Approx 4 chars per token; check well under cap with margin.
    assert len(prompt) < 200 * 5
    assert prompt.startswith("Topics include:") or prompt.startswith("Glossary:")


def test_build_initial_prompt_deterministic() -> None:
    a = build_initial_prompt(token_budget=200)
    b = build_initial_prompt(token_budget=200)
    assert a == b


def test_build_initial_prompt_prioritizes_companies_and_products() -> None:
    prompt = build_initial_prompt(token_budget=200)
    # Companies + product names should land first in the budget.
    assert "Elasticsearch" in prompt
    assert "Weaviate" in prompt
    assert "ClickHouse" in prompt
```

- [ ] **Step 2: Run tests, confirm they fail (import error)**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_jargon.py -v`
Expected: ImportError / module not found.

- [ ] **Step 3: Implement `jargon.py`**

```python
"""Tech-jargon catalog for Whisper initial_prompt and fuzzy post-correction.

The full catalog is used for fuzzy correction. A deterministic sample
(companies + product names first, then concepts) feeds Whisper's prompt
within its ~224-token cap.
"""
from __future__ import annotations

from typing import Iterable


CATEGORIES: dict[str, list[str]] = {
    "Traditional databases": [
        "PostgreSQL", "Postgres", "MySQL", "MariaDB", "Oracle Database", "SQL Server",
        "SQLite", "MongoDB", "Cassandra", "ScyllaDB", "DynamoDB", "Cosmos DB",
        "FaunaDB", "CockroachDB", "TiDB", "YugabyteDB", "SingleStore", "Aerospike",
        "Couchbase", "Neo4j", "ArangoDB", "Dgraph", "JanusGraph", "RethinkDB",
        "RavenDB", "InfluxDB", "TimescaleDB", "QuestDB", "VictoriaMetrics",
    ],
    "Analytics OLAP warehouses": [
        "ClickHouse", "DuckDB", "Snowflake", "BigQuery", "Redshift", "Databricks",
        "Firebolt", "MotherDuck", "Tinybird", "Materialize", "RisingWave",
        "Apache Druid", "Apache Pinot", "StarRocks", "Apache Doris", "Greenplum",
        "Vertica", "Trino", "Presto", "Athena", "Dremio",
    ],
    "Vector databases": [
        "Pinecone", "Weaviate", "Qdrant", "Milvus", "Zilliz", "Chroma", "ChromaDB",
        "LanceDB", "Marqo", "Vespa", "Vectara", "Turbopuffer", "pgvector",
        "pg_embedding", "MyScale", "Vald", "txtai",
    ],
    "Caching and KV stores": [
        "Redis", "Valkey", "KeyDB", "Dragonfly", "Memcached", "Hazelcast",
        "etcd", "Consul",
    ],
    "Search": [
        "Elasticsearch", "Elastic", "OpenSearch", "Solr", "Apache Lucene", "Algolia",
        "Typesense", "Meilisearch", "Coveo",
    ],
    "AI labs and model providers": [
        "OpenAI", "Anthropic", "Claude", "GPT-4", "GPT-5", "Gemini", "Google DeepMind",
        "Meta AI", "Llama", "Mistral", "Mixtral", "Cohere", "AI21", "Stability AI",
        "Inflection", "Perplexity", "xAI", "Grok", "Hugging Face",
    ],
    "Inference infrastructure": [
        "Replicate", "Together AI", "Groq", "Fireworks AI", "Modal", "RunPod",
        "Lambda Labs", "Anyscale", "Baseten", "OctoAI", "vLLM", "TGI",
        "TensorRT-LLM", "Triton Inference Server",
    ],
    "LLM frameworks": [
        "LangChain", "LlamaIndex", "Haystack", "DSPy", "CrewAI", "AutoGen",
        "Pydantic AI", "Semantic Kernel", "Guidance", "LMQL", "Outlines",
    ],
    "Embedding models": [
        "text-embedding-3", "ada-002", "Voyage", "voyage-3", "Jina",
        "jina-embeddings-v3", "BGE", "E5", "Nomic", "Cohere embed", "GTE",
        "INSTRUCTOR", "ColBERT", "ColPali", "SPLADE",
    ],
    "Retrieval and search concepts": [
        "RAG", "retrieval-augmented generation", "HNSW", "IVF", "PQ",
        "product quantization", "OPQ", "scalar quantization", "binary quantization",
        "kNN", "ANN", "approximate nearest neighbor", "BM25", "TF-IDF", "MMR",
        "maximal marginal relevance", "reranking", "hybrid search", "semantic search",
        "lexical search", "dense retrieval", "sparse retrieval", "late interaction",
        "dense passage retrieval", "query expansion", "cross-encoder", "bi-encoder",
        "learned sparse retrieval", "chunking", "recursive chunking",
    ],
    "MLOps and training": [
        "PyTorch", "TensorFlow", "JAX", "MLX", "ONNX", "CUDA", "ROCm", "MosaicML",
        "Weights and Biases", "MLflow", "Kubeflow", "Ray", "Determined AI",
    ],
    "Cloud platforms": [
        "AWS", "GCP", "Google Cloud", "Azure", "Cloudflare", "Fastly", "Vercel",
        "Netlify", "Render", "Fly.io", "DigitalOcean", "Linode", "Hetzner", "OVH",
    ],
    "AWS services": [
        "EC2", "S3", "Lambda", "DynamoDB", "RDS", "Aurora", "Redshift", "Kinesis",
        "MSK", "EKS", "ECS", "Fargate", "SageMaker", "Bedrock", "Transcribe", "Polly",
        "Rekognition", "Comprehend", "OpenSearch Service", "ElastiCache", "Athena",
        "Glue", "EMR", "Step Functions", "EventBridge", "SQS", "SNS", "IAM", "VPC",
        "CloudFront", "Route 53", "Graviton", "Nitro", "i3en", "i7ie", "i8g",
    ],
    "Containers orchestration IaC": [
        "Kubernetes", "k8s", "Docker", "containerd", "Podman", "Helm", "Argo",
        "Argo CD", "Flux", "Terraform", "Pulumi", "OpenTofu", "Ansible",
    ],
    "Streaming and messaging": [
        "Kafka", "Confluent", "Redpanda", "Apache Pulsar", "NATS", "RabbitMQ",
        "AWS Kinesis", "Amazon MSK", "Apache Flink", "Apache Beam", "Spark Streaming",
    ],
    "Observability": [
        "Datadog", "New Relic", "Honeycomb", "Grafana", "Prometheus", "OpenTelemetry",
        "OTel", "Splunk", "Sumo Logic", "Lightstep", "Tempo", "Loki", "Mimir",
        "Jaeger", "Zipkin", "Sentry", "Rollbar",
    ],
    "Security": [
        "Snyk", "Wiz", "CrowdStrike", "SentinelOne", "Palo Alto Networks", "Okta",
        "Auth0", "HashiCorp Vault", "Tailscale", "Cloudflare Access", "Zscaler",
    ],
    "Dev tooling and IDEs": [
        "VS Code", "Cursor", "Zed", "Neovim", "JetBrains", "IntelliJ", "GitHub",
        "GitLab", "Bitbucket", "GitHub Copilot", "Cody", "Sourcegraph", "Tabnine",
        "Continue", "Aider", "Codeium", "Claude Code",
    ],
    "Frontend and web": [
        "React", "Next.js", "Vue", "Svelte", "SvelteKit", "Remix", "Astro", "Solid",
        "Qwik", "Tailwind", "shadcn",
    ],
    "Backend frameworks": [
        "Node.js", "Deno", "Bun", "Express", "Fastify", "NestJS", "Django",
        "FastAPI", "Flask", "Rails", "Phoenix", "Spring Boot", "Gin", "Echo", "Actix",
    ],
    "Languages": [
        "Python", "TypeScript", "JavaScript", "Rust", "Go", "Golang", "Java",
        "Kotlin", "Swift", "C#", "Elixir", "Clojure", "Haskell", "OCaml", "Zig",
    ],
    "Standards and protocols": [
        "HTTP", "HTTPS", "gRPC", "GraphQL", "REST", "JSON", "Protocol Buffers",
        "protobuf", "Avro", "Thrift", "MCP", "Model Context Protocol", "OAuth",
        "OIDC", "SAML", "JWT", "mTLS", "TLS", "WebSockets", "WebRTC", "QUIC",
        "HTTP/2", "HTTP/3",
    ],
    "Companies likely as guests or topics": [
        "Cloudflare", "Weaviate", "ClickHouse", "Snyk", "Elastic", "MongoDB",
        "Confluent", "Databricks", "Snowflake", "HashiCorp", "GitLab", "GitHub",
        "Datadog", "New Relic", "Stripe", "Twilio", "Okta", "Auth0", "Vercel",
        "Netlify", "Supabase", "PlanetScale", "Neon", "Turso", "Fly.io", "Render",
        "Linear", "Notion", "Figma", "Anthropic", "OpenAI", "Hugging Face", "Cohere",
        "Pinecone", "Qdrant", "Chroma", "LangChain", "LlamaIndex", "Replicate",
        "Modal", "Groq", "Fireworks", "Together AI", "Tinybird", "MotherDuck",
        "DuckDB Labs", "Materialize", "Redpanda", "Aiven", "Instaclustr", "Astronomer",
        "dbt Labs", "Fivetran", "Airbyte", "Metabase", "Hex", "Mode Analytics",
    ],
    "Roles": [
        "CTO", "CEO", "CMO", "VP Engineering", "VP Product", "founder", "co-founder",
        "principal engineer", "staff engineer", "distinguished engineer",
        "developer advocate", "DevRel", "developer relations",
    ],
    "Show specific": [
        "Chad", "Steve Mayzak", "Software in Blue",
        "Can I Get That Software in Blue", "SIB",
    ],
}


# Categories prioritized for the Whisper initial_prompt (highest signal first).
# Companies and product names land in the prompt; pure concepts only if budget
# remains.
_PROMPT_PRIORITY: list[str] = [
    "Show specific",
    "Companies likely as guests or topics",
    "Search",
    "Vector databases",
    "Analytics OLAP warehouses",
    "AI labs and model providers",
    "Embedding models",
    "Inference infrastructure",
    "LLM frameworks",
    "Traditional databases",
    "AWS services",
    "Cloud platforms",
    "Containers orchestration IaC",
    "Caching and KV stores",
    "Streaming and messaging",
    "Observability",
    "Security",
    "Dev tooling and IDEs",
    "Frontend and web",
    "Backend frameworks",
    "Languages",
    "MLOps and training",
    "Standards and protocols",
    "Retrieval and search concepts",
    "Roles",
]


def all_terms() -> list[str]:
    """Flat, deduplicated list of every term in the catalog. Order preserved
    by insertion order of CATEGORIES, with first-occurrence-wins dedup."""
    seen: set[str] = set()
    out: list[str] = []
    for terms in CATEGORIES.values():
        for t in terms:
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out


def _approx_tokens(s: str) -> int:
    """Rough token estimate (Whisper tokenizer ~= 4 chars/token for English)."""
    return max(1, len(s) // 4)


def build_initial_prompt(token_budget: int) -> str:
    """Build a deterministic Whisper initial_prompt within the token budget.

    Walks `_PROMPT_PRIORITY` in order, adding terms (deduplicated) until budget
    is exhausted. Result is stable across runs (no randomness).
    """
    seen: set[str] = set()
    chosen: list[str] = []
    header = "Glossary: "
    used = _approx_tokens(header)
    for cat in _PROMPT_PRIORITY:
        for term in CATEGORIES.get(cat, []):
            if term in seen:
                continue
            cost = _approx_tokens(term) + 1  # +1 for separator
            if used + cost > token_budget:
                return header + ", ".join(chosen) + "."
            seen.add(term)
            chosen.append(term)
            used += cost
    return header + ", ".join(chosen) + "."
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_jargon.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/podcast_lib/jargon.py tests/test_jargon.py
git commit -m "feat(podcast): tech jargon catalog + Whisper prompt builder"
```

---

### Task 5: `correct.py` — fuzzy jargon correction

**Files:**
- Create: `scripts/podcast_lib/correct.py`
- Test: `tests/test_correct.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_correct.py`:

```python
from __future__ import annotations

from scripts.podcast_lib.correct import correct_transcript


def test_corrects_misheard_elastic_search() -> None:
    transcript = {
        "segments": [
            {
                "start": 0.0, "end": 1.0, "text": "We use elastic search.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "We", "start": 0.0, "end": 0.1},
                    {"word": "use", "start": 0.1, "end": 0.3},
                    {"word": "elastic", "start": 0.3, "end": 0.6},
                    {"word": "search.", "start": 0.6, "end": 1.0},
                ],
            }
        ]
    }
    corrected, log = correct_transcript(transcript)
    seg = corrected["segments"][0]
    assert "Elasticsearch" in seg["text"]
    assert any("Elasticsearch" in entry["after"] for entry in log)


def test_corrects_misheard_clickhouse() -> None:
    transcript = {
        "segments": [
            {
                "start": 0.0, "end": 1.0, "text": "We picked Click House.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "We", "start": 0.0, "end": 0.1},
                    {"word": "picked", "start": 0.1, "end": 0.4},
                    {"word": "Click", "start": 0.4, "end": 0.6},
                    {"word": "House.", "start": 0.6, "end": 1.0},
                ],
            }
        ]
    }
    corrected, log = correct_transcript(transcript)
    assert "ClickHouse" in corrected["segments"][0]["text"]


def test_no_change_when_already_correct() -> None:
    transcript = {
        "segments": [
            {
                "start": 0.0, "end": 1.0, "text": "ClickHouse is fast.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "ClickHouse", "start": 0.0, "end": 0.5},
                    {"word": "is", "start": 0.5, "end": 0.7},
                    {"word": "fast.", "start": 0.7, "end": 1.0},
                ],
            }
        ]
    }
    corrected, log = correct_transcript(transcript)
    assert corrected["segments"][0]["text"] == "ClickHouse is fast."
    assert log == []


def test_does_not_corrupt_unrelated_words() -> None:
    transcript = {
        "segments": [
            {
                "start": 0.0, "end": 1.0, "text": "The quick brown fox.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "The", "start": 0.0, "end": 0.1},
                    {"word": "quick", "start": 0.1, "end": 0.3},
                    {"word": "brown", "start": 0.3, "end": 0.6},
                    {"word": "fox.", "start": 0.6, "end": 1.0},
                ],
            }
        ]
    }
    corrected, log = correct_transcript(transcript)
    assert corrected["segments"][0]["text"] == "The quick brown fox."
    assert log == []
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_correct.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `correct.py`**

```python
"""Fuzzy post-correction of transcripts against the tech-jargon catalog.

For each segment, we slide a window of 1-3 consecutive words over the
segment's words list and compare each window's joined string against
every catalog term using rapidfuzz. A match above FUZZY_MATCH_THRESHOLD
replaces the window in both the segment-level `text` and the per-word
`word` field of the first word in the window (subsequent words in the
window are blanked, then filtered out).

We intentionally only replace exact-token-count matches (don't drop a
3-word window onto a 1-word slot) to keep timestamps coherent.

Every replacement is recorded for auditing.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from rapidfuzz import fuzz

from .config import FUZZY_MATCH_THRESHOLD
from .jargon import all_terms


# Window sizes to try, largest first so multi-word terms beat single-word.
_WINDOW_SIZES = (3, 2, 1)


def _strip_punct(s: str) -> str:
    return s.rstrip(",.!?;:")


def _term_word_count(term: str) -> int:
    return len(term.split())


def correct_transcript(transcript: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (corrected_transcript, replacement_log).

    The original transcript is not mutated.
    """
    out = deepcopy(transcript)
    log: list[dict[str, Any]] = []
    catalog = all_terms()

    # Group catalog terms by word count for efficient per-window lookup.
    by_size: dict[int, list[str]] = {1: [], 2: [], 3: []}
    for term in catalog:
        wc = _term_word_count(term)
        if wc in by_size:
            by_size[wc].append(term)

    for seg_idx, seg in enumerate(out.get("segments", [])):
        words = seg.get("words", [])
        if not words:
            continue
        i = 0
        while i < len(words):
            matched = False
            for size in _WINDOW_SIZES:
                if i + size > len(words):
                    continue
                window_tokens = [_strip_punct(words[i + k]["word"]) for k in range(size)]
                window_str = " ".join(window_tokens)
                if not window_str.strip():
                    continue
                best_term = None
                best_score = 0.0
                for term in by_size[size]:
                    score = fuzz.ratio(window_str.lower(), term.lower())
                    if score > best_score:
                        best_score = score
                        best_term = term
                # Skip exact matches (already correct) and weak matches.
                if (
                    best_term is not None
                    and best_score >= FUZZY_MATCH_THRESHOLD
                    and window_str != best_term
                    and window_str.lower() != best_term.lower()
                ):
                    # Preserve trailing punctuation from the last word in window.
                    last_raw = words[i + size - 1]["word"]
                    trailing = ""
                    for ch in reversed(last_raw):
                        if ch in ",.!?;:":
                            trailing = ch + trailing
                        else:
                            break
                    replacement = best_term + trailing
                    log.append({
                        "segment": seg_idx,
                        "before": " ".join(words[i + k]["word"] for k in range(size)),
                        "after": replacement,
                        "score": round(best_score, 1),
                    })
                    # Update the first word; mark rest for removal.
                    words[i]["word"] = replacement
                    words[i]["end"] = words[i + size - 1]["end"]
                    for k in range(1, size):
                        words[i + k]["_drop"] = True
                    i += size
                    matched = True
                    break
            if not matched:
                i += 1
        # Filter dropped words.
        seg["words"] = [w for w in words if not w.get("_drop")]
        # Rebuild segment text from corrected words.
        seg["text"] = " ".join(w["word"] for w in seg["words"]).strip()

    return out, log
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_correct.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/podcast_lib/correct.py tests/test_correct.py
git commit -m "feat(podcast): fuzzy jargon correction with rapidfuzz"
```

---

### Task 6: `audio.py` — ffmpeg extraction

**Files:**
- Create: `scripts/podcast_lib/audio.py`

(No unit test — wraps a subprocess. Manual smoke test in Task 13.)

- [ ] **Step 1: Implement `audio.py`**

```python
"""Audio extraction from MP4 → 16kHz mono WAV via ffmpeg."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import TARGET_CHANNELS, TARGET_SAMPLE_RATE


class AudioError(Exception):
    """Raised when audio extraction fails. Exit code 2."""


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise AudioError(
            "ffmpeg not found on PATH. Install it: 'brew install ffmpeg' (Mac) "
            "or 'apt install ffmpeg' (Linux)."
        )


def extract_audio(video: Path, dest_wav: Path, *, force: bool = False) -> Path:
    """Extract a 16kHz mono WAV from the given video file.

    Returns the destination path. If `dest_wav` already exists and
    `force` is False, returns immediately.
    """
    ensure_ffmpeg()
    if dest_wav.exists() and not force:
        return dest_wav
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-ac", str(TARGET_CHANNELS),
        "-ar", str(TARGET_SAMPLE_RATE),
        "-vn",
        str(dest_wav),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AudioError(
            f"ffmpeg failed (exit {proc.returncode}):\n{proc.stderr}"
        )
    if not dest_wav.exists():
        raise AudioError(f"ffmpeg succeeded but output missing: {dest_wav}")
    return dest_wav
```

- [ ] **Step 2: Sanity-import**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -c "from scripts.podcast_lib.audio import extract_audio, AudioError; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add scripts/podcast_lib/audio.py
git commit -m "feat(podcast): audio extraction via ffmpeg"
```

---

### Task 7: `metadata.py` and `speakers.py`

**Files:**
- Create: `scripts/podcast_lib/metadata.py`
- Create: `scripts/podcast_lib/speakers.py`
- Test: `tests/test_metadata.py`
- Test: `tests/test_speakers.py`

- [ ] **Step 1: Write failing tests for metadata**

Create `tests/test_metadata.py`:

```python
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
```

- [ ] **Step 2: Write failing tests for speakers**

Create `tests/test_speakers.py`:

```python
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
```

- [ ] **Step 3: Run tests, confirm they fail**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_metadata.py tests/test_speakers.py -v`
Expected: ImportError.

- [ ] **Step 4: Implement `metadata.py`**

```python
"""Read/write `metadata.json` describing pipeline runs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Metadata:
    path: Path
    data: dict[str, Any] = field(default_factory=lambda: {"stages": {}, "corrections": []})

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def record_stage(self, name: str, *, duration_s: float, ok: bool, **extra: Any) -> None:
        self.data.setdefault("stages", {})[name] = {
            "duration_s": duration_s,
            "ok": ok,
            **extra,
        }

    def add_correction(self, entry: dict[str, Any]) -> None:
        self.data.setdefault("corrections", []).append(entry)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True))


def load_metadata(path: Path) -> Metadata:
    if not path.exists():
        return Metadata(path=path)
    return Metadata(path=path, data=json.loads(path.read_text()))
```

- [ ] **Step 5: Implement `speakers.py`**

```python
"""Read/write `speakers.json` mapping SPEAKER_NN → human name."""
from __future__ import annotations

import json
from pathlib import Path


class SpeakerError(Exception):
    """Raised on bad speaker override input."""


def load_speakers(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_speakers(path: Path, mapping: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping, indent=2, sort_keys=True))


def apply_overrides(existing: dict[str, str], pairs: list[str]) -> dict[str, str]:
    """Merge `KEY=VALUE` strings into `existing`, returning the new mapping."""
    out = dict(existing)
    for raw in pairs:
        if "=" not in raw:
            raise SpeakerError(f"Bad speaker override '{raw}': expected KEY=VALUE")
        k, v = raw.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k or not v:
            raise SpeakerError(f"Bad speaker override '{raw}': empty key or value")
        out[k] = v
    return out
```

- [ ] **Step 6: Run tests**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_metadata.py tests/test_speakers.py -v`
Expected: 7 passed (2 metadata + 5 speakers).

- [ ] **Step 7: Commit**

```bash
git add scripts/podcast_lib/metadata.py scripts/podcast_lib/speakers.py tests/test_metadata.py tests/test_speakers.py
git commit -m "feat(podcast): metadata + speakers I/O"
```

---

### Task 8: Output formatters (SRT, VTT, TXT, MD)

**Files:**
- Create: `scripts/podcast_lib/formatters/srt.py`
- Create: `scripts/podcast_lib/formatters/vtt.py`
- Create: `scripts/podcast_lib/formatters/txt.py`
- Create: `scripts/podcast_lib/formatters/md.py`
- Test: `tests/test_formatters.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_formatters.py`:

```python
from __future__ import annotations

from scripts.podcast_lib.formatters.md import render_md
from scripts.podcast_lib.formatters.srt import render_srt
from scripts.podcast_lib.formatters.txt import render_txt
from scripts.podcast_lib.formatters.vtt import render_vtt


def test_srt_header_and_indices(sample_transcript: dict) -> None:
    out = render_srt(sample_transcript)
    # First cue starts at index 1 in SRT.
    assert out.splitlines()[0] == "1"


def test_srt_no_mid_word_breaks(sample_transcript: dict) -> None:
    out = render_srt(sample_transcript)
    # No cue text should end with a partial word like "Elastic" alone.
    for block in out.strip().split("\n\n"):
        text_line = block.splitlines()[2]  # index, time, text
        # Bare heuristic: cue text is whitespace-stripped, no trailing dash.
        assert not text_line.endswith("-")


def test_srt_cues_under_three_seconds(sample_transcript: dict) -> None:
    out = render_srt(sample_transcript)
    for block in out.strip().split("\n\n"):
        time_line = block.splitlines()[1]
        start, end = time_line.split(" --> ")
        s_h, s_m, s_s = start.replace(",", ".").split(":")
        e_h, e_m, e_s = end.replace(",", ".").split(":")
        s_total = int(s_h) * 3600 + int(s_m) * 60 + float(s_s)
        e_total = int(e_h) * 3600 + int(e_m) * 60 + float(e_s)
        assert e_total - s_total <= 3.05  # tiny float slop


def test_vtt_starts_with_header(sample_transcript: dict) -> None:
    out = render_vtt(sample_transcript)
    assert out.splitlines()[0] == "WEBVTT"


def test_txt_has_no_timestamps(sample_transcript: dict) -> None:
    out = render_txt(sample_transcript)
    assert "-->" not in out
    assert "Welcome" in out
    assert "Elasticsearch" in out


def test_md_groups_consecutive_speakers(sample_transcript: dict) -> None:
    out = render_md(sample_transcript, speakers={})
    # Two SPEAKER_00 segments → one paragraph; one SPEAKER_01 → second paragraph.
    paragraphs = [p for p in out.split("\n\n") if p.strip()]
    assert len(paragraphs) == 2
    assert paragraphs[0].startswith("**SPEAKER_00:**")
    assert paragraphs[1].startswith("**SPEAKER_01:**")


def test_md_uses_human_names_when_provided(sample_transcript: dict) -> None:
    out = render_md(sample_transcript, speakers={"SPEAKER_00": "Chad", "SPEAKER_01": "Steve"})
    assert "**Chad:**" in out
    assert "**Steve:**" in out
    assert "SPEAKER_00" not in out
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_formatters.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `formatters/srt.py`**

```python
"""SRT subtitle renderer.

Cue strategy: walk a segment's word list, accumulating words into the
current cue. Close the cue when any of these is reached:
- MAX_CUE_SECONDS of duration
- MAX_CUE_WORDS of word count
- a sentence-ending punctuation (`.!?`)

Cues never split a word — the word is the smallest unit.
"""
from __future__ import annotations

from typing import Any

from ..config import MAX_CUE_SECONDS, MAX_CUE_WORDS


def _format_ts(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _cues_for_segment(seg: dict[str, Any]) -> list[tuple[float, float, str]]:
    words = seg.get("words", [])
    if not words:
        text = seg.get("text", "").strip()
        if text:
            return [(seg["start"], seg["end"], text)]
        return []
    cues: list[tuple[float, float, str]] = []
    cur_start: float | None = None
    cur_words: list[str] = []
    for w in words:
        if cur_start is None:
            cur_start = w["start"]
        cur_words.append(w["word"])
        is_sentence_end = any(w["word"].rstrip().endswith(p) for p in (".", "!", "?"))
        too_long = w["end"] - cur_start >= MAX_CUE_SECONDS
        too_many = len(cur_words) >= MAX_CUE_WORDS
        if is_sentence_end or too_long or too_many:
            cues.append((cur_start, w["end"], " ".join(cur_words).strip()))
            cur_words = []
            cur_start = None
    if cur_words and cur_start is not None:
        cues.append((cur_start, words[-1]["end"], " ".join(cur_words).strip()))
    return cues


def render_srt(transcript: dict[str, Any]) -> str:
    blocks: list[str] = []
    idx = 1
    for seg in transcript.get("segments", []):
        for start, end, text in _cues_for_segment(seg):
            blocks.append(
                f"{idx}\n{_format_ts(start)} --> {_format_ts(end)}\n{text}"
            )
            idx += 1
    return "\n\n".join(blocks) + ("\n" if blocks else "")
```

- [ ] **Step 4: Implement `formatters/vtt.py`**

```python
"""WebVTT renderer. Reuses SRT cue logic, swaps timestamp format and header."""
from __future__ import annotations

from typing import Any

from .srt import _cues_for_segment


def _format_ts(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def render_vtt(transcript: dict[str, Any]) -> str:
    out = ["WEBVTT", ""]
    for seg in transcript.get("segments", []):
        for start, end, text in _cues_for_segment(seg):
            out.append(f"{_format_ts(start)} --> {_format_ts(end)}")
            out.append(text)
            out.append("")
    return "\n".join(out)
```

- [ ] **Step 5: Implement `formatters/txt.py`**

```python
"""Plain-text transcript renderer. No timestamps, no speaker labels."""
from __future__ import annotations

from typing import Any


def render_txt(transcript: dict[str, Any]) -> str:
    lines = []
    for seg in transcript.get("segments", []):
        text = seg.get("text", "").strip()
        if text:
            lines.append(text)
    return "\n".join(lines) + ("\n" if lines else "")
```

- [ ] **Step 6: Implement `formatters/md.py`**

```python
"""Speaker-labeled Markdown transcript.

Consecutive segments by the same speaker are merged into one paragraph.
Speaker label uses `speakers[id]` if available, else the raw id.
"""
from __future__ import annotations

from typing import Any


def _label(speaker_id: str, mapping: dict[str, str]) -> str:
    return mapping.get(speaker_id, speaker_id)


def render_md(transcript: dict[str, Any], speakers: dict[str, str]) -> str:
    paragraphs: list[str] = []
    current_speaker: str | None = None
    current_text: list[str] = []

    def flush() -> None:
        if current_speaker is not None and current_text:
            text = " ".join(s.strip() for s in current_text).strip()
            paragraphs.append(f"**{_label(current_speaker, speakers)}:** {text}")

    for seg in transcript.get("segments", []):
        sp = seg.get("speaker", "SPEAKER_??")
        if sp != current_speaker:
            flush()
            current_speaker = sp
            current_text = []
        text = seg.get("text", "").strip()
        if text:
            current_text.append(text)
    flush()
    return "\n\n".join(paragraphs) + ("\n" if paragraphs else "")
```

- [ ] **Step 7: Run tests**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_formatters.py -v`
Expected: 7 passed.

- [ ] **Step 8: Commit**

```bash
git add scripts/podcast_lib/formatters/ tests/test_formatters.py
git commit -m "feat(podcast): SRT/VTT/TXT/MD formatters with cue limits"
```

---

### Task 9: Transcription backend Protocol + WhisperX implementation

**Files:**
- Create: `scripts/podcast_lib/transcribe/base.py`
- Create: `scripts/podcast_lib/transcribe/whisperx_backend.py`
- Create: `scripts/podcast_lib/transcribe/deepgram_backend.py`
- Create: `scripts/podcast_lib/transcribe/aws_backend.py`

(No unit tests for the WhisperX backend — it's an integration boundary tested in Task 13's E2E run.)

- [ ] **Step 1: Implement `transcribe/base.py`**

```python
"""Transcription backend protocol.

A backend ingests a path to a 16kHz mono WAV plus options, and returns a
WhisperX-shaped dict with `language` and `segments` (each with words +
optional speaker label).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class TranscriptionOptions:
    model: str
    initial_prompt: str
    min_speakers: int
    max_speakers: int
    hf_token: str | None


class TranscriptionBackend(Protocol):
    """Implementations transcribe + word-align + diarize and return a single dict."""

    name: str

    def transcribe(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        ...

    def device_info(self) -> dict[str, str]:
        ...
```

- [ ] **Step 2: Implement `transcribe/whisperx_backend.py`**

```python
"""WhisperX transcription backend with auto-detected device.

Device selection:
  - CUDA available → 'cuda', float16
  - Apple MPS available → 'mps' for alignment + diarization, but 'cpu' int8
    for the Whisper transcription pass (CTranslate2 has no Metal support).
  - Otherwise → 'cpu', int8

Stages:
  1. Load Whisper model and transcribe (raw segments, no word ts).
  2. Load alignment model for the detected language and align word-level ts.
  3. Run pyannote diarization, assign speaker labels per word/segment.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import TranscriptionBackend, TranscriptionOptions


def _detect_device() -> tuple[str, str, str]:
    """Return (transcribe_device, transcribe_compute, align_diarize_device)."""
    try:
        import torch  # type: ignore
    except Exception:
        return "cpu", "int8", "cpu"
    if torch.cuda.is_available():
        return "cuda", "float16", "cuda"
    mps_avail = getattr(getattr(torch, "backends", None), "mps", None)
    if mps_avail is not None and torch.backends.mps.is_available():
        # Whisper transcription stays on CPU (CT2), other stages on MPS.
        return "cpu", "int8", "mps"
    return "cpu", "int8", "cpu"


class WhisperXBackend:
    name = "whisperx"

    def __init__(self) -> None:
        self._tx_dev, self._tx_compute, self._align_dev = _detect_device()

    def device_info(self) -> dict[str, str]:
        return {
            "backend": self.name,
            "transcribe_device": self._tx_dev,
            "transcribe_compute": self._tx_compute,
            "align_diarize_device": self._align_dev,
        }

    def transcribe(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        # Imported lazily so unit tests of CLI/registration don't require whisperx.
        import whisperx  # type: ignore

        audio = whisperx.load_audio(str(audio_path))

        model = whisperx.load_model(
            opts.model,
            device=self._tx_dev,
            compute_type=self._tx_compute,
            asr_options={"initial_prompt": opts.initial_prompt} if opts.initial_prompt else None,
        )
        result = model.transcribe(audio, batch_size=16)
        # Free model memory before next stage.
        del model
        try:
            import gc
            gc.collect()
            import torch  # type: ignore
            if self._tx_dev == "cuda":
                torch.cuda.empty_cache()
        except Exception:
            pass

        align_model, align_meta = whisperx.load_align_model(
            language_code=result["language"], device=self._align_dev
        )
        aligned = whisperx.align(
            result["segments"], align_model, align_meta, audio,
            self._align_dev, return_char_alignments=False,
        )
        del align_model

        if not opts.hf_token:
            raise RuntimeError(
                "HF_TOKEN not set. Diarization requires a Hugging Face token "
                "with access to pyannote/speaker-diarization-3.1. "
                "See .env.example for setup."
            )

        try:
            diarize_pipeline = whisperx.DiarizationPipeline(
                use_auth_token=opts.hf_token, device=self._align_dev
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load pyannote diarization pipeline: {e}. "
                "Confirm you accepted the gated model terms at "
                "https://huggingface.co/pyannote/speaker-diarization-3.1"
            ) from e

        diarize_segments = diarize_pipeline(
            str(audio_path),
            min_speakers=opts.min_speakers,
            max_speakers=opts.max_speakers,
        )
        final = whisperx.assign_word_speakers(diarize_segments, aligned)
        # final is shaped like {"segments": [...], "word_segments": [...]}.
        # Add language for downstream tools.
        final["language"] = result["language"]
        return final
```

- [ ] **Step 3: Implement `transcribe/deepgram_backend.py`**

```python
"""Deepgram backend stub.

Will speak the same Protocol as WhisperX once implemented.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import TranscriptionOptions


class DeepgramBackend:
    name = "deepgram"

    def device_info(self) -> dict[str, str]:
        return {"backend": self.name, "transcribe_device": "cloud"}

    def transcribe(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        raise NotImplementedError(
            "Deepgram backend not yet implemented. Use --backend whisperx."
        )
```

- [ ] **Step 4: Implement `transcribe/aws_backend.py`**

```python
"""AWS Transcribe backend stub.

Will speak the same Protocol as WhisperX once implemented.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import TranscriptionOptions


class AWSTranscribeBackend:
    name = "aws"

    def device_info(self) -> dict[str, str]:
        return {"backend": self.name, "transcribe_device": "cloud"}

    def transcribe(self, audio_path: Path, opts: TranscriptionOptions) -> dict[str, Any]:
        raise NotImplementedError(
            "AWS Transcribe backend not yet implemented. Use --backend whisperx."
        )
```

- [ ] **Step 5: Sanity-import (no actual whisperx call yet)**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -c "from scripts.podcast_lib.transcribe.whisperx_backend import WhisperXBackend; b = WhisperXBackend(); print(b.device_info())"`
Expected: prints a dict with `backend: whisperx` and detected device strings. No model loaded yet.

- [ ] **Step 6: Commit**

```bash
git add scripts/podcast_lib/transcribe/
git commit -m "feat(podcast): WhisperX backend with device auto-detect; Deepgram + AWS stubs"
```

---

### Task 10: `diarize.py` — placeholder reserved for future direct-diarization use

**Files:**
- Create: `scripts/podcast_lib/diarize.py`

The WhisperX backend already runs diarization inline. We expose a small helper here so future backends (e.g. Deepgram with no built-in diarization) can call pyannote directly.

- [ ] **Step 1: Implement `diarize.py`**

```python
"""Standalone pyannote diarization for backends that don't include it.

The WhisperX backend handles diarization internally; this module exists
so future backends (Deepgram, AWS) can reuse the same pyannote pipeline.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def diarize(audio_path: Path, *, hf_token: str, min_speakers: int, max_speakers: int,
            device: str = "cpu") -> Any:
    """Run pyannote/speaker-diarization-3.1. Returns the pipeline output."""
    if not hf_token:
        raise RuntimeError(
            "HF_TOKEN not set. Diarization requires a Hugging Face token. "
            "See .env.example."
        )
    try:
        from pyannote.audio import Pipeline  # type: ignore
    except Exception as e:
        raise RuntimeError(f"pyannote.audio unavailable: {e}") from e

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", use_auth_token=hf_token
    )
    try:
        import torch  # type: ignore
        pipeline.to(torch.device(device))
    except Exception:
        pass
    return pipeline(
        str(audio_path),
        min_speakers=min_speakers,
        max_speakers=max_speakers,
    )
```

- [ ] **Step 2: Sanity-import**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -c "from scripts.podcast_lib.diarize import diarize; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add scripts/podcast_lib/diarize.py
git commit -m "feat(podcast): standalone diarize helper for future non-WhisperX backends"
```

---

### Task 11: `transcribe` command — wire everything together

**Files:**
- Create: `scripts/podcast_lib/commands/transcribe.py`

(No unit tests — orchestrator. E2E test in Task 13.)

- [ ] **Step 1: Implement `commands/transcribe.py`**

```python
"""`podcast transcribe` subcommand."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

from ..audio import AudioError, extract_audio
from ..config import (
    ArtifactPaths,
    DEFAULT_BACKEND,
    DEFAULT_MAX_SPEAKERS,
    DEFAULT_MIN_SPEAKERS,
    DEFAULT_MODEL,
    PROMPT_TOKEN_BUDGET,
)
from ..correct import correct_transcript
from ..episode import EpisodeError, discover_master_video, resolve_episode_folder
from ..formatters.md import render_md
from ..formatters.srt import render_srt
from ..formatters.txt import render_txt
from ..formatters.vtt import render_vtt
from ..jargon import build_initial_prompt
from ..metadata import load_metadata
from ..speakers import load_speakers
from ..transcribe.aws_backend import AWSTranscribeBackend
from ..transcribe.base import TranscriptionOptions
from ..transcribe.deepgram_backend import DeepgramBackend
from ..transcribe.whisperx_backend import WhisperXBackend


def _backend(name: str):
    if name == "whisperx":
        return WhisperXBackend()
    if name == "deepgram":
        return DeepgramBackend()
    if name == "aws":
        return AWSTranscribeBackend()
    raise typer.BadParameter(f"unknown backend: {name}")


def run(
    episode: str = typer.Argument(..., help="Episode folder (e.g. Episode43)"),
    model: str = typer.Option(DEFAULT_MODEL, "--model"),
    min_speakers: int = typer.Option(DEFAULT_MIN_SPEAKERS, "--min-speakers"),
    max_speakers: int = typer.Option(DEFAULT_MAX_SPEAKERS, "--max-speakers"),
    backend: str = typer.Option(DEFAULT_BACKEND, "--backend"),
    file_override: Optional[Path] = typer.Option(None, "--file", help="Path to a non-standard MP4."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing transcript.json."),
) -> None:
    load_dotenv()
    console = Console()

    try:
        folder = resolve_episode_folder(episode)
        master = discover_master_video(folder, override=file_override)
    except EpisodeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)

    paths = ArtifactPaths(root=folder)
    paths.ensure()

    if paths.transcript_json.exists() and not force:
        console.print(
            f"[yellow]transcript.json already exists at {paths.transcript_json}. "
            "Pass --force to overwrite.[/yellow]"
        )
        raise typer.Exit(0)

    md_state = load_metadata(paths.metadata)
    md_state.set("episode", folder.name)
    md_state.set("master_video", str(master))
    md_state.set("model", model)
    md_state.set("min_speakers", min_speakers)
    md_state.set("max_speakers", max_speakers)

    # Stage 1: audio
    console.print(f"[cyan]Extracting audio[/cyan] {master.name} → {paths.audio.name}")
    t0 = time.monotonic()
    try:
        extract_audio(master, paths.audio, force=force)
    except AudioError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    md_state.record_stage("audio", duration_s=round(time.monotonic() - t0, 2), ok=True)
    md_state.save()

    # Stage 2: transcribe + align + diarize
    bk = _backend(backend)
    md_state.set("device_info", bk.device_info())
    md_state.save()

    prompt = build_initial_prompt(token_budget=PROMPT_TOKEN_BUDGET)
    console.print(f"[cyan]Transcribing[/cyan] backend={backend} model={model}")
    t0 = time.monotonic()
    try:
        result = bk.transcribe(
            paths.audio,
            TranscriptionOptions(
                model=model,
                initial_prompt=prompt,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
                hf_token=os.environ.get("HF_TOKEN"),
            ),
        )
    except NotImplementedError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    except Exception as e:
        console.print(f"[red]Transcription failed: {e}[/red]")
        md_state.record_stage("transcribe", duration_s=round(time.monotonic() - t0, 2), ok=False, error=str(e))
        md_state.save()
        raise typer.Exit(2)
    md_state.record_stage("transcribe", duration_s=round(time.monotonic() - t0, 2), ok=True)
    md_state.save()

    # Stage 3: fuzzy correction
    console.print("[cyan]Applying fuzzy jargon correction[/cyan]")
    t0 = time.monotonic()
    corrected, log = correct_transcript(result)
    for entry in log:
        md_state.add_correction(entry)
    md_state.record_stage("correct", duration_s=round(time.monotonic() - t0, 2), ok=True, replacements=len(log))
    md_state.save()

    # Persist canonical transcript.
    paths.transcript_json.write_text(json.dumps(corrected, indent=2))

    # Stage 4: render derivatives
    console.print("[cyan]Rendering SRT/VTT/TXT/MD[/cyan]")
    speakers = load_speakers(paths.speakers)
    paths.transcript_srt.write_text(render_srt(corrected))
    paths.transcript_vtt.write_text(render_vtt(corrected))
    paths.transcript_txt.write_text(render_txt(corrected))
    paths.transcript_md.write_text(render_md(corrected, speakers=speakers))
    md_state.record_stage("render", duration_s=0.0, ok=True)
    md_state.save()

    console.print(f"[green]Done.[/green] Artifacts in {paths.artifacts_dir}")
```

- [ ] **Step 2: Sanity-import**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -c "from scripts.podcast_lib.commands.transcribe import run; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add scripts/podcast_lib/commands/transcribe.py
git commit -m "feat(podcast): transcribe command orchestrating audio + WhisperX + correction + render"
```

---

### Task 12: `subtitle`, `label`, `status` commands + stub commands

**Files:**
- Create: `scripts/podcast_lib/commands/subtitle.py`
- Create: `scripts/podcast_lib/commands/label.py`
- Create: `scripts/podcast_lib/commands/status.py`
- Create: `scripts/podcast_lib/commands/moments.py`
- Create: `scripts/podcast_lib/commands/thumbnail.py`
- Create: `scripts/podcast_lib/commands/describe.py`
- Create: `scripts/podcast_lib/commands/linkedin.py`
- Create: `scripts/podcast_lib/commands/chapters.py`
- Create: `scripts/podcast_lib/commands/publish_youtube.py`
- Create: `scripts/podcast_lib/commands/publish_spotify.py`

- [ ] **Step 1: Implement `commands/subtitle.py`**

```python
"""`podcast subtitle` — regenerate SRT/VTT from transcript.json (no re-transcribe)."""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from ..config import ArtifactPaths
from ..episode import EpisodeError, resolve_episode_folder
from ..formatters.srt import render_srt
from ..formatters.vtt import render_vtt


def run(episode: str = typer.Argument(...)) -> None:
    console = Console()
    try:
        folder = resolve_episode_folder(episode)
    except EpisodeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    paths = ArtifactPaths(root=folder)
    if not paths.transcript_json.exists():
        console.print(f"[red]No transcript.json at {paths.transcript_json}. Run `podcast transcribe` first.[/red]")
        raise typer.Exit(2)
    transcript = json.loads(paths.transcript_json.read_text())
    paths.transcript_srt.write_text(render_srt(transcript))
    paths.transcript_vtt.write_text(render_vtt(transcript))
    console.print(f"[green]Regenerated SRT + VTT in {paths.artifacts_dir}[/green]")
```

- [ ] **Step 2: Implement `commands/label.py`**

```python
"""`podcast label` — set speaker names and re-render transcript.md."""
from __future__ import annotations

import json
from typing import List

import typer
from rich.console import Console

from ..config import ArtifactPaths
from ..episode import EpisodeError, resolve_episode_folder
from ..formatters.md import render_md
from ..speakers import SpeakerError, apply_overrides, load_speakers, save_speakers


def run(
    episode: str = typer.Argument(...),
    pairs: List[str] = typer.Argument(..., help="SPEAKER_00=Chad SPEAKER_01=Steve ..."),
) -> None:
    console = Console()
    try:
        folder = resolve_episode_folder(episode)
    except EpisodeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    paths = ArtifactPaths(root=folder)
    if not paths.transcript_json.exists():
        console.print(f"[red]No transcript.json at {paths.transcript_json}. Run `podcast transcribe` first.[/red]")
        raise typer.Exit(2)
    existing = load_speakers(paths.speakers)
    try:
        merged = apply_overrides(existing, pairs)
    except SpeakerError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    save_speakers(paths.speakers, merged)
    transcript = json.loads(paths.transcript_json.read_text())
    paths.transcript_md.write_text(render_md(transcript, speakers=merged))
    console.print(f"[green]Updated speakers.json + transcript.md.[/green] {merged}")
```

- [ ] **Step 3: Implement `commands/status.py`**

```python
"""`podcast status` — show which artifacts exist."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from ..config import ArtifactPaths
from ..episode import EpisodeError, resolve_episode_folder


def run(episode: str = typer.Argument(...)) -> None:
    console = Console()
    try:
        folder = resolve_episode_folder(episode)
    except EpisodeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    paths = ArtifactPaths(root=folder)

    table = Table(title=f"Status: {folder.name}")
    table.add_column("Artifact")
    table.add_column("Path")
    table.add_column("Exists")
    for label, p in [
        ("audio.wav", paths.audio),
        ("transcript.json", paths.transcript_json),
        ("transcript.srt", paths.transcript_srt),
        ("transcript.vtt", paths.transcript_vtt),
        ("transcript.txt", paths.transcript_txt),
        ("transcript.md", paths.transcript_md),
        ("speakers.json", paths.speakers),
        ("metadata.json", paths.metadata),
    ]:
        marker = "[green]yes[/green]" if p.exists() else "[red]no[/red]"
        table.add_row(label, str(p), marker)
    console.print(table)
```

- [ ] **Step 4: Implement each stub (7 files, identical body)**

For each file `scripts/podcast_lib/commands/{moments,thumbnail,describe,linkedin,chapters,publish_youtube,publish_spotify}.py`:

```python
"""`podcast <stage>` — not implemented yet."""
from __future__ import annotations

import typer
from rich.console import Console


def run(episode: str = typer.Argument(...)) -> None:
    Console().print("[yellow]not implemented yet[/yellow]")
    raise typer.Exit(0)
```

- [ ] **Step 5: Sanity-import all command modules**

Run:

```bash
cd /Users/ctindel/src/softwareinblue.com && python3 -c "
from scripts.podcast_lib.commands import (
    transcribe, subtitle, label, status,
    moments, thumbnail, describe, linkedin, chapters,
    publish_youtube, publish_spotify,
)
print('ok')
"
```

Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add scripts/podcast_lib/commands/
git commit -m "feat(podcast): subtitle/label/status commands + 7 stage stubs"
```

---

### Task 13: `podcast.py` Typer entrypoint + CLI registration test

**Files:**
- Create: `podcast.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI test**

Create `tests/test_cli.py`:

```python
from __future__ import annotations

from typer.testing import CliRunner

from podcast import app

runner = CliRunner()


def test_help_shows_all_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for sub in [
        "transcribe", "subtitle", "label", "status",
        "moments", "thumbnail", "describe", "linkedin", "chapters",
        "publish-youtube", "publish-spotify",
    ]:
        assert sub in result.stdout, f"Missing subcommand in help: {sub}"


def test_moments_stub_exits_zero(tmp_path) -> None:
    (tmp_path / "Episode99").mkdir()
    result = runner.invoke(app, ["moments", str(tmp_path / "Episode99")])
    assert result.exit_code == 0
    assert "not implemented yet" in result.stdout


def test_status_on_missing_folder_exits_2(tmp_path) -> None:
    result = runner.invoke(app, ["status", str(tmp_path / "Episode404")])
    assert result.exit_code == 2
```

- [ ] **Step 2: Run test, confirm it fails**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/test_cli.py -v`
Expected: ImportError on `from podcast import app`.

- [ ] **Step 3: Implement `podcast.py`**

```python
"""Top-level Typer CLI for SIB podcast post-processing."""
from __future__ import annotations

import typer

from scripts.podcast_lib.commands import (
    chapters,
    describe,
    label,
    linkedin,
    moments,
    publish_spotify,
    publish_youtube,
    status,
    subtitle,
    thumbnail,
    transcribe,
)


app = typer.Typer(
    help="Post-production for the 'Can I Get That Software in Blue?' podcast.",
    no_args_is_help=True,
)

app.command("transcribe")(transcribe.run)
app.command("subtitle")(subtitle.run)
app.command("label")(label.run)
app.command("status")(status.run)
app.command("moments")(moments.run)
app.command("thumbnail")(thumbnail.run)
app.command("describe")(describe.run)
app.command("linkedin")(linkedin.run)
app.command("chapters")(chapters.run)
app.command("publish-youtube")(publish_youtube.run)
app.command("publish-spotify")(publish_spotify.run)


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run all tests**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 -m pytest tests/ -v`
Expected: all tests pass (test_cli + everything from prior tasks).

- [ ] **Step 5: Verify CLI runs interactively**

Run: `cd /Users/ctindel/src/softwareinblue.com && python3 podcast.py --help`
Expected: help output listing all 11 subcommands.

- [ ] **Step 6: Commit**

```bash
git add podcast.py tests/test_cli.py
git commit -m "feat(podcast): Typer CLI entrypoint with all subcommands wired"
```

---

### Task 14: SKILL.md

**Files:**
- Create: `.claude/skills/podcast-postprocessing/SKILL.md`

- [ ] **Step 1: Create the skill directory and file**

```bash
cd /Users/ctindel/src/softwareinblue.com && mkdir -p .claude/skills/podcast-postprocessing
```

- [ ] **Step 2: Write `SKILL.md`**

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/podcast-postprocessing/SKILL.md
git commit -m "feat(podcast): skill descriptor pointing at the CLI"
```

---

### Task 15: Amplify selective-deploy via GitHub Actions webhook

**Files:**
- Create: `.github/workflows/amplify-deploy.yml`

The plan also documents the AWS Console click-through the user must perform; that's not committed but is in the README.

- [ ] **Step 1: Create the workflow**

```bash
cd /Users/ctindel/src/softwareinblue.com && mkdir -p .github/workflows
```

Create `.github/workflows/amplify-deploy.yml`:

```yaml
name: Trigger Amplify deploy

on:
  push:
    branches: [main]
    paths-ignore:
      - 'scripts/**'
      - '.claude/**'
      - 'docs/**'
      - 'tests/**'
      - 'podcast.py'
      - 'requirements.txt'
      - '.env.example'
      - '.gitignore'
      - '**/*.md'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: POST to Amplify webhook
        run: |
          curl -fsS -X POST \
            -H 'Content-Type: application/json' \
            -d '{}' \
            "${AMPLIFY_WEBHOOK_URL}"
        env:
          AMPLIFY_WEBHOOK_URL: ${{ secrets.AMPLIFY_WEBHOOK_URL }}
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/amplify-deploy.yml
git commit -m "ci: selective Amplify deploy via webhook for non-script/skill changes"
```

> **Note for user (manual steps, not committed):**
>
> 1. AWS Amplify Console → app `softwareinblue.com` → Hosting → Build settings → branch `main`. Toggle **Auto build OFF**.
> 2. Same panel → **Incoming webhooks** → create webhook for `main`. Copy the URL.
> 3. GitHub repo → Settings → Secrets and variables → Actions → add `AMPLIFY_WEBHOOK_URL` with that URL.
>
> After those three steps, only pushes that touch web-relevant files trigger a deploy.

---

### Task 16: README updates

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current README**

Run: `cat /Users/ctindel/src/softwareinblue.com/README.md`

- [ ] **Step 2: Append the podcast section**

Add at the end of `README.md`:

```markdown

## Podcast post-processing

Automation for "Can I Get That Software in Blue?" episodes — transcription, subtitles, speaker labels, with future stubs for clip-finding, descriptions, LinkedIn posts, and publishing.

### One-time setup

1. Install ffmpeg.
   - Mac: `brew install ffmpeg`
   - Linux: `apt install ffmpeg`
2. Install Python deps. Use a venv if you like.
   - `pip install -r requirements.txt`
   - On Linux with NVIDIA GPU, install the CUDA wheel of PyTorch first per the official PyTorch site to get GPU acceleration.
3. Get a Hugging Face token.
   - Create one (read scope) at https://huggingface.co/settings/tokens
   - Accept gated model terms at https://huggingface.co/pyannote/speaker-diarization-3.1
   - `cp .env.example .env`, paste token into `HF_TOKEN`.
4. First-run model download is ~3 GB (Whisper large-v3 + alignment + pyannote).

### Running

From the repo root:

```
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
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README setup + run instructions for podcast post-processing"
```

---

### Task 17: End-to-end acceptance test on `Episode43/`

This task only runs if the user has staged `Episode43/SIB_E43_Final.mp4` locally. If not, ask them where it is and stage it first.

- [ ] **Step 1: Confirm Episode43 is staged**

Run: `ls /Users/ctindel/src/softwareinblue.com/Episode43/*Final*.mp4 2>/dev/null || ls /tmp/Episode43/*Final*.mp4 2>/dev/null`

If neither exists, ask the user where the file lives and stage it (copy or symlink) before continuing.

- [ ] **Step 2: Confirm `.env` has `HF_TOKEN`**

Run: `grep -q '^HF_TOKEN=hf_' /Users/ctindel/src/softwareinblue.com/.env && echo ok || echo MISSING`

If MISSING, ask the user to populate `.env` from `.env.example`.

- [ ] **Step 3: Run transcribe**

```bash
cd /Users/ctindel/src/softwareinblue.com && python3 podcast.py transcribe Episode43
```

Expected: progress lines for each stage, then "Done. Artifacts in .../Episode43/artifacts".
First run will download ~3GB of models — be patient.

- [ ] **Step 4: Verify all six artifacts exist**

```bash
cd /Users/ctindel/src/softwareinblue.com && python3 podcast.py status Episode43
```

Expected: every row shows "yes".

- [ ] **Step 5: Verify jargon spellings**

```bash
cd /Users/ctindel/src/softwareinblue.com && grep -E 'Elasticsearch|Weaviate|ClickHouse|kNN|RAG|HNSW' Episode43/artifacts/transcript.txt
```

Expected: at least some matches (assuming the episode actually mentions those terms). If specific terms appear misspelled in the raw transcript, the fuzzy correction log in `metadata.json` should show the replacement.

- [ ] **Step 6: Verify SRT cue limits**

```bash
cd /Users/ctindel/src/softwareinblue.com && python3 -c "
import re
text = open('Episode43/artifacts/transcript.srt').read()
ok = True
for block in text.strip().split('\n\n'):
    lines = block.splitlines()
    if len(lines) < 3: continue
    s, e = lines[1].split(' --> ')
    def to_s(ts):
        h, m, rest = ts.split(':'); s = float(rest.replace(',', '.'))
        return int(h)*3600 + int(m)*60 + s
    if to_s(e) - to_s(s) > 3.05:
        print('CUE TOO LONG:', lines[1]); ok = False
print('OK' if ok else 'FAIL')
"
```

Expected: `OK`.

- [ ] **Step 7: Verify stubs**

```bash
cd /Users/ctindel/src/softwareinblue.com && python3 podcast.py moments Episode43
```

Expected: "not implemented yet", exit code 0.

- [ ] **Step 8: Spot-check transcript.md**

Open `Episode43/artifacts/transcript.md` in an editor. Confirm paragraphs are speaker-labeled (`**SPEAKER_00:**` style until you run `label`).

- [ ] **Step 9: Run label and verify rename**

```bash
cd /Users/ctindel/src/softwareinblue.com && python3 podcast.py label Episode43 SPEAKER_00=Chad SPEAKER_01=Steve
grep '\*\*Chad' Episode43/artifacts/transcript.md | head -1
```

Expected: at least one line starting with `**Chad:**`.

- [ ] **Step 10: No commit needed for E2E test, but tag the milestone**

```bash
cd /Users/ctindel/src/softwareinblue.com && git log --oneline -1
```

Expected: HEAD points to the README docs commit. The test run produced artifacts under `Episode43/artifacts/` which are gitignored — nothing to commit.

---

## Self-review notes (for the implementer)

- **DRY:** `_cues_for_segment` lives in `srt.py` and is reused by `vtt.py` (deliberately imported as private — single source of cue logic).
- **YAGNI:** Backends file scaffold but only WhisperX implemented. Stub commands are no-ops. No moment/thumbnail/etc. logic yet.
- **TDD:** Every pure-logic module (episode, jargon, correct, formatters, metadata, speakers, CLI registration) has tests written before implementation. Audio + transcribe + diarize are integration boundaries; covered by Task 17 E2E.
- **Frequent commits:** Each task ends with a commit; bigger tasks split into per-step commits where helpful.
