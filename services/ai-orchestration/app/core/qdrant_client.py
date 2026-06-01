from functools import lru_cache
from qdrant_client import AsyncQdrantClient
from shared.config.settings import get_settings

settings = get_settings()

_client: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
            timeout=10,
        )
    return _client
