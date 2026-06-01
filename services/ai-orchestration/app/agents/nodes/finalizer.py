"""
Node: finalizer
Persists match results, publishes completion event, pushes WebSocket update.
"""
import json
import logging
from datetime import datetime

from app.agents.graphs.match_graph import MatchState
from app.core.redis_client import get_redis_sync
from shared.utils.kafka import get_producer, publish

logger = logging.getLogger(__name__)


async def finalizer_node(state: MatchState) -> MatchState:
    redis    = get_redis_sync()
    match_id = state["match_id"]
    user_id  = state["user_id"]
    scored   = state.get("scored_jobs", [])

    results_payload = {
        "match_id":    match_id,
        "user_id":     user_id,
        "results":     scored[:10],
        "total_found": len(scored),
        "completed_at": datetime.utcnow().isoformat(),
        "status":      "done",
    }

    # ── Persist to Redis (fast read path) ─────────────────────────────────────
    await redis.setex(f"match_status:{match_id}", 7200, "done")
    await redis.setex(f"match_results:{match_id}", 7200, json.dumps(results_payload))

    # ── Push WebSocket update ──────────────────────────────────────────────────
    await redis.publish(
        f"match_updates:{match_id}",
        json.dumps({"status": "done", "results": scored[:5]}),
    )

    # ── Kafka event for downstream consumers (notifications, analytics) ────────
    producer = await get_producer()
    try:
        await publish(producer, "match.completed", results_payload, key=user_id)
    finally:
        await producer.stop()

    # ── Async Postgres write (fire-and-forget via worker) ─────────────────────
    await publish_to_analytics_worker(match_id, state)

    logger.info("Match %s finalised with %d results", match_id, len(scored))
    return {**state, "status": "done"}


async def publish_to_analytics_worker(match_id: str, state: MatchState) -> None:
    """Write match record to Postgres via worker (keeps API path non-blocking)."""
    producer = await get_producer()
    try:
        await publish(producer, "analytics.match_completed", {
            "match_id":      match_id,
            "user_id":       state["user_id"],
            "resume_id":     state["resume_id"],
            "filters":       state["filters"],
            "result_count":  len(state.get("scored_jobs", [])),
            "created_at":    datetime.utcnow().isoformat(),
        })
    finally:
        await producer.stop()
