from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.base import UserModel


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> UserModel | None:
        result = await self.db.execute(select(UserModel).where(UserModel.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> UserModel | None:
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, email: str, password: str) -> UserModel:
        user = UserModel(email=email, password_hash=hash_password(password), tier="free")
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_last_active(self, user_id: UUID) -> None:
        from sqlalchemy import update
        from datetime import datetime, timezone
        await self.db.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_active_at=datetime.now(timezone.utc))
        )
