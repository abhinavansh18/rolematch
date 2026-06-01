"""
Node: reranker
Cross-encoder reranking + RRF fusion over top-200 ANN candidates.
Populates: ranked_jobs
"""
import logging

from app.agents.graphs.match_graph import MatchState
from ml.reranker.cross_encoder_reranker import rerank, reciprocal_rank_fusion

logger = logging.getLogger(__name__)


async def reranker_node(state: MatchState) -> MatchState:
    qdrant_results = state.get("_qdrant_results", [])
    resume = state.get("resume_structured") or {}

    if not qdrant_results:
        logger.warning("No ANN candidates to rerank for match %s", state["match_id"])
        return {**state, "ranked_jobs": []}

    # Build query text from resume summary
    query_text = (
        f"Title: {resume.get('current_title', '')} "
        f"Skills: {', '.join(resume.get('skills', [])[:15])} "
        f"Experience: {resume.get('total_experience_years', 0)} years"
    )

    # Convert Qdrant results to dicts
    candidates = [
        {
            "job_id":               str(r.id),
            "title":                r.payload.get("title", ""),
            "company":              r.payload.get("company", ""),
            "location":             r.payload.get("location", ""),
            "skills":               r.payload.get("skills", []),
            "description_compressed": r.payload.get("description_compressed", ""),
            "vector_score":         r.score,
        }
        for r in qdrant_results
    ]

    # Cross-encoder rerank (CPU, ~50ms for 200 candidates)
    cross_ranked = rerank(query_text, candidates, top_k=20)

    # RRF fusion: vector rank + cross-encoder rank
    fused = reciprocal_rank_fusion(candidates[:20], cross_ranked, id_key="job_id")

    logger.info(
        "Reranked %d candidates → top %d for match %s",
        len(candidates), len(fused), state["match_id"],
    )
    return {**state, "ranked_jobs": fused[:20]}
