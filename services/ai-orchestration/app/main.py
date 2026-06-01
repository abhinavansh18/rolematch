from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import match, tailor, health
from app.core.telemetry import setup_telemetry
from shared.config.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="AI Orchestration Service", version="1.0.0", lifespan=lifespan)
setup_telemetry(app, service_name="ai-orchestration")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(match.router,  prefix="/api/v1/match",  tags=["match"])
app.include_router(tailor.router, prefix="/api/v1/tailor", tags=["tailor"])
app.include_router(health.router, prefix="/api/v1",        tags=["health"])
