# Project 2 closeout

**Project status:** COMPLETE — PORTFOLIO/DEMO SCOPE  
**Live hostname:** `energy.platform.eoghanclancy.eu`  
**SmartEnergy deployment revision:** The immutable SmartEnergy Git commit containing this closeout record and production overlay. Its exact SHA is pinned externally by Project 1's `Application/smartenergy`.  
**Runtime image digest:** `sha256:0d13398c342931d23d726b4db1903508272e45fefc27687f9cfe311798a4e363`<br>
**Platform:** existing approximately 4 GiB Hetzner single-node K3s VM  
**Final observed node memory:** approximately 75%, with MemoryPressure, DiskPressure, and PIDPressure false

The deployed portfolio demonstrates a Python/FastAPI backend, PostgreSQL, Redis, a Celery worker and Beat scheduler, Alembic migrations, an immutable GHCR image, Kubernetes and Kustomize, GitOps delivery with Argo CD, restricted Pod Security Admission, exact NetworkPolicies, local-path PVC persistence, private Prometheus metrics, cert-manager TLS, Traefik Ingress, health probes, a controlled rollout, and live capacity validation. PostgreSQL and Redis persistence across controlled Pod restarts has been validated.

The deployment deliberately remains single-node and non-HA. PostgreSQL and Redis each run one replica on local-path PVCs. PostgreSQL data survives Pod replacement, but node or PVC loss has no off-node recovery path. Off-node backup and disaster recovery are outside the current portfolio scope. The single API replica can have brief downtime during rollout, and the current VM has limited spare memory headroom.
