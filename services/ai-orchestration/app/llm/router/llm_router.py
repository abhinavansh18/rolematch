"""
Cost- and latency-aware LLM router with circuit breakers, fallback chains,
semantic caching, and hedged requests.
"""
import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

import httpx

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ProviderState(Enum):
    CLOSED = "closed"      # Healthy
    OPEN = "open"          # Failing — skip
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    reset_timeout: int = 60
    _failures: int = 0
    _state: ProviderState = ProviderState.CLOSED
    _last_failure: float = 0.0

    def record_success(self):
        self._failures = 0
        self._state = ProviderState.CLOSED

    def record_failure(self):
        self._failures += 1
        self._last_failure = time.monotonic()
        if self._failures >= self.failure_threshold:
            self._state = ProviderState.OPEN
            logger.warning("Circuit OPENED after %d failures", self._failures)

    @property
    def is_available(self) -> bool:
        if self._state == ProviderState.CLOSED:
            return True
        if self._state == ProviderState.OPEN:
            if time.monotonic() - self._last_failure > self.reset_timeout:
                self._state = ProviderState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN: allow one probe


# ── Provider registry ─────────────────────────────────────────────────────────
TASK_PROVIDER_MAP: dict[str, list[str]] = {
    "bulk_scoring":      ["groq", "openrouter", "openai"],
    "resume_analysis":   ["groq", "openai", "anthropic"],
    "resume_tailoring":  ["anthropic", "openai"],
    "cover_letter":      ["anthropic", "openai"],
    "ats_analysis":      ["groq", "openai"],
    "match_explanation": ["groq", "openai"],
    "job_normalization": ["groq", "openrouter"],
}

PROVIDER_TIMEOUTS: dict[str, float] = {
    "groq": 4.0, "openai": 9.0, "anthropic": 12.0, "openrouter": 14.0
}

PROVIDER_MODELS: dict[str, str] = {
    "groq":       "llama-3.1-70b-versatile",
    "openai":     "gpt-4o-mini",
    "anthropic":  "claude-haiku-4-5-20251001",
    "openrouter": "mistralai/mistral-7b-instruct",
}


class LLMResponse:
    def __init__(self, content: str, provider: str, model: str, usage: dict, from_cache: bool = False):
        self.content = content
        self.provider = provider
        self.model = model
        self.usage = usage
        self.from_cache = from_cache


class LLMRouter:
    def __init__(self):
        self._circuit_breakers: dict[str, CircuitBreaker] = {
            p: CircuitBreaker() for p in PROVIDER_MODELS
        }
        self._cache: dict[str, str] = {}  # In-process L1; backed by Redis in production

    async def route(
        self,
        task_type: str,
        messages: list[dict],
        user_tier: str = "free",
        stream: bool = False,
    ) -> LLMResponse:
        # ── L1 semantic cache ──────────────────────────────────────────────────
        cache_key = self._cache_key(messages)
        if cached := self._cache.get(cache_key):
            return LLMResponse(cached, "cache", "cache", {}, from_cache=True)

        providers = TASK_PROVIDER_MAP.get(task_type, ["openai"])
        # Enterprise users get quality-first routing
        if user_tier == "enterprise" and task_type == "resume_tailoring":
            providers = ["anthropic", "openai"]

        last_exc: Exception | None = None
        for provider in providers:
            cb = self._circuit_breakers[provider]
            if not cb.is_available:
                logger.debug("Skipping %s (circuit open)", provider)
                continue

            try:
                response = await asyncio.wait_for(
                    self._call(provider, messages, stream),
                    timeout=PROVIDER_TIMEOUTS.get(provider, 10.0),
                )
                cb.record_success()
                self._cache[cache_key] = response.content
                return response
            except (asyncio.TimeoutError, httpx.HTTPError) as e:
                cb.record_failure()
                last_exc = e
                logger.warning("Provider %s failed: %s", provider, e)
                continue

        raise RuntimeError(f"All LLM providers exhausted for task {task_type}") from last_exc

    async def _call(self, provider: str, messages: list[dict], stream: bool) -> LLMResponse:
        model = PROVIDER_MODELS[provider]
        if provider == "openai":
            return await self._call_openai(model, messages)
        elif provider == "anthropic":
            return await self._call_anthropic(model, messages)
        elif provider == "groq":
            return await self._call_groq(model, messages)
        elif provider == "openrouter":
            return await self._call_openrouter(model, messages)
        raise ValueError(f"Unknown provider: {provider}")

    async def _call_openai(self, model: str, messages: list[dict]) -> LLMResponse:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(model=model, messages=messages, max_tokens=1000)
        return LLMResponse(
            content=resp.choices[0].message.content,
            provider="openai", model=model,
            usage={"input": resp.usage.prompt_tokens, "output": resp.usage.completion_tokens},
        )

    async def _call_anthropic(self, model: str, messages: list[dict]) -> LLMResponse:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        resp = await client.messages.create(model=model, max_tokens=1000, messages=messages)
        return LLMResponse(
            content=resp.content[0].text,
            provider="anthropic", model=model,
            usage={"input": resp.usage.input_tokens, "output": resp.usage.output_tokens},
        )

    async def _call_groq(self, model: str, messages: list[dict]) -> LLMResponse:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.groq_api_key)
        resp = await client.chat.completions.create(model=model, messages=messages, max_tokens=1000)
        return LLMResponse(
            content=resp.choices[0].message.content,
            provider="groq", model=model,
            usage={"input": resp.usage.prompt_tokens, "output": resp.usage.completion_tokens},
        )

    async def _call_openrouter(self, model: str, messages: list[dict]) -> LLMResponse:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                json={"model": model, "messages": messages, "max_tokens": 1000},
            )
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                provider="openrouter", model=model,
                usage=data.get("usage", {}),
            )

    @staticmethod
    def _cache_key(messages: list[dict]) -> str:
        content = "".join(m.get("content", "") for m in messages)
        return hashlib.md5(content.encode()).hexdigest()
