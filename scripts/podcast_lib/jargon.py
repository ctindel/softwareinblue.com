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
    """Build a deterministic Whisper initial_prompt within the token budget."""
    seen: set[str] = set()
    chosen: list[str] = []
    header = "Glossary: "
    used = _approx_tokens(header)
    for cat in _PROMPT_PRIORITY:
        for term in CATEGORIES.get(cat, []):
            if term in seen:
                continue
            cost = _approx_tokens(term) + 1
            if used + cost > token_budget:
                return header + ", ".join(chosen) + "."
            seen.add(term)
            chosen.append(term)
            used += cost
    return header + ", ".join(chosen) + "."
