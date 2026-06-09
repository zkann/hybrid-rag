"""Unit tests for the retrieval metrics (pure, no DB or network)."""

import math

from evals.retrieval_metrics import dedup_preserve, hit_at_k, mrr, ndcg_at_k, recall_at_k


def test_recall_and_hit_full():
    ranked = ["a", "b", "c"]
    rel = {"b"}
    assert recall_at_k(ranked, rel, 3) == 1.0
    assert hit_at_k(ranked, rel, 3) == 1.0


def test_hit_and_recall_respect_k():
    ranked = ["a", "b", "c"]
    rel = {"b"}
    assert hit_at_k(ranked, rel, 1) == 0.0  # b is not in the top 1
    assert recall_at_k(ranked, rel, 1) == 0.0


def test_recall_partial():
    assert recall_at_k(["a", "b", "c"], {"b", "x"}, 3) == 0.5


def test_mrr():
    assert mrr(["a", "b", "c"], {"b"}) == 0.5
    assert mrr(["a", "b"], {"z"}) == 0.0


def test_ndcg_discounts_by_position():
    # one relevant doc at rank 2 (index 1): gain 1/log2(3), ideal 1/log2(2)=1
    got = ndcg_at_k(["a", "b", "c"], {"b"}, 3)
    assert abs(got - (1.0 / math.log2(3))) < 1e-9


def test_ndcg_perfect_is_one():
    assert abs(ndcg_at_k(["b", "a"], {"b"}, 2) - 1.0) < 1e-9


def test_empty_relevant_is_zero():
    assert recall_at_k(["a"], set(), 3) == 0.0


def test_dedup_preserve_order():
    assert dedup_preserve(["a", "a", "b", "a", "c"]) == ["a", "b", "c"]
