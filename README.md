# AI Job Matching & Resume Tailoring Platform

> Production-grade, event-driven platform for semantic job matching and LLM-powered resume tailoring.  
> Scales from MVP → 10k → 100k → 1M+ users.

[![CI](https://github.com/your-org/ai-job-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/ai-job-platform/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/your-org/ai-job-platform/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/ai-job-platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Repository Structure

```
ai-job-platform/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                        # Lint, test, security scan, build & push
│   │   └── cd.yml                        # Canary deploy to staging → prod
│   └── ISSUE_TEMPLATE/
│
├── services/                             # Bounded-context microservices
│   ├── user-service/                     # Auth, profiles, resume uploads
│   │   ├── app/
│   │   │   ├── main.py                   # FastAPI app factory + lifespan
│   │   │   ├── api/v1/routes/
│   │   │   │   ├── auth.py               # /register, /login, /logout
│   │   │   │   ├── users.py              # Profile CRUD
│   │   │   │   └── resumes.py            # Upload, list, delete resumes
│   │   │   ├── core/
│   │   │   │   ├── security.py           # JWT, bcrypt, token creation
│   │   │   │   ├── deps.py               # FastAPI dependency injection
│   │   │   │   └── telemetry.py          # OpenTelemetry setup
│   │   │   ├── db/
│   │   │   │   └── session.py            # SQLAlchemy async engine + session
│   │   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   └── services/
│   │   │       ├── user_service.py       # User CRUD business logic
│   │   │       └── resume_service.py     # Resume upload, parse enqueue, S3
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── alembic/                      # Database migrations
│   │
│   ├── job-service/                      # Job ingestion, search, scraper scheduling
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api/v1/routes/
│   │   │   │   ├── jobs.py               # GET /jobs, /jobs/{id}, /jobs/search
│   │   │   │   └── scraper.py            # Admin: trigger scrape, view status
│   │   │   ├── scraper/
│   │   │   │   ├── crawlers/
│   │   │   │   │   ├── base_crawler.py   # Abstract crawler: httpx + Playwright
│   │   │   │   │   ├── linkedin_crawler.py
│   │   │   │   │   ├── indeed_crawler.py
│   │   │   │   │   └── greenhouse_crawler.py
│   │   │   │   ├── parsers/
│   │   │   │   │   └── job_normalizer.py # Rule-based field extraction + LLM fallback
│   │   │   │   └── scheduler/
│   │   │   │       └── scheduler.py      # APScheduler: cron-based scrape enqueue
│   │   │   └── services/
│   │   │       ├── job_service.py        # Job CRUD + deduplication
│   │   │       └── dedup_service.py      # Bloom filter + hash deduplication
│   │   ├── tests/
│   │   └── requirements.txt
│   │
│   ├── ai-orchestration/                 # LangGraph pipeline, LLM routing, streaming
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api/v1/routes/
│   │   │   │   ├── match.py              # POST /match/request, GET /status, WS /ws
│   │   │   │   └── tailor.py             # POST /tailor, streaming SSE endpoint
│   │   │   ├── agents/
│   │   │   │   ├── graphs/
│   │   │   │   │   └── match_graph.py    # LangGraph StateGraph: full match pipeline
│   │   │   │   └── nodes/
│   │   │   │       ├── resume_analyzer.py # Extract structure, embed, cache
│   │   │   │       ├── job_retriever.py   # Qdrant ANN + payload filter
│   │   │   │       ├── reranker.py        # Cross-encoder + RRF fusion
│   │   │   │       ├── match_scorer.py    # Concurrent LLM scoring (Groq)
│   │   │   │       └── finalizer.py       # Persist results, emit events
│   │   │   └── llm/
│   │   │       ├── router/
│   │   │       │   └── llm_router.py     # Circuit-broken multi-provider router
│   │   │       ├── providers/            # Per-provider thin wrappers
│   │   │       └── cache/
│   │   │           └── semantic_cache.py # MD5 exact + Qdrant semantic cache
│   │   ├── tests/
│   │   └── requirements.txt
│   │
│   └── worker-service/                   # Background consumers + processors
│       ├── app/
│       │   ├── consumers/
│       │   │   ├── job_pipeline_consumer.py  # Kafka: scraped→normalize→embed
│       │   │   └── resume_pipeline_consumer.py # Kafka: uploaded→parse→analyze
│       │   ├── processors/
│       │   │   ├── normalizer.py         # Batch job HTML → NormalizedJob
│       │   │   └── embedder.py           # SentenceTransformer batch → Qdrant
│       │   └── tasks/
│       │       ├── notification_tasks.py # Email / push notifications
│       │       └── cache_warming_tasks.py # Pre-warm top-job caches
│       ├── tests/
│       └── requirements.txt
│
├── shared/                               # Cross-service shared code (no circular deps)
│   ├── models/
│   │   ├── job.py                        # RawJob, NormalizedJob, Job Pydantic models
│   │   ├── resume.py                     # Resume, ResumeStructured models
│   │   └── user.py                       # User, UserTier models
│   ├── utils/
│   │   ├── hashing.py                    # SHA256, MD5, text normalisation
│   │   └── kafka.py                      # Shared producer/consumer factory
│   └── config/
│       └── settings.py                   # Pydantic Settings (single source of truth)
│
├── ml/                                   # ML model code (standalone, importable)
│   ├── embeddings/
│   │   └── embedding_service.py          # SentenceTransformer wrapper + batching
│   ├── reranker/
│   │   └── cross_encoder_reranker.py     # Cross-encoder + RRF fusion
│   └── vllm/
│       └── vllm_client.py                # OpenAI-compatible vLLM client
│
├── infra/
│   ├── docker/
│   │   └── Dockerfile.service            # Multi-stage distroless service image
│   ├── k8s/
│   │   ├── namespaces/                   # K8s namespace definitions
│   │   ├── base/                         # Base Deployments, Services, HPAs
│   │   └── overlays/                     # Kustomize overlays per environment
│   │       ├── dev/
│   │       ├── staging/
│   │       └── prod/
│   ├── helm/
│   │   └── jobmatch/                     # Umbrella Helm chart
│   │       ├── Chart.yaml
│   │       ├── values-staging.yaml
│   │       └── values-prod.yaml
│   └── terraform/
│       ├── modules/
│       │   ├── gke/main.tf               # GKE cluster + node pools (incl. GPU)
│       │   ├── rds/main.tf               # Cloud SQL Postgres Multi-AZ
│       │   ├── redis/main.tf             # Memorystore Redis Cluster
│       │   ├── kafka/main.tf             # MSK / Confluent Cloud
│       │   └── qdrant/main.tf            # Qdrant Cloud or self-hosted VM
│       └── environments/
│           ├── dev/main.tf
│           └── prod/main.tf
│
├── observability/
│   ├── otel/
│   │   └── otel-collector-config.yaml    # OTLP → Jaeger + Prometheus + Loki
│   ├── alerts/
│   │   └── llm-cost-alerts.yaml          # Prometheus alert rules
│   └── dashboards/                       # Grafana dashboard JSON exports
│
├── scripts/
│   ├── setup_local.sh                    # One-command local bootstrap
│   ├── init_qdrant.py                    # Create Qdrant collections
│   └── init_db.sql                       # Postgres DDL (also run by Alembic)
│
├── docs/                                 # ADRs, runbooks, architecture diagrams
├── docker-compose.yml                    # Full local stack
├── .env.example                          # Environment variable template
└── README.md
```

---

## Architecture at a Glance

```
Client → API Gateway (Kong/Traefik: auth, rate-limit, circuit-break)
       → User Service (FastAPI)          → Postgres + S3
       → Job Service (FastAPI)           → Postgres + Qdrant + Kafka
       → AI Orchestration (FastAPI+WS)   → LangGraph → LLM Router
                                                     → Qdrant (ANN)
                                                     → Redis (state/cache)
       → Worker Service (Celery+Kafka)   → Embedding → Qdrant
                                         → Scraper   → Kafka
```

**LangGraph match pipeline nodes:**
```
resume_analyzer → job_retriever → reranker → match_scorer (parallel×5) → finalizer
```

**LLM routing order by task:**
| Task | Provider chain |
|------|---------------|
| Bulk job scoring | Groq → OpenRouter → OpenAI |
| Resume tailoring | Anthropic → OpenAI |
| ATS analysis | Groq → OpenAI |
| Cover letter | Anthropic → OpenAI |

---

## Quick Start

```bash
# Clone
git clone https://github.com/your-org/ai-job-platform.git && cd ai-job-platform

# Bootstrap (creates venvs, starts infra, runs migrations)
./scripts/setup_local.sh

# Set your API keys
nano .env

# Run
docker compose up --build
```

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for full local, Docker, K8s, and CI/CD instructions.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.115, Python 3.12 |
| Agent Orchestration | LangGraph 0.2 |
| Queue / Streams | Apache Kafka (aiokafka), RabbitMQ (aio-pika) |
| Primary DB | PostgreSQL 16 (SQLAlchemy async + Alembic) |
| Vector DB | Qdrant (HNSW + BM25 hybrid search) |
| Cache | Redis 7 (session, rate-limit, state, prompt cache) |
| Embeddings | BAAI/bge-large-en-v1.5 (SentenceTransformers) |
| Reranking | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| LLM Providers | OpenAI, Anthropic, Groq, OpenRouter, vLLM |
| Container Runtime | Docker → Kubernetes (GKE) |
| IaC | Terraform + Helm + Kustomize |
| GitOps | ArgoCD + Argo Rollouts (canary) |
| Observability | OpenTelemetry + Prometheus + Grafana + Langfuse |
| Security | mTLS (Istio), External Secrets Operator, OPA |

---

## Development

```bash
# Run all tests
for svc in user-service job-service ai-orchestration worker-service; do
  cd services/$svc && source .venv/bin/activate
  pytest tests/ -v --asyncio-mode=auto
  cd ../..
done

# Lint
ruff check services/ shared/ ml/

# Type check
mypy services/ shared/ --ignore-missing-imports

# Format
ruff format services/ shared/ ml/
```

---

## Cost Estimates (Monthly)

| Phase | MAU | Est. Cost |
|-------|-----|-----------|
| MVP | 1k | ~$455 |
| Growth | 10k | ~$5,700 |
| Scale | 100k | ~$29,100 |
| Enterprise | 1M+ | ~$174,000 |

Full breakdown in [architecture blueprint](docs/architecture-blueprint.md).

---

## Contributing

1. Branch from `develop`: `git checkout -b feat/your-feature`
2. Write tests first — no PR without coverage
3. `ruff check` and `mypy` must pass before pushing
4. PR title format: `feat:`, `fix:`, `chore:`, `docs:`
5. One logical change per PR

---

## License

MIT — see [LICENSE](LICENSE).
