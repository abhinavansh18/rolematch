import redis.asyncio as aioredis
from functools import lru_cache
from shared.config.settings import get_settings

settings = get_settings()

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            db=settings.redis_state_db,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis


def get_redis_sync() -> aioredis.Redis:
    """Return cached Redis client (must call get_redis() at least once first)."""
    global _redis
    if _redis is None:
        import asyncio
        _redis = asyncio.get_event_loop().run_until_complete(get_redis())
    return _redis
