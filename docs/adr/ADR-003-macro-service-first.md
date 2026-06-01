# ADR-003: Macro-Service Architecture → Extract Under Load

**Status:** Accepted  
**Date:** 2025-01-10

## Context
Classic build-vs-microservices debate at project start with 2 engineers.

## Decision
Start with 4 bounded-context services (User, Job, AI Orchestration, Worker). Extract further only when a service hits an independent scaling bottleneck measurable in production.

## Rationale
- Premature decomposition at MVP = distributed monolith without the benefits
- Each service already has an independent Dockerfile, DB scope, and Kafka boundary
- Extraction criteria: service CPU > 80% sustained OR P95 latency SLO breach attributable to a sub-component

## Trigger Points for Future Extraction
- Scraper → independent service when job ingestion volume > 1M/day
- Reranker → independent gRPC service when cross-encoder becomes GPU-bound
- Resume Parser → independent service when parse queue lag > 10min sustained

## Consequences
- Some coupling within services (acceptable: same bounded context)
- Faster initial development velocity
- Clear extraction playbook reduces future migration risk
