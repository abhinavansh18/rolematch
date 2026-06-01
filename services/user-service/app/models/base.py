from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id:             Mapped[UUID]     = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email:          Mapped[str]      = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash:  Mapped[str|None] = mapped_column(Text, nullable=True)
    tier:           Mapped[str]      = mapped_column(String(20), nullable=False, default="free")
    preferences:    Mapped[dict]     = mapped_column(JSONB, nullable=False, default=dict)
    created_at:     Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResumeModel(Base):
    __tablename__ = "resumes"

    id:          Mapped[UUID]     = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id:     Mapped[UUID]     = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    version:     Mapped[int]      = mapped_column(nullable=False, default=1)
    is_active:   Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    file_key:    Mapped[str]      = mapped_column(Text, nullable=False)
    file_hash:   Mapped[str]      = mapped_column(String(64), nullable=False)
    parsed_data: Mapped[dict|None]= mapped_column(JSONB, nullable=True)
    ats_score:   Mapped[int|None] = mapped_column(nullable=True)
    ats_issues:  Mapped[dict|None]= mapped_column(JSONB, nullable=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
