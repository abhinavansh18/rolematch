"""
Two-layer job deduplication:
  Layer 1 — Redis Bloom filter (fast, probabilistic, ~0.1% FPR)
  Layer 2 — Postgres exact content_hash check (authoritative)
"""
import hashlib
import logging
import re

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_model import JobModel
from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BLOOM_KEY = "job_urls_bloom"
BLOOM_CAPACITY = 50_000_000   # 50M URLs
BLOOM_ERROR_RATE = 0.001      # 0.1% false positive rate


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode()).hexdigest()


class DeduplicationService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db    = db
        self.redis = redis

    async def is_duplicate(self, url: str, description_text: str) -> bool:
        # Layer 1: Bloom filter (sub-millisecond)
        try:
            in_bloom = await self.redis.execute_command("BF.EXISTS", BLOOM_KEY, url)
            if not in_bloom:
                return False
        except Exception:
            logger.warning("Bloom filter unavailable — falling back to DB check")

        # Layer 2: Exact hash (DB)
        chash = content_hash(description_text)
        result = await self.db.execute(
            select(JobModel.id).where(JobModel.content_hash == chash).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def mark_seen(self, url: str) -> None:
        try:
            await self.redis.execute_command("BF.ADD", BLOOM_KEY, url)
        except Exception:
            logger.warning("Failed to add URL to bloom filter: %s", url)

    async def ensure_bloom_filter(self) -> None:
        """Idempotently create the bloom filter with desired capacity."""
        try:
            exists = await self.redis.execute_command("BF.EXISTS", BLOOM_KEY, "__probe__")
        except Exception:
            await self.redis.execute_command(
                "BF.RESERVE", BLOOM_KEY, BLOOM_ERROR_RATE, BLOOM_CAPACITY
            )
            logger.info("Bloom filter created: capacity=%d err=%.3f", BLOOM_CAPACITY, BLOOM_ERROR_RATE)
