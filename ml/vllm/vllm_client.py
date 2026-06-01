"""
OpenAI-compatible vLLM client with connection pooling and health checking.
Drop-in replacement for OpenAI SDK calls pointing at self-hosted vLLM.
"""
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://vllm-svc.inference.svc.cluster.local")
VLLM_MODEL    = os.getenv("VLLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
TIMEOUT       = httpx.Timeout(connect=2.0, read=30.0, write=5.0, pool=2.0)

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=VLLM_BASE_URL,
            timeout=TIMEOUT,
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )
    return _client


async def chat_complete(
    messages: list[dict],
    model: str = VLLM_MODEL,
    max_tokens: int = 1000,
    temperature: float = 0.1,
    stream: bool = False,
) -> dict:
    client = get_client()
    start  = time.monotonic()

    payload = {
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
        "stream":      stream,
    }

    resp = await client.post("/v1/chat/completions", json=payload)
    resp.raise_for_status()
    data = resp.json()

    latency_ms = (time.monotonic() - start) * 1000
    logger.debug("vLLM latency: %.1fms tokens_out=%d", latency_ms,
                 data.get("usage", {}).get("completion_tokens", 0))
    return data


async def health_check() -> bool:
    try:
        client = get_client()
        resp   = await client.get("/health", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False
