# app/cache.py
from __future__ import annotations

import json
from typing import Any, Optional, cast

from redis.asyncio import Redis, from_url

from app.config import settings

_redis: Optional[Redis] = None


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):  # Pydantic v2 models
        return obj.model_dump()
    raise TypeError(f"Object of type {type(obj)!r} is not JSON serializable")


async def get_redis() -> Redis:
    """Return a singleton Redis client; soft-fail if unreachable."""
    global _redis
    if _redis is None:
        _redis = from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await _redis.ping()
        except Exception:
            # keep the client but don't crash in dev
            pass
    return cast(Redis, _redis)


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.close()
        finally:
            _redis = None


async def ping_redis() -> bool:
    try:
        client = await get_redis()
    except Exception:
        return False
    try:
        return bool(await client.ping())
    except Exception:
        return False


async def cache_get(key: str) -> Optional[str]:
    try:
        client = await get_redis()
    except Exception:
        return None
    try:
        return await client.get(key)
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    try:
        client = await get_redis()
    except Exception:
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
