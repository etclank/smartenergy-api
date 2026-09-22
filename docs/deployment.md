# Deploying SmartEnergy

SmartEnergy is not deployed to the Cloud-Native Service Control Plane. This document separates the repository's current deployment helpers from the approved hosted design. The design provides production-like deployment controls for a portfolio application while remaining deliberately single-node and non-HA.

The [architecture decision record](architecture-deployment-decisions.md) is the stable reference for the approved choices. The root [README](../README.md) remains the application and local-development guide.

## Current deployment assets

The repository currently provides:

- a local Compose stack with PostgreSQL 16, a one-shot Alembic migration service, Redis 7, the API, a concurrency-1 Celery worker, and a separate Beat scheduler;
- a runtime-only VM Compose file with optional separate worker and Beat services;
- one digest-pinned, multi-stage application image used by the API, worker, Beat, and migration command;
- a production Kustomize package containing the API, worker, Beat, migration, private Service, network boundaries, Ingress, TLS Certificate, and middleware;
- CI validation that can publish a full-SHA-tagged GHCR image with digest metadata, SBOM, and provenance after all quality gates pass.

[`deploy/kubernetes/overlays/production`](../deploy/kubernetes/overlays/production/) is the application-owned production package. Stage 5 will add PostgreSQL, Redis, persistent storage, and backups. Project 1 still owns the Namespace, ResourceQuota, AppProject, and eventual Argo CD Application.

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

The verified public image tag is `ghcr.io/etclank/smartenergy-api:1cbe7dd0991b1495dfabdd08a69a00755c5961aa`. The production overlay pins registry digest `sha256:7a35d14461bd6ee81bf67cf09bef792c866ad7673add9077e7b770e5fff99792`. Its SPDX SBOM and SLSA provenance are attached in GHCR.

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

The migration command and application-owned Kubernetes Job are implemented. Useful inspection and drift commands are:

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

The application image runs as UID/GID 10001, keeps application files read-only, and needs only writable `/tmp` storage for ephemeral state. This contract has been exercised locally with a read-only root filesystem. PostgreSQL and Redis require their own persistent data mounts. Their exact image UIDs, security contexts, and writable paths must be validated under the platform's restricted Pod Security Admission policy before live deployment.

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

The following are private or disabled in the production overlay:

- Prometheus metrics;
- Swagger UI;
- ReDoc;
- OpenAPI JSON.

Prometheus metrics are separated onto TCP 9090 and are not routed through Ingress. Recorded system metrics remain public temporarily because the dashboard reads `/api/system_metrics/latest`; changing that contract is deferred to a later API/security stage. `ENABLE_API_DOCS=0` disables Swagger, ReDoc, and OpenAPI JSON in production while local development retains them. The Ingress also rewrites those documentation paths to a non-existent route. This closes the public paths for the pinned Stage 3 artifact while the application flag enters the next published image.

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

Build the same artifact locally with:

```bash
REVISION=$(git rev-parse HEAD)
docker build -f docker/Dockerfile \
  --build-arg VCS_REF="$REVISION" \
  --build-arg VERSION="$REVISION" \
  -t smartenergy-api:"$REVISION" .
```

On a push to `main`, CI runs application and integration tests, builds and smoke-tests the runtime image, then publishes exactly `ghcr.io/etclank/smartenergy-api:<full-40-character-sha>`. It records the registry `sha256:...` as a job output, workflow summary, and `image-metadata-<sha>` artifact. Buildx also attaches an SBOM and maximum-mode provenance to the registry image. These attestations provide traceability; no admission policy currently enforces them.

The current production reference is `ghcr.io/etclank/smartenergy-api@sha256:7a35d14461bd6ee81bf67cf09bef792c866ad7673add9077e7b770e5fff99792`. GHCR visibility is public, so no image pull Secret is required.

The Python base is pinned as a readable tag plus multi-platform digest in `docker/Dockerfile`. To update it, inspect the current upstream manifest with `docker buildx imagetools inspect python:3.13-slim`, replace the verified digest in both the build argument and OCI base label, then rebuild and repeat the test and read-only smoke suites. Alembic uses the Python PostgreSQL drivers and does not need `psql`; the main image therefore omits `postgresql-client`. Stage 5 should use a separate digest-pinned PostgreSQL backup image for `pg_dump`.

The image-level Docker healthcheck calls `/api/health/z` for local Docker and Compose operation. It does not define future Kubernetes liveness or readiness probes; those will be configured explicitly in the Kubernetes workload.

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

## Production Kubernetes package

The application-owned package is:

```text
deploy/kubernetes/
  base/
  overlays/
    production/
```

The overlay selects namespace `smartenergy`, the verified application digest, and `energy.platform.eoghanclancy.eu`. It creates no Namespace, ResourceQuota, AppProject, RBAC, ServiceAccount, or Secret values. Render it with:

```bash
kubectl kustomize deploy/kubernetes/overlays/production
```

Required external Secret contracts are:

| Secret | Required keys |
| --- | --- |
| `smartenergy-runtime` | `JWT_SECRET` |
| `smartenergy-postgres` | `DATABASE_URL` |
| `smartenergy-redis` | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| `smartenergy-backup` | Reserved for Stage 5; contract not yet consumed |

The API requests `50m/128Mi` and limits `250m/256Mi`; the worker requests `50m/128Mi` and limits `300m/256Mi`; Beat requests `10m/48Mi` and limits `50m/96Mi`; migration requests `25m/96Mi` and limits `150m/192Mi`. API uses a no-surge rollout, accepting single-replica downtime to limit temporary memory. Worker and singleton Beat use `Recreate`; a worker restart can redeliver work under late acknowledgements.

Every Pod runs as UID/GID 10001 with RuntimeDefault seccomp, all capabilities dropped, privilege escalation disabled, service-account token automount disabled, a read-only root, and only a size-limited `/tmp` `emptyDir`. `/api/health/z` is startup/liveness; `/api/health/readyz` checks PostgreSQL readiness without making Redis a readiness dependency.

The migration is an Argo CD `PreSync` hook with a fixed name, a source-revision annotation, and `BeforeHookCreation`. A failed migration blocks the sync and remains available for diagnosis. The next manually admitted release removes the previous Job immediately before creating its replacement, preventing permanent buildup while retaining evidence between releases.

Default-deny ingress and egress apply to all package Pods. DNS is limited to CoreDNS UDP/TCP 53. Traefik may reach API TCP 8000, and Prometheus may reach metrics TCP 9090, using their exact platform identities. Application roles may reach only the stable Stage 5 PostgreSQL label on TCP 5432 and Redis label on TCP 6379. No unrestricted internet or TCP 443 egress exists; SendGrid and OTLP remain disabled.

Ingress uses Traefik, permanent HTTPS redirect, documentation-path blocking, and rate limiting at five requests per second with a burst of ten. Cert-manager writes `smartenergy-tls` using the existing `letsencrypt-production` ClusterIssuer. These values match the current platform convention and keep metrics outside public routing.

The rendered package fits the Project 1 quota including the reserved Stage 5 budget: steady state is `210m/1000m` CPU and `544Mi/1088Mi` memory; with migration it is `235m/1150m` and `640Mi/1280Mi`. Stage 5 must retain the tested label and resource reservation contracts.

Do not apply this overlay directly. After Stage 5 validation, Project 1 will add a commit-pinned Argo Application and the Prometheus discovery edge, followed by manual sync. Live DNS also remains separate.

## Capacity and rollout

The platform is a single approximately 4 GiB node. The first deployment will use one replica per role, worker concurrency 1, explicit resources, and no-surge application rollouts. PostgreSQL, Redis, API, worker, Beat, ingress, and metrics will be admitted incrementally with measurements after every checkpoint. A VM resize remains an evidence-based fallback.

This architecture provides production-like deployment controls and operational evidence. It does not claim high availability, fault tolerance across nodes, or production service-level objectives.
