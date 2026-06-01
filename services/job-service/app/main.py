from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routes import jobs, scraper
from app.core.telemetry import setup_telemetry
from app.db.session import init_db, close_db
from app.scraper.scheduler.scheduler import start_scheduler, stop_scheduler
from shared.config.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_scheduler()
    yield
    await stop_scheduler()
    await close_db()


app = FastAPI(title="Job Service", version="1.0.0", lifespan=lifespan)
setup_telemetry(app, service_name="job-service")

app.include_router(jobs.router,    prefix="/api/v1/jobs",    tags=["jobs"])
app.include_router(scraper.router, prefix="/api/v1/scraper", tags=["scraper"])


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "service": "job-service"}
