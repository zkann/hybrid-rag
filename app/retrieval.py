"""Retrieval: vector (pgvector/HNSW) + keyword (Postgres FTS), fused with
Reciprocal Rank Fusion.

Why hybrid: dense vector search captures meaning ("how do I guard a route")
but misses rare exact tokens (an API symbol, an error code, a flag). Keyword
search nails the exact tokens but misses paraphrase. RRF fuses the two ranked
lists without needing the scores to be on the same scale:

    score(d) = sum_over_arms 1 / (rrf_k + rank_d_in_arm)

so a doc ranked highly by either arm floats up, and docs ranked by both win.

`retrieve(query, strategy=...)` exposes all three strategies (hybrid / vector /
keyword) so the eval harness can compare them head to head.
"""

from dataclasses import dataclass

from .config import get_settings
from .db import get_pool, to_pgvector
from .embeddings import embed_query


@dataclass
class Hit:
    chunk_id: int
    document_id: int
    source: str
    title: str
    content: str
    score: float


def _vector_ids(cur, qvec: list[float], k: int) -> list[int]:
    cur.execute(
        "SELECT id FROM chunks WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> %s::vector LIMIT %s",
        (to_pgvector(qvec), k),
    )
    return [r[0] for r in cur.fetchall()]


def _keyword_ids(cur, query: str, k: int) -> list[int]:
    cur.execute(
        "SELECT id FROM chunks "
        "WHERE tsv @@ websearch_to_tsquery('english', %s) "
        "ORDER BY ts_rank_cd(tsv, websearch_to_tsquery('english', %s)) DESC "
        "LIMIT %s",
        (query, query, k),
    )
    return [r[0] for r in cur.fetchall()]


def reciprocal_rank_fusion(rank_lists: list[list[int]], rrf_k: int) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for ranked in rank_lists:
        for rank, cid in enumerate(ranked):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def _hydrate(cur, ranked_ids: list[int], scores: dict[int, float]) -> list[Hit]:
    if not ranked_ids:
        return []
    cur.execute(
        "SELECT c.id, c.document_id, d.source, d.title, c.content "
        "FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE c.id = ANY(%s)",
        (ranked_ids,),
    )
    rows = {r[0]: r for r in cur.fetchall()}
    hits: list[Hit] = []
    for cid in ranked_ids:
        r = rows.get(cid)
        if r:
            hits.append(Hit(cid, r[1], r[2], r[3], r[4], round(scores.get(cid, 0.0), 6)))
    return hits


def retrieve(query: str, top_k: int | None = None, strategy: str = "hybrid") -> list[Hit]:
    """strategy: 'hybrid' (default) | 'vector' | 'keyword'."""
    s = get_settings()
    top_k = top_k or s.top_k
    strategy = strategy.lower()

    with get_pool().connection() as conn, conn.cursor() as cur:
        if strategy == "keyword":
            ranked = _keyword_ids(cur, query, max(top_k, s.candidate_k))[:top_k]
            scores = {cid: 1.0 / (i + 1) for i, cid in enumerate(ranked)}
        elif strategy == "vector":
            qvec = embed_query(query)
            ranked = _vector_ids(cur, qvec, max(top_k, s.candidate_k))[:top_k]
            scores = {cid: 1.0 / (i + 1) for i, cid in enumerate(ranked)}
        elif strategy == "hybrid":
            qvec = embed_query(query)
            vec = _vector_ids(cur, qvec, s.candidate_k)
            kw = _keyword_ids(cur, query, s.candidate_k)
            fused = reciprocal_rank_fusion([vec, kw], s.rrf_k)[:top_k]
            ranked = [cid for cid, _ in fused]
            scores = dict(fused)
        else:
            raise ValueError(f"unknown strategy: {strategy!r}")
        return _hydrate(cur, ranked, scores)


def hybrid_search(query: str, top_k: int | None = None) -> list[Hit]:
    return retrieve(query, top_k=top_k, strategy="hybrid")
