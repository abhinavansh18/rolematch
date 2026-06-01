"""Parse, ATS-score, and embed uploaded resumes."""
import io
import logging

import boto3
import pdfminer.high_level as pdf_hl

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def parse_and_analyze(event: dict) -> dict:
    file_key     = event["file_key"]
    resume_id    = event["resume_id"]
    content_type = event.get("content_type", "application/pdf")

    raw_bytes = await _download_from_s3(file_key)
    text      = _extract_text(raw_bytes, content_type)
    structured = _extract_structure(text)
    ats_score, ats_issues = _score_ats(text, structured)

    return {
        "resume_id":   resume_id,
        "user_id":     event["user_id"],
        "parsed_data": structured,
        "ats_score":   ats_score,
        "ats_issues":  ats_issues,
        "text_length": len(text),
    }


async def _download_from_s3(file_key: str) -> bytes:
    s3 = boto3.client("s3", region_name=settings.aws_region)
    obj = s3.get_object(Bucket=settings.s3_resume_bucket, Key=file_key)
    return obj["Body"].read()


def _extract_text(raw: bytes, content_type: str) -> str:
    if "pdf" in content_type:
        return pdf_hl.extract_text(io.BytesIO(raw))
    elif "wordprocessingml" in content_type:
        import docx
        doc = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)
    return raw.decode("utf-8", errors="ignore")


def _extract_structure(text: str) -> dict:
    import re
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Naive section detection; replaced by LLM for Pro users
    skills = []
    TECH = {"python","java","go","rust","typescript","react","fastapi","kubernetes","aws","gcp","sql","postgres","redis","kafka"}
    words = set(re.findall(r"\b[A-Za-z][A-Za-z0-9+#.]*\b", text.lower()))
    skills = sorted(words & TECH)

    return {
        "name":    lines[0] if lines else "",
        "skills":  skills,
        "summary": " ".join(lines[1:4]) if len(lines) > 3 else "",
        "experience": [],
        "education":  [],
        "total_experience_years": None,
        "current_title": None,
    }


def _score_ats(text: str, structured: dict) -> tuple[int, dict]:
    issues = []
    score  = 100

    if len(text) < 200:
        issues.append({"type": "too_short", "severity": "high"})
        score -= 30

    if not structured.get("skills"):
        issues.append({"type": "no_skills_detected", "severity": "medium"})
        score -= 15

    import re
    if re.search(r"<table|<img|<div", text, re.IGNORECASE):
        issues.append({"type": "html_formatting_detected", "severity": "high"})
        score -= 20

    return max(score, 0), {"issues": issues, "score": score}
