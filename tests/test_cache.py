# tests/test_cache.py
import pytest
from app.core.cache import ping_redis, get_redis
from app.core.config import settings

@pytest.mark.asyncio
async def test_redis_connection_or_skip():
    """Verify Redis is reachable or skip test gracefully."""
    if not settings.redis_url:
        pytest.skip("REDIS_URL not set; skipping Redis tests")

    client = await get_redis()
    if client is None or not await ping_redis():
        pytest.skip(f"Redis not reachable ({settings.redis_url})")
    assert await ping_redis() is True
