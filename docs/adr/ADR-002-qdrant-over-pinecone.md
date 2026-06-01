# ADR-002: Self-hosted Qdrant over Pinecone Managed

**Status:** Accepted  
**Date:** 2025-01-20

## Context
Vector DB for semantic job and resume search. Options evaluated: Pinecone, Weaviate, Qdrant.

## Decision
Qdrant, self-hosted on Kubernetes.

## Rationale
| Factor        | Pinecone     | Qdrant (self-hosted) |
|---------------|-------------|----------------------|
| Cost at 10M vectors | ~$700/mo | ~$450/mo (3 nodes) |
| Cost at 50M vectors | ~$3,500/mo | ~$900/mo (6 nodes) |
| Hybrid search (BM25+dense) | ❌ | ✅ |
| Filtering on payload | Limited | ✅ Full |
| Data residency | Limited | ✅ Full control |
| Ops burden | None | Medium |

Break-even: Qdrant cheaper from day 1 given hybrid search requirement.

## Consequences
- Team must operate Qdrant cluster (mitigated: Qdrant Cloud as escape hatch)
- Snapshot/restore runbook required
- Accepted: cost savings justify ops overhead at any meaningful scale
