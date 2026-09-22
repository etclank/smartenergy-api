# app/api/metrics.py
"""Prometheus metrics and the API process's private metrics listener."""

from threading import Thread
from wsgiref.simple_server import WSGIServer

from prometheus_client import (
    Counter,
    Histogram,
    REGISTRY,
    start_http_server,
)


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


def start_metrics_server(host: str, port: int) -> tuple[WSGIServer, Thread]:
    """Start the private Prometheus listener for the API process."""
    return start_http_server(port, addr=host)


def stop_metrics_server(server: WSGIServer, thread: Thread) -> None:
    """Stop a metrics listener created by :func:`start_metrics_server`."""
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
