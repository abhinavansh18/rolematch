import hashlib


def sha256_hex(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode()
    return hashlib.sha256(content).hexdigest()


def md5_hex(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode()
    return hashlib.md5(content).hexdigest()


def normalize_job_text(text: str) -> str:
    """Strip whitespace and lowercase for stable content hashing."""
    import re
    return re.sub(r"\s+", " ", text.lower()).strip()
