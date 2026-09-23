from functools import lru_cache
from pathlib import Path
import re
import subprocess

import yaml


ROOT = Path(__file__).parents[1]
OVERLAY = ROOT / "deploy" / "kubernetes" / "overlays" / "production"
RESTORE_JOB = ROOT / "deploy" / "kubernetes" / "operations" / "restore-job.yaml"
BACKUP_CRONJOB = (
    ROOT / "deploy" / "kubernetes" / "operations" / "backup" / "cronjob.yaml"
)
IMAGE = (
    "ghcr.io/etclank/smartenergy-api@"
    "sha256:b9ed2c1be78d707f234df14e08679204a5249def787d0b8e26f398cce41e415f"
)
OLD_IMAGE_DIGEST = (
    "sha256:7a35d14461bd6ee81bf67cf09bef792c866ad7673add9077e7b770e5fff99792"
)
POSTGRES_IMAGE = (
    "postgres:16.15-bookworm@"
    "sha256:efedf3595f1d6f415c08568ba171029bf54052e754cc9f030e3f2412b21f3d67"
)
REDIS_IMAGE = (
    "redis:7.4.11-bookworm@"
    "sha256:c6eabf748fc7a61dbb5a705c78bcf3d6377b1127a97d0ce965c11c44ba46896f"
)
CURL_IMAGE = (
    "curlimages/curl:8.22.0@"
    "sha256:58adaa4e8dca9c988bae2aba4ab3434a0bb2da16bbe3f92dec39ec7785166777"
)
IMAGE_SOURCE_REVISION = "3e39c1e66c15f276aeb88fa5c4d322ec301870e2"
OLD_IMAGE_SOURCE_REVISION = "1cbe7dd0991b1495dfabdd08a69a00755c5961aa"


@lru_cache
def rendered_text() -> str:
    result = subprocess.run(
        ["kubectl", "kustomize", str(OVERLAY)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


@lru_cache
def resources() -> tuple[dict, ...]:
    return tuple(yaml.safe_load_all(rendered_text()))


def by_kind_name(kind: str, name: str) -> dict:
    return next(
        resource
        for resource in resources()
        if resource["kind"] == kind and resource["metadata"]["name"] == name
    )


def pod_spec(resource: dict) -> dict:
    if resource["kind"] == "CronJob":
        return resource["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    return resource["spec"]["template"]["spec"]


def container(resource: dict) -> dict:
    return pod_spec(resource)["containers"][0]


def all_containers(resource: dict) -> list[dict]:
    spec = pod_spec(resource)
    return [*spec.get("initContainers", []), *spec.get("containers", [])]


def env_map(resource: dict) -> dict[str, dict]:
    return {entry["name"]: entry for entry in container(resource).get("env", [])}


def cpu_millicores(value: str) -> int:
    assert value.endswith("m")
    return int(value.removesuffix("m"))


def memory_mebibytes(value: str) -> int:
    assert value.endswith("Mi")
    return int(value.removesuffix("Mi"))


def scalar_values(value: object):
    if isinstance(value, dict):
        for child in value.values():
            yield from scalar_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from scalar_values(child)
    else:
        yield value


def test_render_is_deterministic_complete_and_namespaced() -> None:
    second = subprocess.run(
        ["kubectl", "kustomize", str(OVERLAY)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    assert rendered_text() == second
    assert len(resources()) == 24
    assert "replace-me" not in rendered_text()
    assert not any(
        isinstance(value, str) and re.fullmatch(r"\$\{[A-Z][A-Z0-9_]*\}", value)
        for resource in resources()
        for value in scalar_values(resource)
    )

    identities = [
        (resource["apiVersion"], resource["kind"], resource["metadata"]["name"])
        for resource in resources()
    ]
    assert len(identities) == len(set(identities))
    assert all(
        resource["metadata"]["namespace"] == "smartenergy" for resource in resources()
    )


def test_render_owns_no_platform_or_secret_resources() -> None:
    forbidden = {
        "Namespace",
        "ResourceQuota",
        "AppProject",
        "Secret",
        "ServiceAccount",
        "Role",
        "RoleBinding",
        "ClusterRole",
        "ClusterRoleBinding",
    }
    assert not {resource["kind"] for resource in resources()} & forbidden


def test_all_application_roles_use_the_verified_digest() -> None:
    workloads = [
        by_kind_name("Deployment", "smartenergy-api"),
        by_kind_name("Deployment", "smartenergy-worker"),
        by_kind_name("Deployment", "smartenergy-beat"),
        by_kind_name("Job", "smartenergy-migration"),
    ]
    assert {container(workload)["image"] for workload in workloads} == {IMAGE}
    assert all("@sha256:" in container(workload)["image"] for workload in workloads)
    assert all(":latest" not in container(workload)["image"] for workload in workloads)
    assert OLD_IMAGE_DIGEST not in rendered_text()
    assert OLD_IMAGE_SOURCE_REVISION not in rendered_text()


def test_every_production_container_uses_an_immutable_image() -> None:
    workloads = [
        resource
        for resource in resources()
        if resource["kind"] in {"Deployment", "StatefulSet", "Job", "CronJob"}
    ]
    images = {
        runtime["image"]
        for workload in workloads
        for runtime in all_containers(workload)
    }
    assert images == {IMAGE, POSTGRES_IMAGE, REDIS_IMAGE}
    assert all("@sha256:" in image for image in images)


def test_runtime_roles_and_rollouts() -> None:
    api = by_kind_name("Deployment", "smartenergy-api")
    worker = by_kind_name("Deployment", "smartenergy-worker")
    beat = by_kind_name("Deployment", "smartenergy-beat")

    assert env_map(api)["ROLE"]["value"] == "web"
    assert env_map(worker)["ROLE"]["value"] == "worker"
    assert env_map(beat)["ROLE"]["value"] == "beat"
    assert env_map(beat)["DATABASE_URL"]["valueFrom"]["secretKeyRef"] == {
        "name": "smartenergy-postgres",
        "key": "DATABASE_URL",
    }
    assert api["spec"]["strategy"] == {
        "type": "RollingUpdate",
        "rollingUpdate": {"maxSurge": 0, "maxUnavailable": 1},
    }
    assert worker["spec"]["strategy"]["type"] == "Recreate"
    assert beat["spec"]["replicas"] == 1
    assert beat["spec"]["strategy"]["type"] == "Recreate"


def test_restricted_pod_security_contract() -> None:
    workloads = [
        resource
        for resource in resources()
        if resource["kind"] in {"Deployment", "Job"}
    ]
    for workload in workloads:
        spec = pod_spec(workload)
        assert spec["automountServiceAccountToken"] is False
        assert spec["securityContext"]["runAsNonRoot"] is True
        assert spec["securityContext"]["runAsUser"] == 10001
        assert spec["securityContext"]["runAsGroup"] == 10001
        assert spec["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
        expected_tmp_limits = {
            "smartenergy-api": "64Mi",
            "smartenergy-worker": "64Mi",
            "smartenergy-beat": "32Mi",
            "smartenergy-migration": "32Mi",
        }
        assert spec["volumes"] == [
            {
                "name": "tmp",
                "emptyDir": {
                    "sizeLimit": expected_tmp_limits[workload["metadata"]["name"]]
                },
            }
        ]
        runtime = container(workload)
        assert runtime["securityContext"] == {
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": True,
            "capabilities": {"drop": ["ALL"]},
        }
        assert runtime["volumeMounts"] == [{"name": "tmp", "mountPath": "/tmp"}]


def test_resources_match_budget_and_leave_stage5_headroom() -> None:
    expected = {
        "smartenergy-api": (50, 250, 128, 256),
        "smartenergy-worker": (50, 300, 128, 256),
        "smartenergy-beat": (10, 50, 96, 128),
        "smartenergy-migration": (25, 150, 96, 192),
    }
    measured: dict[str, tuple[int, int, int, int]] = {}
    for kind, name in [
        ("Deployment", "smartenergy-api"),
        ("Deployment", "smartenergy-worker"),
        ("Deployment", "smartenergy-beat"),
        ("Job", "smartenergy-migration"),
    ]:
        values = container(by_kind_name(kind, name))["resources"]
        measured[name] = (
            cpu_millicores(values["requests"]["cpu"]),
            cpu_millicores(values["limits"]["cpu"]),
            memory_mebibytes(values["requests"]["memory"]),
            memory_mebibytes(values["limits"]["memory"]),
        )
    assert measured == expected

    stage4_steady = tuple(
        sum(
            measured[name][index]
            for name in measured
            if name != "smartenergy-migration"
        )
        for index in range(4)
    )
    stage5_reserved = (100, 400, 240, 480)
    eventual_steady = tuple(
        stage4_steady[index] + stage5_reserved[index] for index in range(4)
    )
    eventual_with_migration = tuple(
        eventual_steady[index] + measured["smartenergy-migration"][index]
        for index in range(4)
    )
    assert eventual_steady == (210, 1000, 592, 1120)
    assert eventual_with_migration == (235, 1150, 688, 1312)
    assert eventual_with_migration[0] <= 500
    assert eventual_with_migration[1] <= 1500
    assert eventual_with_migration[2] <= 896
    assert eventual_with_migration[3] <= 1536


def test_final_quota_and_pvc_budget() -> None:
    steady_names = {
        "smartenergy-api",
        "smartenergy-worker",
        "smartenergy-beat",
        "smartenergy-postgres",
        "smartenergy-redis",
    }
    measured: dict[str, tuple[int, int, int, int]] = {}
    for workload in [
        resource
        for resource in resources()
        if resource["kind"] in {"Deployment", "StatefulSet"}
    ]:
        values = container(workload)["resources"]
        measured[workload["metadata"]["name"]] = (
            cpu_millicores(values["requests"]["cpu"]),
            cpu_millicores(values["limits"]["cpu"]),
            memory_mebibytes(values["requests"]["memory"]),
            memory_mebibytes(values["limits"]["memory"]),
        )
    assert set(measured) == steady_names
    steady = tuple(
        sum(values[index] for values in measured.values()) for index in range(4)
    )
    assert steady == (210, 1000, 592, 1120)

    transient = (25, 150, 96, 192)
    with_one_job = tuple(steady[index] + transient[index] for index in range(4))
    assert with_one_job == (235, 1150, 688, 1312)
    assert all(
        actual <= limit
        for actual, limit in zip(with_one_job, (500, 1500, 896, 1536), strict=True)
    )
    assert len(steady_names) + 1 <= 12

    claims = [
        claim
        for workload in resources()
        if workload["kind"] == "StatefulSet"
        for claim in workload["spec"]["volumeClaimTemplates"]
    ]
    assert len(claims) == 2
    assert {claim["spec"]["resources"]["requests"]["storage"] for claim in claims} == {
        "1Gi",
        "5Gi",
    }
    assert (
        sum(
            int(claim["spec"]["resources"]["requests"]["storage"][:-2])
            for claim in claims
        )
        == 6
    )


def test_api_ports_and_probes() -> None:
    api = by_kind_name("Deployment", "smartenergy-api")
    runtime = container(api)
    assert {(port["name"], port["containerPort"]) for port in runtime["ports"]} == {
        ("http", 8000),
        ("metrics", 9090),
    }
    assert runtime["startupProbe"]["httpGet"] == {
        "path": "/api/health/z",
        "port": "http",
    }
    assert runtime["livenessProbe"]["httpGet"] == {
        "path": "/api/health/z",
        "port": "http",
    }
    assert runtime["readinessProbe"]["httpGet"] == {
        "path": "/api/health/readyz",
        "port": "http",
    }

    service = by_kind_name("Service", "smartenergy-api")
    assert service["spec"]["type"] == "ClusterIP"
    assert {(port["name"], port["port"]) for port in service["spec"]["ports"]} == {
        ("http", 8000),
        ("metrics", 9090),
    }


def test_postgres_stateful_contract() -> None:
    postgres = by_kind_name("StatefulSet", "smartenergy-postgres")
    spec = pod_spec(postgres)
    runtime = container(postgres)
    assert postgres["spec"]["replicas"] == 1
    assert postgres["spec"]["serviceName"] == "smartenergy-postgres"
    assert runtime["image"] == POSTGRES_IMAGE
    assert runtime["resources"] == {
        "requests": {"cpu": "75m", "memory": "192Mi"},
        "limits": {"cpu": "300m", "memory": "384Mi"},
    }
    assert env_map(postgres)["PGDATA"]["value"] == "/var/lib/postgresql/data/pgdata"
    assert set(env_map(postgres)) == {
        "PGDATA",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    }
    assert all(
        "pg_isready" in probe["exec"]["command"][-1]
        for probe in (
            runtime["startupProbe"],
            runtime["readinessProbe"],
            runtime["livenessProbe"],
        )
    )
    claim = postgres["spec"]["volumeClaimTemplates"][0]
    assert claim["metadata"]["name"] == "data"
    assert claim["spec"]["storageClassName"] == "local-path"
    assert claim["spec"]["resources"]["requests"]["storage"] == "5Gi"
    assert spec["securityContext"]["runAsUser"] == 999
    assert spec["securityContext"]["runAsGroup"] == 999
    assert spec["securityContext"]["fsGroup"] == 999

    service = by_kind_name("Service", "smartenergy-postgres")
    assert service["spec"]["type"] == "ClusterIP"
    assert service["spec"]["ports"] == [
        {"name": "postgres", "port": 5432, "targetPort": "postgres", "protocol": "TCP"}
    ]


def test_redis_stateful_contract() -> None:
    redis = by_kind_name("StatefulSet", "smartenergy-redis")
    spec = pod_spec(redis)
    runtime = container(redis)
    script = runtime["args"][0]
    assert redis["spec"]["replicas"] == 1
    assert redis["spec"]["serviceName"] == "smartenergy-redis"
    assert runtime["image"] == REDIS_IMAGE
    assert runtime["resources"] == {
        "requests": {"cpu": "25m", "memory": "48Mi"},
        "limits": {"cpu": "100m", "memory": "96Mi"},
    }
    assert "appendonly yes" in script
    assert "appendfsync everysec" in script
    assert "requirepass %s" in script
    assert "$REDIS_PASSWORD" in script
    assert set(env_map(redis)) == {"REDIS_PASSWORD", "REDISCLI_AUTH"}
    claim = redis["spec"]["volumeClaimTemplates"][0]
    assert claim["spec"]["storageClassName"] == "local-path"
    assert claim["spec"]["resources"]["requests"]["storage"] == "1Gi"
    assert spec["securityContext"]["runAsUser"] == 999
    assert spec["securityContext"]["runAsGroup"] == 999
    assert spec["securityContext"]["fsGroup"] == 999

    service = by_kind_name("Service", "smartenergy-redis")
    assert service["spec"]["type"] == "ClusterIP"
    assert service["spec"]["ports"] == [
        {"name": "redis", "port": 6379, "targetPort": "redis", "protocol": "TCP"}
    ]


def test_stateful_restricted_security() -> None:
    workloads = [
        by_kind_name("StatefulSet", "smartenergy-postgres"),
        by_kind_name("StatefulSet", "smartenergy-redis"),
    ]
    for workload in workloads:
        spec = pod_spec(workload)
        assert spec["automountServiceAccountToken"] is False
        assert spec["securityContext"]["runAsNonRoot"] is True
        assert spec["securityContext"]["seccompProfile"] == {"type": "RuntimeDefault"}
        for runtime in all_containers(workload):
            security = runtime["securityContext"]
            assert security["allowPrivilegeEscalation"] is False
            assert security["readOnlyRootFilesystem"] is True
            assert security["capabilities"] == {"drop": ["ALL"]}


def test_optional_backup_template_is_safe_and_excluded_from_production() -> None:
    backup = yaml.safe_load(BACKUP_CRONJOB.read_text())
    assert backup["spec"]["schedule"] == "30 2 * * *"
    assert backup["spec"]["timeZone"] == "Etc/UTC"
    assert backup["spec"]["concurrencyPolicy"] == "Forbid"
    spec = pod_spec(backup)
    dump, upload = all_containers(backup)
    assert dump["image"] == POSTGRES_IMAGE
    assert upload["image"] == CURL_IMAGE
    dump_env = {entry["name"]: entry for entry in dump["env"]}
    assert dump_env["IMAGE_SOURCE_REVISION"]["value"] == IMAGE_SOURCE_REVISION
    assert "pg_dump --format=custom" in dump["args"][0]
    assert "${IMAGE_SOURCE_REVISION}" in dump["args"][0]
    assert "alembic_version" in dump["args"][0]
    assert "curl --config /tmp/curl.conf" in upload["args"][0]
    assert "fail-with-body" in upload["args"][0]
    assert dump["resources"] == {
        "requests": {"cpu": "25m", "memory": "96Mi"},
        "limits": {"cpu": "150m", "memory": "192Mi"},
    }
    assert upload["resources"] == {
        "requests": {"cpu": "10m", "memory": "32Mi"},
        "limits": {"cpu": "50m", "memory": "64Mi"},
    }
    assert spec["restartPolicy"] == "Never"
    assert not any(
        resource["kind"] == "CronJob"
        and resource["metadata"]["name"] == "smartenergy-postgres-backup"
        for resource in resources()
    )


def test_restore_job_is_explicit_safe_and_excluded_from_production() -> None:
    restore = yaml.safe_load(RESTORE_JOB.read_text())
    assert restore["metadata"]["generateName"] == "smartenergy-postgres-restore-"
    assert restore["spec"]["backoffLimit"] == 0
    dump, restore_runtime = all_containers(restore)
    assert dump["image"] == CURL_IMAGE
    assert restore_runtime["image"] == POSTGRES_IMAGE
    assert "BACKUP_OBJECT_KEY" in {entry["name"] for entry in dump["env"]}
    assert (
        "target database already exists; refusing overwrite"
        in restore_runtime["args"][0]
    )
    assert (
        'test "$CONFIRM_RESTORE" = "restore:$TARGET_DATABASE"'
        in restore_runtime["args"][0]
    )
    assert not any(
        resource["kind"] == "Job"
        and resource["metadata"].get("generateName") == "smartenergy-postgres-restore-"
        for resource in resources()
    )


def test_migration_job_is_a_diagnosable_sync_hook() -> None:
    migration = by_kind_name("Job", "smartenergy-migration")
    annotations = migration["metadata"]["annotations"]
    assert annotations["argocd.argoproj.io/hook"] == "Sync"
    assert annotations["argocd.argoproj.io/hook-delete-policy"] == "BeforeHookCreation"
    assert annotations["argocd.argoproj.io/sync-wave"] == "-1"
    assert (
        annotations["smartenergy.eoghanclancy.eu/image-source-revision"]
        == IMAGE_SOURCE_REVISION
    )
    assert container(migration)["command"] == ["alembic", "upgrade", "head"]
    assert set(env_map(migration)) == {"DATABASE_URL"}
    assert migration["spec"]["backoffLimit"] == 2
    assert migration["spec"]["activeDeadlineSeconds"] == 600
    assert not any(
        resource["kind"] == "Service"
        and resource["metadata"]["name"] == "smartenergy-migration"
        for resource in resources()
    )


def test_config_and_secret_references_match_documented_contract() -> None:
    config = by_kind_name("ConfigMap", "smartenergy-config")
    assert config["data"] == {
        "ENV": "prod",
        "LOG_LEVEL": "INFO",
        "PORT": "8000",
        "JWT_ALG": "HS256",
        "JWT_EXPIRE_MINUTES": "60",
        "CACHE_TTL_SECONDS": "60",
        "SEED_DEMO": "0",
        "ENABLE_TELEMETRY": "0",
        "ENABLE_API_DOCS": "0",
        "METRICS_HOST": "0.0.0.0",
        "METRICS_PORT": "9090",
    }
    contract = {
        "smartenergy-runtime": {"JWT_SECRET"},
        "smartenergy-postgres": {
            "DATABASE_URL",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
        },
        "smartenergy-redis": {
            "REDIS_URL",
            "CELERY_BROKER_URL",
            "CELERY_RESULT_BACKEND",
            "REDIS_PASSWORD",
        },
    }
    references: dict[str, set[str]] = {name: set() for name in contract}
    for workload in [
        resource
        for resource in resources()
        if resource["kind"] in {"Deployment", "StatefulSet", "Job", "CronJob"}
    ]:
        for runtime in all_containers(workload):
            for source in runtime.get("envFrom", []):
                assert source == {"configMapRef": {"name": "smartenergy-config"}}
            for entry in runtime.get("env", []):
                if "valueFrom" not in entry:
                    continue
                reference = entry["valueFrom"]["secretKeyRef"]
                assert reference["name"] in contract
                assert reference["key"] in contract[reference["name"]]
                references[reference["name"]].add(reference["key"])
    assert references == contract


def test_default_deny_and_dns_policies() -> None:
    default_deny = by_kind_name("NetworkPolicy", "default-deny")
    assert default_deny["spec"] == {
        "podSelector": {},
        "policyTypes": ["Ingress", "Egress"],
        "ingress": [],
        "egress": [],
    }
    dns = by_kind_name("NetworkPolicy", "allow-dns-egress")["spec"]["egress"][0]
    assert dns["to"][0]["namespaceSelector"]["matchLabels"] == {
        "kubernetes.io/metadata.name": "kube-system"
    }
    assert dns["to"][0]["podSelector"]["matchLabels"] == {"k8s-app": "kube-dns"}
    assert {(port["protocol"], port["port"]) for port in dns["ports"]} == {
        ("UDP", 53),
        ("TCP", 53),
    }


def test_ingress_identity_policies_are_port_scoped() -> None:
    traefik = by_kind_name("NetworkPolicy", "allow-traefik-api-ingress")["spec"]
    traefik_rule = traefik["ingress"][0]
    assert traefik_rule["from"][0]["podSelector"]["matchLabels"] == {
        "app.kubernetes.io/name": "traefik",
        "app.kubernetes.io/instance": "traefik-kube-system",
    }
    assert traefik_rule["ports"] == [{"protocol": "TCP", "port": 8000}]

    prometheus = by_kind_name("NetworkPolicy", "allow-prometheus-metrics-ingress")[
        "spec"
    ]
    prometheus_rule = prometheus["ingress"][0]
    assert prometheus_rule["from"][0]["podSelector"]["matchLabels"] == {
        "app.kubernetes.io/name": "prometheus",
        "app.kubernetes.io/instance": "observability",
        "app.kubernetes.io/component": "server",
    }
    assert prometheus_rule["ports"] == [{"protocol": "TCP", "port": 9090}]


def test_cert_manager_http01_solver_ingress_is_exact() -> None:
    solver = by_kind_name(
        "NetworkPolicy", "allow-traefik-cert-manager-http01-solver-ingress"
    )["spec"]
    assert solver == {
        "podSelector": {"matchLabels": {"acme.cert-manager.io/http01-solver": "true"}},
        "policyTypes": ["Ingress"],
        "ingress": [
            {
                "from": [
                    {
                        "namespaceSelector": {
                            "matchLabels": {
                                "kubernetes.io/metadata.name": "kube-system"
                            }
                        },
                        "podSelector": {
                            "matchLabels": {
                                "app.kubernetes.io/name": "traefik",
                                "app.kubernetes.io/instance": "traefik-kube-system",
                            }
                        },
                    }
                ],
                "ports": [{"protocol": "TCP", "port": 8089}],
            }
        ],
    }
    assert not any(port in str(solver) for port in ("8000", "9090", "5432", "6379"))


def test_stateful_egress_contracts_are_exact() -> None:
    postgres = by_kind_name("NetworkPolicy", "allow-postgres-egress")["spec"]
    redis = by_kind_name("NetworkPolicy", "allow-redis-egress")["spec"]
    assert postgres["egress"][0]["to"][0]["podSelector"]["matchLabels"] == {
        "app.kubernetes.io/name": "smartenergy-postgres",
        "app.kubernetes.io/component": "database",
    }
    assert postgres["egress"][0]["ports"] == [{"protocol": "TCP", "port": 5432}]
    assert redis["egress"][0]["to"][0]["podSelector"]["matchLabels"] == {
        "app.kubernetes.io/name": "smartenergy-redis",
        "app.kubernetes.io/component": "cache",
    }
    assert redis["egress"][0]["ports"] == [{"protocol": "TCP", "port": 6379}]


def test_stateful_ingress_contracts_are_exact() -> None:
    postgres = by_kind_name("NetworkPolicy", "allow-postgres-ingress")["spec"]
    redis = by_kind_name("NetworkPolicy", "allow-redis-ingress")["spec"]
    assert postgres["ingress"][0]["from"][0]["podSelector"]["matchExpressions"][0][
        "values"
    ] == ["api", "worker", "migration"]
    assert postgres["ingress"][0]["ports"] == [{"protocol": "TCP", "port": 5432}]
    assert redis["ingress"][0]["from"][0]["podSelector"]["matchExpressions"][0][
        "values"
    ] == ["api", "worker", "beat"]
    assert redis["ingress"][0]["ports"] == [{"protocol": "TCP", "port": 6379}]

    assert "cidr: 0.0.0.0/0" not in rendered_text()


def test_backup_resources_are_excluded_from_production() -> None:
    identities = {
        (resource["kind"], resource["metadata"]["name"]) for resource in resources()
    }
    assert ("CronJob", "smartenergy-postgres-backup") not in identities
    assert ("NetworkPolicy", "allow-backup-object-storage-egress") not in identities
    assert "smartenergy-backup" not in rendered_text()


def test_public_ingress_tls_and_middleware_contract() -> None:
    ingress = by_kind_name("Ingress", "smartenergy")
    assert ingress["spec"]["ingressClassName"] == "traefik"
    assert ingress["spec"]["rules"][0]["host"] == "energy.platform.eoghanclancy.eu"
    backend = ingress["spec"]["rules"][0]["http"]["paths"][0]["backend"]["service"]
    assert backend == {"name": "smartenergy-api", "port": {"name": "http"}}
    assert "metrics" not in str(ingress["spec"])

    certificate = by_kind_name("Certificate", "smartenergy")
    assert certificate["spec"] == {
        "secretName": "smartenergy-tls",
        "dnsNames": ["energy.platform.eoghanclancy.eu"],
        "issuerRef": {
            "group": "cert-manager.io",
            "kind": "ClusterIssuer",
            "name": "letsencrypt-production",
        },
    }
    redirect = by_kind_name("Middleware", "redirect-https")
    disable_docs = by_kind_name("Middleware", "disable-api-docs")
    rate_limit = by_kind_name("Middleware", "rate-limit")
    assert redirect["spec"] == {
        "redirectScheme": {"scheme": "https", "permanent": True}
    }
    assert disable_docs["spec"] == {
        "replacePathRegex": {
            "regex": r"^/(docs|redoc|openapi\.json)(/.*)?$",
            "replacement": "/_documentation-disabled",
        }
    }
    assert rate_limit["spec"] == {
        "rateLimit": {"average": 5, "burst": 10, "period": "1s"}
    }
    assert ingress["metadata"]["annotations"][
        "traefik.ingress.kubernetes.io/router.middlewares"
    ] == (
        "smartenergy-redirect-https@kubernetescrd,"
        "smartenergy-disable-api-docs@kubernetescrd,"
        "smartenergy-rate-limit@kubernetescrd"
    )
