# app/api/metrics.py
"""
Prometheus-compatible metrics endpoint for SmartEnergy API.
Collects request latency, status counts, and cache statistics.
Safe for reloads (avoids duplicate timeseries registration).
"""

from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)
from fastapi import APIRouter, Response

router = APIRouter(prefix="/metrics", tags=["metrics"])


# --- Prevent duplicate registration ---
def _metric_exists(name: str) -> bool:
    try:
        for collector in REGISTRY._names_to_collectors.keys():
            if collector.startswith(name):
                return True
    except Exception:
        pass
    return False


# --- Define metrics safely ---
if not _metric_exists("http_requests_total"):
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total number of HTTP requests",
        ["method", "path", "status"],
    )

if not _metric_exists("http_request_duration_seconds"):
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "Request latency in seconds",
        ["method", "path"],
    )

if not _metric_exists("cache_hits_total"):
    CACHE_HITS = Counter("cache_hits_total", "Number of cache hits", ["endpoint"])

if not _metric_exists("cache_misses_total"):
    CACHE_MISSES = Counter("cache_misses_total", "Number of cache misses", ["endpoint"])


@router.get("", include_in_schema=False)
@router.get("/", summary="Prometheus metrics")
async def metrics_endpoint() -> Response:
    """Return all metrics in Prometheus exposition format."""
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)
