"""
Cross-encoder reranker using ms-marco-MiniLM-L-6-v2.
Converts a 200-candidate ANN result set into a top-20 ranked list
with ~50ms latency on CPU (batch=50).
"""
import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def load_cross_encoder() -> CrossEncoder:
    logger.info("Loading cross-encoder: %s", CROSS_ENCODER_MODEL)
    return CrossEncoder(CROSS_ENCODER_MODEL, max_length=512)


def rerank(
    query_text: str,
    candidates: list[dict],
    top_k: int = 20,
    description_key: str = "description_compressed",
) -> list[dict]:
    """
    Args:
        query_text: Resume text (compressed) used as the query.
        candidates: List of job dicts with description_compressed field.
        top_k: Number of results to return after reranking.

    Returns:
        Reranked list of job dicts with added 'cross_encoder_score' field.
    """
    if not candidates:
        return []

    model = load_cross_encoder()
    pairs = [
        (query_text, c.get(description_key) or c.get("description_text", "")[:512])
        for c in candidates
    ]

    scores: np.ndarray = model.predict(pairs, batch_size=50, show_progress_bar=False)

    ranked = sorted(
        zip(candidates, scores.tolist()),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    return [
        {**job, "cross_encoder_score": score, "rank": i + 1}
        for i, (job, score) in enumerate(ranked)
    ]


def reciprocal_rank_fusion(
    vector_results: list[dict],
    cross_encoder_results: list[dict],
    k: int = 60,
    id_key: str = "job_id",
) -> list[dict]:
    """
    Fuse vector search ranks and cross-encoder ranks via RRF.
    RRF score = 1/(k + rank_A) + 1/(k + rank_B)
    """
    vector_rank = {r[id_key]: i + 1 for i, r in enumerate(vector_results)}
    cross_rank  = {r[id_key]: i + 1 for i, r in enumerate(cross_encoder_results)}

    all_ids = set(vector_rank) | set(cross_rank)
    fused = {
        jid: (
            1 / (k + vector_rank.get(jid, len(vector_rank) + k))
            + 1 / (k + cross_rank.get(jid, len(cross_rank) + k))
        )
        for jid in all_ids
    }

    id_to_doc = {r[id_key]: r for r in vector_results + cross_encoder_results}
    return [
        {**id_to_doc[jid], "rrf_score": score}
        for jid, score in sorted(fused.items(), key=lambda x: x[1], reverse=True)
    ]
