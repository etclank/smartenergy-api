# SmartEnergy API & Dashboard

[![CI](https://github.com/etclank/smartenergy-api/actions/workflows/ci.yml/badge.svg)](https://github.com/etclank/smartenergy-api/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/etclank/smartenergy-api/branch/main/graph/badge.svg)](https://codecov.io/gh/etclank/smartenergy-api)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/etclank/smartenergy-api)


A modern FastAPI starter with async SQLAlchemy, JWT auth, Alembic migrations, optional Redis caching, and GitHub Actions CI.
Includes a tiny static frontend (/site) to showcase the API with either live data or mock JSON.

---

## 🚀 Tech Stack

| Layer   | Choice                               | Notes                                |
| ------- | ------------------------------------ | ------------------------------------ |
| Runtime | **Python 3.13**                      | Poetry-managed                       |
| Web API | **FastAPI 0.115+**                   | Async REST, auto Swagger/Redoc       |
| DB      | **SQLite (dev)** / **Postgres**      | Async SQLAlchemy 2.x + Alembic       |
| Cache   | **Redis** (optional)                 | Used for cache/ping placeholder      |
| Auth    | **JWT** (python-jose)                | `/auth/login`, `/auth/me`            |
| CI/CD   | **GitHub Actions**                   | Ruff, mypy, pytest, coverage         |
| Demo UI | **Static HTML/CSS/JS** under `/site` | Calls API or falls back to mock JSON |


---

## 🧭 Architecture (starter)
```bash
┌───────────┐   HTTP    ┌──────────┐
│  /site    │◀────────▶ │ FastAPI  │
│  static   │           │  (REST)  │
└───────────┘           └────┬─────┘
                              │  async SQLAlchemy
                       ┌──────▼───────┐
                       │ SQLite / PG  │
                       └──────────────┘
                 (optional)
                       ┌──────────────┐
                       │   Redis      │
                       └──────────────┘
```

## 🗂️ Project Structure

```bash
.
├── app/
│   ├── main.py
│   ├── core/               # config, db, security, deps
│   ├── models/             # User, Site, Meter, Tariff, Energy*, MaxPower
│   ├── api/
│   │   ├── routers.py
│   │   ├── auth.py, health.py, sites.py, meters.py, tariffs.py
│   │   ├── energy_imported.py, energy_exported.py, energy_reactive.py, max_power.py
│   │   └── schemas/
│   │       ├── auth.py, meter.py, site.py, tariff.py, energy.py, __init__.py
│   ├── services/           # (future logic layer)
│   ├── tasks/              # background example
│   └── telemetry/          # observability stubs
│
├── site/                   # static demo frontend served at /site
│   ├── index.html          # dashboard summary page
│   ├── pages/
│   │   ├── sites.html, meters.html, meter.html, tariffs.html
│   ├── assets/
│   │   ├── css/style.css
│   │   ├── js/
│   │   │   ├── api.js, charts.js
│   │   │   ├── components/breadcrumb.js
│   │   │   └── pages/dashboard.js, sites.js, meters.js, meter.js, tariffs.js
│   │   ├── vendor/         # Chart.js + date-fns adapters
│   │   └── config.js
│   └── favicon.svg
│
├── scripts/
│   ├── prestart.sh, seed_demo.py
│   ├── site-serve.sh, site-open.sh
│
├── alembic/                # migrations
│   ├── env.py
│   └── versions/
│       └── *baseline & model migrations*
│
├── docker/ Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml / poetry.lock
├── render.yaml
├── docs/db-diagram.xml
└── tests/                  # pytest suite for health/auth/meters/energy
    ├── __init__.py
    ├── conftest.py                 # async test fixtures
    ├── test_health.py
    ├── test_auth.py
    └── test_meters.py
```

## ⚙️ Configuration
Environment variables (read via pydantic-settings, .env supported):

| var                  | example / default              | purpose                                  |
| -------------------- | ------------------------------ | ---------------------------------------- |
| `ENV`                | `dev`                          | environment label                        |
| `API_HOST`           | `0.0.0.0`                      | server host                              |
| `API_PORT`           | `8000`                         | server port                              |
| `DATABASE_URL`       | `sqlite+aiosqlite:///./app.db` | DB URL (SQLite dev, Postgres in Compose) |
| `REDIS_URL`          | `redis://localhost:6379/0`     | optional Redis                           |
| `JWT_SECRET`         | `change-me`                    | JWT signing secret                       |
| `JWT_ALG`            | `HS256`                        | JWT algorithm                            |
| `JWT_EXPIRE_MINUTES` | `60`                           | token lifetime                           |
| `FRONTEND_ORIGINS`   | `http://localhost:5173`        | CSV or JSON array; CORS allowlist        |

FRONTEND_ORIGINS can be a CSV (http://a,https://b) or a JSON array (["http://a","https://b"]).

Copy .env.example → .env and adjust as needed.

## 🧪 Quick Start (API)
### Option A — Poetry (SQLite dev)
```bash
poetry install
poetry run alembic upgrade head          # create tables
poetry run uvicorn app.main:app --reload
```

Docs available at:
- Swagger → http://127.0.0.1:8000/docs
- ReDoc → http://127.0.0.1:8000/redoc

### Option B — 🐋 Local Docker Workflow (Makefile)
**Build the Docker image**
```bash
make build
```
**Run container interactively (SQLite in image)**
```bash
make up
```
**Run container with explicit database URL and JWT secret**
```bash
make up DATABASE_URL="sqlite+aiosqlite:////tmp/app.db" JWT_SECRET=dev
```
**Stop and remove the background container**
```bash
make stop
```
**Follow logs**
```bash
make logs
```
**Open a shell inside the running container**
```bash
make sh
```
**Run a quick smoke test (healthz, site, meters)**
```bash
make smoke
```
**Create a demo meter**
```bash
make seed
```
### 🧱 Full Stack (Docker Compose)
```bash
make compose-up
# then open http://localhost:8000
make compose-down
```

For Postgres + Redis + API, use:
- API → http://localhost:8000
- Postgres → localhost:5432 (from Compose)
- Redis → localhost:6379 (optional)
Compose uses your .env for configuration. For CORS with the static site, include FRONTEND_ORIGINS=http://localhost:5173.

## 🖥️ Demo Frontend (/site)
The /site static frontend now includes a complete demo dashboard:
- /site/index.html – Dashboard Overview (status badges + KPI cards)
- /site/pages/sites.html – list of sites
- /site/pages/meters.html – meters per site
- /site/pages/meter.html – detailed charts with date-range filters
- /site/pages/tariffs.html – tariff summary table
The demo supports light/dark theme, charting with Chart.js + date-fns, and mock or live API mode (set via window.SITE_API_BASE).

- Configure in site/assets/config.js:
```bash
// Use the live API during local dev:
window.SITE_API_BASE = "http://localhost:8000";
window.SITE_USE_MOCK = false; // set true to force mock
```
- Serve locally:
```bash
./scripts/site-serve.sh
# then open http://localhost:5173
```
- Pages:
  - /site/index.html – landing page
  - /site/pages/meters.html – lists meters from API (or mock)
- You can also force mock mode via URL: ?mock=1

## 🔌 API Endpoints (starter)
- GET /healthz → {"status":"ok"}
- GET /cachez → {"redis":"up|down"} (optional Redis)
- POST /auth/login → {"access_token": "...", "token_type": "bearer"}
- GET /auth/me (Bearer token) → current user claims
- GET /meters/ → list meters
- POST /meters/ → create meter { "name": "...", "location": "..." }
- GET /meters/{id} → get meter by id

## 🧰 Dev Tasks
### Tests, Lint, Types
```bash
# Lint
poetry run ruff check .

# Types
poetry run mypy app

# Tests (SQLite in-memory for CI; local uses your env)
DATABASE_URL='sqlite+aiosqlite:///:memory:' JWT_SECRET='dev' \
poetry run pytest --maxfail=1 --disable-warnings -q
```
### Alembic
```bash
# Create / migrate schema
poetry run alembic upgrade head

# Make a new revision (edit models first)
poetry run alembic revision -m "add something"
poetry run alembic upgrade head
```

### Local test of image:
```bash
docker build -t smartenergy-api -f docker/Dockerfile .
docker run --rm -p 8000:8000 \
  -e ENV=prod \
  -e DATABASE_URL=sqlite+aiosqlite:///tmp/app.db \
  -e JWT_SECRET=localsecret \
  smartenergy-api
```

### 🧱 CI
- Workflow: .github/workflows/ci.yml
- Steps: checkout → setup Python → Poetry install → Ruff → mypy → pytest (+ coverage)
- Badges at top of this README
Codecov badge assumes you’ve connected the repo in Codecov and are uploading coverage from CI.

### Run tests
```bash
poetry run pytest --maxfail=1 --disable-warnings -q
```

## Roadmap (nice-to-have)
- Redis-backed rate limiting (FastAPI-Limiter)
- Background jobs (Celery or BackgroundTasks)
- GraphQL endpoint (Strawberry) and WS stream
- Telemetry (OpenTelemetry → exporter)
- Helm chart under /chart for AKS/K8s
- Render deploy (wired up via render.yaml)

## 🔮 Future Enhancements / Next Architecture Iteration

```bash
# SmartEnergy — High-Level Architecture (ASCII)

               HTTP / WS
┌─────────────┐ <--------> ┌────────────────────┐
│  React/PWA  │            │ FastAPI REST + GQL │
└─────────────┘            └─────────┬──────────┘
                                     │  (async SQLAlchemy)
                                     │
                               ┌─────▼─────┐
                               │ PostgreSQL│
                               └───────────┘
                                     ┊
                                     ┊  (optional CDC)
                                     ▼
                               ┌───────────┐
                               │ Workers   │
                               │ (Celery/  │
                               │  Dramatiq)│
                               └─────┬─────┘
                                     │
               pub/sub               │
┌───────────┐  <---------------------┘
│   Redis   │  <------>  FastAPI
└───────────┘

         OTEL traces/metrics/logs
FastAPI & Workers -----------------------> Observability
                                          (Prometheus / Grafana / Tempo / Jaeger)
```

### Potential additions:
- **GraphQL schema & subscriptions:** Use Strawberry for queries/mutations; WebSocket subscriptions for live readings per meter.
- **Real-time pipeline:** Redis Pub/Sub or Streams for fan-out; background workers consume and compute rollups (hourly/daily stats).
- **Background jobs:** Celery (Redis broker) or Dramatiq; example tasks like compute_daily_stats(meter_id, date).
- **CDC / eventing:** Debezium or logical decoding to stream DB changes to workers or analytics sinks.
- **Observability:** OpenTelemetry SDK → OTEL Collector → Prometheus/Grafana (metrics), Tempo/Jaeger (traces), Loki (logs).
- **Resilience & scale:** Rate limiting (FastAPI-Limiter+Redis), idempotency keys on ingest, pagination & keyset queries.
- **Data model hardening:** Partitions by time, read replicas, retention policies for raw vs. aggregated data.
- **Security:** Per-tenant JWT claims, API keys for machine clients, scopes/roles, audit logging.
- **Packaging:** Helm/Kustomize for Kubernetes, health/readiness probes, horizontal autoscaling.

## 📜 License
MIT — see LICENSE.

## 🚧 Phase 2 Implementation Roadmap (2025)

**Goal:** Transition the SmartEnergy API from a working MVP into a production-style backend service that demonstrates advanced FastAPI + DevOps maturity.
Each phase builds incrementally on the deployed app while remaining free-tier-friendly.

## 🚀 Phase 2 — Production-Style Backend + Frontend Evolution

> Goal: Transform SmartEnergy from a working MVP into a production-grade FastAPI platform demonstrating relational modeling, caching, observability, and a cohesive static frontend — all deployable on free-tier cloud services.

| Stage   | Focus                                         | Key Deliverables                                                                                                                                                                                  |
| :------ | :-------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **2.0** | 🧱 **Relational Data Model Foundation**       | Normalize schema across **Users**, **Sites**, **Meters**, **Tariffs**, and **Energy Readings**. Implement SQLAlchemy 2.x models, Alembic migrations, and CRUD routes with typed Pydantic schemas. |
| **2.1** | 💻 **Interactive Frontend + API Integration** | Expand `/site` into a full demo dashboard: Sites → Meters → Meter Details with Chart.js visualizations, date-range filters, theme toggle, tariffs table, and KPI summary cards.                   |
| **2.2** | 💾 **Persistent Postgres Integration**        | Migrate from **SQLite** (dev) to managed **Postgres** (Neon / Render). Validate Alembic migrations, seeding, and connection pooling for async SQLAlchemy.                                         |
| **2.3** | ⚡ **Caching & Performance Layer**             | Introduce **Redis** caching for high-volume endpoints (`/energy_*`), configurable TTL ≈ 60 s, with lazy invalidation and optional background warm-up.                                             |
| **2.4** | 🧮 **Background Jobs & Automation**           | Add `/tasks/refresh` or Celery-based worker to compute daily summaries, clean stale cache, and demonstrate async task patterns.                                                                   |
| **2.5** | 🔍 **Observability & Telemetry**              | Integrate **OpenTelemetry** traces, structured logging with request IDs, and Prometheus-style metrics for latency, throughput, and errors.                                                        |
| **2.6** | 🧪 **Testing & CI Hardening**                 | Achieve ≥ 90 % pytest coverage, enforce mypy + Ruff checks via GitHub Actions, and upload coverage to Codecov.                                                                                    |
| **2.7** | 📘 **Documentation & Deployment Polish**      | Finalize architecture diagrams, update README + Makefile targets, include `render.yaml` deployment guide, and produce a short demo video.                                                         |

## ✅ Phase 2.1 — Frontend Integration & Demo Dashboard (Completed)

**Milestone:** The /site frontend has evolved into a complete interactive demo showcasing live API integration and production-ready UI patterns.

**Delivered Features**

- 🧭 Full Navigation Flow: Sites → Meters → Meter Detail with breadcrumb trail and consistent top-bar layout.

- 📊 Dynamic Chart.js Visualizations: Multi-series energy charts with time-axis, tooltips, and color-adaptive theme.

- 🎨 Light/Dark Mode: Theme toggle using CSS variables and persisted localStorage preference.

- 📅 Date-Range Filtering: Client-side chart filtering with auto-refreshing dataset.

- 💸 Tariff Management Page: Tabular tariff summary per site, live from API.

- 🧱 Backend Parity: Matching /api/sites, /api/meters, /api/energy_*, and /api/tariffs routes fully implemented with async SQLAlchemy.

- 🧪 Seeded Demo Data: scripts/seed_demo.py populates week-long meter readings for continuous demo availability.

**Outcome:**
SmartEnergy now provides a cohesive, data-driven dashboard that bridges the backend API and frontend visualization layer — ready for Phase 2.2 (Postgres + Caching).