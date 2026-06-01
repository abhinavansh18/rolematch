"""
Kafka consumer: resume.parse → parse → ATS score → embed → store.
Processes one resume at a time (heavier per-item work than job pipeline).
"""
import asyncio
import logging

from app.processors.resume_processor import parse_and_analyze
from shared.utils.kafka import get_consumer, get_producer, publish

logger = logging.getLogger(__name__)

TOPIC_IN  = "resume.parse"
TOPIC_OUT = "resume.parsed"
GROUP_ID  = "resume-pipeline-workers"


async def run_resume_pipeline_consumer():
    consumer = await get_consumer([TOPIC_IN], GROUP_ID)
    producer = await get_producer()

    try:
        async for msg in consumer:
            event = msg.value
            resume_id = event.get("resume_id")
            logger.info("Processing resume %s", resume_id)

            try:
                result = await parse_and_analyze(event)
                await publish(producer, TOPIC_OUT, result, key=event.get("user_id"))
                await consumer.commit()
                logger.info("Resume %s parsed: ats_score=%s", resume_id, result.get("ats_score"))
            except Exception as e:
                logger.error("Resume parse failed for %s: %s", resume_id, e, exc_info=True)
                await _send_to_dlq(producer, msg.value, str(e))
                await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()


async def _send_to_dlq(producer, payload: dict, error: str) -> None:
    await publish(producer, "resume.parse.failed", {**payload, "error": error})
