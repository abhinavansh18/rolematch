"""Admin-only endpoints to trigger and inspect scrape jobs."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from shared.utils.kafka import get_producer, publish

router = APIRouter()

ADMIN_TOKEN = "admin-secret"  # Replace with proper RBAC in prod


class ScrapeRequest(BaseModel):
    source: str
    query: str
    location: str = "United States"
    max_pages: int = 5


def verify_admin(token: str = ""):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin only")


@router.post("/trigger")
async def trigger_scrape(payload: ScrapeRequest):
    producer = await get_producer()
    try:
        await publish(producer, "scrape.requested", {
            "source":    payload.source,
            "query":     payload.query,
            "location":  payload.location,
            "max_pages": payload.max_pages,
            "priority":  "high",
        }, key=payload.source)
    finally:
        await producer.stop()
    return {"status": "enqueued", "source": payload.source, "query": payload.query}


@router.get("/sources")
async def list_sources():
    return {
        "sources": [
            {"name": "linkedin",   "status": "active", "schedule": "0 */4 * * *"},
            {"name": "indeed",     "status": "active", "schedule": "30 */4 * * *"},
            {"name": "greenhouse", "status": "active", "schedule": "0 */6 * * *"},
        ]
    }
