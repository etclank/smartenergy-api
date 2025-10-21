# -----------------------------
# SmartEnergy API — Makefile
# -----------------------------

# Image / container
IMAGE       ?= smartenergy-api
TAG         ?= local
APP_NAME    ?= smartenergy-api

# App config
PORT        ?= 8000
ENV         ?= prod
DATABASE_URL?= sqlite+aiosqlite:///./app.db   # absolute: sqlite+aiosqlite:////tmp/app.db
JWT_SECRET  ?= dev

# Paths
DOCKERFILE  ?= docker/Dockerfile

# Utilities
CURL        ?= curl -sSf
DOCKER      ?= docker
DC          ?= docker compose

# ==============================
#         HELP / META
# ==============================
.PHONY: help
help:
	@echo ""
	@echo "SmartEnergy API — Local Workflow"
	@echo "--------------------------------"
	@echo "Single-container (SQLite):"
	@echo "  make up-sqlite     → build & run FastAPI + SQLite"
	@echo "  make logs-sqlite   → tail logs"
	@echo "  make stop-sqlite   → stop single container"
	@echo "  make smoke-sqlite  → run basic health checks"
	@echo ""
	@echo "Full stack (Postgres + Redis + API):"
	@echo "  make up-pg         → docker compose up --build"
	@echo "  make down-pg       → stop & remove compose stack"
	@echo "  make logs-pg       → tail logs for all services"
	@echo "  make smoke         → run API + Redis health checks"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean         → remove all containers, volumes, networks"
	@echo "  make seed-demo     → run demo seeder inside API container"
	@echo "--------------------------------"
	@echo "Variables (override like VAR=value make up-sqlite):"
	@echo "  PORT, ENV, DATABASE_URL, JWT_SECRET, IMAGE, TAG, APP_NAME"
	@echo ""

# ==============================
#     SINGLE CONTAINER (SQLite)
# ==============================
.PHONY: build
build:
	$(DOCKER) build -t $(IMAGE):$(TAG) -f $(DOCKERFILE) .

.PHONY: up-sqlite
up-sqlite: build
	@echo "→ Starting FastAPI + SQLite container"
	$(DOCKER) run -d \
		--name $(APP_NAME)-sqlite \
		-p $(PORT):8000 \
		-e ENV=$(ENV) \
		-e DATABASE_URL="$(DATABASE_URL)" \
		-e JWT_SECRET="$(JWT_SECRET)" \
		$(IMAGE):$(TAG)
	@echo "✓ Running at http://localhost:$(PORT)"

.PHONY: stop-sqlite
stop-sqlite:
	-$(DOCKER) rm -f $(APP_NAME)-sqlite >/dev/null 2>&1 || true

.PHONY: logs-sqlite
logs-sqlite:
	$(DOCKER) logs -f $(APP_NAME)-sqlite

.PHONY: smoke-sqlite
smoke-sqlite:
	@echo "→ Checking API health (SQLite mode)..."
	@$(CURL) http://localhost:$(PORT)/api/health/z >/dev/null && echo "  /api/health/z OK" || echo "  /api/health/z FAIL"
	@$(CURL) http://localhost:$(PORT)/site/ >/dev/null && echo "  /site/ OK" || echo "  /site/ FAIL"
	@$(CURL) http://localhost:$(PORT)/api/meters/ >/dev/null && echo "  /api/meters/ OK" || echo "  /api/meters/ (may be empty)"
	@echo "✓ Smoke checks (SQLite) complete"

# ==============================
#   FULL STACK (Postgres+Redis)
# ==============================
.PHONY: up-pg
up-pg:
	@echo "→ Starting Postgres + Redis + API stack (deployment parity mode)"
	$(DC) up --build -d
	@echo "✓ Stack up — http://localhost:8000"

.PHONY: down-pg
down-pg:
	@echo "→ Stopping Postgres + Redis + API stack"
	$(DC) down -v --remove-orphans || true
	@echo "✓ Stack removed"

.PHONY: logs-pg
logs-pg:
	$(DC) logs -f --tail=50

.PHONY: smoke
smoke:
	@echo "→ Checking full stack health..."
	@$(CURL) http://localhost:$(PORT)/api/health/z >/dev/null && echo "  /api/health/z OK" || echo "  /api/health/z FAIL"
	@$(CURL) http://localhost:$(PORT)/api/health/cachez >/dev/null && echo "  /api/health/cachez OK" || echo "  /api/health/cachez DOWN"
	@$(CURL) http://localhost:$(PORT)/site/ >/dev/null && echo "  /site/ OK" || echo "  /site/ FAIL"
	@$(CURL) http://localhost:$(PORT)/api/meters/ >/dev/null && echo "  /api/meters/ OK" || echo "  /api/meters/ (may be empty)"
	@echo "✓ Smoke checks complete"

# ==============================
#          UTILITIES
# ==============================
.PHONY: seed-demo
seed-demo:
	$(DC) exec api python -m scripts.seed_demo

.PHONY: clean
clean:
	@echo "→ Cleaning up all containers, networks, and volumes..."
	$(DC) down -v --remove-orphans || true
	$(DOCKER) rm -f $$(docker ps -aq --filter "name=$(APP_NAME)") 2>/dev/null || true
	$(DOCKER) volume prune -f >/dev/null || true
	$(DOCKER) network prune -f >/dev/null || true
	@echo "✓ Environment reset complete"

# ==============================
#          Worker + tasks
# ==============================
.PHONY: worker
worker: ## Run Celery worker with Beat scheduler
	docker compose up worker

.PHONY: tasks-refresh
tasks-refresh: ## Trigger manual KPI refresh
	curl -s -X POST http://localhost:8000/api/tasks/refresh-kpis | jq

.PHONY: tasks-warm
tasks-warm: ## Trigger manual cache warmup
	curl -s -X POST http://localhost:8000/api/tasks/cache/warmup | jq

.PHONY: tasks-backup
tasks-backup:
	curl -s -X POST http://localhost:8000/api/tasks/backup/db | jq

.PHONY: tasks-email
tasks-email:
	curl -s -X POST http://localhost:8000/api/tasks/email/health | jq


# ==============================
#          Pytest
# ==============================
.PHONY: test
test:
	@echo "→ Running pytest suite (SQLite mode)"
	poetry run pytest -q

