# SmartEnergy API & Dashboard

[![CI](https://github.com/etclank/smartenergy-api/actions/workflows/ci.yml/badge.svg)](https://github.com/etclank/smartenergy-api/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/etclank/smartenergy-api/branch/main/graph/badge.svg)](https://codecov.io/gh/etclank/smartenergy-api)
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
│   ├── main.py                     # FastAPI app entrypoint (creates app, mounts routers, serves /site)
│   │
│   ├── core/                       # Core runtime modules
│   │   ├── config.py               # Pydantic settings: loads ENV, DATABASE_URL, JWT, etc.
│   │   ├── db.py                   # Async SQLAlchemy engine/session creation
│   │   ├── security.py             # Password hashing (bcrypt) + JWT utilities
│   │   ├── deps.py                 # Dependency injection helpers for routes
│   │   ├── cache.py                # Optional Redis caching logic
│   │   └── telemetry.py            # Placeholder for OpenTelemetry integration (future)
│   │
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── base.py                 # Declarative Base + metadata
│   │   ├── user.py                 # User(id, username, email, password_hash)
│   │   ├── site.py                 # Site(id, name, location, owner_id)
│   │   ├── meter.py                # Meter(id, name, serial_number, site_id)
│   │   ├── tariff.py               # Tariff(id, name, price_per_kwh, site_id)
│   │   ├── energy_imported.py      # Hourly imported energy readings
│   │   ├── energy_exported.py      # Hourly exported energy readings
│   │   ├── energy_reactive.py      # Reactive energy readings
│   │   ├── max_power.py            # Daily maximum power values
│   │   ├── summary_kpi.py          # daily KPI summaries per site
│   │   ├── system_metrics.py       # DB + Redis latency + row counts
│   │   ├── summary_event.py        # simple event log for future analytics
│   │   └── __init__.py
│   │   └── __init__.py
│   │
│   ├── api/                        # REST API routes & schemas
│   │   ├── routers.py              # Central router registration for all endpoints
│   │   ├── auth.py                 # /api/auth/login and /api/auth/me
│   │   ├── health.py               # /api/healthz (service health endpoint)
│   │   ├── sites.py                # CRUD for /api/sites
│   │   ├── meters.py               # CRUD for /api/meters
│   │   ├── tariffs.py              # CRUD for /api/tariffs
│   │   ├── energy_imported.py      # /api/energy_imported
│   │   ├── energy_exported.py      # /api/energy_exported
│   │   ├── energy_reactive.py      # /api/energy_reactive
│   │   ├── max_power.py            # /api/max_power
│   │   ├── tasks.py                # /api/tasks/* endpoints for manual triggers
│   │   ├── utils/                    # Utility modules for API layer
│   │   │   └── cache_utils.py        # Stage 2.3: @cache_response decorator for Redis caching
│   │   └── schemas/                # Pydantic request/response models
│   │       ├── auth.py
│   │       ├── site.py
│   │       ├── meter.py
│   │       ├── tariff.py
│   │       ├── energy.py
│   │       └── __init__.py
│   │
│   ├── services/                   # Optional business logic layer
│   │   ├── user_service.py         # Example service for user creation/validation
│   │   └── meter_service.py        # Example service for meter logic
│   │
│   ├── tasks/                      # Celery + async background tasks
│   │   ├── __init__.py
│   │   ├── demo_data.py            # generate_demo_data / clean_demo_data
│   │   ├── refresh_kpis.py         # compute daily KPIs into summary_kpi
│   │   ├── cache_tasks.py          # clean_stale_cache / warmup_cache
│   │   ├── metrics_tasks.py        # record_system_metrics / update_meta_cache
│   │   ├── backup.py               # backup_db_snapshot (Postgres pg_dump or SQLite copy)
│   │   ├── email.py                # send_health_email via SendGrid (optional)
│   │   └── worker.py               # Celery + Beat scheduler configuration
│   │
│   ├── telemetry/                  # Observability & monitoring stubs
│   │   └── __init__.py
│   │
│   └── graphql/                    # Placeholder for future GraphQL schema (Strawberry)
│       └── __init__.py
│
├── site/                           # Static frontend demo
│   ├── index.html                  # Dashboard summary
│   ├── favicon.svg
│   ├── pages/                      # Section pages
│   │   ├── sites.html              # List of sites
│   │   ├── meters.html             # Meter list per site
│   │   ├── meter.html              # Meter detail charts
│   │   └── tariffs.html            # Tariff summary
│   ├── mock/                       # Offline fallback JSON
│   │   └── meters.json
│   ├── assets/
│   │   ├── config.js               # API base URL + mock settings
│   │   ├── css/style.css           # Styling (light/dark themes)
│   │   ├── js/                     # Frontend logic
│   │   │   ├── api.js              # Fetch wrapper for API calls
│   │   │   ├── charts.js           # Chart.js setup + helpers
│   │   │   ├── theme.js            # Light/dark theme toggle
│   │   │   ├── components/
│   │   │   │   └── breadcrumb.js
│   │   │   └── pages/              # Page-specific JS controllers
│   │   │       ├── dashboard.js
│   │   │       ├── sites.js
│   │   │       ├── meters.js
│   │   │       ├── meter.js
│   │   │       └── tariffs.js
│   │   └── vendor/                 # Third-party libs
│   │       ├── chart.min.js
│   │       ├── chartjs-adapter-date-fns.min.js
│   │       └── date-fns.min.js
│
├── scripts/                        # Management & automation scripts
│   ├── prestart.sh                 # Runs before Uvicorn: wait for DB, init, seed
│   ├── init_db.py                  # Creates tables & seeds if SEED_DEMO=1
│   ├── seed_demo.py                # Generates sample data for demo visualization
│   ├── site-serve.sh               # Local static server (for /site)
│   └── site-open.sh                # Opens local site in browser
│
├── docker/
│   └── Dockerfile                  # Multi-stage Docker build (Poetry-based)
│
├── docker-compose.yml              # Local dev stack (Postgres + Redis + API)
├── render.yaml                     # Render deployment definition (Docker)
│
├── Makefile                        # CLI shortcuts for build, run, logs, smoke, etc.
├── pyproject.toml / poetry.lock     # Dependencies & metadata
├── mypy.ini / pytest.ini            # Type-check & testing configuration
├── LICENSE                          # MIT license
│
├── docs/
│   ├── db-diagram.drawio           # ERD visual of database schema
│   └── db-diagram.xml
│
└── tests/                          # pytest suite
    ├── conftest.py                 # async fixtures, DB setup
    ├── test_health.py              # Health endpoint test
    ├── test_auth.py                # JWT auth tests
    ├── test_meters.py              # Meter CRUD tests
    ├── test_energy_endpoints.py    # Energy route coverage
    ├── test_tariff.py              # Tariff endpoints
    ├── test_cache.py               #  verifies Redis caching + fail-open behavior
    ├── test_tasks_integration.py   # endpoint tests for /api/tasks/*
    └── test_worker_tasks.py        # direct task execution tests

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

## 🔍Observability & Telemetry (✅ Completed)

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

## 🔍 Stage 2.5 — Observability & Telemetry (✅ Completed)

### 🎯 Objective
Transform the SmartEnergy API into a fully observable platform by instrumenting telemetry, metrics, and structured logs.
Expose Prometheus-style runtime metrics, correlate requests with traces, and visualize live system performance in the /site dashboard.

### 🧱 Key Deliverables
| Category                        | Deliverable                                                   | Description                                                                                                                                  |
| ------------------------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. Telemetry Core**           | `app/core/telemetry.py`                                       | Initializes OpenTelemetry tracing + metrics if `ENABLE_TELEMETRY=1`.<br>Supports OTLP or console export.                                     |
| **B. Structured Logging**       | `app/core/logging.py`                                         | Unified Loguru JSON logging (Prod) + colored human output (Dev).<br>Correlates logs with OTel trace IDs.                                     |
| **C. Prometheus Metrics**       | `app/api/metrics.py` + middleware                             | Exposes `/api/metrics` endpoint with Prometheus exposition text.<br>Tracks `http_requests_total`, latency histograms, and cache hits/misses. |
| **D. System Metrics Expansion** | `app/models/system_metrics.py` + `app/tasks/metrics_tasks.py` | Records CPU %, memory %, uptime seconds via `psutil`; persisted to DB.                                                                       |
| **E. Frontend Visualization**   | `/site/pages/system.html` + `assets/js/pages/system.js`       | New System Health panel: gauges for CPU/mem + trend charts for latency.                                                                      |
| **F. Testing & Validation**     | `tests/test_metrics_*`, `tests/test_system_metrics_api.py`    | Verifies Prometheus output and DB recording; all async pytest green.                                                                         |

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

### 📊 Stage 2.5 Outcome
SmartEnergy API now provides **end-to-end observability**:
- Real-time request and cache metrics via Prometheus.
- Automatic trace context for every API request (OpenTelemetry).
- Structured JSON logs for searchable auditing.
- Self-contained System Health UI with live charts.

Next milestone: Stage 2.6 — Testing & CI Hardening, focusing on 90 %+ coverage, Ruff/mypy enforcement, and Codecov integration.