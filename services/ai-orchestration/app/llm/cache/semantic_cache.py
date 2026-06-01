"""
Two-layer prompt cache:
  L1 — MD5 exact match in Redis (sub-ms)
  L2 — Qdrant semantic similarity (cosine > 0.97 threshold)
"""
import hashlib
import json
import logging
import uuid

from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.redis_client import get_redis_sync
from app.core.qdrant_client import get_qdrant

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.97
TTL_SECONDS = 3600


class SemanticPromptCache:
    def __init__(self, task_type: str):
        self.collection = f"prompt_cache_{task_type.replace('.', '_')}"
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
        return self._encoder

    def _prompt_to_text(self, messages: list[dict]) -> str:
        return " ".join(m.get("content", "") for m in messages)

    async def get(self, messages: list[dict]) -> str | None:
        redis = get_redis_sync()
        text  = self._prompt_to_text(messages)

        # L1: exact
        l1_key = f"pc:exact:{hashlib.md5(text.encode()).hexdigest()}"
        if val := await redis.get(l1_key):
            logger.debug("Prompt cache L1 hit")
            return val

        # L2: semantic
        try:
            encoder = self._get_encoder()
            embedding = encoder.encode(text, normalize_embeddings=True).tolist()
            qdrant = get_qdrant()
            results = await qdrant.search(
                collection_name=self.collection,
                query_vector=embedding,
                limit=1,
                score_threshold=SIMILARITY_THRESHOLD,
                with_payload=True,
            )
            if results:
                resp_key = results[0].payload.get("response_key")
                if resp_key:
                    if val := await redis.get(resp_key):
                        logger.debug("Prompt cache L2 hit (score=%.3f)", results[0].score)
                        return val
        except Exception as e:
            logger.warning("Semantic cache lookup failed: %s", e)

        return None

    async def set(self, messages: list[dict], response: str) -> None:
        redis = get_redis_sync()
        text  = self._prompt_to_text(messages)

        l1_key   = f"pc:exact:{hashlib.md5(text.encode()).hexdigest()}"
        resp_key = f"pc:resp:{hashlib.sha256(text.encode()).hexdigest()}"

        await redis.setex(l1_key, TTL_SECONDS, response)
        await redis.setex(resp_key, TTL_SECONDS, response)

        try:
            encoder   = self._get_encoder()
            embedding = encoder.encode(text, normalize_embeddings=True).tolist()
            qdrant    = get_qdrant()
            await qdrant.upsert(
                collection_name=self.collection,
                points=[PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={"response_key": resp_key},
                )],
            )
        except Exception as e:
            logger.warning("Semantic cache write failed: %s", e)
