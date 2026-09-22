from __future__ import annotations

from types import SimpleNamespace
from urllib.request import urlopen

import pytest
from fastapi import status

from app.api.metrics import start_metrics_server, stop_metrics_server


@pytest.mark.asyncio
async def test_public_api_does_not_expose_metrics(client):
    response = await client.get("/api/metrics")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_private_listener_serves_bounded_request_metrics(client):
    server, thread = start_metrics_server("127.0.0.1", 0)
    try:
        await client.get("/api/health/z")
        await client.get("/not-a-real-route-one")
        await client.get("/not-a-real-route-two")
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/metrics", timeout=2
        ) as response:
            body = response.read().decode()
    finally:
        stop_metrics_server(server, thread)

    assert "http_requests_total" in body
    assert 'path="/api/health/z"' in body
    assert 'path="unmatched"' in body
    assert "not-a-real-route-one" not in body
    assert "not-a-real-route-two" not in body
    assert "cache_hits_total" in body
    assert "cache_misses_total" in body


@pytest.mark.asyncio
async def test_metrics_listener_follows_api_lifespan(monkeypatch):
    from app import main

    calls: list[str] = []
    server = object()
    thread = object()

    monkeypatch.setattr(
        main,
        "start_metrics_server",
        lambda _host, _port: (server, thread),
    )
    monkeypatch.setattr(
        main,
        "stop_metrics_server",
        lambda actual_server, actual_thread: calls.append(
            f"stop:{actual_server is server}:{actual_thread is thread}"
        ),
    )

    async def no_op() -> None:
        return None

    monkeypatch.setattr(main, "get_redis", no_op)
    monkeypatch.setattr(main, "close_redis", no_op)
    monkeypatch.setattr(main, "engine", SimpleNamespace(dispose=no_op))

    async with main.lifespan(main.app):
        calls.append("running")

    assert calls == ["running", "stop:True:True"]
