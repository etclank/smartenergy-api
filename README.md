# SmartEnergy API & Dashboard

A backend/data application built with FastAPI, PostgreSQL and Redis, featuring asynchronous SQLAlchemy, JWT authentication, response caching, automated tests, Docker support and a small dashboard backed by API data.

The project demonstrates a smart-meter data model and the flow from stored readings to API responses, charts and scheduled summaries. Demo readings are synthetic; this is a portfolio application, not a production energy-management service.

## Quick start

Requires Python 3.13 and Poetry 2.2.1. Run commands from the repository root.

```bash
poetry install
cp .env.example .env
# Generate a local signing secret without printing it:
poetry run python -c 'import secrets; from pathlib import Path; p=Path(".env"); p.write_text(p.read_text().replace("JWT_SECRET=", "JWT_SECRET=" + secrets.token_urlsafe(48), 1))'
poetry run python -m scripts.init_db
poetry run uvicorn app.main:app --reload
```

Open [the dashboard](http://localhost:8000/site/), [Swagger UI](http://localhost:8000/docs) or [ReDoc](http://localhost:8000/redoc). SQLite is the default in `.env.example`; Redis is optional for the API. The first run creates empty tables.

For synthetic data, set `DEMO_PASSWORD` to a unique password in `.env`, then run:

```bash
poetry run python -m scripts.seed_demo
```

This creates the `demo` user, two sites, six meters, tariffs and seven days of readings. Seeding leaves an existing database with users unchanged. `SEED_DEMO=1` optionally seeds during initialization; the default is off.

## Current architecture and features

```mermaid
flowchart LR
    Dashboard[Static HTML / Chart.js dashboard] --> API[FastAPI REST API]
    Client[Authenticated operator] --> JWT[JWT validation]
    JWT --> API
    API --> DB[(PostgreSQL or SQLite)]
    API <--> Cache[(Redis response cache)]
    API --> Tasks[In-process background tasks]
    Tasks --> DB
    Beat[Celery Beat] --> Broker[(Redis broker)]
    Broker --> Worker[Celery worker]
    Worker --> DB
    Worker --> Cache
```

This diagram describes the application today. The local Compose stack runs PostgreSQL 16, Redis 7, the API, and one Celery worker that also runs Beat. Direct HTTP task requests still use FastAPI `BackgroundTasks` inside the API process.

- Python 3.13, FastAPI, Pydantic, SQLAlchemy 2, asyncpg/PostgreSQL and aiosqlite/SQLite; versions resolved in `poetry.lock`.
- Sites, meters, tariffs, imported/exported/reactive energy, maximum power and daily site summaries.
- Public read endpoints for the dashboard; password-verified JWT login for meter creation and operational tasks.
- Redis caching with bounded TTLs and database fallback when Redis is unavailable.
- Celery/Beat jobs for synthetic readings, KPI refresh, cache maintenance, system metrics and optional SendGrid email.
- Prometheus metrics, optional OpenTelemetry instrumentation, and Loguru console/file logs.

`app/api/` contains routes and schemas, `app/models/` the database mappings, `app/core/` configuration and infrastructure, and `app/tasks/` background work. `scripts/` contains database initialization and seeding; `site/` contains the static dashboard. Tests live in `tests/`.

HTTP task endpoints use FastAPI `BackgroundTasks` in the API process. They do **not** enqueue Celery messages. Celery Beat separately schedules the same task implementations. A `202` response confirms scheduling, not successful completion.

The planned hosted architecture separates the API, Celery worker, and the single Celery Beat scheduler. It also adds a migration Job, backup CronJob, PostgreSQL and Redis StatefulSets, and a private Prometheus listener on TCP 9090. These are approved design targets, not current behavior. See the [architecture and deployment decisions](docs/architecture-deployment-decisions.md) for the stable design record.

## Configuration

Settings read process environment first, then `.env`. Real environment files, logs, backups and database files are ignored by Git and excluded from Docker builds.

| Variable | Purpose / default |
| --- | --- |
| `DATABASE_URL` | Required async SQLAlchemy URL. SQLite example in `.env.example`; PostgreSQL uses `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE`. |
| `JWT_SECRET` | Required signing secret; generate a random value. Production requires at least 32 characters. |
| `JWT_ALG`, `JWT_EXPIRE_MINUTES` | Signing algorithm and token lifetime; `HS256`, `60`. |
| `REDIS_URL` | Optional cache URL; blank disables API caching. Keep Redis private. |
| `CACHE_TTL_SECONDS` | Positive default TTL, `60`; route-specific TTLs override it. |
| `FRONTEND_ORIGINS` | JSON array of allowed origins; default `[]` (same-origin dashboard needs no CORS). |
| `SEED_DEMO`, `DEMO_PASSWORD` | Opt-in seeding and chosen demo-user password. Never use a shared default password. |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Worker Redis URLs; each falls back to `REDIS_URL`. |
| `API_HOST`, `API_PORT` | Address used by task cache warmup. Set to the API service from a separate worker. |
| `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `HEALTH_EMAIL_TO` | Optional health email; use a verified sender and a restricted key. |
| `ENV` | Application environment, default `dev`. |
| `PORT`, `ROLE` | Container startup: HTTP port (default `8000`) and `web` or `worker`. |
| `LOG_LEVEL`, `ENABLE_TELEMETRY` | Process environment only: default `INFO`, `0`. |
| `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS` | Process environment only; optional telemetry export configuration. |

Direct `uvicorn` commands set their bind address/port through CLI options. Telemetry with no endpoint uses console traces; a configured OTLP endpoint is passed to both trace and metric exporters, so verify collector routing before enabling remote export.

## Database setup

```bash
poetry run python -m scripts.init_db
```

Initialization creates missing tables with SQLAlchemy `create_all`, adds three legacy telemetry columns with direct `ALTER TABLE` statements when needed, and optionally seeds demo data. This remains suitable for local or disposable environments only. There is **no versioned migration framework**: `create_all` does not migrate arbitrary existing schemas.

Before persistent PostgreSQL deployment, the hosted path will become Alembic migrations run by a dedicated migration Job, followed by API startup without DDL. That lifecycle is planned but not implemented.

Sessions are scoped to requests, and short-lived background-task engines are disposed after use. Tariff reads eagerly load related sites. Most list endpoints are unpaginated and are intended for small demo datasets.

## Authentication and API

Login accepts JSON and checks the stored bcrypt password hash:

```bash
curl --fail-with-body http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"YOUR_CHOSEN_DEMO_PASSWORD"}'
```

Use the returned token as `Authorization: Bearer <token>`. There is no public registration endpoint. Swagger documents the JSON login route; its OAuth password dialog is not a form-based login implementation.

| Endpoint | Access / behavior |
| --- | --- |
| `GET /api/health/z`, `/api/health/cachez` | Public process/cache status. Cache failure is reported in JSON with HTTP 200; these are not database readiness probes. |
| `POST /api/auth/login`, `GET /api/auth/me` | Password login / authenticated user. |
| `GET /api/sites/`, `/api/meters/`, `/api/meters/{id}` | Public site and meter data. |
| `POST /api/meters/` | Authenticated meter creation. |
| `GET /api/energy_imported/`, `/api/energy_exported/`, `/api/energy_reactive/`, `/api/max_power/` | Public readings; optional `meter_id` filter. |
| `GET /api/tariffs/` | Public tariffs; optional `site_id` filter. |
| `GET /api/system_metrics/`, `/api/system_metrics/latest` | Public recorded system measurements. |
| `GET /api/metrics` | Prometheus exposition. |
| `POST /api/tasks/*` | Authenticated operational actions; inspect `/docs` for all routes. |

OpenAPI is available at `/openapi.json`. All authenticated users currently share operator privileges; there is no tenant isolation or role hierarchy. Read endpoints intentionally expose demo data publicly.

## Caching

Sites, meters and energy reads use 60-second TTLs; maximum power uses 120 seconds and tariffs 300 seconds. Keys include the request path and query string. Cache misses query the database; responses are encoded as JSON before storage. Redis errors fall back to database reads.

Writes do not invalidate cached reads immediately: data can remain stale until its TTL expires. The authenticated `/api/tasks/cache/clean` action clears `cache:*` keys, and warmup requests common read routes. Redis remains necessary for the Celery broker even though it is optional for API reads.

## Dashboard

The API serves the dashboard at `/site/`. `site/assets/config.js` defaults to the same-origin `/api`; the landing-page API base setting is stored in browser local storage and overrides that default. An external API base must include `/api`, for example `http://localhost:8000/api`.

For a separate static server:

```bash
bash scripts/site-serve.sh
# Open http://localhost:5173/site/
```

Set the dashboard API base to `http://localhost:8000/api` and `FRONTEND_ORIGINS` to `["http://localhost:5173"]` in the API environment, then restart the API. The script serves only `/site/` paths. `?mock=1` supports the meter-list fixture; it is not a complete offline dashboard. Chart timestamps reflect stored readings without artificial date shifts.

## Tests and CI

```bash
poetry run pytest
poetry run pytest --cov=app --cov-branch --cov-report=term-missing
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy --config-file mypy.ini app
# Optional dashboard regression smoke (Node.js 18+):
node tests/dashboard_smoke.cjs
```

Tests use a temporary SQLite database and safe configuration set before application imports. They cover routes, password/token behavior, protected writes, cache keys/serialization, initialization, tasks and failure paths. External email is mocked. The optional Redis integration test skips unless `TEST_REDIS_URL` points to a disposable test Redis instance:

```bash
TEST_REDIS_URL=redis://127.0.0.1:6379/15 poetry run pytest
```

GitHub Actions runs lint, formatting, mypy, tests with coverage artifacts and a Docker build. It needs no Codecov token. Coverage is reported, with no claimed percentage or enforced threshold. SQLite tests do not establish full PostgreSQL or managed-service compatibility.

## Docker

Docker Engine and the Compose plugin are required. Create `.env` and generate `JWT_SECRET` as in the quick start. Compose supplies its own PostgreSQL/Redis addresses; it does not reuse the SQLite URL from `.env`.

```bash
docker compose up --build -d
docker compose ps
curl --fail http://localhost:8000/api/health/z
docker compose logs --tail=50 api worker
docker compose down
```

Compose starts PostgreSQL 16, Redis 7, the API, and a Celery worker with Beat. Ports bind to localhost. PostgreSQL has a named persistent volume and local-only development credentials. The worker waits for API initialization/health. Do not use these database defaults on a public host.

For a standalone SQLite container:

```bash
docker build -f docker/Dockerfile -t smartenergy-api:local .
docker run --rm --name smartenergy-sqlite -p 127.0.0.1:8000:8000 \
  --env-file .env smartenergy-api:local
```

The image runs as a non-root user. SQLite data, logs, Beat state and file snapshots inside a container are ephemeral unless you mount writable storage owned by UID 10001. `docker compose down` preserves PostgreSQL data; adding `-v` deletes it.

## VM and Kubernetes deployment

The same image can run on a Docker VM or a Kubernetes cluster. The dashboard is served by the API; it does not need a separate frontend deployment.

- [Deployment guide](docs/deployment.md): image delivery, private dependencies, secrets, TLS, validation and rollback.
- [Architecture decisions](docs/architecture-deployment-decisions.md): approved hosted design and conditions for revisiting it.
- [`deploy/compose.vm.yml`](deploy/compose.vm.yml): runtime-only VM configuration with an optional worker profile, a read-only filesystem and localhost HTTP binding.
- [`deploy/kubernetes/`](deploy/kubernetes/): current Kustomize starter for one API replica and a private ClusterIP Service. It is not the final production package.
- `deploy/kubernetes/overlays/production`: planned production overlay path; it does not exist yet.
- [Limitations](#limitations): current application and reliability boundaries.

PostgreSQL and Redis are provisioned separately; these runtime examples do not create database storage or backups. The existing root `docker-compose.yml` remains the local development stack.

SmartEnergy is intended for onboarding to the Cloud-Native Service Control Plane through its GitOps/Kustomize application route. The platform already reserves the `smartenergy` namespace and AppProject, but `Application/smartenergy` does not exist and no SmartEnergy workload is deployed. Review capacity and data persistence before adding it to the small single-node cluster. The starter does not enable OTLP export or add Prometheus targets.

## Limitations

This project remains a demonstration application:

- No rate limiting, token revocation, tenant isolation or durable HTTP task queue. Restrict deployment access and use HTTPS before handling non-demo data.
- No full migration lifecycle, broad pagination or concurrency guarantees for scheduled aggregates/seeding. Run one Beat scheduler.
- Celery has no `acks_late`, worker-lost rejection, explicit retry or prefetch policy, or task time limits. It does not claim exactly-once or guaranteed delivery.
- The snapshot task supports local SQLite file copies only; it is not a consistent online-backup solution and does not back up PostgreSQL. Configure provider backups separately.
- Health/system metrics are public, and metrics persistence failures can be tolerated silently. Do not treat them as an availability guarantee.
- Some tests share fixture data; deprecation warnings remain in the existing date/time and client code. Managed-service integration and load testing are outside the unit suite.
- Dependencies are locked for reproducibility; that is not a vulnerability-free guarantee. Update and audit them before deployment.

Keep runtime credentials outside Git and container images. Use private database/cache access, rotate credentials through the deployment environment, and keep registry credentials scoped to image pulls.

The editable database diagram sources are [`docs/db-diagram.drawio`](docs/db-diagram.drawio) and [`docs/db-diagram.xml`](docs/db-diagram.xml). Both are retained because the repository does not identify either distinct representation as generated or obsolete.

## License

[MIT](LICENSE). Vendored chart libraries retain their upstream license notices.
