from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ResumeExperience(BaseModel):
    title: str
    company: str
    start_date: str | None = None
    end_date: str | None = None
    description: str
    bullets: list[str] = []


class ResumeEducation(BaseModel):
    degree: str
    field: str
    institution: str
    year: int | None = None


class ResumeStructured(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    summary: str | None = None
    skills: list[str] = []
    experience: list[ResumeExperience] = []
    education: list[ResumeEducation] = []
    total_experience_years: int | None = None
    current_title: str | None = None


class Resume(BaseModel):
    id: UUID
    user_id: UUID
    version: int
    is_active: bool
    file_key: str
    file_hash: str
    parsed_data: ResumeStructured | None = None
    ats_score: int | None = None
    ats_issues: dict | None = None
    embedding_id: UUID | None = None
    created_at: datetime
