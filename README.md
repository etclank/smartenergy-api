# SmartEnergy API & Dashboard

[![CI](https://github.com/etclank/smartenergy-api/actions/workflows/ci.yml/badge.svg)](https://github.com/etclank/smartenergy-api/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/etclank/smartenergy-api/branch/main/graph/badge.svg?token=${{ secrets.CODECOV_TOKEN }})](https://codecov.io/gh/etclank/smartenergy-api)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/etclank/smartenergy-api)


---

A production-style **FastAPI + PostgreSQL + Redis** backend with async SQLAlchemy 2.x, JWT auth, configurable caching, and full Docker + Render deployment.  
Includes a static **demo dashboard** (`/site`) visualizing live API data.

---

## 🚀 Tech Stack (updated for Stage 2.4)


| Layer            | Choice                                     | Notes                                                           |
| :--------------- | :----------------------------------------- | :-------------------------------------------------------------- |
| Runtime          | **Python 3.13**                            | Poetry-managed environment                                      |
| Web API          | **FastAPI 0.115+**                         | Async REST + auto Swagger/ReDoc                                 |
| Database         | **SQLite (dev)** / **PostgreSQL (prod)**   | Async SQLAlchemy 2.x (create_all init)                          |
| Cache / Broker   | **Redis 7 (local)** / **Upstash (Render)** | Used for API caching + Celery message broker                    |
| Auth             | **JWT (python-jose)**                      | `/auth/login`, `/auth/me`                                       |
| Background Jobs  | **Celery 5 + Redis Beat**                  | Periodic tasks for KPI refresh, cache cleanup, metrics, backups |
| DevOps Utilities | **SendGrid (optional)**                    | Daily health email + DB snapshot tasks                          |
| CI/CD            | **GitHub Actions + Codecov**               | Ruff · mypy · pytest · coverage                                 |
| Demo UI          | **Static HTML + Chart.js**                 | Served under `/site` (showing live API status + KPIs)           |


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
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entrypoint: mounts routers & serves /site
│   │
│   ├── core/                        # Core runtime modules
│   │   ├── config.py                # Settings via Pydantic (DB_URL, Redis, JWT, etc.)
│   │   ├── db.py                    # Async SQLAlchemy engine/session
│   │   ├── deps.py                  # Dependency injection helpers
│   │   ├── cache.py                 # Redis caching utilities
│   │   ├── security.py              # JWT + password hashing utilities
│   │   ├── logging.py               # Loguru setup (colored dev / JSON prod)
│   │   └── telemetry.py             # OpenTelemetry setup for traces + metrics
│   │
│   ├── models/                      # SQLAlchemy ORM definitions
│   │   ├── base.py                  # Declarative base
│   │   ├── user.py                  # Users (id, username, email, password)
│   │   ├── site.py                  # Sites (id, name, location)
│   │   ├── meter.py                 # Meters linked to sites
│   │   ├── tariff.py                # Tariff definitions
│   │   ├── energy_imported.py       # Hourly imported energy
│   │   ├── energy_exported.py       # Hourly exported energy
│   │   ├── energy_reactive.py       # Reactive energy readings
│   │   ├── max_power.py             # Max power readings
│   │   ├── summary_kpi.py           # KPI summaries
│   │   ├── system_metrics.py        # Persisted system metrics
│   │   ├── summary_event.py         # Event log (system events)
│   │   └── __init__.py
│   │
│   ├── api/                         # REST API routes & schemas
│   │   ├── routers.py               # Unified router registry
│   │   ├── auth.py                  # /api/auth/login, /api/auth/me
│   │   ├── health.py                # /api/healthz
│   │   ├── sites.py                 # /api/sites CRUD
│   │   ├── meters.py                # /api/meters CRUD
│   │   ├── tariffs.py               # /api/tariffs CRUD
│   │   ├── energy_imported.py       # /api/energy_imported
│   │   ├── energy_exported.py       # /api/energy_exported
│   │   ├── energy_reactive.py       # /api/energy_reactive
│   │   ├── max_power.py             # /api/max_power
│   │   ├── metrics.py               # Prometheus metrics exposition
│   │   ├── system_metrics.py        # /api/system_metrics (DB-backed)
│   │   ├── tasks.py                 # Manual Celery triggers (/api/tasks/*)
│   │   ├── utils/
│   │   │   └── cache_utils.py       # @cache_response decorator + cache stats
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── site.py
│   │       ├── meter.py
│   │       ├── tariff.py
│   │       ├── energy.py
│   │       └── ...
│   │
│   ├── tasks/                       # Celery async background jobs
│   │   ├── __init__.py
│   │   ├── demo_data.py             # generate_demo_data() / clean_demo_data()
│   │   ├── refresh_kpis.py          # refresh_kpis() aggregates KPIs
│   │   ├── cache_tasks.py           # clean_stale_cache() / warmup_cache()
│   │   ├── metrics_tasks.py         # record_system_metrics() / update_meta_cache()
│   │   ├── backup.py                # backup_db_snapshot() to /backups
│   │   ├── email.py                 # send_health_email() via SendGrid
│   │   └── worker.py                # Celery app + Beat schedule (production-ready)
│   │
│   ├── telemetry/
│   │   └── __init__.py
│   │
│   └── graphql/
│       └── __init__.py
│
├── site/                            # Static dashboard frontend
│   ├── index.html
│   ├── pages/
│   │   ├── sites.html
│   │   ├── meters.html
│   │   ├── tariffs.html
│   │   └── system.html              # System Health dashboard
│   ├── assets/
│   │   ├── css/style.css
│   │   ├── js/
│   │   │   ├── api.js
│   │   │   ├── charts.js
│   │   │   ├── theme.js
│   │   │   ├── components/breadcrumb.js
│   │   │   └── pages/system.js
│   │   └── config.js
│   └── vendor/
│       ├── chart.min.js
│       └── date-fns.min.js
│
├── scripts/                         # Automation & local utilities
│   ├── prestart.sh
│   ├── init_db.py
│   ├── seed_demo.py
│   ├── site-serve.sh
│   └── site-open.sh
│
├── docker/
│   └── Dockerfile                   # Multi-stage Poetry-based build
│
├── docker-compose.yml               # Local dev stack (Postgres + Redis + API)
├── render.yaml                      # Render deploy definition (web + worker)
│
├── Makefile                         # CLI shortcuts for build/run/logs/smoke
├── pyproject.toml / poetry.lock     # Dependencies & metadata
├── mypy.ini / pytest.ini            # Type-checking & testing config
├── LICENSE                          # MIT license
│
├── docs/
│   ├── db-diagram.drawio
│   └── db-diagram.xml
│
└── tests/                           # pytest suite
    ├── conftest.py                  # Async fixtures + in-memory SQLite setup
    ├── test_health.py               # /api/healthz endpoint
    ├── test_auth.py                 # Auth + JWT tests
    ├── test_meters.py               # Meter CRUD tests
    ├── test_energy_endpoints.py     # Energy endpoints (import/export/reactive)
    ├── test_tariff.py               # Tariff endpoints
    ├── test_metrics_endpoints.py    # Prometheus metrics endpoint
    ├── test_system_metrics_api.py   # System metrics API
    ├── test_metrics_task.py         # record_system_metrics Celery task
    ├── test_core_cache.py           # Core Redis cache logic (app/core/cache.py)
    ├── test_telemetry_config.py     # Telemetry init + OTLP/console exporters
    ├── test_metrics_tasks_retry.py  # Metrics retry + resilience logic
    ├── test_security_bad_token.py   # Invalid JWT & auth edge cases
    ├── test_worker_module.py        # Celery worker module + task registration
    ├── test_task_core_minimal.py    # Minimal integration tests for cache/email/backup tasks
    ├── test_cache.py                # Redis caching decorator behavior
    ├── test_tasks_integration.py    # /api/tasks/* endpoints integration
    └── test_worker_tasks.py         # Direct Celery task execution (refresh, clean, warmup)

```

## ⚙️ Configuration
- Environment variables (read via pydantic-settings, .env supported):

- FRONTEND_ORIGINS can be a CSV (http://a,https://b) or a JSON array (["http://a","https://b"]).

- Copy .env.example → .env and adjust as needed.


## 🧪 Quick Start

### 🐍 Local (dev, SQLite)
```bash
poetry install
poetry run python -m scripts.init_db
poetry run uvicorn app.main:app --reload
```

Docs available at:
- Swagger → http://127.0.0.1:8000/docs
- ReDoc → http://127.0.0.1:8000/redoc

### 🐋 Using Docker Compose (Postgres + Redis + API)
```bash
make up-pg
make logs-pg
make smoke
# open http://localhost:8000
```
### Services:

| Service  | URL                                            | Notes                 |
| :------- | :--------------------------------------------- | :-------------------- |
| API      | [http://localhost:8000](http://localhost:8000) | FastAPI + static site |
| Postgres | localhost:5432                                 | `postgres/postgres`   |
| Redis    | localhost:6379                                 | cache layer           |


## ☁️ Deployment on Render
### 🧱 Render Setup
1. Create a free Render PostgreSQL database.
- Example URL:
      postgresql://smartenergy_user:abc123@smartenergy-db:5432/smartenergy
2. Copy that URL and update render.yaml:
```bash
- key: DATABASE_URL
  value: "postgresql+asyncpg://smartenergy_user:abc123@smartenergy-db:5432/smartenergy"
- key: SEED_DEMO
  value: "1"
```

Click “Deploy to Render” → done!
Your app will be live at https://smartenergy-api.onrender.com.
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

## 🔌 API Highlights
- GET /api/healthz → health check
- POST /api/auth/login → JWT login
- GET /api/auth/me → current user
- GET /api/sites / /api/meters / /api/tariffs → main entities
- GET /api/energy_* → hourly energy data

## 🧰 Dev Tasks
```bash
# Lint
poetry run ruff check .
# Type check
poetry run mypy app
# Tests
poetry run pytest --maxfail=1 --disable-warnings -q
# Local smoke test
make smoke
```

### 🧱 CI
- Workflow: .github/workflows/ci.yml
- Steps: checkout → setup Python → Poetry install → Ruff → mypy → pytest (+ coverage)
- Badges at top of this README
Codecov badge assumes you’ve connected the repo in Codecov and are uploading coverage from CI.


## 🧮 Background Jobs & Automation

### Highlights
SmartEnergy API Stage 2.4 introduces real, production-style background processing and DevOps utilities powered by Celery + Redis.
| Category             | Tasks                                                           | Purpose                                                                     |
| -------------------- | --------------------------------------------------------------- | --------------------------------------------------------------------------- |
| **Data lifecycle**   | `generate_demo_data(days)` / `clean_demo_data(older_than_days)` | Extend or trim demo readings weekly / monthly                               |
| **Analytics**        | `refresh_kpis()`                                                | Aggregate daily site KPIs into `summary_kpi` table                          |
| **Cache lifecycle**  | `clean_stale_cache()` / `warmup_cache()`                        | Clear expired Redis keys and pre-populate hot endpoints                     |
| **System metrics**   | `record_system_metrics()` / `update_meta_cache()`               | Measure DB + Redis latency, table counts, and update `meta:api`             |
| **DevOps utilities** | `backup_db_snapshot()` / `send_health_email()`                  | Snapshot Postgres / SQLite → `/app/backups`; optional SendGrid daily report |


### 🔁 Two Execution Modes
| Mode                     | Trigger             | Where it runs                 | Description                                                  |
| ------------------------ | ------------------- | ----------------------------- | ------------------------------------------------------------ |
| **HTTP on-demand**       | `POST /api/tasks/*` | FastAPI via `BackgroundTasks` | Non-blocking immediate runs; works even without Celery       |
| **Scheduled automation** | Celery Beat cron    | Separate `worker` container   | Periodic jobs: KPIs daily, metrics 10 min, cache daily, etc. |

### 📅 Celery Beat Schedule
```bash
celery_app.conf.beat_schedule = {
    "kpis-refresh-daily":    {"task": "kpis.refresh",     "schedule": 60*60*24},
    "demo-generate-weekly":  {"task": "demo.generate",    "schedule": 60*60*24*7},
    "demo-clean-weekly":     {"task": "demo.clean",       "schedule": 60*60*24*7},
    "cache-clean-daily":     {"task": "cache.clean",      "schedule": 60*60*24},
    "cache-warmup-daily":    {"task": "cache.warmup",     "schedule": 60*60*24},
    "metrics-every-10m":     {"task": "metrics.record",   "schedule": 600},
    "meta-update-hourly":    {"task": "meta.update",      "schedule": 3600},
    "backup-db-daily":       {"task": "backup.db",        "schedule": 60*60*24},
    "health-email-daily":    {"task": "email.health",     "schedule": 60*60*24},
}
```

### Flow
```bash
+-------------+      +-------------+        +-----------+
|  FastAPI    | ---> |  Redis      | <----> |  Celery   |
|  /api/tasks |      |  (broker)   |        |  Worker+Beat |
+-------------+      +-------------+        +-----------+
       |                     |                     |
       |   async SQLAlchemy   |                     |
       +--------------------->|   PostgreSQL / SQLite|
                              +----------------------+
```
- FastAPI exposes manual task endpoints.
- Redis acts as both Celery broker and cache store.
- Celery worker + beat (separate container) executes and schedules all jobs.
- PostgreSQL / SQLite stores metrics and summaries.

## 🧰 Local Testing
```bash
make up-pg         # start Postgres + Redis + API + Worker
make smoke         # health check
make tasks-refresh # trigger KPI refresh
make logs-pg       # watch worker executing beat jobs
```

## 🔍Observability & Telemetry

### 🎯 Objective
Transform the SmartEnergy API into a fully observable platform by instrumenting telemetry, metrics, and structured logs.
Expose Prometheus-style runtime metrics, correlate requests with traces, and visualize live system performance in the /site dashboard.

### ⚙️ Configuration
| Variable                      | Example Value                           | Description                              |
| ----------------------------- | --------------------------------------- | ---------------------------------------- |
| `ENABLE_TELEMETRY`            | `1` or `0`                              | Enables/disables OpenTelemetry startup.  |
| `OTEL_SERVICE_NAME`           | `smartenergy-api`                       | Logical service name for traces/metrics. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `https://otlp-grafana.example.com:4318` | Optional remote OTLP export.             |
| `OTEL_EXPORTER_OTLP_HEADERS`  | `Authorization=Bearer <token>`          | HTTP headers for remote export.          |
| `LOG_LEVEL`                   | `INFO / DEBUG / WARNING`                | Global logging threshold.                |

Default (ENABLE_TELEMETRY=0) logs to console only and exports no traces—safe for local dev.

### 🧠 Design Flow
```bash
┌──────────────┐   HTTP   ┌──────────────┐
│  /site/system │◀────────│  FastAPI API │
│  Chart.js UI  │         │  + Middleware│
└──────┬───────┘         └──────┬───────┘
       │   /api/system_metrics   │
       │   /api/metrics          │
       ▼                         ▼
  Prometheus scrape      OTLP traces/metrics/logs
                         └──> Console / Grafana Cloud
```
- Middleware captures every request’s latency and increments counters.
- record_system_metrics() persists CPU/mem stats to DB every 10 min (via Celery or Render Cron).
- /site/pages/system.html fetches /api/system_metrics/latest for live graphs.

### 🧰 Developer Verification
```bash
# Run API locally with telemetry disabled
poetry run uvicorn app.main:app --reload

# Run with telemetry + console exporter
ENABLE_TELEMETRY=1 poetry run uvicorn app.main:app

# Hit endpoints
curl http://localhost:8000/api/metrics
curl http://localhost:8000/api/system_metrics/latest

# Run full test suite
poetry run pytest -q
poetry run mypy app
```

## 🔬 Stage 2.6 — Testing & CI

### 🧪 Coverage Summary
| Metric                   | Result                                                  |
| :----------------------- | :------------------------------------------------------ |
| **Lines covered**        | ≥ 90 % total (including core, tasks, and telemetry)     |
| **Tested modules**       | 45 / 45 core and task modules covered                   |
| **New test files added** | 6 new high-value test suites                            |
| **CI gate**              | `pytest --cov=app --cov-fail-under=90 --cov-report=xml` |


### ⚙️ CI / Codecov Workflow
```bash
# .github/workflows/ci.yml (excerpt)
- name: Coverage (XML)
  run: poetry run pytest --cov=app --cov-branch --cov-report=xml --cov-report=term-missing

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v5
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    files: ./coverage.xml
    flags: unittests
    fail_ci_if_error: true
```

### 🧩 CI Pipeline Summary
| Step                | Tool                         | Purpose                                          |
| ------------------- | ---------------------------- | ------------------------------------------------ |
| **Ruff**            | `ruff check .`               | Style, linting, import order, and code hygiene   |
| **Mypy**            | `mypy app`                   | Static type checking (strict mode)               |
| **Pytest**          | `pytest --asyncio-mode=auto` | Full async test suite (FastAPI, Redis, Celery)   |
| **Codecov**         | `codecov/codecov-action@v5`  | Upload & visualize coverage metrics per commit   |
| **Artifact Upload** | `coverage.xml`               | Stored for manual review and historical tracking |

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

## 🔬 Stage 2.6 — Testing & CI Hardening (✅ Completed)

### 🎯 Objective
Elevate SmartEnergy API to production-grade testing and CI standards by enforcing strict static analysis, automated coverage enforcement, and continuous visibility through Codecov integration.

### 🧱 Key Deliverables
| Category                           | Deliverable                                 | Description                                                                                                             |
| ---------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **A. Unit Test Expansion**         | Full coverage for all core modules          | Added dedicated tests for `core.cache`, `core.telemetry`, `core.security`, `tasks.*`, and Celery worker initialization. |
| **B. Coverage Enforcement**        | 90 % global threshold (pytest-cov)          | Coverage now verified in CI (`--cov-fail-under=90`); failures block merge.                                              |
| **C. Codecov Integration**         | GitHub Action upload + dashboard + badge    | Coverage uploaded via `codecov/codecov-action@v5`; PR comments and per-file diff coverage visible in Codecov dashboard. |
| **D. CI Pipeline Upgrade**         | `.github/workflows/ci.yml` streamlined      | Runs **Ruff → Mypy → Pytest (coverage) → Codecov** in sequence using Poetry, with caching for dependencies.             |
| **E. Test Structure Cleanup**      | Modular async test design via `conftest.py` | Unified async fixtures with SQLite in-memory DB and dependency overrides for all FastAPI routes.                        |
| **F. Stability & Fail-Open Logic** | Robust error handling verified              | Confirmed safe fallback for cache failures, backup errors, and Redis unavailability across test cases.                  |

### 🧪 Coverage Summary
| Metric                   | Result                                                  |
| :----------------------- | :------------------------------------------------------ |
| **Lines covered**        | ≥ 90 % total (including core, tasks, and telemetry)     |
| **Tested modules**       | 45 / 45 core and task modules covered                   |
| **New test files added** | 6 new high-value test suites                            |
| **CI gate**              | `pytest --cov=app --cov-fail-under=90 --cov-report=xml` |


### ⚙️ CI / Codecov Workflow
```bash
# .github/workflows/ci.yml (excerpt)
- name: Coverage (XML)
  run: poetry run pytest --cov=app --cov-branch --cov-report=xml --cov-report=term-missing

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v5
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    files: ./coverage.xml
    flags: unittests
    fail_ci_if_error: true
```

### 🧩 CI Pipeline Summary
| Step                | Tool                         | Purpose                                          |
| ------------------- | ---------------------------- | ------------------------------------------------ |
| **Ruff**            | `ruff check .`               | Style, linting, import order, and code hygiene   |
| **Mypy**            | `mypy app`                   | Static type checking (strict mode)               |
| **Pytest**          | `pytest --asyncio-mode=auto` | Full async test suite (FastAPI, Redis, Celery)   |
| **Codecov**         | `codecov/codecov-action@v5`  | Upload & visualize coverage metrics per commit   |
| **Artifact Upload** | `coverage.xml`               | Stored for manual review and historical tracking |


### 📈 Stage 2.6 Outcome
- ✅ Achieved consistent 90 %+ coverage across all modules.
- ✅ Established zero-warning linting and static type safety gates.
- ✅ Fully automated test-→-coverage-→-upload pipeline in GitHub Actions.
- 🧮 Codecov dashboard and badge reflect real-time coverage health for each PR.

Next milestone: Stage 2.7 — Documentation & Deployment Polish, consolidating final README diagrams, Render deploy guides, and a short demo video.