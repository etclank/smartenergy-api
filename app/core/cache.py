# app/core/cache.py
from __future__ import annotations
import json
from typing import Any, Optional
import redis.asyncio as redis
from app.core.config import settings

_client: Optional[redis.Redis] = None


# --- Core connection --------------------------------------------------------
async def get_redis() -> Optional[redis.Redis]:
    """
    Return a singleton Redis client (Upstash or local).
    If REDIS_URL is unset or unreachable, return None gracefully.
    """
    global _client
    if _client or not settings.redis_url:
        return _client

    try:
        _client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            encoding="utf-8",
        )
        await _client.ping()
        print(f"[cache] Connected to Redis: {settings.redis_url}")
    except Exception as e:
        print(f"[cache] Redis unavailable ({e})")
        _client = None

    return _client


async def close_redis() -> None:
    global _client
    if _client:
        try:
            await _client.close()
        finally:
            _client = None


# --- Utility functions ------------------------------------------------------
async def ping_redis() -> bool:
    """Check if Redis is reachable."""
    client = await get_redis()
    if not client:
        return False
    try:
        return bool(await client.ping())
    except Exception:
        return False


async def cache_get(key: str) -> Optional[Any]:
    """Retrieve cached JSON value and deserialize."""
    client = await get_redis()
    if not client:
        return None
    try:
        val = await client.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """Serialize and store data in cache with optional TTL."""
    client = await get_redis()
    if not client:
        return
    try:
        payload = value if isinstance(value, str) else json.dumps(value, default=str)
        ttl = ttl or settings.cache_ttl_seconds
        await client.setex(key, ttl, payload)
    except Exception:
        # Fail open — never break API behavior
        pass
