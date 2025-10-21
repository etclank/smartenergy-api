from __future__ import annotations

import httpx
from app.core.cache import get_redis
from app.core.config import settings


async def clean_stale_cache(pattern: str = "cache:*") -> dict:
    """
    Delete all Redis keys matching a given pattern.
    Safe if Redis unavailable (fail-open).
    """
    r = await get_redis()
    if not r:
        return {"status": "skip", "reason": "redis_unavailable"}

    deleted = 0
    try:
        keys: list[str] = []
        async for k in r.scan_iter(match=pattern):
            # decode Upstash bytes → str for safety
            key = k.decode() if isinstance(k, (bytes, bytearray)) else k
            keys.append(key)

        if keys:
            await r.delete(*keys)
            deleted = len(keys)

        return {"status": "ok", "deleted": deleted}
    except Exception as e:
        return {"status": "error", "error": str(e), "deleted": deleted}


async def warmup_cache(base_url: str | None = None) -> dict:
    """
    Pre-populate Redis cache by calling common read endpoints.
    Uses decorator @cache_response under each route.
    """
    # allow override via .env or parameter
    base_url = base_url or f"http://{settings.api_host}:{settings.api_port}"

    endpoints = [
        "/api/sites/",
        "/api/meters/",
        "/api/tariffs/",
        "/api/energy_imported/",
        "/api/energy_exported/",
        "/api/energy_reactive/",
        "/api/max_power/",
    ]

    ok = 0
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        for ep in endpoints:
            url = base_url.rstrip("/") + ep
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    ok += 1
                else:
                    errors.append(f"{ep} → {resp.status_code}")
            except Exception as e:
                errors.append(f"{ep} → {type(e).__name__}")

    return {
        "status": "ok" if ok else "partial" if errors else "skip",
        "warmed": ok,
        "total": len(endpoints),
        "errors": errors,
    }
