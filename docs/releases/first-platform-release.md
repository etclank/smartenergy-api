# First platform release

This record identifies the immutable artifacts prepared for the first SmartEnergy admission to the Cloud-Native Service Control Plane. It contains no credentials and does not claim that the application is deployed.

| Item | Value |
| --- | --- |
| Application image source revision | `3e39c1e66c15f276aeb88fa5c4d322ec301870e2` |
| Application image tag | `ghcr.io/etclank/smartenergy-api:3e39c1e66c15f276aeb88fa5c4d322ec301870e2` |
| Application image digest | `sha256:b9ed2c1be78d707f234df14e08679204a5249def787d0b8e26f398cce41e415f` |
| Alembic revision | `6defe7ba9eda` |
| PostgreSQL image | `postgres:16.15-bookworm@sha256:efedf3595f1d6f415c08568ba171029bf54052e754cc9f030e3f2412b21f3d67` |
| Redis image | `redis:7.4.11-bookworm@sha256:c6eabf748fc7a61dbb5a705c78bcf3d6377b1127a97d0ce965c11c44ba46896f` |
| Backup dump image | `postgres:16.15-bookworm@sha256:efedf3595f1d6f415c08568ba171029bf54052e754cc9f030e3f2412b21f3d67` |
| Backup upload image | `curlimages/curl:8.22.0@sha256:58adaa4e8dca9c988bae2aba4ab3434a0bb2da16bbe3f92dec39ec7785166777` |
| Production overlay | `deploy/kubernetes/overlays/production` |
| Namespace | `smartenergy` |
| Hostname | `energy.platform.eoghanclancy.eu` |
| Deployment revision | The immutable SmartEnergy Git commit containing this release record and production overlay. Its exact SHA is pinned externally by Project 1's `Application/smartenergy`. |

The application image source revision is the commit whose runtime inputs produced the published image. The deployment revision is the later Git commit containing the reviewed production overlay that pins that image digest. Project 1 records the deployment revision's exact SHA outside this repository. These are intentionally different immutable revisions, which avoids a self-referential commit and image publication loop.
