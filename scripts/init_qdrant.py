#!/usr/bin/env python3
"""
Idempotently creates Qdrant collections with production-grade HNSW config.
Run once after starting Qdrant (also safe to re-run).
"""
import asyncio

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, HnswConfigDiff, OptimizersConfigDiff,
    QuantizationConfig, ScalarQuantizationConfig,
    SparseVectorParams, Modifier, VectorParams,
)

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

COLLECTIONS = {
    "jobs": {"size": 1024, "distance": Distance.COSINE},
    "resumes": {"size": 1024, "distance": Distance.COSINE},
    "prompt_cache_bulk_scoring":    {"size": 384, "distance": Distance.COSINE},
    "prompt_cache_resume_analysis": {"size": 384, "distance": Distance.COSINE},
}


async def main():
    client = AsyncQdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    existing = {c.name for c in (await client.get_collections()).collections}

    for name, cfg in COLLECTIONS.items():
        if name in existing:
            print(f"Collection '{name}' already exists — skipping")
            continue

        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=cfg["size"],
                distance=cfg["distance"],
                on_disk=True,
                hnsw_config=HnswConfigDiff(m=16, ef_construct=200, on_disk=False),
                quantization_config=QuantizationConfig(
                    scalar=ScalarQuantizationConfig(type="int8", quantile=0.99, always_ram=True)
                ),
            ),
            sparse_vectors_config={"bm25": SparseVectorParams(modifier=Modifier.IDF)}
            if name in ("jobs", "resumes") else {},
            optimizers_config=OptimizersConfigDiff(
                default_segment_number=2,
                indexing_threshold=10000,
                flush_interval_sec=5,
            ),
        )
        print(f"Created collection '{name}' (dim={cfg['size']})")

    await client.close()
    print("Qdrant initialisation complete.")


if __name__ == "__main__":
    asyncio.run(main())
