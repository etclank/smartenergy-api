# Deploying SmartEnergy

SmartEnergy is not deployed to the Cloud-Native Service Control Plane. This document separates the repository's current deployment helpers from the approved hosted design. The design provides production-like deployment controls for a portfolio application while remaining deliberately single-node and non-HA.

The [architecture decision record](architecture-deployment-decisions.md) is the stable reference for the approved choices. The root [README](../README.md) remains the application and local-development guide.

## Current deployment assets

The repository currently provides:

- a local Compose stack with PostgreSQL 16, a one-shot Alembic migration service, Redis 7, the API, and a Celery worker that also runs Beat;
- a runtime-only VM Compose file with an optional combined worker/Beat service;
- one application image used by the API and worker;
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

The current local and VM Compose worker runs Beat in the same process. Do not scale that combined service because doing so would create multiple schedulers.

The hosted design will use:

| Role | Responsibility |
| --- | --- |
| API Deployment | FastAPI, dashboard, public HTTP on TCP 8000 |
| Worker Deployment | Celery task execution, concurrency 1 initially |
| Beat Deployment | Exactly one scheduler with an independent lifecycle |
| Migration Job | Versioned schema upgrades before application rollout |
| Backup CronJob | Daily PostgreSQL logical backup and off-node upload |

Separating Beat gives the scheduler an independent lifecycle and resource budget and reduces duplicate-scheduling risk.

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

Application HTTP will remain on TCP 8000. Prometheus metrics will move from the current `/api/metrics` route to a private TCP 9090 listener. The current route must not be publicly exposed during hosted deployment.

## Logging and writable paths

Local development may retain Loguru file output. Kubernetes will use structured JSON on stdout/stderr and will not persist `/app/logs`. API, worker, Beat, and migration processes will use a read-only root filesystem with a bounded writable `/tmp` where needed.

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

This is target deployment behavior. The current application still serves metrics, system metrics, Swagger, ReDoc, and OpenAPI on the main HTTP listener. Later application and ingress work will enforce the approved boundary.

## Celery reliability and schedule policy

The current Celery configuration has no `acks_late`, worker-lost rejection, explicit retry policy, prefetch policy, or task time limits. HTTP task endpoints currently use FastAPI `BackgroundTasks` rather than publishing Celery messages. A `202` therefore confirms local scheduling only. The system does not claim exactly-once or guaranteed delivery.

A later stage will move operational HTTP work that promises durable execution to Celery and return a task identifier. It will still document at-least-once and loss/duplication boundaries rather than claiming exactly-once semantics.

The initial hosted Beat policy will review only these candidates for enablement:

- KPI refresh;
- system metrics recording;
- cache cleanup.

These schedules will remain disabled initially:

- demo generation;
- demo cleanup;
- health email;
- API cache warmup;
- obsolete SQLite backup.

The existing code schedule remains unchanged until that review is implemented.

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

The API binds to localhost. A reviewed TLS reverse proxy must preserve application paths. The optional worker profile still combines worker and Beat, uses concurrency 1, and must remain a single instance.

Enable that current combined process only when its schedule has been reviewed:

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
