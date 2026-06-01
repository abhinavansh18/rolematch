"""
Node: resume_analyzer
Loads and analyzes the resume, checking cache first.
Populates: resume_structured, resume_embedding
"""
import json
import logging

from app.agents.graphs.match_graph import MatchState
from app.core.redis_client import get_redis_sync
from app.llm.router.llm_router import LLMRouter
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)
llm_router = LLMRouter()
embedding_svc = EmbeddingService()


async def resume_analyzer_node(state: MatchState) -> MatchState:
    redis = get_redis_sync()
    resume_id = state["resume_id"]

    # ── Cache check ────────────────────────────────────────────────────────────
    cache_key = f"resume_analysis:{resume_id}"
    if cached := await redis.get(cache_key):
        logger.info("Cache hit for resume %s", resume_id)
        structured = json.loads(cached)
        embedding = await embedding_svc.get_or_create(resume_id, structured)
        return {**state, "resume_structured": structured, "resume_embedding": embedding}

    # ── Fetch raw resume text from DB / S3 ─────────────────────────────────────
    from app.services.resume_loader import load_resume_text
    resume_text = await load_resume_text(resume_id)

    # ── LLM structured extraction ──────────────────────────────────────────────
    extraction_prompt = [
        {
            "role": "user",
            "content": f"""Extract structured data from this resume as JSON.
Return ONLY valid JSON with keys:
name, email, current_title, total_experience_years,
skills (list), experience (list of {{title,company,description}}), education (list of {{degree,field,institution}})

Resume:
{resume_text[:4000]}""",
        }
    ]

    response = await llm_router.route(
        task_type="resume_analysis",
        messages=extraction_prompt,
        user_tier=state.get("user_tier", "free"),
    )

    structured = json.loads(response.content)
    await redis.setex(cache_key, 86400, json.dumps(structured))  # 24h TTL

    embedding = await embedding_svc.get_or_create(resume_id, structured)

    logger.info("Resume %s analyzed: %d skills", resume_id, len(structured.get("skills", [])))
    return {**state, "resume_structured": structured, "resume_embedding": embedding}
