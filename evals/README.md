# Evaluation

Measures the two things that decide whether a RAG system is any good: does
retrieval surface the right documents, and is the generated answer faithful to
what was retrieved.

## Retrieval quality (the experiment that justifies hybrid)

`run_eval.py` runs every query in `dataset.jsonl` through all three strategies,
**hybrid**, **vector-only**, and **keyword-only**, and reports document-level
metrics against the labeled relevant sources:

- **recall@k**: fraction of relevant docs found in the top k
- **hit@k**: did any relevant doc make the top k
- **MRR**: reciprocal rank of the first relevant doc
- **nDCG@k**: rank-discounted gain

Running all three side by side turns "hybrid is better" from an assertion into
a measurement. Metrics are document-level: retrieved chunks collapse to their
source before scoring.

### What the eval found (sample corpus, FastAPI docs, k=5)

All 28 queries (20 paraphrase + 8 exact-token):

| strategy | recall@5 | hit@5 | MRR | nDCG@5 |
|---|---|---|---|---|
| hybrid | 0.964 | 1.000 | 0.911 | 0.919 |
| vector | 0.982 | 1.000 | 1.000 | 0.986 |
| keyword | 0.500 | 0.536 | 0.449 | 0.451 |

Exact-token subset only (8 queries, where keyword should help most):

| strategy | recall@5 | MRR | nDCG@5 |
|---|---|---|---|
| hybrid | 1.000 | 1.000 | 1.000 |
| vector | 1.000 | 1.000 | 1.000 |
| keyword | 0.938 | 0.938 | 0.906 |

Takeaway: on this clean prose corpus, dense retrieval alone wins, and hybrid does
not beat it. `text-embedding-3-small` even nails the exact-symbol queries
(BackgroundTasks, jsonable_encoder, WebSocketDisconnect) because those tokens
appear verbatim and the embedding captures them; the keyword arm only adds noise
on paraphrase queries, so unweighted RRF trails pure vector. Hybrid is the right
default for *unknown* corpora and pays off where rare exact tokens defeat the
embedding model (codes, identifiers, jargon). The value here is the measurement:
it tells you, for this corpus, you could ship vector-only, and the next lever if
you needed hybrid to win would be weighted or query-adaptive fusion.

### Answer quality (LLM-as-judge, 28 queries, hybrid retrieval)

| metric | score (1-5) |
|---|---|
| faithfulness | 4.96 |
| answer_relevance | 5.00 |

The generation half holds up: answers are grounded in the retrieved passages
(near-perfect faithfulness, so essentially no hallucination beyond context) and
directly address the question. Combined with the guardrail that makes `/ask`
refuse out-of-context questions, the system answers what it can support and
declines what it can't.

```bash
make eval            # retrieval metrics, hybrid vs vector vs keyword
make eval-judge      # + LLM-as-judge answer quality (spends tokens)
```

## Answer quality (LLM-as-judge)

With `--judge`, each hybrid answer is scored 1-5 on:

- **faithfulness**: are the answer's claims supported by the retrieved context
- **answer_relevance**: does the answer address the question

Reference-free, so no gold answers to maintain. Runs behind a flag because it
costs tokens.

## Dataset

`dataset.jsonl`, one labeled query per line:

```json
{"id": "cors", "question": "How do I enable CORS in FastAPI?", "relevant_sources": ["fastapi/tutorial/cors.md"]}
```

Labels are document sources (stable across re-seeds), not chunk ids.

## What's tested in CI

The metric math (`retrieval_metrics.py`) is unit-tested in `tests/` and runs in
CI on every push, deterministic, no DB or keys. The full retrieval/answer eval
needs a seeded database and API keys, so it runs locally via `make eval`.
