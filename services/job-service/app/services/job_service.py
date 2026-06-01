from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_model import JobModel


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, job_id: UUID) -> JobModel | None:
        result = await self.db.execute(
            select(JobModel).where(JobModel.id == job_id, JobModel.is_active == True)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        q: str | None = None,
        location: str | None = None,
        remote_type: str | None = None,
        salary_min: float | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[JobModel], int]:
        stmt = select(JobModel).where(JobModel.is_active == True)

        if q:
            stmt = stmt.where(
                text("to_tsvector('english', title || ' ' || description_text) @@ plainto_tsquery('english', :q)")
            ).params(q=q)
        if location:
            stmt = stmt.where(JobModel.location.ilike(f"%{location}%"))
        if remote_type:
            stmt = stmt.where(JobModel.remote_type == remote_type)
        if salary_min:
            stmt = stmt.where(JobModel.salary_max >= salary_min)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def upsert(self, job_data: dict) -> JobModel:
        existing = await self.db.execute(
            select(JobModel).where(JobModel.content_hash == job_data["content_hash"])
        )
        job = existing.scalar_one_or_none()
        if job:
            job.last_seen_at = job_data.get("last_seen_at")
            return job

        job = JobModel(**job_data)
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_stats(self) -> dict:
        total = (await self.db.execute(select(func.count(JobModel.id)))).scalar_one()
        active = (await self.db.execute(
            select(func.count(JobModel.id)).where(JobModel.is_active == True)
        )).scalar_one()
        return {"total_jobs": total, "active_jobs": active}
