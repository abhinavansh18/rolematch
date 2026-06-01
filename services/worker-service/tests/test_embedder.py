import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch


def test_build_embed_text():
    from app.processors.embedder import _build_embed_text
    job = {
        "title": "Senior Python Engineer",
        "skills": ["python", "fastapi", "postgres"],
        "description_compressed": "Build scalable backend systems.",
    }
    text = _build_embed_text(job)
    assert "Senior Python Engineer" in text
    assert "python" in text


def test_content_hash_stable():
    from services.job_service.app.services.dedup_service import content_hash
    h1 = content_hash("  Hello World  ")
    h2 = content_hash("hello world")
    assert h1 == h2, "Normalisation must make hashes stable"


@pytest.mark.asyncio
async def test_normalize_jobs_empty():
    from app.processors.normalizer import normalize_jobs
    result = await normalize_jobs([])
    assert result == []
