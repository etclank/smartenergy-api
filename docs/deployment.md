# Deploying SmartEnergy

SmartEnergy is not deployed to the Cloud-Native Service Control Plane. This document separates the repository's current deployment helpers from the approved hosted design. The design provides production-like deployment controls for a portfolio application while remaining deliberately single-node and non-HA.

The [architecture decision record](architecture-deployment-decisions.md) is the stable reference for the approved choices. The root [README](../README.md) remains the application and local-development guide.

## Current deployment assets

The repository currently provides:

- a local Compose stack with PostgreSQL 16, a one-shot Alembic migration service, Redis 7, the API, a concurrency-1 Celery worker, and a separate Beat scheduler;
- a runtime-only VM Compose file with optional separate worker and Beat services;
- one application image used by the API, worker, and Beat;
- a Kubernetes starter containing one API Deployment and ClusterIP Service;
- CI validation that builds, but does not publish, the image.

[`deploy/kubernetes/`](../deploy/kubernetes/) is a starter. It is not a complete production package and does not contain PostgreSQL, Redis, worker, Beat, migrations, backups, ingress, certificates, middleware, or NetworkPolicies. It will later evolve into a base and `deploy/kubernetes/overlays/production` structure. No files have been moved yet.

## Project 1 hosting contract

The completed platform contract reserves:

| Item | Value |
| --- | --- |
| Namespace | `smartenergy` |
| Argo CD AppProject | `smartenergy` |
| Public host | `energy.platform.eoghanclancy.eu` |
| Delivery | Manual Argo sync |
| Source revision | Full Git commit pin |
| Image reference | Immutable registry digest |

`Application/smartenergy` does not exist. No SmartEnergy workload is deployed. The application repository will own its production Kustomize package and namespaced runtime resources; Project 1 will later add the Argo Application and private Prometheus integration.

The intended image is public `ghcr.io/etclank/smartenergy-api`, published with a full commit-SHA tag and deployed by digest. Current CI does not publish this package.

Runtime Secret values remain outside Git. At minimum, the hosted application will require a private PostgreSQL `DATABASE_URL`, a newly generated `JWT_SECRET` of at least 32 characters, and authenticated Redis URLs for cache, broker, and result roles. Automatic seeding and OpenTelemetry export remain disabled initially. The application repository may reference a Secret by name but does not own its values.

## Current and target runtime roles

The local and VM Compose definitions run API, worker, and Beat as separate processes. Exactly one Beat process is a deployment invariant.

The hosted design will use:

| Role | Responsibility |
| --- | --- |
| API Deployment | FastAPI, dashboard, public HTTP on TCP 8000 |
| Worker Deployment | Celery task execution, concurrency 1 initially |
| Beat Deployment | Exactly one scheduler with an independent lifecycle |
| Migration Job | Versioned schema upgrades before application rollout |
| Backup CronJob | Daily PostgreSQL logical backup and off-node upload |

Beat stores non-authoritative schedule state at `/tmp/celerybeat-schedule`; it does not require a persistent volume.

## Schema lifecycle

Alembic now owns schema evolution. The API startup script starts Uvicorn without `create_all`, direct DDL, migrations, or seeding. `scripts/init_db.py` remains an explicit helper that creates the current schema only for a new disposable local SQLite database; it rejects PostgreSQL and does not evolve existing tables or seed data.

The hosted lifecycle will be:

```text
database available
→ dedicated migration step runs `alembic upgrade head`
→ API, worker, and Beat start without schema DDL
```

The migration command is implemented. Its future Kubernetes Job is not. Useful inspection and drift commands are:

```bash
poetry run alembic current
poetry run alembic history
poetry run alembic heads
poetry run alembic check
```

For a pre-Alembic database, back up first, then run the guarded adoption command:

```bash
poetry run python -m scripts.adopt_legacy_schema
poetry run python -m scripts.adopt_legacy_schema --stamp
```

The command refuses to stamp when the existing schema differs from the baseline. Never use a blind `alembic stamp head` against an unknown database.

The baseline has a mechanical downgrade for disposable testing, but production rollback does not promise destructive downgrades. Future changes should use expand-and-contract compatibility, a forward fix, or a validated backup restore.

## Health and metrics contract

`/api/health/z` reports process and Redis state with HTTP 200 and remains suitable for liveness. `/api/health/cachez` is informational. `/api/health/readyz` performs a PostgreSQL-compatible `SELECT 1` with a two-second bound and returns HTTP 503 without connection details when the database is unavailable.

The probe contract is:

- liveness: process health;
- readiness: a bounded PostgreSQL `SELECT 1`, returning HTTP 503 on failure;
- Redis: informational health only, because API reads fall back to PostgreSQL.

Application HTTP remains on TCP 8000. The API process starts and stops a separate Prometheus listener on TCP 9090 with its FastAPI lifespan. `/api/metrics` no longer exists. The later Service may expose 9090 privately, but Ingress must not route it.

## Logging and writable paths

Local development retains readable console and file output. With `ENV=prod`, API, worker, and Beat emit role-labelled structured JSON to stdout/stderr and never create `/app/logs`. Beat writes only its ephemeral state under `/tmp`; hosted roles do not create SQLite or backup files during normal operation.

PostgreSQL and Redis require their own persistent data mounts. The exact image UIDs, security contexts, and writable paths must be validated under the platform's restricted Pod Security Admission policy before live deployment.

## PostgreSQL and Redis targets

The PostgreSQL target is version 16, one StatefulSet replica, and an approximately 5 GiB `local-path` PVC. It is intentionally non-HA. The exact digest-pinned image and security context remain subject to restricted-PSA testing on a fresh volume.

One authenticated Redis 7 instance will minimize resource use. It will use one StatefulSet replica, AOF persistence, an approximately 1 GiB `local-path` PVC, and these logical databases:

| Logical database | Responsibility |
| --- | --- |
| DB 0 | API response cache |
| DB 1 | Celery broker |
| DB 2 | Celery result backend |

This is also intentionally non-HA. Redis loss degrades API caching but affects Celery delivery and result handling more directly.

## Backup and restore

The current task only copies local SQLite files. For PostgreSQL it returns `skip`; it is not a PostgreSQL backup.

The hosted backup contract is:

- `pg_dump -Fc` daily;
- upload to off-node storage;
- retain seven daily and four weekly recovery points;
- use `concurrencyPolicy: Forbid`;
- report failures through Kubernetes Job status;
- validate `pg_restore` into a disposable database before closeout.

The destination, credentials, compatible PostgreSQL client image, CronJob, and restore runbook will be implemented later.

## Public exposure target

The initial hosted public surface will contain:

- `/` and `/site/`;
- login at `/api/auth/login`;
- intended demo-data read APIs;
- a minimal health endpoint.

The following will be private or disabled initially:

- Prometheus metrics;
- recorded system metrics;
- Swagger UI;
- ReDoc;
- OpenAPI JSON.

Prometheus metrics are now separated onto TCP 9090. Recorded system metrics remain public because the current dashboard reads them; changing that contract is deferred to a later API/security stage. Swagger, ReDoc, and OpenAPI also remain enabled until the production HTTP surface is implemented and tested.

## Celery reliability and schedule policy

Authenticated operational endpoints for KPI refresh, demo generation/cleanup, cache cleanup, system metric recording, meta-cache update, and health email publish Celery messages. Their `202` response means accepted for asynchronous execution and contains a task ID; it does not mean completed. The authenticated status endpoint returns only `PENDING`, `STARTED`, `SUCCESS`, or `FAILURE` and never returns task results, exceptions, or tracebacks. Broker/backend failures return controlled HTTP 503 responses.

Cache warmup remains an explicit best-effort API-local action because running it in a worker would restore a worker-to-API network dependency. SQLite snapshots remain a direct local-development function and have no hosted task endpoint or schedule. Schema migrations, demo seeding, and PostgreSQL backup remain explicit deployment or administration procedures.

Celery uses late acknowledgements, rejects work when a worker is lost, tracks started tasks, and limits prefetch to one. This gives at-least-once-like behavior: a task can execute more than once after worker or broker failure. Exactly-once execution is not claimed. Broad retries and task time limits are omitted because the operations do not yet have measured duration and transient-failure contracts.

The enabled Beat schedule contains only:

- KPI refresh;
- system metrics recording;
- cache cleanup.

These schedules are disabled:

- demo generation;
- demo cleanup;
- health email;
- API cache warmup;
- obsolete SQLite backup.

Idempotency classification is:

| Operation | Classification | Initial policy |
| --- | --- | --- |
| Cache cleanup | Idempotent | Scheduled and API-triggerable |
| KPI refresh | Mostly idempotent upsert | Scheduled and API-triggerable; duplicate delivery may repeat computation |
| System metrics | Not idempotent; each run appends telemetry | Scheduled; duplicate rows are acceptable operational telemetry |
| Meta-cache update | Idempotent | API-triggerable only |
| Demo cleanup | Mostly idempotent | API-triggerable only |
| Demo generation | Not idempotent | API-triggerable only and never scheduled |
| Health email | Not idempotent | API-triggerable only and never scheduled |
| API cache warmup | Best-effort | API-local only and never scheduled |
| SQLite snapshot | Not a hosted backup | Local manual use only |

## Image delivery

The current manual example remains useful before CI publication exists:

```bash
IMAGE=ghcr.io/etclank/smartenergy-api
REVISION=$(git rev-parse HEAD)
docker build -f docker/Dockerfile \
  --label org.opencontainers.image.revision="$REVISION" \
  -t "$IMAGE:$REVISION" .
docker push "$IMAGE:$REVISION"
docker buildx imagetools inspect "$IMAGE:$REVISION"
```

Record the registry digest and use `ghcr.io/etclank/smartenergy-api@sha256:...` in the production overlay. The planned CI path will use a digest-pinned multi-stage application image; the current Dockerfile remains unchanged.

## Docker on a VM

Use [`deploy/compose.vm.yml`](../deploy/compose.vm.yml), not the root development stack:

```bash
cp deploy/vm.env.example .env.vm
chmod 600 .env.vm
docker compose --env-file .env.vm -f deploy/compose.vm.yml config --quiet
docker compose --env-file .env.vm -f deploy/compose.vm.yml pull
docker compose --env-file .env.vm -f deploy/compose.vm.yml up -d
curl --fail http://127.0.0.1:8000/api/health/z
```

The API and metrics listener bind to localhost. A reviewed TLS reverse proxy must preserve application paths and must not publish port 9090. The optional worker profile starts one concurrency-1 worker and one separate Beat scheduler. Keep exactly one Beat instance.

Enable the worker and Beat processes with:

```bash
docker compose --env-file .env.vm -f deploy/compose.vm.yml --profile worker up -d
```

## Kubernetes implementation path

The future package will use:

```text
deploy/kubernetes/
  base/
  overlays/
    production/
```

The production overlay will select the `smartenergy` namespace, public host, image digest, resources, storage, and exact ingress and policy configuration. It will not create the Namespace, ResourceQuota, AppProject, or Secret values owned outside the application repository.

Until that structure exists, render only the starter:

```bash
kubectl kustomize deploy/kubernetes
```

Once implemented, validate the production overlay locally and with server-side dry-run in the approved cluster context before requesting manual Argo sync. Do not point Argo at a mutable branch or mutable image tag.

## Capacity and rollout

The platform is a single approximately 4 GiB node. The first deployment will use one replica per role, worker concurrency 1, explicit resources, and no-surge application rollouts. PostgreSQL, Redis, API, worker, Beat, ingress, and metrics will be admitted incrementally with measurements after every checkpoint. A VM resize remains an evidence-based fallback.

This architecture provides production-like deployment controls and operational evidence. It does not claim high availability, fault tolerance across nodes, or production service-level objectives.
