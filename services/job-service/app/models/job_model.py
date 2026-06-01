from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class JobModel(Base):
    __tablename__ = "jobs"

    id:                     Mapped[UUID]      = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    title:                  Mapped[str]       = mapped_column(String(500), nullable=False)
    company_name:           Mapped[str]       = mapped_column(String(255), nullable=False, default="")
    location:               Mapped[str|None]  = mapped_column(String(255))
    remote_type:            Mapped[str|None]  = mapped_column(String(20))
    salary_min:             Mapped[float|None]= mapped_column(Float)
    salary_max:             Mapped[float|None]= mapped_column(Float)
    salary_currency:        Mapped[str]       = mapped_column(String(3), default="USD")
    description_text:       Mapped[str]       = mapped_column(Text, nullable=False, default="")
    description_compressed: Mapped[str|None]  = mapped_column(Text)
    skills:                 Mapped[list]      = mapped_column(ARRAY(String), nullable=False, default=list)
    content_hash:           Mapped[str]       = mapped_column(String(64), nullable=False, unique=True)
    source_url:             Mapped[str]       = mapped_column(Text, nullable=False, default="")
    source_domain:          Mapped[str]       = mapped_column(String(255), nullable=False, default="")
    is_active:              Mapped[bool]      = mapped_column(Boolean, nullable=False, default=True)
    first_seen_at:          Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at:           Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at:             Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
