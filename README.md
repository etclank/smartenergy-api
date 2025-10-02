# SmartEnergy API

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
├── README.md
├── .env.example
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py              # pydantic-settings: DB/Redis/JWT/CORS
│   ├── db.py                  # async SQLAlchemy engine/session
│   ├── deps.py                # FastAPI Depends (db session, auth)
│   ├── security.py            # JWT helpers
│   ├── cache.py               # optional Redis client + helpers
│   ├── api/
│   │   ├── routers.py         # include_router hub
│   │   ├── auth.py            # /auth/login, /auth/me
│   │   ├── health.py          # /healthz, /cachez
│   │   ├── meters.py          # CRUD sample
│   │   └── schemas.py         # Pydantic models
│   ├── models/
│   │   └── meter.py           # SQLAlchemy model
│   ├── graphql/               # (future)
│   ├── tasks/                 # (future)
│   └── telemetry.py           # (future)
├── site/                      # static demo frontend
│   ├── index.html
│   ├── pages/
│   │   └── meters.html
│   ├── assets/
│   │   ├── config.js          # window.SITE_API_BASE, window.SITE_USE_MOCK
│   │   ├── css/style.css
│   │   └── js/api.js          # calls API or mock JSON
│   └── mock/
│       └── meters.json
├── scripts/
│   ├── prestart.sh
│   └── site-serve.sh          # local static server for /site
├── docker/
│   └── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── poetry.lock
└── tests/
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

### Option B — Docker Compose (API + Postgres + Redis)
```bash
docker compose up --build
```

### With Docker Compose
```bash
docker compose up --build
```
- API → http://localhost:8000
- Postgres → localhost:5432 (from Compose)
- Redis → localhost:6379 (optional)
Compose uses your .env for configuration. For CORS with the static site, include FRONTEND_ORIGINS=http://localhost:5173.

## 🖥️ Demo Frontend (/site)
A tiny static UI to list meters and show the API status. It will call the live API if window.SITE_API_BASE is set; otherwise it can fall back to mock JSON.
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

