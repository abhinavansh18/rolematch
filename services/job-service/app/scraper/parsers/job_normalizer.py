"""
Normalizes raw job HTML into structured NormalizedJob records.
Combines rule-based extraction with LLM fallback for ambiguous fields.
"""
import re
from datetime import datetime

import trafilatura

from shared.models.job import NormalizedJob
from shared.utils.hashing import sha256_hex, normalize_job_text


SALARY_PATTERN = re.compile(
    r"\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:k|K)?(?:\s*[-–]\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:k|K)?)?",
    re.IGNORECASE,
)

REMOTE_KEYWORDS = {
    "remote": "remote",
    "hybrid": "hybrid",
    "onsite": "onsite",
    "on-site": "onsite",
    "in office": "onsite",
    "in-office": "onsite",
}


def parse_salary(text: str) -> tuple[float | None, float | None]:
    match = SALARY_PATTERN.search(text)
    if not match:
        return None, None
    lo = float(match.group(1).replace(",", ""))
    hi = float(match.group(2).replace(",", "")) if match.group(2) else lo
    # Normalise K notation
    if lo < 500:
        lo, hi = lo * 1000, hi * 1000
    return lo, hi


def detect_remote_type(text: str) -> str | None:
    lower = text.lower()
    for kw, rtype in REMOTE_KEYWORDS.items():
        if kw in lower:
            return rtype
    return None


def extract_skills(text: str) -> list[str]:
    """Naive keyword extraction; replaced by LLM-based extraction in worker."""
    TECH_SKILLS = {
        "python", "java", "typescript", "javascript", "go", "rust", "c++",
        "react", "fastapi", "django", "kubernetes", "docker", "aws", "gcp",
        "postgres", "redis", "kafka", "pytorch", "tensorflow", "sql",
    }
    words = set(re.findall(r"\b[A-Za-z][A-Za-z0-9+#.]*\b", text.lower()))
    return sorted(words & TECH_SKILLS)


def normalize(raw_html: str, source_url: str, source_domain: str, job_id: str) -> NormalizedJob:
    text = trafilatura.extract(raw_html) or ""
    lines = text.split("\n")
    title = lines[0].strip() if lines else "Unknown"

    salary_min, salary_max = parse_salary(text)
    remote_type = detect_remote_type(text)
    skills = extract_skills(text)

    content_hash = sha256_hex(normalize_job_text(text))

    return NormalizedJob(
        job_id=job_id,
        title=title,
        company="",
        description_text=text,
        skills=skills,
        salary_min=salary_min,
        salary_max=salary_max,
        remote_type=remote_type,
        source_url=source_url,
        source_domain=source_domain,
        normalized_at=datetime.utcnow(),
        idempotency_key=content_hash,
    )
