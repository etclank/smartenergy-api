# Architecture and Deployment Decisions

Status: approved design for the hosted SmartEnergy deployment. The application-owned stateless, stateful, migration, backup, and restore package is implemented; Project 1 admission and live deployment remain future work.

## D1 — Versioned schema lifecycle

- **Decision:** Use Alembic before persistent PostgreSQL deployment. Run upgrades in a migration Job and start the API without DDL.
- **Context:** API startup previously ran `create_all`, direct legacy `ALTER TABLE` statements, and optional seeding. It now starts without schema mutation.
- **Reason:** Persistent data needs ordered, reviewable, testable schema revisions.
- **Trade-off:** Releases gain migration files, compatibility work, and another Job.
- **Reconsider when:** The database is permanently disposable or a better SQLAlchemy-compatible lifecycle is proven.

## D2 — Private metrics listener

- **Decision:** Serve Prometheus metrics privately on TCP 9090; application HTTP remains on TCP 8000.
- **Context:** `/api/metrics` has been removed; the API lifecycle now owns a separate listener on TCP 9090.
- **Reason:** Project 1 scrapes a private port, and application ingress should not expose operational metrics.
- **Trade-off:** The API process owns a second listener and Service port.
- **Reconsider when:** A separate metrics process or sidecar has a measured operational benefit.

## D3 — Kubernetes logging

- **Decision:** Emit structured JSON on stdout/stderr and disable file logging in Kubernetes.
- **Context:** `ENV=prod` now emits role-labelled JSON only to stdout/stderr; local development retains file logging.
- **Reason:** Container streams provide the platform log boundary and simplify a read-only root filesystem.
- **Trade-off:** Pods retain no rotated application log files.
- **Reconsider when:** The platform adopts a supported file-based log collection contract.

## D4 — Immutable application image

- **Decision:** Build a digest-pinned, multi-stage application image and deploy it by registry digest.
- **Context:** The application now uses a digest-pinned multi-stage image, transfers a locked virtual environment, and omits build tooling from runtime.
- **Reason:** A smaller reproducible runtime improves delivery traceability and reduces unnecessary packages.
- **Trade-off:** The Dockerfile and dependency-copy process become more involved.
- **Reconsider when:** Measured maintenance cost exceeds the size and reproducibility benefit.

## D5 — Durable operational dispatch

- **Decision:** HTTP operations that promise durable execution will enqueue Celery and return a task identifier.
- **Context:** Durable HTTP task endpoints now enqueue Celery work and return task IDs. Explicit cache warmup remains documented best-effort API-local work.
- **Reason:** Accepted operational work needs a durable broker boundary and observable identity.
- **Trade-off:** Those endpoints depend on Redis/Celery and need explicit failure semantics.
- **Reconsider when:** An operation is deliberately documented as best-effort and safe to lose.

## D6 — One Redis instance

- **Decision:** Use one authenticated Redis instance with AOF and logical DB separation: DB 0 cache, DB 1 broker, DB 2 result backend.
- **Context:** The production package now runs one authenticated Redis 7.4.11 StatefulSet with `appendonly yes`, `appendfsync everysec`, a 1 GiB local-path PVC, and those logical roles.
- **Reason:** One instance demonstrates cache and Celery integration without unnecessary memory overhead.
- **Trade-off:** Cache and task infrastructure share a non-HA failure domain.
- **Reconsider when:** Measured reliability or workload isolation requires separate instances.

## D7 — PostgreSQL image validation

- **Decision:** Use the official PostgreSQL 16.15 Bookworm image by immutable digest, fixed UID/GID 999, and a 5 GiB local-path PVC.
- **Context:** Fresh initialization and restart with existing data passed restricted PSA using a writable `PGDATA` subdirectory, socket `emptyDir`, and read-only root.
- **Reason:** A manifest that passes policy but cannot initialize a fresh volume is not deployable.
- **Trade-off:** Stateful packaging requires a disposable-cluster validation stage.
- **Reconsider when:** A supported non-root image contract removes the uncertainty.

## D8 — Redis image validation

- **Decision:** Use the official Redis 7.4.11 Bookworm image by immutable digest, fixed UID/GID 999, authenticated AOF, and a 1 GiB local-path PVC.
- **Context:** Fresh initialization, AOF creation, authentication, and restart recovery passed restricted PSA with only `/data` and `/tmp` writable.
- **Reason:** Authentication and persistence must work without weakening namespace policy.
- **Trade-off:** Stateful packaging requires another image-specific test.
- **Reconsider when:** A supported non-root image contract removes the uncertainty.

## D9 — PostgreSQL backup contract

- **Decision:** Run daily off-node `pg_dump -Fc` backups, retaining seven daily and four weekly recovery points, and validate restore.
- **Context:** A daily CronJob now creates a custom-format dump with the PostgreSQL 16 client and uploads it to S3-compatible HTTPS storage using a separate pinned curl image. A guarded restore Job template and admin script were exercised against a clean database.
- **Reason:** Local-path storage is tied to one node and needs independently recoverable data.
- **Trade-off:** The deployment needs storage credentials, retention handling, and restore exercises.
- **Reconsider when:** Another low-cost mechanism proves equivalent off-node recovery and portability.

## D10 — Initial public surface

- **Decision:** Expose the dashboard, intended demo read APIs, login, minimal health, and the system-metrics data currently required by the dashboard. Keep Prometheus metrics private, and disable Swagger, ReDoc, and OpenAPI initially.
- **Context:** Prometheus uses its private listener, and the production overlay disables API documentation. Recorded system metrics remain public temporarily because the dashboard reads them.
- **Reason:** The first hosted release should have a small, deliberate public boundary.
- **Trade-off:** Interactive API documentation is not initially available as public portfolio evidence.
- **Reconsider when:** The operational API has been reviewed and public documentation adds clear portfolio value.

## D11 — Conservative resource and rollout policy

- **Decision:** Begin with low explicit resources, worker concurrency 1, one replica per role, and no-surge rollouts.
- **Context:** Project 1 runs on one approximately 4 GiB node.
- **Reason:** Incremental admission and measurement preserve existing platform stability.
- **Trade-off:** Single-replica updates cause downtime and limits may need tuning.
- **Reconsider when:** Measurements show sustained throttling, memory pressure, or capacity for higher availability.

## D12 — Public GHCR and immutable delivery

- **Decision:** Publish a public GHCR image tagged with the full Git SHA and pin its digest in the production overlay.
- **Context:** GHCR contains the public full-SHA image for source revision `3e39c1e66c15f276aeb88fa5c4d322ec301870e2`, with verified digest, SBOM, and provenance; the later deployment revision pins that digest in the production overlay.
- **Reason:** Public pulls avoid registry credentials while the digest binds deployment to reviewed content.
- **Trade-off:** The image is publicly downloadable.
- **Reconsider when:** Image contents or repository policy require private distribution.

## D13 — Initial Beat policy

- **Decision:** Enable only KPI refresh, system metrics, and cache cleanup initially. Keep demo generation, demo cleanup, email, API cache warmup, and SQLite backup disabled.
- **Context:** The default code schedule now contains only KPI refresh, system metrics recording, and cache cleanup.
- **Reason:** Initial hosted behavior should be predictable and limited to understood operations.
- **Trade-off:** Some demonstration automation remains inactive.
- **Reconsider when:** Each task is idempotent, operationally justified, and covered by failure/recovery tests.
