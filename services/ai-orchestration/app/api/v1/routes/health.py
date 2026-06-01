from fastapi import APIRouter
from app.core.redis_client import get_redis
from app.core.qdrant_client import get_qdrant

router = APIRouter()


@router.get("/healthz")
async def health():
    return {"status": "ok", "service": "ai-orchestration"}


@router.get("/readyz")
async def readiness():
    checks = {}
    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = str(e)

    try:
        qdrant = get_qdrant()
        await qdrant.get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = str(e)

    ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if ok else "degraded", "checks": checks}
