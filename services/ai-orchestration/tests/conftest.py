import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def mock_redis():
    with patch("app.core.redis_client.get_redis") as m:
        redis = AsyncMock()
        redis.get.return_value = None
        redis.setex.return_value = True
        redis.ping.return_value = True
        m.return_value = redis
        yield redis


@pytest.fixture
def mock_llm_router():
    with patch("app.llm.router.llm_router.LLMRouter.route") as m:
        from app.llm.router.llm_router import LLMResponse
        m.return_value = LLMResponse(
            content='{"overall_score": 85, "skill_gaps": [], "strengths": ["Python"], "apply_confidence": "high"}',
            provider="groq", model="llama-3.1-70b-versatile", usage={"input": 100, "output": 50},
        )
        yield m
