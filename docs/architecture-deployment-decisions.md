# Architecture and Deployment Decisions

Status: approved design for the hosted SmartEnergy deployment. D1, D2, D3, D5, and D13 are implemented in application tooling; their production Kubernetes wiring remains future work. Unless a section says otherwise, the remaining decisions describe planned work.

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
- **Context:** The small single-node platform has a strict resource budget, and current configuration already uses those logical roles.
- **Reason:** One instance demonstrates cache and Celery integration without unnecessary memory overhead.
- **Trade-off:** Cache and task infrastructure share a non-HA failure domain.
- **Reconsider when:** Measured reliability or workload isolation requires separate instances.

## D7 — PostgreSQL image validation

- **Decision:** Use PostgreSQL 16 only after its digest-pinned image, UID, writable paths, and approximately 5 GiB PVC have passed restricted-PSA testing.
- **Context:** Official image startup and volume ownership may assume root-time initialization.
- **Reason:** A manifest that passes policy but cannot initialize a fresh volume is not deployable.
- **Trade-off:** Stateful packaging requires a disposable-cluster validation stage.
- **Reconsider when:** A supported non-root image contract removes the uncertainty.

## D8 — Redis image validation

- **Decision:** Use Redis 7 only after its digest-pinned image, UID, AOF path, authentication, and approximately 1 GiB PVC have passed restricted-PSA testing.
- **Context:** Entrypoint ownership behavior and read-only-root compatibility vary by image.
- **Reason:** Authentication and persistence must work without weakening namespace policy.
- **Trade-off:** Stateful packaging requires another image-specific test.
- **Reconsider when:** A supported non-root image contract removes the uncertainty.

## D9 — PostgreSQL backup contract

- **Decision:** Run daily off-node `pg_dump -Fc` backups, retaining seven daily and four weekly recovery points, and validate restore.
- **Context:** The current backup task only copies SQLite files and skips PostgreSQL.
- **Reason:** Local-path storage is tied to one node and needs independently recoverable data.
- **Trade-off:** The deployment needs storage credentials, retention handling, and restore exercises.
- **Reconsider when:** Another low-cost mechanism proves equivalent off-node recovery and portability.

## D10 — Initial public surface

- **Decision:** Expose the dashboard, intended demo read APIs, login, and minimal health. Keep Prometheus metrics and system metrics private, and disable Swagger, ReDoc, and OpenAPI initially.
- **Context:** Prometheus now uses its private listener; recorded system metrics and API documentation remain on the application listener pending the production HTTP-surface stage.
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
- **Context:** CI can publish a full-SHA-tagged GHCR image with digest metadata, SBOM, and provenance after all validation jobs pass. Package existence and public visibility still require the first remote run.
- **Reason:** Public pulls avoid registry credentials while the digest binds deployment to reviewed content.
- **Trade-off:** The image is publicly downloadable.
- **Reconsider when:** Image contents or repository policy require private distribution.

## D13 — Initial Beat policy

- **Decision:** Enable only KPI refresh, system metrics, and cache cleanup initially. Keep demo generation, demo cleanup, email, API cache warmup, and SQLite backup disabled.
- **Context:** The default code schedule now contains only KPI refresh, system metrics recording, and cache cleanup.
- **Reason:** Initial hosted behavior should be predictable and limited to understood operations.
- **Trade-off:** Some demonstration automation remains inactive.
- **Reconsider when:** Each task is idempotent, operationally justified, and covered by failure/recovery tests.
