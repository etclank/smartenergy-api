# Project 1 – smartenergy-api
## 1 · Purpose & elevator pitch
A production-grade backend that ingests “smart-meter” energy readings, exposes them via REST, GraphQL, and WebSocket real-time feeds, and kicks off background analytics jobs.
It demonstrates modern Python, async I/O, background processing, observability, and Azure-native deployment.

## 2 · Tech stack (locked to 2025 stable versions)
| Layer              | Choice                                                                                                                                   | Notes                       |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| Runtime            | **Python 3.13**                                                                                                                          | asdf-managed                |
| Web framework      | **FastAPI 0.115 +** ([github.com][1])                                                                                                    | OpenAPI docs auto-generated |
| GraphQL            | **Strawberry 0.273 +** ([github.com][2])                                                                                                 | Single endpoint `/graphql`  |
| DB                 | **Azure Database for PostgreSQL Flexible Server 15** (General-Purpose tier) ([learn.microsoft.com][3], [learn.microsoft.com][4])         | Async SQLAlchemy 2 ORM      |
| Cache & queues     | **Azure Cache for Redis Enterprise 7** (in dev: Docker Redis)                                                                            |                             |
| Background workers | Celery (**Redis broker**) + optional Dramatiq (feature flag)                                                                             |                             |
| Auth               | JWT (PyJWT) with Azure AD B2C compatibility hook                                                                                         |                             |
| Observability      | OpenTelemetry Python SDK → Azure Monitor & **Application Insights**                                                                      |                             |
| Containers         | Multi-arch Buildx → **Azure Container Registry**                                                                                         |                             |
| Orchestration      | **Azure Kubernetes Service** (AKS) via Helm chart                                                                                        |                             |
| CI/CD              | GitHub Actions → OIDC deploy to ACR + AKS; preview envs in **Azure Container Apps** ([azure.microsoft.com][5], [azure.microsoft.com][6]) |                             |

[1]: https://github.com/fastapi/fastapi/releases?utm_source=chatgpt.com "Releases · fastapi/fastapi - GitHub"
[2]: https://github.com/strawberry-graphql/strawberry/releases?utm_source=chatgpt.com "Releases · strawberry-graphql/strawberry - GitHub"
[3]: https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-compute?utm_source=chatgpt.com "Compute options - Azure Database for PostgreSQL flexible server"
[4]: https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/overview?utm_source=chatgpt.com "What Is Azure Database for PostgreSQL Flexible Server?"
[5]: https://azure.microsoft.com/en-us/products/container-apps?utm_source=chatgpt.com "Azure Container Apps"
[6]: https://azure.microsoft.com/updates?id=492133&utm_source=chatgpt.com "Azure updates | Microsoft Azure"

## 3 · High-level architecture
```bash
┌─────────────┐   HTTP / WS   ┌──────────────┐
│ React/PWA   │◀─────────────▶│ FastAPI REST │
└─────────────┘               │  + GraphQL   │
          ▲                   └──────┬───────┘
          │  pub/sub (Redis)         │async SQLAlchemy
┌─────────┴──────┐           ┌───────▼─────────┐
│ Background     │           │ PostgreSQL 15   │
│  Worker Pool   │           └─────────────────┘
└──────┬─────────┘                  ▲
       │ OTEL                       │ Change data capture (future)
┌──────▼─────────┐           ┌──────┴─────────┐
│ Azure Monitor  │◀──────────┤  OpenTelemetry │
└────────────────┘           └────────────────┘
```
(Final repo will include a Mermaid/PlantUML source + PNG.)

## 4 · Functional scope
| Epic                  | End-points / Tasks                                                        | Done-when                          |
| --------------------- | ------------------------------------------------------------------------- | ---------------------------------- |
| **Meter CRUD**        | `GET /meters`, `POST /meters`, `GET /meters/{id}`                         | unit + integration tests pass      |
| **Readings ingest**   | `POST /readings` bulk & single; GraphQL mutation `addReading`             | handles 5 k req/s in k6 test       |
| **Query feeds**       | GraphQL query `latestReadings(meterId)`; WS topic `/ws/stream/{meterId}`  | < 200 ms p99 latency locally       |
| **Background jobs**   | Celery task `compute_daily_stats(meter_id, date)`                         | Redis/Queue metrics exported       |
| **Auth & rate-limit** | JWT bearer; 100 req/min per user via FastAPI-Limiter                      | returns RFC 6586 errors            |
| **Observability**     | OTEL traces & Prom metrics visible in Azure Portal dashboard              | Grafana panel screenshot in README |
| **Docs & SDK**        | Auto-generated OpenAPI; `npx openapi-typescript` script to emit TS client | README badge links to docs site    |

## 5 · Non-functional requirements
- Performance: sustain 5 k rps ingest, 50 ms p95 DB latency, 0 data loss in Redis.
- Security: OWASP ASVS L1; CodeQL & Trivy scans block PR merge on critical.
- Portability: docker compose up works on macOS (Apple silicon) & CI amd64.
- Reliability: 99.5 % uptime SLO in AKS; readiness/liveness probes for all pods.
- Cost ceiling (dev): ≤ $50 / month using Azure Postgres Burstable tier + free Redis dev cache.

## 6 · Directory outline
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
│   ├── config.py              # pydantic-settings: DB/Redis/JWT/ENV flags
│   ├── db.py                  # async SQLAlchemy engine/session for Postgres
│   ├── deps.py                # FastAPI Depends (db session, auth)
│   ├── security.py            # JWT utils (create/verify tokens), password hashing
│   ├── cache.py               # Redis client + helpers
│   ├── api/
│   │   ├── routers.py         # include_router here
│   │   ├── auth.py            # /auth/login (JWT), /auth/refresh (optional)
│   │   ├── health.py          # /healthz (public), /readyz, /metrics (optional)
│   │   ├── meters.py          # sample resource; GET uses Redis cache
│   │   └── schemas.py         # Pydantic models (Meter, Auth tokens, etc.)
│   ├── models/
│   │   └── meter.py           # SQLAlchemy models (Meter)
│   ├── tasks/                 # (optional) background tasks
│   └── telemetry.py           # (optional) OTEL hooks
├── chart/                     # (optional) Helm, keep as-is for later
│   └── templates/
├── docker/
│   └── Dockerfile
├── docker-compose.yml         # dev: api+postgres+redis
├── pyproject.toml
├── poetry.lock
└── tests/
    ├── test_health.py
    ├── test_auth.py
    └── test_meters.py
```

## 7 · CI/CD flow
1. Push / PR
- test.yml – matrix (ubuntu-22.04, macos-14) → Ruff, mypy, pytest, coverage.
- Build multi-arch image, push to temporary ACR repo.
2. Merge to main
- deploy-aks.yml – OIDC login to Azure, helm upgrade smartenergy-api in AKS dev namespace.
- Tag vX.Y.Z triggers GitHub Release; semantic-release updates changelog.
3. Preview environments
- Each PR auto-deploys to Azure Container Apps with {pr-number} suffix hostname; comment bot posts URL.

## 8 · Definition of Done checklist All epics complete & tested (≥ 90 % coverage).
- [ ] Helm chart passes helm lint and deploys cleanly to AKS dev cluster.
- [ ] README: elevator pitch, quick-start, architecture diagram, badges (build, codecov, container size, release).
- [ ] Loom / GIF demo linked at top of README (< 90 s).
- [ ] Cost sheet (docs/cost.md) listing dev/prod Azure SKUs & monthly estimate.
- [ ] v1.0.0 GitHub Release with SBOM (Syft) attached.

## 9 · Suggested first 10 daily tasks (≈ 2 weeks)
| Day | 1-hour task                                                                       |
| --- | --------------------------------------------------------------------------------- |
| D1  | Create repo, add `.tool-versions`, initialise Poetry / Pip-tools.                 |
| D2  | Scaffold `main.py`, health check route, run locally.                              |
| D3  | Write multi-stage Dockerfile, `docker compose up` with Postgres & Redis services. |
| D4  | Add GitHub Action `test.yml` with pytest boilerplate.                             |
| D5  | Push initial commit; ensure CI badge green.                                       |
| D6  | Design DB schema (Meter, Reading) in SQLModel / SQLAlchemy; alembic revision.     |
| D7  | Implement CRUD router `/meters`; unit tests.                                      |
| D8  | Add Strawberry GraphQL schema & playground; query `meters`.                       |
| D9  | Configure OTEL exporter → stdout; view traces in Jaeger docker.                   |
| D10 | Draft README skeleton + architecture Mermaid diagram.                             |
