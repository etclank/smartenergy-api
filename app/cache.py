# app/cache.py
from __future__ import annotations

import json
from typing import Any, Optional

from redis.asyncio import Redis, from_url

from app.config import settings

_redis: Optional[Redis] = None


def _json_default(obj: Any) -> Any:
    # Pydantic v2 models
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    # Fallback that raises TypeError if it can't serialize
    raise TypeError(f"Object of type {type(obj)!r} is not JSON serializable")


def _build_client() -> Optional[Redis]:
    url = settings.redis_url
    if not url:
        return None
    try:
        # Works with redis://, rediss:// (e.g., Upstash)
        return Redis.from_url(url, decode_responses=True)
    except Exception:
        return None


async def get_redis() -> Redis:
    """Return a singleton Redis client; ping to verify connectivity."""
    global _redis
    if _redis is None:
        _redis = from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Warm check; don't crash if Redis is optional in dev
        try:
            await _redis.ping()
        except Exception:
            pass
    return _redis  # type: ignore[return-value]

async def close_redis() -> None:
    """Close the Redis client if it was created."""
    global _redis
    if _redis is not None:
        try:
            await _redis.close()
        finally:
            _redis = None


async def ping_redis() -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(await client.ping())
    except Exception:
        return False


async def cache_get(key: str) -> Optional[str]:
    client = get_redis()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        payload = value if isinstance(value, str) else json.dumps(value, default=_json_default)
        if ttl and ttl > 0:
            await client.setex(key, ttl, payload)
        else:
            await client.set(key, payload)
    except Exception:
        # fail-open: never break API on cache errors
        return
