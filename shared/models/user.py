from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class User(BaseModel):
    id: UUID
    email: EmailStr
    tier: UserTier = UserTier.FREE
    preferences: dict = {}
    created_at: datetime
    last_active_at: datetime | None = None
