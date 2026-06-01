from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.routes import auth, users, resumes
from app.core.telemetry import setup_telemetry
from app.db.session import init_db, close_db
from shared.config.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="User Service",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    lifespan=lifespan,
)

setup_telemetry(app, service_name="user-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

app.include_router(auth.router,    prefix="/api/v1/auth",    tags=["auth"])
app.include_router(users.router,   prefix="/api/v1/users",   tags=["users"])
app.include_router(resumes.router, prefix="/api/v1/resumes", tags=["resumes"])


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "service": "user-service"}
