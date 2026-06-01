"""
APScheduler-based scrape scheduler.
Reads source configs and enqueues scrape tasks via Kafka.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from shared.utils.kafka import get_producer, publish

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

SCRAPE_SOURCES = [
    {"source": "linkedin",   "queries": ["software engineer", "data scientist"], "cron": "0 */4 * * *"},
    {"source": "indeed",     "queries": ["backend developer", "ml engineer"],    "cron": "30 */4 * * *"},
    {"source": "greenhouse", "queries": ["product manager", "devops engineer"],  "cron": "0 */6 * * *"},
]


async def _enqueue_scrape(source: str, queries: list[str]) -> None:
    producer = await get_producer()
    try:
        for query in queries:
            await publish(
                producer,
                topic="scrape.requested",
                value={"source": source, "query": query, "location": "United States"},
                key=source,
            )
            logger.info("Enqueued scrape: source=%s query=%s", source, query)
    finally:
        await producer.stop()


async def start_scheduler() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")

    for src in SCRAPE_SOURCES:
        trigger = CronTrigger.from_crontab(src["cron"])
        _scheduler.add_job(
            _enqueue_scrape,
            trigger=trigger,
            kwargs={"source": src["source"], "queries": src["queries"]},
            id=f"scrape_{src['source']}",
            replace_existing=True,
            max_instances=1,
        )

    _scheduler.start()
    logger.info("Scrape scheduler started with %d sources", len(SCRAPE_SOURCES))


async def stop_scheduler() -> None:
    if _scheduler:
        _scheduler.shutdown(wait=False)
