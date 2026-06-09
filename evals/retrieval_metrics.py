"""Information-retrieval metrics, document-level and binary-relevance.

All take a `ranked` list of source identifiers (deduplicated, best first) and a
`relevant` set of source identifiers. Pure functions, no DB or network.
"""

import math


def dedup_preserve(seq: list[str]) -> list[str]:
    """De-duplicate while preserving order (chunks collapse to their source)."""
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Fraction of the relevant set that appears in the top k."""
    relevant = set(relevant)
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def hit_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """1.0 if any relevant doc is in the top k, else 0.0."""
    return 1.0 if set(ranked[:k]) & set(relevant) else 0.0


def mrr(ranked: list[str], relevant: set[str]) -> float:
    """Reciprocal rank of the first relevant doc (0 if none)."""
    relevant = set(relevant)
    for i, src in enumerate(ranked):
        if src in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Normalized discounted cumulative gain at k, binary relevance."""
    relevant = set(relevant)
    dcg = sum(1.0 / math.log2(i + 2) for i, src in enumerate(ranked[:k]) if src in relevant)
    ideal = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal))
    return dcg / idcg if idcg > 0 else 0.0
