from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db.session import get_db
from app.services.job_service import JobService

router = APIRouter()


class JobSearchParams(BaseModel):
    q: str | None = None
    location: str | None = None
    remote_type: str | None = None
    salary_min: float | None = None
    skills: list[str] = []
    page: int = 1
    page_size: int = 20


@router.get("/")
async def list_jobs(
    q:           str | None = Query(None),
    location:    str | None = Query(None),
    remote_type: str | None = Query(None),
    salary_min:  float | None = Query(None),
    page:        int = Query(1, ge=1),
    page_size:   int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    svc = JobService(db)
    jobs, total = await svc.search(
        q=q, location=location, remote_type=remote_type,
        salary_min=salary_min, page=page, page_size=page_size,
    )
    return {"items": jobs, "total": total, "page": page, "page_size": page_size}


@router.get("/{job_id}")
async def get_job(job_id: UUID, db=Depends(get_db)):
    svc = JobService(db)
    job = await svc.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/stats/summary")
async def job_stats(db=Depends(get_db)):
    svc = JobService(db)
    return await svc.get_stats()
