"""
Node: job_retriever
ANN search in Qdrant using resume embedding + hard filters.
Populates: candidate_job_ids
"""
import logging

from app.agents.graphs.match_graph import MatchState
from app.core.qdrant_client import get_qdrant
from app.core.redis_client import get_redis_sync

logger = logging.getLogger(__name__)


async def job_retriever_node(state: MatchState) -> MatchState:
    redis = get_redis_sync()
    embedding = state["resume_embedding"]
    filters = state["filters"]

    # ── Cache: embedding hash → candidate job_ids ──────────────────────────────
    import hashlib, json
    embed_hash = hashlib.md5(str(embedding[:10]).encode()).hexdigest()
    cache_key = f"top_jobs:{embed_hash}:{json.dumps(filters, sort_keys=True)[:50]}"

    if cached := await redis.get(cache_key):
        return {**state, "candidate_job_ids": json.loads(cached)}

    qdrant = get_qdrant()
    filter_condition = _build_qdrant_filter(filters)

    results = await qdrant.search(
        collection_name="jobs",
        query_vector=embedding,
        query_filter=filter_condition,
        limit=200,
        search_params={"hnsw_ef": 128},
        with_payload=True,
    )

    job_ids = [str(r.id) for r in results]
    await redis.setex(cache_key, 900, json.dumps(job_ids))  # 15 min TTL

    logger.info("Retrieved %d candidates for match %s", len(job_ids), state["match_id"])
    return {**state, "candidate_job_ids": job_ids, "_qdrant_results": results}


def _build_qdrant_filter(filters: dict):
    from qdrant_client.models import FieldCondition, Filter, MatchAny, Range
    conditions = [FieldCondition(key="is_active", match={"value": True})]

    if remote := filters.get("remote_type"):
        conditions.append(FieldCondition(key="remote_type", match=MatchAny(any=[remote])))
    if salary_min := filters.get("salary_min"):
        conditions.append(FieldCondition(key="salary_max", range=Range(gte=salary_min)))
    if location := filters.get("location"):
        conditions.append(FieldCondition(key="location", match={"value": location}))

    return Filter(must=conditions) if conditions else None
