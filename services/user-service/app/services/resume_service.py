import json
import logging
from uuid import UUID

import boto3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import ResumeModel
from shared.config.settings import get_settings
from shared.utils.kafka import get_producer, publish

logger = logging.getLogger(__name__)
settings = get_settings()


class ResumeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

    async def create_and_enqueue(
        self, user_id: UUID, filename: str, content: bytes,
        file_hash: str, content_type: str,
    ) -> ResumeModel:
        # Get next version number
        existing = await self.list_for_user(user_id)
        version = len(existing) + 1

        file_key = f"raw/{user_id}/{file_hash}/{filename}"

        # Upload to S3
        self._s3.put_object(
            Bucket=settings.s3_resume_bucket,
            Key=file_key,
            Body=content,
            ContentType=content_type,
        )

        resume = ResumeModel(
            user_id=user_id, version=version,
            file_key=file_key, file_hash=file_hash,
        )
        self.db.add(resume)
        await self.db.flush()
        await self.db.refresh(resume)

        # Enqueue for parsing
        producer = await get_producer()
        try:
            await publish(producer, "resume.parse", {
                "resume_id": str(resume.id),
                "user_id":   str(user_id),
                "file_key":  file_key,
                "file_hash": file_hash,
                "content_type": content_type,
            }, key=str(user_id))
        finally:
            await producer.stop()

        logger.info("Resume %s uploaded and queued for parsing", resume.id)
        return resume

    async def get_by_id(self, resume_id: UUID, user_id: UUID) -> ResumeModel | None:
        result = await self.db.execute(
            select(ResumeModel).where(
                ResumeModel.id == resume_id,
                ResumeModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[ResumeModel]:
        result = await self.db.execute(
            select(ResumeModel)
            .where(ResumeModel.user_id == user_id, ResumeModel.is_active == True)
            .order_by(ResumeModel.version.desc())
        )
        return list(result.scalars().all())

    async def delete(self, resume_id: UUID, user_id: UUID) -> bool:
        resume = await self.get_by_id(resume_id, user_id)
        if not resume:
            return False
        resume.is_active = False
        return True
