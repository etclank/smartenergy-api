from functools import lru_cache
from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).parents[1]
OVERLAY = ROOT / "deploy" / "kubernetes" / "overlays" / "production"
IMAGE = (
    "ghcr.io/etclank/smartenergy-api@"
    "sha256:7a35d14461bd6ee81bf67cf09bef792c866ad7673add9077e7b770e5fff99792"
)
REVISION = "1cbe7dd0991b1495dfabdd08a69a00755c5961aa"


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
    if resource["kind"] == "Deployment":
        return resource["spec"]["template"]["spec"]
    return resource["spec"]["template"]["spec"]


def container(resource: dict) -> dict:
    return pod_spec(resource)["containers"][0]


def env_map(resource: dict) -> dict[str, dict]:
    return {entry["name"]: entry for entry in container(resource).get("env", [])}


def cpu_millicores(value: str) -> int:
    assert value.endswith("m")
    return int(value.removesuffix("m"))


def memory_mebibytes(value: str) -> int:
    assert value.endswith("Mi")
    return int(value.removesuffix("Mi"))


def test_render_is_deterministic_complete_and_namespaced() -> None:
    second = subprocess.run(
        ["kubectl", "kustomize", str(OVERLAY)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    assert rendered_text() == second
    assert "replace-me" not in rendered_text()
    assert "${" not in rendered_text()

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


def test_runtime_roles_and_rollouts() -> None:
    api = by_kind_name("Deployment", "smartenergy-api")
    worker = by_kind_name("Deployment", "smartenergy-worker")
    beat = by_kind_name("Deployment", "smartenergy-beat")

    assert env_map(api)["ROLE"]["value"] == "web"
    assert env_map(worker)["ROLE"]["value"] == "worker"
    assert env_map(beat)["ROLE"]["value"] == "beat"
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
        "smartenergy-beat": (10, 50, 48, 96),
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
    assert eventual_steady == (210, 1000, 544, 1088)
    assert eventual_with_migration == (235, 1150, 640, 1280)
    assert eventual_with_migration[0] <= 500
    assert eventual_with_migration[1] <= 1500
    assert eventual_with_migration[2] <= 896
    assert eventual_with_migration[3] <= 1536


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


def test_migration_job_is_a_diagnosable_presync_hook() -> None:
    migration = by_kind_name("Job", "smartenergy-migration")
    annotations = migration["metadata"]["annotations"]
    assert annotations["argocd.argoproj.io/hook"] == "PreSync"
    assert annotations["argocd.argoproj.io/hook-delete-policy"] == "BeforeHookCreation"
    assert annotations["smartenergy.eoghanclancy.eu/revision"] == REVISION
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
        "smartenergy-postgres": {"DATABASE_URL"},
        "smartenergy-redis": {
            "REDIS_URL",
            "CELERY_BROKER_URL",
            "CELERY_RESULT_BACKEND",
        },
    }
    references: dict[str, set[str]] = {name: set() for name in contract}
    for workload in [
        resource
        for resource in resources()
        if resource["kind"] in {"Deployment", "Job"}
    ]:
        for source in container(workload).get("envFrom", []):
            assert source == {"configMapRef": {"name": "smartenergy-config"}}
        for entry in env_map(workload).values():
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
    assert "0.0.0.0/0" not in rendered_text()


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
