"""
Match endpoints: submit a match request, stream results via WebSocket,
or poll for status.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.agents.graphs.match_graph import MatchGraph
from app.core.deps import get_current_user
from app.core.redis_client import get_redis
from shared.models.user import User

router = APIRouter()


class MatchRequest(BaseModel):
    resume_id: str
    filters: dict = {}


class MatchResponse(BaseModel):
    match_id: str
    status: str
    poll_url: str
    ws_url: str


@router.post("/request", response_model=MatchResponse, status_code=202)
async def request_match(
    payload: MatchRequest,
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    match_id = str(uuid.uuid4())
    state = {
        "match_id": match_id,
        "user_id": str(current_user.id),
        "resume_id": payload.resume_id,
        "filters": payload.filters,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
    }
    await redis.setex(f"match_status:{match_id}", 7200, "queued")

    # Enqueue to Kafka via background task
    from app.core.background import enqueue_match
    await enqueue_match(state)

    return MatchResponse(
        match_id=match_id,
        status="queued",
        poll_url=f"/api/v1/match/{match_id}/status",
        ws_url=f"/api/v1/match/{match_id}/ws",
    )


@router.get("/{match_id}/status")
async def get_match_status(match_id: str, redis=Depends(get_redis)):
    status = await redis.get(f"match_status:{match_id}")
    if not status:
        raise HTTPException(status_code=404, detail="Match not found or expired")
    results_raw = await redis.get(f"match_results:{match_id}")
    return {
        "match_id": match_id,
        "status": status,
        "results": results_raw,
    }


@router.websocket("/{match_id}/ws")
async def match_websocket(match_id: str, websocket: WebSocket, redis=Depends(get_redis)):
    """Stream LangGraph node completion events to the client in real-time."""
    await websocket.accept()
    try:
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"match_updates:{match_id}")
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
                if b'"status":"done"' in message["data"]:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"match_updates:{match_id}")
