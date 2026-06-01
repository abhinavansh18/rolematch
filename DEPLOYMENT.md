# Deployment Guide

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Local Development](#2-local-development)
3. [Environment Configuration](#3-environment-configuration)
4. [Database Setup](#4-database-setup)
5. [Running Services Individually](#5-running-services-individually)
6. [Docker Compose (Full Stack)](#6-docker-compose-full-stack)
7. [Kubernetes (Staging / Production)](#7-kubernetes-staging--production)
8. [CI/CD Pipeline](#8-cicd-pipeline)
9. [Monitoring Stack](#9-monitoring-stack)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | ≥ 3.12 | `pyenv install 3.12` |
| Docker + Compose | ≥ 25.0 | https://docs.docker.com/get-docker |
| kubectl | ≥ 1.29 | `brew install kubectl` |
| helm | ≥ 3.14 | `brew install helm` |
| terraform | ≥ 1.7 | `brew install terraform` |
| gcloud CLI | latest | https://cloud.google.com/sdk |
| argocd CLI | latest | `brew install argocd` |

---

## 2. Local Development

```bash
# 1. Clone and enter the repo
git clone https://github.com/your-org/ai-job-platform.git
cd ai-job-platform

# 2. Run the setup script (creates venvs, starts infra, runs migrations)
./scripts/setup_local.sh

# 3. Fill in real API keys
nano .env   # Add OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY

# 4. Start everything
docker compose up --build

# Services available at:
#   User Service:         http://localhost:8001/docs
#   Job Service:          http://localhost:8002/docs
#   AI Orchestration:     http://localhost:8003/docs
#   Qdrant Dashboard:     http://localhost:6333/dashboard
```

---

## 3. Environment Configuration

Copy and populate `.env`:

```bash
cp .env.example .env
```

**Minimum required keys for local dev:**
```
SECRET_KEY=any-32+-char-string
JWT_SECRET=any-32+-char-string
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/jobmatch
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
QDRANT_HOST=localhost
OPENAI_API_KEY=sk-...          # At minimum, one LLM provider
```

**Tier-gated features:**
- `GROQ_API_KEY` enables fast bulk scoring (≈90% cost reduction vs OpenAI for scoring)
- `ANTHROPIC_API_KEY` enables high-quality resume tailoring
- Without both, the LLM router falls back to OpenAI for all tasks

---

## 4. Database Setup

**Run migrations (Alembic):**
```bash
cd services/user-service
.venv/bin/alembic upgrade head

cd services/job-service
.venv/bin/alembic upgrade head
```

**Generate a new migration after model changes:**
```bash
cd services/user-service
.venv/bin/alembic revision --autogenerate -m "add column X to users"
```

**Reset local DB (destructive):**
```bash
docker compose down -v          # removes volumes
docker compose up -d postgres
sleep 5
./scripts/setup_local.sh        # re-runs migrations
```

**Initialise Qdrant collections:**
```bash
python3 scripts/init_qdrant.py
# Creates: jobs, resumes, prompt_cache_* collections
```

---

## 5. Running Services Individually

Each service has its own venv. Run from the service directory:

```bash
# User Service
cd services/user-service
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001

# Job Service
cd services/job-service
source .venv/bin/activate
uvicorn app.main:app --reload --port 8002

# AI Orchestration Service
cd services/ai-orchestration
source .venv/bin/activate
uvicorn app.main:app --reload --port 8003

# Worker Service (Celery)
cd services/worker-service
source .venv/bin/activate
celery -A app.celery_app worker --loglevel=debug --concurrency=2

# Worker Service (Kafka consumer — job pipeline)
cd services/worker-service
source .venv/bin/activate
python -m app.consumers.job_pipeline_consumer
```

**Run tests for a single service:**
```bash
cd services/ai-orchestration
source .venv/bin/activate
pytest tests/ -v --asyncio-mode=auto
```

---

## 6. Docker Compose (Full Stack)

```bash
# Start full stack (first run builds images)
docker compose up --build

# Start only infrastructure (DB, Redis, Kafka, Qdrant)
docker compose up -d postgres redis zookeeper kafka qdrant

# Rebuild a single service after code changes
docker compose up --build ai-orchestration

# View logs
docker compose logs -f ai-orchestration worker-service

# Stop everything (keep volumes)
docker compose down

# Stop and remove all volumes (full reset)
docker compose down -v
```

**Verify services are healthy:**
```bash
curl http://localhost:8001/healthz   # {"status":"ok","service":"user-service"}
curl http://localhost:8002/healthz   # {"status":"ok","service":"job-service"}
curl http://localhost:8003/healthz   # {"status":"ok","service":"ai-orchestration"}
```

---

## 7. Kubernetes (Staging / Production)

### 7.1 GCP / GKE Setup (First Time)

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Provision infrastructure with Terraform
cd infra/terraform/environments/prod
terraform init
terraform plan -var="project_id=YOUR_PROJECT_ID"
terraform apply

# Get cluster credentials
gcloud container clusters get-credentials jobmatch-prod --region us-central1

# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace
```

### 7.2 Deploy via Helm

```bash
# Staging
helm upgrade --install jobmatch infra/helm/jobmatch \
  --namespace api --create-namespace \
  -f infra/helm/jobmatch/values-staging.yaml \
  --set global.image.tag=$(git rev-parse --short HEAD) \
  --atomic --timeout 5m

# Production (manual promote; CI/CD uses canary flow)
helm upgrade --install jobmatch infra/helm/jobmatch \
  --namespace api \
  -f infra/helm/jobmatch/values-prod.yaml \
  --set global.image.tag=VERIFIED_SHA \
  --atomic --timeout 5m
```

### 7.3 Apply K8s Manifests Directly (base)

```bash
# Apply namespaces first
kubectl apply -f infra/k8s/namespaces/

# Apply base workloads
kubectl apply -k infra/k8s/overlays/staging/   # Kustomize overlay
```

### 7.4 Secrets Management

```bash
# Store secrets in AWS Secrets Manager (or GCP Secret Manager)
aws secretsmanager create-secret \
  --name prod/jobmatch/llm-keys \
  --secret-string '{"openai_key":"sk-...","anthropic_key":"sk-ant-..."}'

# External Secrets Operator syncs to K8s Secrets automatically
kubectl get secrets -n api   # llm-api-keys should appear
```

### 7.5 Rolling Back

```bash
# Via Helm
helm rollback jobmatch -n api

# Via ArgoCD
argocd app rollback jobmatch --revision PREVIOUS_SHA

# Emergency: scale to zero (kill switch)
kubectl scale deployment ai-orchestration --replicas=0 -n api
```

---

## 8. CI/CD Pipeline

**Trigger flow:**
```
PR opened → CI (lint + test + scan) → merge to main → build images
→ push to GCR → update Helm values → ArgoCD detects diff
→ auto-deploy to staging → smoke tests → manual gate → canary prod deploy
```

**Required GitHub Secrets:**
```
GCP_PROJECT_ID           # Your GCP project
GCP_WIF_PROVIDER         # Workload Identity Federation provider
GCP_SERVICE_ACCOUNT      # CI service account email
CODECOV_TOKEN            # Coverage reporting
```

**Branch protection rules (main):**
- Require CI to pass
- Require 1 review
- No direct pushes
- Linear history only

---

## 9. Monitoring Stack

### Deploy Prometheus + Grafana

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install kube-prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  -f observability/dashboards/prometheus-values.yaml
```

### Deploy OpenTelemetry Collector

```bash
kubectl apply -f observability/otel/otel-collector-config.yaml
```

### Import Grafana Dashboards

```bash
# Port-forward Grafana
kubectl port-forward svc/kube-prometheus-grafana 3000:80 -n monitoring

# Dashboards are in observability/dashboards/*.json
# Import via Grafana UI: + → Import → Upload JSON
```

### Key Dashboards to Import
- `observability/dashboards/llm-cost-dashboard.json` — LLM spend by provider/task
- `observability/dashboards/match-pipeline-sla.json` — P50/P95/P99 latencies
- `observability/dashboards/kafka-consumer-lag.json` — Pipeline health

### Langfuse (LLM Tracing)

```bash
# Cloud: set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY in .env
# Self-hosted:
docker compose -f observability/langfuse-compose.yml up -d
# Access at http://localhost:3000
```

---

## 10. Troubleshooting

### Service won't start
```bash
# Check logs
docker compose logs user-service --tail=50
# Common cause: missing .env keys — check REQUIRED vars above
```

### Qdrant collection missing
```bash
python3 scripts/init_qdrant.py
```

### Kafka consumer lag growing
```bash
# Check lag
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group jobmatch-workers

# Scale workers
docker compose up --scale worker-service=4
```

### LLM router exhausting all providers
```bash
# Check circuit breaker state in Redis
redis-cli -n 2 KEYS "cb:*"
# Reset a breaker (set failures to 0)
redis-cli -n 2 DEL cb:groq
```

### Database migrations failing
```bash
# Check current revision
alembic current
# Stamp current state without running migration
alembic stamp head
# Then re-run
alembic upgrade head
```

### Out-of-memory on embedding worker
```bash
# Reduce batch size in embedder.py (default 32 → 8)
EMBEDDING_BATCH_SIZE=8 docker compose up worker-service
```
