"""
Kafka consumer: job.scraped → normalize → embed → write to Qdrant.
Uses micro-batching (50 messages or 5 seconds, whichever comes first).
"""
import asyncio
import logging

from app.processors.normalizer import normalize_jobs
from app.processors.embedder import embed_and_store
from shared.utils.kafka import get_consumer, get_producer, publish

logger = logging.getLogger(__name__)

TOPIC_IN  = "job.scraped"
TOPIC_OUT = "job.normalized"
GROUP_ID  = "job-pipeline-workers"
BATCH_SIZE = 50
BATCH_TIMEOUT_S = 5.0


async def run_job_pipeline_consumer():
    consumer = await get_consumer([TOPIC_IN], GROUP_ID)
    producer = await get_producer()

    try:
        batch = []
        deadline = asyncio.get_event_loop().time() + BATCH_TIMEOUT_S

        async for msg in consumer:
            batch.append(msg.value)
            now = asyncio.get_event_loop().time()

            if len(batch) >= BATCH_SIZE or now >= deadline:
                await _process_batch(batch, producer)
                await consumer.commit()
                batch = []
                deadline = asyncio.get_event_loop().time() + BATCH_TIMEOUT_S
    finally:
        await consumer.stop()
        await producer.stop()


async def _process_batch(batch: list[dict], producer) -> None:
    try:
        normalized = await normalize_jobs(batch)
        await embed_and_store(normalized)

        for job in normalized:
            await publish(producer, TOPIC_OUT, job, key=job.get("source_domain"))

        logger.info("Processed batch of %d jobs", len(normalized))
    except Exception as e:
        logger.error("Batch processing failed: %s", e, exc_info=True)
        # TODO: Route to DLQ after N retries
