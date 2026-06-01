"""Enqueue LangGraph match jobs to Kafka."""
import logging
from shared.utils.kafka import get_producer, publish

logger = logging.getLogger(__name__)


async def enqueue_match(state: dict) -> None:
    producer = await get_producer()
    try:
        await publish(
            producer,
            topic="match.requested",
            value=state,
            key=state.get("user_id"),
        )
        logger.info("Match %s enqueued", state.get("match_id"))
    finally:
        await producer.stop()
