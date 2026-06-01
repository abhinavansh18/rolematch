"""
Embedding processor: encodes normalized job text and upserts into Qdrant.
Uses BAAI/bge-large-en-v1.5 (1024-dim) with INT8 quantisation on CPU.
"""
import logging
from typing import cast

import numpy as np
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-large-en-v1.5")
        logger.info("Embedding model loaded")
    return _model


def _build_embed_text(job: dict) -> str:
    skills = ", ".join(job.get("skills", [])[:20])
    desc = job.get("description_compressed") or job.get("description_text", "")[:500]
    return f"Job Title: {job.get('title', '')}\nSkills: {skills}\nDescription: {desc}"


async def embed_and_store(jobs: list[dict]) -> None:
    if not jobs:
        return

    model = get_model()
    texts = [_build_embed_text(j) for j in jobs]
    embeddings: np.ndarray = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    qdrant = AsyncQdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key,
    )

    points = [
        PointStruct(
            id=job["job_id"],
            vector=cast(list[float], emb.tolist()),
            payload={
                "title":        job.get("title"),
                "company":      job.get("company"),
                "location":     job.get("location"),
                "remote_type":  job.get("remote_type"),
                "salary_min":   job.get("salary_min"),
                "salary_max":   job.get("salary_max"),
                "skills":       job.get("skills", []),
                "source_domain": job.get("source_domain"),
                "is_active":    True,
                "description_compressed": job.get("description_compressed", "")[:512],
            },
        )
        for job, emb in zip(jobs, embeddings)
    ]

    # Upsert in chunks of 100 to avoid payload size limits
    for i in range(0, len(points), 100):
        chunk = points[i : i + 100]
        await qdrant.upsert(collection_name=settings.qdrant_collection_jobs, points=chunk)

    logger.info("Upserted %d job embeddings to Qdrant", len(points))
    await qdrant.close()
