"""
Standalone embedding service wrapper.
Handles model loading, batching, caching, and dimension validation.
"""
import hashlib
import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_CONFIGS = {
    "bge-large": {
        "model_id": "BAAI/bge-large-en-v1.5",
        "dimensions": 1024,
        "max_seq_length": 512,
        "query_prefix": "Represent this sentence for searching relevant passages: ",
    },
    "minilm": {
        "model_id": "all-MiniLM-L6-v2",
        "dimensions": 384,
        "max_seq_length": 256,
        "query_prefix": "",
    },
}


@lru_cache(maxsize=2)
def load_model(model_name: str) -> SentenceTransformer:
    cfg = MODEL_CONFIGS[model_name]
    logger.info("Loading embedding model: %s", cfg["model_id"])
    model = SentenceTransformer(cfg["model_id"])
    model.max_seq_length = cfg["max_seq_length"]
    return model


def embed_texts(
    texts: list[str],
    model_name: str = "bge-large",
    batch_size: int = 32,
    is_query: bool = False,
) -> np.ndarray:
    model = load_model(model_name)
    cfg = MODEL_CONFIGS[model_name]

    if is_query and cfg["query_prefix"]:
        texts = [cfg["query_prefix"] + t for t in texts]

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 100,
        convert_to_numpy=True,
    )
    assert embeddings.shape[1] == cfg["dimensions"], (
        f"Dimension mismatch: expected {cfg['dimensions']}, got {embeddings.shape[1]}"
    )
    return embeddings


def embedding_cache_key(text: str) -> str:
    return f"embed:{hashlib.md5(text.encode()).hexdigest()}"
