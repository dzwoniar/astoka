#!/usr/bin/env bash
# Astoka one-shot install — clone → run, ready to login at http://localhost:3000.
#
# What this does:
#   1. Verify Docker + Docker Compose are present
#   2. Warn if NVIDIA Container Toolkit is missing (CPU mode still works)
#   3. Generate .env from .env.example with random API_SECRET_KEY
#   4. Build Docker images
#   5. Bring up Postgres + Redis + MinIO and wait until healthy
#   6. Apply Alembic migrations
#   7. Seed admin/admin user
#   8. Bring up API + worker + web
#   9. Print success message with URL + credentials
#
# Use --gpu to also start Ollama (highlight LLM) — requires NVIDIA Container Toolkit.

set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"
# Base compose; --gpu adds the GPU override (-f infra/docker-compose.gpu.yml).
COMPOSE="docker compose -f infra/docker-compose.dev.yml --env-file .env"

GPU=0
WORKER=1
PROFILES=()

for arg in "$@"; do
    case "$arg" in
        --gpu)
            GPU=1
            COMPOSE="docker compose -f infra/docker-compose.dev.yml -f infra/docker-compose.gpu.yml --env-file .env"
            PROFILES+=(--profile gpu)
            ;;
        --no-worker) WORKER=0 ;;
        --help|-h)
            cat <<EOF
Usage: scripts/install.sh [--gpu] [--no-worker]

Options:
  --gpu        Also start Ollama (LLM service for highlight reranking).
               Requires NVIDIA Container Toolkit. Without it, highlight
               detection falls back to heuristic-only mode (lower quality).
  --no-worker  Skip building/starting the worker (Phase B+ only).
               Use this if you only want to test auth + projects (Phase A).
  --help       Show this message.

Demo: after install, login admin/admin at http://localhost:3000.
EOF
            exit 0
            ;;
        *) echo "Unknown arg: $arg (try --help)" >&2; exit 1 ;;
    esac
done

if [[ $WORKER -eq 1 ]]; then
    PROFILES+=(--profile worker)
fi

# Re-build COMPOSE with profiles for `up` calls. Other commands use bare COMPOSE.
COMPOSE_UP="$COMPOSE ${PROFILES[*]:-}"

cyan() { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*"; }

cyan "==> Astoka installer"
echo

# ============ Step 1: prerequisites ============
cyan "==> Checking prerequisites..."

if ! command -v docker >/dev/null 2>&1; then
    red "ERROR: Docker not found. Install from https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    red "ERROR: Docker Compose v2 not found. Install/upgrade Docker Desktop."
    exit 1
fi

DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
green "  ✓ Docker $DOCKER_VERSION"
green "  ✓ Docker Compose $(docker compose version --short)"

# Check NVIDIA Container Toolkit (warn-only)
if [[ $GPU -eq 1 ]]; then
    if docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1; then
        green "  ✓ NVIDIA Container Toolkit (GPU mode enabled)"
    else
        red "ERROR: --gpu requested but NVIDIA Container Toolkit isn't working."
        red "  Install: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/"
        red "  Or run without --gpu (heuristic-only highlights, slower ASR)."
        exit 1
    fi
else
    yellow "  ! GPU disabled (no --gpu flag). Highlights will run heuristic-only."
    yellow "    For LLM reranking, install NVIDIA Container Toolkit and re-run with --gpu."
fi

# ============ Step 2: .env ============
cyan "==> Setting up .env..."

if [[ ! -f .env ]]; then
    cp .env.example .env
    # Generate random secret key
    if command -v openssl >/dev/null 2>&1; then
        SECRET=$(openssl rand -hex 32)
        # macOS sed wants -i ''; GNU sed wants -i. Use a portable awk alternative.
        awk -v secret="$SECRET" '/^API_SECRET_KEY=/{print "API_SECRET_KEY=" secret; next} {print}' .env > .env.tmp
        mv .env.tmp .env
        green "  ✓ Generated .env with random API_SECRET_KEY"
    else
        yellow "  ! openssl not found — leaving placeholder API_SECRET_KEY in .env (NOT secure)"
    fi
else
    green "  ✓ .env exists (keeping)"
fi

# ============ Step 3: build ============
cyan "==> Building Docker images (~3-5 min on first run)..."
$COMPOSE_UP build
green "  ✓ Images built"

# ============ Step 4: start core services ============
cyan "==> Starting Postgres + Redis + MinIO..."
$COMPOSE up -d postgres redis minio
echo "  Waiting for healthchecks..."
TIMEOUT=60
WAITED=0
while [[ $WAITED -lt $TIMEOUT ]]; do
    UNHEALTHY=$($COMPOSE ps --format json 2>/dev/null | grep -c '"Health":"unhealthy\|starting"' || true)
    HEALTHY_COUNT=$($COMPOSE ps --format json 2>/dev/null | grep -c '"Health":"healthy"' || true)
    if [[ $HEALTHY_COUNT -ge 3 ]]; then
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done
if [[ $WAITED -ge $TIMEOUT ]]; then
    yellow "  ! Some services slow to start. Continuing anyway — check 'make logs' if next steps fail."
else
    green "  ✓ Postgres + Redis + MinIO healthy"
fi

# minio-init runs as one-shot
$COMPOSE up minio-init
green "  ✓ MinIO bucket created"

# ============ Step 5: migrations ============
cyan "==> Running database migrations..."
$COMPOSE run --rm api alembic upgrade head
green "  ✓ Migrations applied"

# ============ Step 6: seed admin ============
cyan "==> Seeding admin user..."
$COMPOSE run --rm api python -m astoka_api.cli.seed
green "  ✓ Admin user ready (admin/admin)"

# ============ Step 7: bring up rest ============
cyan "==> Starting API + web..."
$COMPOSE_UP up -d
green "  ✓ Stack running"

# ============ Final ============
echo
green "════════════════════════════════════════════════════════════"
green "  Astoka is ready"
green "════════════════════════════════════════════════════════════"
echo
echo "  Web UI:        http://localhost:3000"
echo "  API:           http://localhost:8000/docs"
echo "  MinIO Console: http://localhost:9001  (login: astoka / astoka_dev_only)"
echo
echo "  Login:    admin / admin"
echo
if [[ $GPU -eq 0 ]]; then
    echo "  Note: GPU mode off. Highlight detection will use heuristic fallback"
    echo "        once you upload material. Re-run with --gpu for LLM reranking."
    echo
fi
echo "  Useful commands:"
echo "    make logs        Tail all service logs"
echo "    make ps          Show running containers"
echo "    make down        Stop the stack (data preserved)"
echo
