"""Resume tailoring endpoint with SSE streaming."""
import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.llm.router.llm_router import LLMRouter
from shared.models.user import User

router = APIRouter()
llm_router = LLMRouter()


class TailorRequest(BaseModel):
    resume_id: str
    job_id:    str
    sections:  list[str] = ["summary", "experience"]


@router.post("/stream")
async def tailor_resume_stream(
    payload: TailorRequest,
    current_user: User = Depends(get_current_user),
):
    """Streams tailored resume sections as Server-Sent Events."""

    async def event_generator():
        tailor_id = str(uuid4())
        yield f"data: {json.dumps({'tailor_id': tailor_id, 'status': 'started'})}\n\n"

        for section in payload.sections:
            yield f"data: {json.dumps({'section': section, 'status': 'processing'})}\n\n"
            await asyncio.sleep(0)  # Yield control

            prompt = [{"role": "user", "content":
                f"Tailor the '{section}' section of a resume for a software engineering role. "
                f"Keep it concise and ATS-optimised. Resume ID: {payload.resume_id}, "
                f"Job ID: {payload.job_id}. Return the improved text only."}]

            response = await llm_router.route(
                task_type="resume_tailoring",
                messages=prompt,
                user_tier=current_user.tier.value,
            )

            yield f"data: {json.dumps({'section': section, 'status': 'done', 'content': response.content})}\n\n"

        yield f"data: {json.dumps({'status': 'complete', 'tailor_id': tailor_id})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/sync")
async def tailor_resume_sync(
    payload: TailorRequest,
    current_user: User = Depends(get_current_user),
):
    """Blocking tailor — for Pro+ users who want immediate JSON response."""
    results = {}
    for section in payload.sections:
        prompt = [{"role": "user", "content":
            f"Tailor the '{section}' section for job {payload.job_id}. "
            f"Resume {payload.resume_id}. Return improved text only."}]
        resp = await llm_router.route(
            task_type="resume_tailoring",
            messages=prompt,
            user_tier=current_user.tier.value,
        )
        results[section] = resp.content

    return {"resume_id": payload.resume_id, "job_id": payload.job_id, "sections": results}
