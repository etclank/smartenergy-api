# Deploying SmartEnergy

SmartEnergy runs from one container image. The FastAPI process also serves `/site/`; PostgreSQL stores application data and Redis provides optional response caching and the Celery broker. This repository includes local development Compose, a VM runtime Compose file, and a Kubernetes API starter. None represents a live deployment.

## Image delivery

Run the existing tests and build the image from the repository root. Use a registry you control; the following commands are a delivery example, not an automatic publication workflow:

```bash
IMAGE=ghcr.io/YOUR_OWNER/smartenergy-api
REVISION=$(git rev-parse HEAD)
docker build -f docker/Dockerfile \
  --label org.opencontainers.image.revision="$REVISION" \
  -t "$IMAGE:$REVISION" .
# Authenticate to the registry using its approved credential flow first.
docker push "$IMAGE:$REVISION"
docker buildx imagetools inspect "$IMAGE:$REVISION"
```

Record the registry digest and deploy `ghcr.io/YOUR_OWNER/smartenergy-api@sha256:...`. Keep the previous digest for rollback. The current CI validates builds but does not publish packages. For the control plane, add image publication through its reviewed immutable delivery process and use namespace-scoped, read-only registry credentials. Match the image architecture to the target node (the target control-plane VM is x86-64).

## Runtime requirements

- Set `DATABASE_URL` to a private `postgresql+asyncpg://...` connection. URL-encode reserved characters in credentials. Use the database provider's required TLS configuration when connecting across a network.
- Set a newly generated `JWT_SECRET` with at least 32 characters. The application's JWT secret is separate from the control-plane API bearer token.
- Set `REDIS_URL` for caching. The optional worker also requires `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`, or uses `REDIS_URL` for both. Keep broker/result/cache databases distinct where supported; a managed Redis service must support Celery's required commands and connections.
- Leave `SEED_DEMO=0`. Database initialization creates missing tables on API startup. It is not a versioned migration tool. Back up persistent data before schema changes.
- Keep `ENABLE_TELEMETRY=0` until Collector routing, allowed workload identity and exporter configuration have been reviewed.
- The image runs as UID/GID 10001 and needs writable `/tmp` and `/app/logs`. The examples provide ephemeral storage for these paths; stdout remains available to the container runtime. They require PostgreSQL, not a SQLite database in the read-only application directory.

The examples do not provision PostgreSQL, Redis, persistent data volumes, database backups, DNS or certificates. Decide where the stateful services live and verify backup restoration before deployment. A local-path volume on a single K3s node is not redundant storage.

## Docker on a VM

Use [`deploy/compose.vm.yml`](../deploy/compose.vm.yml), not the root development Compose file. It starts only the API by default, uses an existing image, and does not expose database/cache ports.

```bash
cp deploy/vm.env.example .env.vm
chmod 600 .env.vm
# Edit .env.vm: set the published image digest, private DB URL and JWT secret.
docker compose --env-file .env.vm -f deploy/compose.vm.yml config --quiet
docker compose --env-file .env.vm -f deploy/compose.vm.yml pull
docker compose --env-file .env.vm -f deploy/compose.vm.yml up -d
docker compose --env-file .env.vm -f deploy/compose.vm.yml ps
curl --fail http://127.0.0.1:8000/api/health/z
```

`.env.vm` is ignored by Git and excluded from image builds. Avoid printing expanded Compose configuration because it contains secrets. Private service addresses must be reachable from the container network: `localhost` inside the container is not the VM host or a separate database container.

The API binds to `127.0.0.1:8000` on the host. Put the VM's reviewed TLS reverse proxy in front of it, proxying the original paths (`/api`, `/site`, `/docs`, `/redoc`) without stripping prefixes. Only expose approved HTTPS routes; keep port 8000 private. Apply authentication/rate limits at the proxy as needed. The dashboard uses same-origin `/api`, so separate CORS configuration is unnecessary in this arrangement.

After checking capacity and configuring Redis, enable the worker explicitly:

```bash
docker compose --env-file .env.vm -f deploy/compose.vm.yml --profile worker up -d
```

The worker uses concurrency 1 and a single Beat scheduler. Do not scale this combined worker/Beat service. Its Beat schedule file is ephemeral, so restarts can alter scheduling timing. Default scheduled jobs include generating/cleaning synthetic readings; review those jobs before using any non-demo dataset. The PostgreSQL backup task returns `skip`; use real database backups separately. Optional SendGrid settings are not needed to run the API.

Both services have initial 0.5 CPU / 512 MiB limits. These are starting budgets, not measured capacity guarantees. Host stdout logs are rotated; temporary application logs are discarded with the container. `up -d` recreates services when the configured image changes, with downtime possible for the single replica.

To roll back, restore the previous digest in `.env.vm`, pull it and rerun `up -d`. An application rollback does not undo schema or data changes. Stop the runtime with `down`; it owns no database volume to delete.

## Kubernetes and the Cloud-Native Service Control Plane

The Cloud-Native Service Control Plane operator currently accepts only the `demo-http` ManagedService template. Use its documented **GitOps/Kustomize application onboarding path** for SmartEnergy. Do not submit a SmartEnergy image to the existing lifecycle API or edit operator-owned Deployments.

[`deploy/kubernetes/`](../deploy/kubernetes/) contains a one-replica Deployment and ClusterIP Service. It does not install a namespace, Secret, registry credential, Ingress, NetworkPolicy, worker or stateful service. The placeholder image deliberately requires replacement in an environment overlay.

Before onboarding to the 2-vCPU / 4-GB single-node platform, remeasure CPU, memory and disk use. Its published utilization is historical evidence, not a current capacity budget. Account for PostgreSQL, Redis, the optional worker and backups in addition to the API. Start with the API and separately provisioned dependencies; resize or defer if capacity is insufficient.

An environment overlay should contain:

1. The approved namespace and immutable image digest.
2. An `imagePullSecrets` reference to a pull-only registry Secret in that namespace.
3. A `smartenergy-runtime` Secret provisioned outside Git with `DATABASE_URL`, `JWT_SECRET`, and optional `REDIS_URL`/CORS settings. Explicit container environment entries keep production mode, seeding off and OTLP off.
4. Reviewed NetworkPolicies for ingress from the selected ingress controller, egress to DNS and the exact database/cache endpoints, plus any explicitly enabled email/telemetry destinations. The base defines no network isolation by itself.
5. A Traefik Ingress, hostname and cert-manager certificate using the platform's existing conventions. Initially validate privately; add public ingress only after reviewing SmartEnergy's intentionally public read endpoints and shared operator privileges.
6. Resource budgets and Argo CD project/repository permissions reviewed for this workload. Do not broaden existing AppProjects merely to bypass a denied sync.

For example, an overlay at `deploy/overlays/production/kustomization.yaml` in a working copy could use the following shape. Replace all placeholders and provision referenced Secrets before use; this is not a ready-to-sync platform configuration:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: applications # use the namespace approved by your platform
resources:
  - ../../kubernetes
images:
  - name: smartenergy-api
    newName: ghcr.io/YOUR_OWNER/smartenergy-api
    newTag: ""
    digest: sha256:REPLACE_WITH_PUBLISHED_DIGEST
patches:
  - target:
      kind: Deployment
      name: smartenergy-api
    patch: |-
      - op: add
        path: /spec/template/spec/imagePullSecrets
        value:
          - name: smartenergy-registry
```

For platform GitOps, vendor the reviewed base and overlay into the application package, or pin a remote base to an immutable Git revision under the platform's dependency policy. Adapt relative paths to that package. Use its existing manual Argo CD sync and rollback process; do not point Argo at a mutable default branch without reviewing the intended revision.

Render the supplied base locally without accessing a cluster:

```bash
kubectl kustomize deploy/kubernetes
```

After preparing the environment overlay, use the platform's private administrative access to validate it against the target API server before manual GitOps sync:

```bash
# Run only in the approved kubeconfig/context, with the reviewed overlay present.
kubectl apply --dry-run=server -k deploy/overlays/production
```

The Deployment uses `Recreate` and one replica because startup performs schema initialization. Expect rollout downtime. The read-only filesystem, non-root UID, dropped capabilities, disabled service-account token and RuntimeDefault seccomp match the intended platform security posture. Writable `emptyDir` volumes hold only temporary files and logs.

Startup and liveness probes check the HTTP listener. Readiness uses `/api/health/z`, which reports Redis state but returns 200 even when Redis is down and does not check PostgreSQL. It is a process-level readiness check, not proof of data-service availability. Validate database-backed endpoints separately; see Kubernetes' [probe behavior](https://kubernetes.io/docs/concepts/workloads/pods/probes/).

After manual sync, verify the rollout and access the private Service:

```bash
kubectl -n applications rollout status deployment/smartenergy-api --timeout=180s
kubectl -n applications port-forward service/smartenergy-api 18000:8000
# In a second terminal:
curl --fail http://127.0.0.1:18000/api/health/z
curl --fail http://127.0.0.1:18000/api/sites/
curl --fail http://127.0.0.1:18000/site/
```

Also verify rejected unauthenticated writes, login with an explicitly provisioned application user, database persistence across Pod recreation, Redis fallback and resource usage. There is no public registration endpoint. For an empty demonstration database, provision `DEMO_PASSWORD` privately and deliberately invoke `python -m scripts.seed_demo`; do not enable automatic seeding for ordinary rollouts.

A Kubernetes worker is a separate later workload: reuse the image with explicit Celery arguments, concurrency/resource budgets, private broker credentials and writable scheduler state, and run exactly one Beat scheduler. HTTP task endpoints still run in-process even when no worker is deployed. The current base intentionally deploys only the API/dashboard.

## Observability and rollback

The control-plane Collector currently admits reviewed identities and uses a nop exporter; workload OTLP export is outside its accepted baseline. Keep SmartEnergy OTLP disabled until that design changes. `/api/metrics` can be scraped privately only after explicitly extending the platform's bounded Prometheus target configuration and network access. Do not add public metrics ingress by default.

Revert the environment overlay to the previous image digest and use the platform's manual sync process to roll back. Confirm schema compatibility first. Keep database backup/restore and credential rotation procedures separate from application-image rollback. Do not treat deleting Kubernetes resources or replacing a Pod as a data-recovery procedure.

References: [Kustomize overlays](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/) and [Compose profiles](https://docs.docker.com/compose/how-tos/profiles/).
