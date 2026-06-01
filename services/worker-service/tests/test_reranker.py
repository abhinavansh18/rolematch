def test_rerank_returns_top_k():
    from ml.reranker.cross_encoder_reranker import rerank
    candidates = [
        {"job_id": str(i), "description_compressed": f"Job description number {i} about software engineering"}
        for i in range(10)
    ]
    # Mock the cross encoder
    from unittest.mock import patch
    import numpy as np
    with patch("ml.reranker.cross_encoder_reranker.load_cross_encoder") as m:
        encoder = m.return_value
        encoder.predict.return_value = np.array([float(i) for i in range(10)])
        result = rerank("python engineer resume", candidates, top_k=5)
        assert len(result) == 5
        assert "cross_encoder_score" in result[0]
        assert result[0]["cross_encoder_score"] >= result[-1]["cross_encoder_score"]


def test_rrf_fusion():
    from ml.reranker.cross_encoder_reranker import reciprocal_rank_fusion
    vec   = [{"job_id": "a"}, {"job_id": "b"}, {"job_id": "c"}]
    cross = [{"job_id": "c"}, {"job_id": "a"}, {"job_id": "b"}]
    fused = reciprocal_rank_fusion(vec, cross, id_key="job_id")
    assert len(fused) == 3
    assert all("rrf_score" in j for j in fused)
