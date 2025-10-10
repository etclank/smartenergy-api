# SmartEnergy API & Dashboard

[![CI](https://github.com/etclank/smartenergy-api/actions/workflows/ci.yml/badge.svg)](https://github.com/etclank/smartenergy-api/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/etclank/smartenergy-api/branch/main/graph/badge.svg)](https://codecov.io/gh/etclank/smartenergy-api)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/etclank/smartenergy-api)


---

A modern **FastAPI + PostgreSQL** backend with async SQLAlchemy, JWT authentication, optional Redis caching, and full Docker + Render deployment.  
Includes a static **demo dashboard** (`/site`) for interactive visualization of live API data.

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
│   ├── tasks/                      # Background jobs (future Celery/Dramatiq tasks)
│   │   ├── __init__.py
│   │   └── refresh_meter.py        # Example placeholder for periodic data refresh
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
    └── __pycache__/                # Compiled cache (ignored in VCS)

```

## ⚙️ Configuration
- Environment variables (read via pydantic-settings, .env supported):

- FRONTEND_ORIGINS can be a CSV (http://a,https://b) or a JSON array (["http://a","https://b"]).

- Copy .env.example → .env and adjust as needed.


## 🧪 Quick Start (Local)
### 🐍 Using Poetry with SQLite
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
make compose-up
# open http://localhost:8000
make compose-down
```
Services:
- API: http://localhost:8000
- Postgres: localhost:5432
- Redis: localhost:6379 (optional)

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

## ✅ 🧱 Stage 2.2 — Persistent Postgres Integration (✅ Completed)

**Goal:** Migrate from ephemeral SQLite to persistent managed Postgres with auto initialization and seed support.

### **Deliverables**
- Replaced Alembic with lightweight SQLAlchemy create_all initialization
- Added scripts/init_db.py + scripts/seed_demo.py
- Updated Docker and prestart.sh for multi-DB support (Postgres & SQLite)
- Successfully deployed to Render using managed Postgres
- Smoke tests and Docker Compose workflows verified

## 🔮 Next Stage (2.3) — Caching & Performance Layer
Introduce Redis-based caching and response acceleration for high-volume endpoints (/energy_*).