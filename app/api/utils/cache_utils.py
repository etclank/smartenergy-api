# app/api/utils/cache_utils.py
"""
Reusable decorator for caching FastAPI GET responses in Redis.

Usage:
    from app.api.utils.cache_utils import cache_response

    @router.get("/")
    @cache_response(ttl=60)
    async def list_energy_imported(...):
        ...
"""

from __future__ import annotations
import json
from functools import wraps
from fastapi import Request
from typing import Awaitable, Callable, Optional, TypeVar, ParamSpec

from app.core.cache import cache_get, cache_set
from app.core.config import settings

P = ParamSpec("P")
R = TypeVar("R")


def cache_response(ttl: Optional[int] = None) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Decorator for caching route responses in Redis.

    - Uses request URL (path + query) as cache key.
    - Serializes/deserializes JSON transparently.
    - Fails open if Redis unavailable.
    - Skips caching entirely if REDIS_URL unset.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = kwargs.get("request")
            if not isinstance(request, Request):
                request = None

            # Skip caching if disabled
            if not settings.redis_url:
                return await func(*args, **kwargs)

            # Build cache key
            if request is not None:
                path = request.url.path
                query = f"?{request.url.query}" if request.url.query else ""
            else:
                path, query = func.__name__, ""
            cache_key = f"cache:{path}{query}"

            # Try cached result
            cached = await cache_get(cache_key)
            if cached is not None:
                return cached

            # Compute and cache
            response = await func(*args, **kwargs)
            try:
                json.dumps(response)
                await cache_set(cache_key, response, ttl or settings.cache_ttl_seconds)
            except Exception:
                pass  # ignore serialization issues silently

            return response

        return wrapper

    return decorator
