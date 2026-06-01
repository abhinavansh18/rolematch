# ADR-001: Use Kafka for Job Pipeline, RabbitMQ for Resume Tasks

**Status:** Accepted  
**Date:** 2025-01-15  
**Deciders:** Platform Team

## Context
We need a message queue for two distinct workloads:
1. **Job pipeline** — high volume (10k-500k msgs/day), needs replay, partitioned by domain
2. **Resume tasks** — low volume (100-10k/day), complex routing, dead-letter queues

## Decision
- **Kafka** for job pipeline topics (`job.scraped`, `job.normalized`, `job.embedded`, `match.*`)
- **RabbitMQ** for resume and notification tasks (`resume.parse`, `notification.*`)

## Rationale
Kafka excels at high-throughput ordered streams with replay capability (scrape reprocessing after parser bug fixes). RabbitMQ's exchange/routing model handles the complex resume pipeline retry logic (per-message TTL, DLQ, priority queues) more naturally than Kafka consumer groups.

## Consequences
- Two message brokers to operate (mitigated: both managed services in prod)
- Operators must understand both systems
- Accepted tradeoff: operational cost < development friction from forcing one tool

## Alternatives Considered
- Pure Kafka: Consumer group complexity for per-message TTL is high
- Pure RabbitMQ: No log-based replay; stream throughput limited
