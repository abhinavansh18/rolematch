from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RawJob(BaseModel):
    job_id: str
    source: str
    raw_html: str
    scraped_at: datetime
    idempotency_key: str  # SHA256(source_url + scrape_date)


class NormalizedJob(BaseModel):
    job_id: str
    title: str
    company: str
    location: str | None = None
    remote_type: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = "USD"
    description_text: str
    description_compressed: str | None = None  # ≤512 tokens
    skills: list[str] = Field(default_factory=list)
    experience_years_min: int | None = None
    source_url: str
    source_domain: str
    normalized_at: datetime
    idempotency_key: str


class Job(NormalizedJob):
    id: UUID
    content_hash: str
    is_active: bool = True
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
