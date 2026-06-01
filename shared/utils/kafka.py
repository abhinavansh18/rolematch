"""
Shared Kafka producer/consumer factory.
All services use this to ensure consistent serialisation & error handling.
"""
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_producer() -> AIOKafkaProducer:
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode(),
        compression_type="snappy",
        max_batch_size=32768,
        linger_ms=5,
        acks="all",
        enable_idempotence=True,
    )
    await producer.start()
    return producer


async def get_consumer(topics: list[str], group_id: str) -> AIOKafkaConsumer:
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=group_id,
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        max_poll_records=50,
        session_timeout_ms=30000,
        heartbeat_interval_ms=10000,
    )
    await consumer.start()
    return consumer


async def publish(producer: AIOKafkaProducer, topic: str, value: dict[str, Any], key: str | None = None) -> None:
    try:
        key_bytes = key.encode() if key else None
        await producer.send_and_wait(topic, value=value, key=key_bytes)
    except KafkaError as e:
        logger.error("Failed to publish to %s: %s", topic, e)
        raise
