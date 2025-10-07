# -----------------------------
# SmartEnergy API — Makefile
# -----------------------------

# Image / container
IMAGE       ?= smartenergy-api
TAG         ?= local
NAME        ?= smartenergy-api

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

# ------------- Help -------------
.PHONY: help
help:
	@echo "Targets:"
	@echo "  build           Build the Docker image ($(IMAGE):$(TAG))"
	@echo "  run             Run container in the foreground (Ctrl+C to stop)"
	@echo "  up              Run container in the background (name=$(NAME))"
	@echo "  stop            Stop & remove the background container"
	@echo "  logs            Tail logs from the background container"
	@echo "  sh              Exec into the running container (sh)"
	@echo "  smoke           Hit health/static/metrics endpoints to verify"
	@echo "  seed            Create a demo meter via API"
	@echo "  # compose workflow (Postgres+Redis+API)"
	@echo "  compose-up      docker compose up --build"
	@echo "  compose-down    docker compose down -v"
	@echo "Vars (override like VAR=value make run): PORT, ENV, DATABASE_URL, JWT_SECRET, IMAGE, TAG, NAME"

# ---------- Single-container ----------
.PHONY: build
build:
	$(DOCKER) build -t $(IMAGE):$(TAG) -f $(DOCKERFILE) .

.PHONY: run
run: build
	$(DOCKER) run --rm -p $(PORT):8000 \
		-e ENV=$(ENV) \
		-e DATABASE_URL="$(DATABASE_URL)" \
		-e JWT_SECRET="$(JWT_SECRET)" \
		--name $(NAME)-fg \
		$(IMAGE):$(TAG)

.PHONY: up
up: build
	$(DOCKER) run -d -p $(PORT):8000 \
		-e ENV=$(ENV) \
		-e DATABASE_URL="$(DATABASE_URL)" \
		-e JWT_SECRET="$(JWT_SECRET)" \
		--name $(NAME) \
		$(IMAGE):$(TAG)
	@echo "Running → http://localhost:$(PORT)"

.PHONY: stop
stop:
	-$(DOCKER) rm -f $(NAME) >/dev/null 2>&1 || true

.PHONY: logs
logs:
	$(DOCKER) logs -f $(NAME)

.PHONY: sh
sh:
	$(DOCKER) exec -it $(NAME) sh

# ---------- Quick checks ----------
.PHONY: smoke
smoke:
	@echo "→ Checking health..."
	@$(CURL) http://localhost:$(PORT)/api/health/z >/dev/null && echo "  /api/health/z OK"
	@$(CURL) http://localhost:$(PORT)/site/ >/dev/null && echo "  /site/ OK"
	@$(CURL) http://localhost:$(PORT)/api/meters/ >/dev/null && echo "  /api/meters/ OK" || echo "  /api/meters/ (may be empty)"
	@echo "✓ Smoke checks passed"

.PHONY: seed
seed:
	@echo "→ Creating demo meter"
	@$(CURL) -X POST http://localhost:$(PORT)/meters/ \
		-H "Content-Type: application/json" \
		-d '{"name":"Demo Meter","location":"Local"}' >/dev/null && echo "  Created"
	@$(CURL) http://localhost:$(PORT)/meters/ | jq '.' || true

# ---------- docker-compose stack ----------
.PHONY: compose-up
compose-up:
	$(DC) up --build

.PHONY: compose-down
compose-down:
	$(DC) down -v
