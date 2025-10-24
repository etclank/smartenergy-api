# app/api/utils/cache_utils.py
"""
Reusable decorator for caching FastAPI GET responses in Redis.

Emits Prometheus metrics for cache hits and misses.
"""

from __future__ import annotations
import json
from functools import wraps
from fastapi import Request
from typing import Awaitable, Callable, Optional, TypeVar, ParamSpec, TYPE_CHECKING
from prometheus_client import Counter

from app.core.cache import cache_get, cache_set
from app.core.config import settings

# Type-only import to help mypy know what CACHE_HITS/CACHE_MISSES are
if TYPE_CHECKING:
    CACHE_HITS: Optional[Counter]
    CACHE_MISSES: Optional[Counter]

# Optional metrics integration (safe runtime import)
try:
    from app.api.metrics import CACHE_HITS as _CACHE_HITS, CACHE_MISSES as _CACHE_MISSES
    _hits: Optional[Counter] = _CACHE_HITS
    _misses: Optional[Counter] = _CACHE_MISSES
except Exception:  # pragma: no cover
    _hits = None
    _misses = None

CACHE_HITS = _hits
CACHE_MISSES = _misses

P = ParamSpec("P")
R = TypeVar("R")


def cache_response(ttl: Optional[int] = None) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Decorator for caching route responses in Redis.

    - Uses request URL (path + query) as cache key.
    - Emits Prometheus counters (cache_hits_total / cache_misses_total) if available.
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
                if CACHE_HITS:
                    CACHE_HITS.labels(endpoint=path).inc()
                return cached

            # Compute and cache
            response = await func(*args, **kwargs)
            try:
                json.dumps(response)
                await cache_set(cache_key, response, ttl or settings.cache_ttl_seconds)
                if CACHE_MISSES:
                    CACHE_MISSES.labels(endpoint=path).inc()
            except Exception:
                # ignore serialization or connection issues silently
                pass

            return response

        return wrapper

    return decorator
