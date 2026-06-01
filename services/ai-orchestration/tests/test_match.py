import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/v1/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_request_match_unauthenticated(client):
    resp = await client.post("/api/v1/match/request", json={
        "resume_id": "some-uuid", "filters": {}
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_match_status_not_found(client, mock_redis):
    mock_redis.get.return_value = None
    resp = await client.get("/api/v1/match/nonexistent-id/status")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_llm_router_fallback(mock_llm_router):
    from app.llm.router.llm_router import LLMRouter
    router = LLMRouter()
    result = await router.route("bulk_scoring", [{"role": "user", "content": "test"}])
    assert result.content is not None


@pytest.mark.asyncio
async def test_llm_router_cache_hit():
    from app.llm.router.llm_router import LLMRouter
    router = LLMRouter()
    msgs = [{"role": "user", "content": "score this job for me"}]
    router._cache[router._cache_key(msgs)] = '{"score": 90}'
    result = await router.route("bulk_scoring", msgs)
    assert result.from_cache is True
