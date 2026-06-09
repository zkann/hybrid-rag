"""Unit tests for the pure retrieval logic (no DB / no network)."""

from app.retrieval import reciprocal_rank_fusion


def test_rrf_rewards_agreement():
    # doc 1 is top of both arms; doc 2 only appears in one. 1 must outrank 2.
    vec = [1, 2, 3]
    kw = [1, 4, 5]
    ranked = reciprocal_rank_fusion([vec, kw], rrf_k=60)
    order = [cid for cid, _ in ranked]
    assert order[0] == 1
    assert order.index(1) < order.index(2)


def test_rrf_score_formula():
    ranked = dict(reciprocal_rank_fusion([[7]], rrf_k=60))
    # single list, rank 0 -> 1/(60+0+1)
    assert abs(ranked[7] - 1.0 / 61) < 1e-9


def test_rrf_combines_scores_for_shared_doc():
    ranked = dict(reciprocal_rank_fusion([[9], [9]], rrf_k=60))
    # appears at rank 0 in both arms -> 2/(61)
    assert abs(ranked[9] - 2.0 / 61) < 1e-9


def test_rrf_empty():
    assert reciprocal_rank_fusion([[], []], rrf_k=60) == []
