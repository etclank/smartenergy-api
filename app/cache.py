# app/cache.py
from __future__ import annotations

from typing import Optional
import redis.asyncio as redis
from app.config import settings

_redis: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    """
    Lazy-init a Redis client. Return None if REDIS_URL is empty.
    """
    global _redis
    if not settings.redis_url:
        return None
    if _redis is None:
        # decode_responses=True -> strings in/out (good for JSON)
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
