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
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Open [the dashboard](http://localhost:8000/site/), [Swagger UI](http://localhost:8000/docs) or [ReDoc](http://localhost:8000/redoc). SQLite is the default in `.env.example`; Redis is optional for the API. The Alembic upgrade creates the empty schema.

For synthetic data, set `DEMO_PASSWORD` to a unique password in `.env`, then run:

```bash
poetry run python -m scripts.seed_demo
```

This creates the `demo` user, two sites, six meters, tariffs and seven days of readings. Seeding leaves an existing database with users unchanged. Migrations, API startup, and the disposable initialization helper never seed automatically.

## Current architecture and features

```mermaid
flowchart LR
    Dashboard[Static HTML / Chart.js dashboard] --> API[FastAPI REST API]
    Client[Authenticated operator] --> JWT[JWT validation]
    JWT --> API
    API --> DB[(PostgreSQL or SQLite)]
    API <--> Cache[(Redis response cache)]
    API -->|enqueue + task ID| Broker[(Redis broker)]
    API -->|explicit cache warmup only| Local[Best-effort local task]
    Beat[Single Celery Beat] --> Broker
    Broker --> Worker[Celery worker]
    Worker --> DB
    Worker --> Cache
```

This diagram describes the application today. The local Compose stack runs PostgreSQL 16, Redis 7, the API, one concurrency-1 Celery worker, and one separate Beat scheduler.

- Python 3.13, FastAPI, Pydantic, SQLAlchemy 2, asyncpg/PostgreSQL and aiosqlite/SQLite; versions resolved in `poetry.lock`.
- Sites, meters, tariffs, imported/exported/reactive energy, maximum power and daily site summaries.
- Public read endpoints for the dashboard; password-verified JWT login for meter creation and operational tasks.
- Redis caching with bounded TTLs and database fallback when Redis is unavailable.
- Celery jobs for synthetic readings, KPI refresh, cache maintenance, system metrics and optional SendGrid email; Beat enables only the reviewed KPI, metrics and cache-clean schedules.
- Private Prometheus metrics on TCP 9090, optional OpenTelemetry instrumentation, and role-labelled Loguru output.

`app/api/` contains routes and schemas, `app/models/` the database mappings, `app/core/` configuration and infrastructure, and `app/tasks/` background work. `scripts/` contains database initialization and seeding; `site/` contains the static dashboard. Tests live in `tests/`.

Durable HTTP task endpoints enqueue Celery messages and return a task ID. A `202` means accepted by the broker, not completed. Explicit cache warmup remains best-effort work in the API process. Database migration, demo seeding and PostgreSQL backup are not task API operations.

The runtime separates the API, concurrency-1 Celery worker, and single Celery Beat scheduler. The production Kustomize package also defines a release migration Job; PostgreSQL, Redis, and backup resources remain Stage 5 work. See the [architecture and deployment decisions](docs/architecture-deployment-decisions.md) for the stable design record.

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
| `DEMO_PASSWORD` | Password used only by the explicit demo seed command. Never use a shared default password. |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Worker Redis URLs; each falls back to `REDIS_URL`. |
| `API_HOST`, `API_PORT` | Address used by explicit best-effort cache warmup. |
| `METRICS_HOST`, `METRICS_PORT` | Private Prometheus listener, `0.0.0.0:9090`. |
| `ENABLE_API_DOCS` | Enables Swagger, ReDoc, and OpenAPI JSON; default `true`, set to `0` in the production overlay. |
| `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `HEALTH_EMAIL_TO` | Optional health email; use a verified sender and a restricted key. |
| `ENV` | Application environment, default `dev`. |
| `PORT`, `ROLE` | Container startup: HTTP port (default `8000`) and `web`, `worker`, or `beat`. |
| `LOG_LEVEL`, `ENABLE_TELEMETRY` | Process environment only: default `INFO`, `0`. |
| `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS` | Process environment only; optional telemetry export configuration. |

Direct `uvicorn` commands set their bind address/port through CLI options. Telemetry with no endpoint uses console traces; a configured OTLP endpoint is passed to both trace and metric exporters, so verify collector routing before enabling remote export.

## Database setup

Alembic owns the schema lifecycle for SQLite and PostgreSQL:

```bash
poetry run alembic upgrade head
poetry run alembic current
poetry run alembic history
poetry run alembic heads
poetry run alembic check  # detect model changes without a migration
```

`scripts/init_db.py` remains an explicit `create_all` helper for a new disposable local SQLite database. It rejects PostgreSQL and does not evolve existing tables or seed data. Normal container startup performs no schema DDL.

For a database created before Alembic, back it up and validate it before stamping:

```bash
poetry run python -m scripts.adopt_legacy_schema
poetry run python -m scripts.adopt_legacy_schema --stamp
```

The first command is read-only. The second repeats validation and stamps `head` only when tables, columns, types, nullability, primary keys, expected unique constraints, indexes, and foreign keys match the baseline. An incompatible or unknown schema is not stamped.

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
| `GET /api/health/z`, `/api/health/cachez` | Public process/cache status. Cache failure is reported in JSON with HTTP 200. |
| `GET /api/health/readyz` | Database readiness. A bounded `SELECT 1` returns 200 when ready and 503 when unavailable; Redis is not a readiness dependency. |
| `POST /api/auth/login`, `GET /api/auth/me` | Password login / authenticated user. |
| `GET /api/sites/`, `/api/meters/`, `/api/meters/{id}` | Public site and meter data. |
| `POST /api/meters/` | Authenticated meter creation. |
| `GET /api/energy_imported/`, `/api/energy_exported/`, `/api/energy_reactive/`, `/api/max_power/` | Public readings; optional `meter_id` filter. |
| `GET /api/tariffs/` | Public tariffs; optional `site_id` filter. |
| `GET /api/system_metrics/`, `/api/system_metrics/latest` | Public recorded system measurements; access changes are deferred because the dashboard currently reads them. |
| `GET :9090/metrics` | Private Prometheus exposition on the separate metrics listener. `/api/metrics` does not exist. |
| `POST /api/tasks/*` | Authenticated actions. Durable operations return `202`, an operation name and Celery task ID. Cache warmup is explicitly best-effort. |
| `GET /api/tasks/{task_id}` | Authenticated bounded task state: `PENDING`, `STARTED`, `SUCCESS`, or `FAILURE`; results and tracebacks are not returned. |

OpenAPI is available at `/openapi.json`. All authenticated users currently share operator privileges; there is no tenant isolation or role hierarchy. Read endpoints intentionally expose demo data publicly.

## Caching

Sites, meters and energy reads use 60-second TTLs; maximum power uses 120 seconds and tariffs 300 seconds. Keys include the request path and query string. Cache misses query the database; responses are encoded as JSON before storage. Redis errors fall back to database reads.

Writes do not invalidate cached reads immediately: data can remain stale until its TTL expires. The authenticated `/api/tasks/cache/clean` action durably enqueues deletion of `cache:*` keys. Explicit cache warmup remains API-local and best-effort; it is not scheduled by Beat. Redis remains necessary for the Celery broker even though it is optional for API reads.

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

Tests use a temporary SQLite database and safe configuration set before application imports. They cover routes, password/token behavior, protected writes, cache keys/serialization, initialization, tasks and failure paths. External email is mocked. Service-backed Redis tests skip unless their test URLs are supplied. The Celery integration test uses separate logical Redis databases for broker and results and a real worker:

```bash
TEST_REDIS_URL=redis://127.0.0.1:6379/15 poetry run pytest
TEST_CELERY_BROKER_URL=redis://127.0.0.1:6379/14 \
TEST_CELERY_RESULT_URL=redis://127.0.0.1:6379/15 \
poetry run pytest tests/integration/test_celery_runtime.py -m celery
```

GitHub Actions runs lint, formatting, mypy, tests with coverage artifacts, and service-backed PostgreSQL and Celery integration checks. It then validates the runtime image and, for a push to `main`, can publish an immutable full-commit-SHA image to GHCR with its digest, SBOM, and provenance. It needs no Codecov token. Coverage is reported, with no claimed percentage or enforced threshold.

## Docker

Docker Engine and the Compose plugin are required. Create `.env` and generate `JWT_SECRET` as in the quick start. Compose supplies its own PostgreSQL/Redis addresses; it does not reuse the SQLite URL from `.env`.

```bash
docker compose up --build -d
docker compose ps
curl --fail http://localhost:8000/api/health/z
docker compose logs --tail=50 api worker beat
docker compose down
```

Compose starts PostgreSQL 16, runs `alembic upgrade head` as a one-shot migration service, then starts Redis, the API, a concurrency-1 Celery worker, and one Beat scheduler. Application and metrics ports bind to localhost. Worker and Beat wait for PostgreSQL migration and Redis health without depending on the API. Do not use these database defaults on a public host.

An existing pre-Alembic Compose volume must be backed up, validated, and stamped with `scripts.adopt_legacy_schema` before the migration service can manage it. Do not delete an existing volume merely to bypass validation.

For a standalone SQLite container:

```bash
docker build -f docker/Dockerfile -t smartenergy-api:local .
docker run --rm --name smartenergy-sqlite -p 127.0.0.1:8000:8000 \
  -p 127.0.0.1:9090:9090 \
  --env-file .env smartenergy-api:local
```

The digest-pinned multi-stage image runs as UID/GID 10001 and contains no compiler, Poetry, or PostgreSQL client. The same artifact runs the API, worker, Beat, and explicit Alembic migrations. In `ENV=prod`, all roles log structured JSON to stdout/stderr and create no log directory. Beat keeps non-authoritative schedule state under `/tmp`, so the hosted roles support a read-only root filesystem with writable temporary storage. Local SQLite data and manually requested SQLite snapshots remain development-only. `docker compose down` preserves PostgreSQL data; adding `-v` deletes it.

The approved Stage 3 publication is `ghcr.io/etclank/smartenergy-api:1cbe7dd0991b1495dfabdd08a69a00755c5961aa`, and the production package consumes it as `ghcr.io/etclank/smartenergy-api@sha256:7a35d14461bd6ee81bf67cf09bef792c866ad7673add9077e7b770e5fff99792`. The package is public and has registry SBOM and provenance attestations.

## VM and Kubernetes deployment

The same image can run on a Docker VM or a Kubernetes cluster. The dashboard is served by the API; it does not need a separate frontend deployment.

- [Deployment guide](docs/deployment.md): image delivery, private dependencies, secrets, TLS, validation and rollback.
- [Architecture decisions](docs/architecture-deployment-decisions.md): approved hosted design and conditions for revisiting it.
- [`deploy/compose.vm.yml`](deploy/compose.vm.yml): runtime-only VM configuration with an optional worker profile, a read-only filesystem and localhost HTTP binding.
- [`deploy/kubernetes/base`](deploy/kubernetes/base): API, worker, Beat, migration, Service, and NetworkPolicy resources.
- [`deploy/kubernetes/overlays/production`](deploy/kubernetes/overlays/production): digest-pinned production configuration, Ingress, Certificate, and Traefik middleware.
- [Limitations](#limitations): current application and reliability boundaries.

PostgreSQL and Redis are provisioned separately; these runtime examples do not create database storage or backups. The existing root `docker-compose.yml` remains the local development stack.

SmartEnergy is ready for later onboarding to the Cloud-Native Service Control Plane through its GitOps/Kustomize application route. The application-owned production package is implemented, but PostgreSQL, Redis, backups, the Project 1 `Application/smartenergy`, DNS, and live deployment are still pending. No SmartEnergy workload is deployed. Render it with `kubectl kustomize deploy/kubernetes/overlays/production`.

## Limitations

This project remains a demonstration application:

- The production Ingress has a modest edge rate limit, but the application has no per-user rate limiting, token revocation, or tenant isolation.
- No zero-downtime multi-version migration guarantee, broad pagination or concurrency guarantees for scheduled aggregates/seeding. Run one Beat scheduler.
- Celery uses late acknowledgements, worker-lost rejection and prefetch 1. Delivery remains at-least-once-like and duplicate execution is possible; exactly-once is not claimed. Broad retries and arbitrary task time limits are intentionally absent.
- The snapshot task supports local SQLite file copies only; it is not a consistent online-backup solution and does not back up PostgreSQL. Configure provider backups separately.
- Recorded system metrics remain public for the current dashboard, while Prometheus metrics are private on TCP 9090. Metrics persistence failures can be tolerated silently; do not treat them as an availability guarantee.
- Some tests share fixture data; deprecation warnings remain in the existing date/time and client code. Managed-service integration and load testing are outside the unit suite.
- Dependencies are locked for reproducibility; that is not a vulnerability-free guarantee. Update and audit them before deployment.

Keep runtime credentials outside Git and container images. Use private database/cache access, rotate credentials through the deployment environment, and keep registry credentials scoped to image pulls.

The editable database diagram sources are [`docs/db-diagram.drawio`](docs/db-diagram.drawio) and [`docs/db-diagram.xml`](docs/db-diagram.xml). Both are retained because the repository does not identify either distinct representation as generated or obsolete.

## License

[MIT](LICENSE). Vendored chart libraries retain their upstream license notices.
