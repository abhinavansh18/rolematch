"""
Node: match_scorer
Scores top-20 jobs concurrently using cheap LLM (Groq/llama-70b).
Populates: scored_jobs
"""
import asyncio
import json
import logging

from app.agents.graphs.match_graph import MatchState
from app.llm.router.llm_router import LLMRouter

logger = logging.getLogger(__name__)
llm_router = LLMRouter()

MAX_CONCURRENT = 5  # Semaphore to control LLM concurrency


async def match_scorer_node(state: MatchState) -> MatchState:
    ranked_jobs = state["ranked_jobs"] or []
    resume = state["resume_structured"] or {}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def score_one(job: dict) -> dict:
        async with semaphore:
            prompt = [
                {
                    "role": "user",
                    "content": f"""Score this job match 0-100. Return JSON only.
Keys: overall_score (int), skill_match_score (int), experience_match_score (int),
skill_gaps (list[str]), strengths (list[str]), apply_confidence (low|medium|high)

Candidate: title={resume.get('current_title')}, skills={resume.get('skills', [])[:15]}, years={resume.get('total_experience_years')}
Job: title={job.get('title')}, skills={job.get('skills', [])[:15]}
Job description excerpt: {job.get('description_compressed', job.get('description_text', ''))[:400]}""",
                }
            ]
            try:
                resp = await llm_router.route(
                    task_type="bulk_scoring",
                    messages=prompt,
                    user_tier=state.get("user_tier", "free"),
                )
                scores = json.loads(resp.content)
                return {**job, "match_scores": scores}
            except Exception as e:
                logger.warning("Scoring failed for job %s: %s", job.get("job_id"), e)
                return {**job, "match_scores": {"overall_score": 0, "error": str(e)}}

    scored = await asyncio.gather(*[score_one(j) for j in ranked_jobs[:20]])
    scored_sorted = sorted(
        scored, key=lambda j: j.get("match_scores", {}).get("overall_score", 0), reverse=True
    )
    logger.info("Scored %d jobs for match %s", len(scored_sorted), state["match_id"])
    return {**state, "scored_jobs": scored_sorted}
