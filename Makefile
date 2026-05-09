# Astoka — main developer entrypoint.
# All long-running services run via Docker Compose; this Makefile orchestrates them.
#
# Quick start: `make install` — clones-to-running in one command.
#
# Two compose files:
#   - infra/docker-compose.dev.yml  → DEFAULT (used by `make install`, `make up`, etc.)
#                                     localhost ports, no Traefik, GPU optional via profile.
#   - infra/docker-compose.yml      → production-ish (Traefik + TLS, full GPU stack)
#                                     Use `make up-prod` to start.

.PHONY: help install install-gpu install-no-worker \
        bootstrap up up-prod up-gpu down down-volumes logs ps restart \
        api-shell worker-shell web-shell db-shell \
        migrate migrate-create seed \
        test test-api test-web test-highlight lint type-check \
        codegen asr-spike clean

SHELL := /bin/bash
COMPOSE_DEV := docker compose -f infra/docker-compose.dev.yml --env-file .env
COMPOSE_DEV_GPU := docker compose -f infra/docker-compose.dev.yml -f infra/docker-compose.gpu.yml --env-file .env
COMPOSE_PROD := docker compose -f infra/docker-compose.yml --env-file .env
COMPOSE := $(COMPOSE_DEV)

# Default profiles for dev: worker enabled. GPU only with `make up-gpu`.
PROFILES := --profile worker

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============ One-shot install ============

install: ## Install + start (CPU mode, all features except LLM reranking)
	bash scripts/install.sh

install-gpu: ## Install + start with GPU (Ollama for LLM-quality highlights)
	bash scripts/install.sh --gpu

install-no-worker: ## Install + start API only (skip workers — Phase A test mode)
	bash scripts/install.sh --no-worker

# ============ Stack control ============

bootstrap: ## Install local dev deps (Node + Python) — for non-Docker iteration
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example"; fi
	pnpm install
	cd services/api && uv sync
	cd services/worker && uv sync
	cd services/highlight && uv sync
	@echo "Bootstrap complete. Run 'make up' to start the stack."

up: ## Start dev stack (no GPU; worker enabled)
	$(COMPOSE_DEV) $(PROFILES) up -d

up-gpu: ## Start dev stack with GPU override (worker + Ollama on GPU)
	$(COMPOSE_DEV_GPU) --profile gpu --profile worker up -d

up-prod: ## Start production-style stack (Traefik + TLS — needs cert in infra/traefik/certs/)
	$(COMPOSE_PROD) up -d

down: ## Stop stack (preserves volumes)
	$(COMPOSE_DEV_GPU) --profile gpu --profile worker down 2>/dev/null || $(COMPOSE_DEV) --profile gpu --profile worker down
	$(COMPOSE_PROD) down 2>/dev/null || true

down-volumes: ## Stop stack AND drop volumes (DESTRUCTIVE)
	$(COMPOSE_DEV_GPU) --profile gpu --profile worker down -v 2>/dev/null || $(COMPOSE_DEV) --profile gpu --profile worker down -v
	$(COMPOSE_PROD) down -v 2>/dev/null || true

logs: ## Tail logs from all services
	$(COMPOSE_DEV) logs -f --tail=100

ps: ## Show service status
	$(COMPOSE_DEV) ps

restart: ## Restart all services
	$(COMPOSE_DEV) restart

# ============ Shells ============

api-shell: ## Open shell in api container
	$(COMPOSE_DEV) exec api bash

worker-shell: ## Open shell in worker container
	$(COMPOSE_DEV) --profile worker exec worker bash

web-shell: ## Open shell in web container
	$(COMPOSE_DEV) exec web sh

db-shell: ## Open psql in postgres container
	$(COMPOSE_DEV) exec postgres psql -U astoka -d astoka

# ============ DB / seed ============

migrate: ## Run pending Alembic migrations
	$(COMPOSE_DEV) run --rm api alembic upgrade head

migrate-create: ## Create new Alembic revision: make migrate-create MSG="add foo"
	$(COMPOSE_DEV) run --rm api alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed initial data (1 admin user — admin/admin)
	$(COMPOSE_DEV) run --rm api python -m astoka_api.cli.seed

# ============ Test / lint ============

test: test-api test-worker test-highlight test-web ## Run all tests

test-api: ## Run backend api tests
	cd services/api && pytest tests -v

test-worker: ## Run worker tests
	cd services/worker && pytest tests -v

test-highlight: ## Run highlight (vendor) tests
	cd services/highlight && pytest tests -v

test-web: ## Run web tests
	pnpm --filter @astoka/web test

lint: ## Lint all code
	pnpm -r lint
	ruff check services/

type-check: ## Type-check all code
	pnpm -r type-check
	cd services/api && mypy astoka_api
	cd services/worker && mypy --config-file mypy.ini astoka_worker

codegen: ## Regenerate TS types from Pydantic OpenAPI schema
	bash scripts/codegen.sh 2>/dev/null || echo "(codegen.sh placeholder — see lib/api-types.ts for hand-written types)"

asr-spike: ## Run ASR baseline on samples in scripts/data/akademia_samples/
	$(COMPOSE_DEV) --profile worker run --rm worker python /app/scripts/asr_spike.py

clean: ## Remove caches and build artifacts
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".next" -prune -exec rm -rf {} +
