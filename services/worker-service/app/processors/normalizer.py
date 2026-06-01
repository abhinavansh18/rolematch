"""
Batch normalizer: raw job HTML → NormalizedJob dicts.
Used by the Kafka job pipeline consumer.
"""
import asyncio
import logging
from datetime import datetime

import trafilatura

from shared.models.job import NormalizedJob
from shared.utils.hashing import sha256_hex, normalize_job_text
from services.job_service.app.scraper.parsers.job_normalizer import (
    parse_salary, detect_remote_type, extract_skills,
)

logger = logging.getLogger(__name__)


async def normalize_jobs(raw_batch: list[dict]) -> list[dict]:
    """
    Normalize a batch of raw job messages from Kafka.
    Each message has: {job_id, source, raw_html, scraped_at, idempotency_key}
    """
    tasks = [_normalize_one(msg) for msg in raw_batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    normalized = []
    for raw, result in zip(raw_batch, results):
        if isinstance(result, Exception):
            logger.warning("Normalization failed for %s: %s", raw.get("job_id"), result)
        else:
            normalized.append(result)
    return normalized


async def _normalize_one(msg: dict) -> dict:
    raw_html  = msg.get("raw_html", "")
    job_id    = msg.get("job_id", "")
    source    = msg.get("source", "")
    source_url = msg.get("source_url", "")

    text = trafilatura.extract(raw_html) or ""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    title = lines[0] if lines else "Unknown Role"

    salary_min, salary_max = parse_salary(text)
    remote_type = detect_remote_type(text)
    skills      = extract_skills(text)
    content_hash = sha256_hex(normalize_job_text(text))

    # Compress description to ~512 tokens (simple truncation; LLM compression in high-value path)
    compressed = text[:2000]

    return {
        "job_id":                job_id,
        "title":                 title,
        "company":               "",        # Extracted by crawler-specific parser
        "location":              "",
        "remote_type":           remote_type,
        "salary_min":            salary_min,
        "salary_max":            salary_max,
        "salary_currency":       "USD",
        "description_text":      text,
        "description_compressed": compressed,
        "skills":                skills,
        "content_hash":          content_hash,
        "source_url":            source_url or f"https://{source}.com",
        "source_domain":         source,
        "normalized_at":         datetime.utcnow().isoformat(),
        "idempotency_key":       msg.get("idempotency_key", content_hash),
    }
