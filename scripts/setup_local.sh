#!/usr/bin/env bash
# Local development bootstrap — run once after cloning.
set -euo pipefail

BOLD="\033[1m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; RESET="\033[0m"
info()    { echo -e "${GREEN}[setup]${RESET} $*"; }
warn()    { echo -e "${YELLOW}[warn]${RESET}  $*"; }

info "Checking prerequisites..."
command -v docker  >/dev/null || { echo "docker required"; exit 1; }
command -v python3 >/dev/null || { echo "python 3.12+ required"; exit 1; }
command -v kubectl >/dev/null || warn "kubectl not found — skip K8s steps"

# ── .env ──────────────────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  cp .env.example .env
  info "Created .env from .env.example — fill in API keys before running"
fi

# ── Python virtual environments (one per service) ────────────────────────────
info "Creating virtual environments..."
for svc in user-service job-service ai-orchestration worker-service; do
  dir="services/$svc"
  if [[ ! -d "$dir/.venv" ]]; then
    python3 -m venv "$dir/.venv"
    "$dir/.venv/bin/pip" install --quiet --upgrade pip
    "$dir/.venv/bin/pip" install --quiet -r "$dir/requirements.txt"
    info "  $svc — venv ready"
  else
    info "  $svc — venv exists, skipping"
  fi
done

# ── Docker infrastructure ─────────────────────────────────────────────────────
info "Starting infrastructure containers..."
docker compose up -d postgres redis zookeeper kafka qdrant

info "Waiting for Postgres to be ready..."
until docker compose exec -T postgres pg_isready -U postgres; do sleep 2; done

# ── Database migrations ───────────────────────────────────────────────────────
info "Running Alembic migrations..."
(cd services/user-service && .venv/bin/alembic upgrade head)

# ── Qdrant collections ────────────────────────────────────────────────────────
info "Initialising Qdrant collections..."
python3 scripts/init_qdrant.py

info ""
info "┌───────────────────────────────────────────────────────────────────┐"
info "│  Setup complete! Run: docker compose up --build                  │"
info "│  Services: user:8001  job:8002  ai-orch:8003  workers:bg         │"
info "└───────────────────────────────────────────────────────────────────┘"
