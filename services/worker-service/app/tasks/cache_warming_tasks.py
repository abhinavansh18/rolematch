"""
Celery tasks to pre-warm Redis caches.
Runs every 15 minutes via beat scheduler.
"""
import asyncio
import json
import logging

from celery_app import celery

logger = logging.getLogger(__name__)


@celery.task
def warm_top_jobs_cache():
    """Pre-compute and cache top jobs per common search term."""
    asyncio.run(_warm_async())


async def _warm_async():
    import redis.asyncio as aioredis
    from shared.config.settings import get_settings

    settings = get_settings()
    redis    = aioredis.from_url(settings.redis_url, db=settings.redis_cache_db, decode_responses=True)

    COMMON_QUERIES = [
        "software engineer", "data scientist", "product manager",
        "devops engineer", "ml engineer", "backend developer",
    ]

    for query in COMMON_QUERIES:
        cache_key = f"top_jobs:query:{query.replace(' ', '_')}"
        if not await redis.exists(cache_key):
            # In production: call job-service search API and cache results
            await redis.setex(cache_key, 900, json.dumps({"query": query, "warmed": True}))
            logger.info("Warmed cache for query: %s", query)

    await redis.aclose()
