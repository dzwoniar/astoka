# Astoka — main developer entrypoint.
# All long-running services run via Docker Compose; this Makefile orchestrates them.

.PHONY: help bootstrap up down logs ps restart \
        api-shell worker-shell web-shell db-shell \
        migrate migrate-create seed \
        test test-api test-web lint type-check \
        codegen asr-spike clean

SHELL := /bin/bash
COMPOSE := docker compose -f infra/docker-compose.yml --env-file .env

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Install all deps (Node + Python) — run once
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example — review before continuing"; fi
	pnpm install
	cd services/api && uv sync
	cd services/worker && uv sync
	cd services/highlight && uv sync
	@echo "Bootstrap complete. Run 'make up' to start the stack."

up: ## Start full Docker Compose stack (Postgres, Redis, MinIO, Ollama, API, worker, web)
	$(COMPOSE) up -d
	@echo "Stack starting. Run 'make logs' to follow output, 'make ps' for status."

down: ## Stop stack (preserves volumes)
	$(COMPOSE) down

down-volumes: ## Stop stack AND drop volumes (DESTRUCTIVE)
	$(COMPOSE) down -v

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

ps: ## Show service status
	$(COMPOSE) ps

restart: ## Restart all services
	$(COMPOSE) restart

api-shell: ## Open shell in api container
	$(COMPOSE) exec api bash

worker-shell: ## Open shell in worker container
	$(COMPOSE) exec worker bash

web-shell: ## Open shell in web container
	$(COMPOSE) exec web sh

db-shell: ## Open psql in postgres container
	$(COMPOSE) exec postgres psql -U astoka -d astoka

migrate: ## Run pending Alembic migrations
	$(COMPOSE) exec api alembic upgrade head

migrate-create: ## Create new Alembic revision: make migrate-create MSG="add foo"
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed initial data (1 admin user)
	$(COMPOSE) exec api python -m astoka_api.cli.seed

test: test-api test-web ## Run all tests

test-api: ## Run backend tests
	$(COMPOSE) exec api pytest

test-web: ## Run web tests
	pnpm --filter @astoka/web test

lint: ## Lint all code
	pnpm -r lint
	cd services/api && uv run ruff check .
	cd services/worker && uv run ruff check .
	cd services/highlight && uv run ruff check . --exclude astoka_highlight/vendor

type-check: ## Type-check all code
	pnpm -r type-check
	cd services/api && uv run mypy astoka_api
	cd services/worker && uv run mypy astoka_worker
	cd services/highlight && uv run mypy astoka_highlight

codegen: ## Regenerate TS types from Pydantic OpenAPI schema
	bash scripts/codegen.sh

asr-spike: ## Run ASR baseline on samples in scripts/data/akademia_samples/
	$(COMPOSE) exec worker python /app/scripts/asr_spike.py

clean: ## Remove caches and build artifacts
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".next" -prune -exec rm -rf {} +
	find . -type d -name "node_modules" -prune -exec rm -rf {} +
