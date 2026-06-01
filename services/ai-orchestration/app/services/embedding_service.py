import json
import logging

import numpy as np

from app.core.redis_client import get_redis_sync

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    return _model


class EmbeddingService:
    async def get_or_create(self, resume_id: str, structured: dict) -> list[float]:
        redis   = get_redis_sync()
        cache_k = f"resume_embedding:{resume_id}"

        if cached := await redis.get(cache_k):
            return json.loads(cached)

        text = (
            f"Title: {structured.get('current_title', '')}\n"
            f"Skills: {', '.join(structured.get('skills', [])[:20])}\n"
            f"Experience: {structured.get('total_experience_years', 0)} years\n"
            f"Summary: {structured.get('summary', '')[:300]}"
        )
        model     = _get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        emb_list  = embedding.tolist()

        await redis.setex(cache_k, 86400, json.dumps(emb_list))
        return emb_list
