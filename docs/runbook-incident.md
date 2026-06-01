# Incident Runbook

## LLM Cost Spike
1. Check: `kubectl logs -l app=ai-orchestration -n api --tail=100 | grep "llm.cost"`
2. Identify provider/task combination driving cost
3. Emergency rate limit: update Redis key `rate:llm:{user_id}` → `0`
4. Kill switch: `kubectl scale deployment ai-orchestration --replicas=0 -n api`
5. Root cause: check Langfuse for prompt runaway (infinite retry loop?)

## Qdrant Down
1. Check: `kubectl get pods -n data -l app=qdrant`
2. Fallback: BM25 PostgreSQL full-text search activates automatically (check logs for "qdrant_fallback=true")
3. Restore from snapshot: `qdrant-client snapshot restore --snapshot-url s3://...`
4. Rebuild index: re-run embedding worker against all active jobs

## Kafka Consumer Lag > 50k
1. Check: Grafana "Kafka Consumer Lag" panel
2. Scale workers: `kubectl scale deployment worker-service --replicas=8 -n workers`
3. KEDA should auto-scale; check KEDA logs if not: `kubectl logs -n keda -l app=keda-operator`
4. If lag is from bad messages: check DLQ topic `job.scraped.dlq`
