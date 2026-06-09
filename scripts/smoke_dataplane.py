#!/usr/bin/env python3
"""Keyless data-plane smoke test: exercises pgvector (HNSW cosine), the FTS
keyword arm, and RRF against a real Postgres, using synthetic embeddings so it
needs no OpenAI/Anthropic keys. Inserts rows under `smoke://` sources and
deletes them afterward.

    make db-up && .venv/bin/python -m scripts.smoke_dataplane
"""

from app.db import get_pool, to_pgvector
from app.retrieval import _keyword_ids, _vector_ids, reciprocal_rank_fusion

DIM = 1536


def unit(i: int) -> list[float]:
    v = [0.0] * DIM
    v[i] = 1.0
    return v


def main() -> int:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE source LIKE 'smoke://%'")
            cur.execute(
                "INSERT INTO documents (source, title) VALUES (%s,%s) RETURNING id",
                ("smoke://doc", "smoke"),
            )
            doc_id = cur.fetchone()[0]
            rows = [
                ("vector databases store high dimensional embeddings", unit(0)),
                ("the xylophone is a percussion instrument", unit(1)),
                ("postgres full text search uses tsvector", unit(2)),
            ]
            for ord_, (content, emb) in enumerate(rows):
                cur.execute(
                    "INSERT INTO chunks (document_id, ord, content, embedding) "
                    "VALUES (%s,%s,%s,%s::vector)",
                    (doc_id, ord_, content, to_pgvector(emb)),
                )
        conn.commit()

        with conn.cursor() as cur:
            # vector arm: query == chunk 0's embedding, so it must rank first
            vec_ids = _vector_ids(cur, unit(0), 10)
            # keyword arm: a rare exact token only in chunk 1
            kw_ids = _keyword_ids(cur, "xylophone", 10)
            fused = reciprocal_rank_fusion([vec_ids, kw_ids], 60)

            cur.execute("SELECT id, content FROM chunks WHERE document_id=%s ORDER BY ord", (doc_id,))
            by_id = {r[0]: r[1] for r in cur.fetchall()}

        print("vector arm (top):", [by_id[i][:40] for i in vec_ids[:3]])
        print("keyword arm     :", [by_id[i][:40] for i in kw_ids])
        print("fused order     :", [by_id[cid][:40] for cid, _ in fused])

        vec_top = by_id[vec_ids[0]]
        kw_hit = [by_id[i] for i in kw_ids]
        ok = vec_top.startswith("vector databases") and any("xylophone" in c for c in kw_hit)

        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE source LIKE 'smoke://%'")
        conn.commit()

    print("\nDATA-PLANE OK" if ok else "\nDATA-PLANE FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
