"""Load resume text from S3 / DB for LangGraph nodes."""
import boto3
import httpx

from shared.config.settings import get_settings

settings = get_settings()


async def load_resume_text(resume_id: str) -> str:
    """
    Fetch parsed resume text.
    Strategy: call user-service API (avoids direct DB coupling between services).
    Falls back to S3 raw file if parsed_data unavailable.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"http://user-service/api/v1/resumes/{resume_id}",
                headers={"X-Internal-Call": "ai-orchestration"},
            )
            resp.raise_for_status()
            data = resp.json()
            if parsed := data.get("parsed_data"):
                return _structured_to_text(parsed)
    except Exception:
        pass

    return ""


def _structured_to_text(parsed: dict) -> str:
    parts = []
    if s := parsed.get("summary"):
        parts.append(f"Summary: {s}")
    if exp := parsed.get("experience"):
        parts.append("Experience:\n" + "\n".join(
            f"  {e.get('title')} at {e.get('company')}: {e.get('description', '')}"
            for e in exp[:3]
        ))
    if skills := parsed.get("skills"):
        parts.append(f"Skills: {', '.join(skills[:20])}")
    if edu := parsed.get("education"):
        parts.append("Education:\n" + "\n".join(
            f"  {e.get('degree')} in {e.get('field')} from {e.get('institution')}"
            for e in edu
        ))
    return "\n\n".join(parts)
