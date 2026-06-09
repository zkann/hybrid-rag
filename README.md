# hybrid-rag

Hybrid retrieval-augmented generation over a document corpus. Dense vector
search (pgvector, HNSW) and keyword search (Postgres full-text) run in
parallel and get fused with Reciprocal Rank Fusion, then a model answers
grounded in the retrieved passages with inline citations.

Postgres is the whole datastore: documents, chunks, embeddings, and the
full-text index all live in one database. No separate vector service.

## Why hybrid

Dense vector search captures meaning. Ask "how do I guard a route" and it finds
the section on dependencies even though those words never appear. But it misses
rare exact tokens: an API symbol, an error code, a flag name. Keyword search is
the opposite, exact on tokens, blind to paraphrase.

Reciprocal Rank Fusion combines the two ranked lists without putting their
scores on a shared scale:

```
score(doc) = sum over arms of  1 / (rrf_k + rank_in_arm)
```

A passage ranked highly by either arm rises; a passage both arms agree on wins.
It is simple and has one parameter. Whether it actually beats a single retriever
depends on your corpus, which is the point of the eval harness below: on the
clean prose corpus here, dense retrieval alone turned out to be competitive, and
hybrid earns its keep mainly on corpora full of rare exact tokens. Measure, don't
assume.

## Architecture

```
                ┌─────────────── query ───────────────┐
                │                                      │
        embed (OpenAI)                          websearch_to_tsquery
                │                                      │
     vector search (pgvector,                  keyword search (GIN,
       HNSW, cosine)                             ts_rank_cd)
                │                                      │
                └──────────► Reciprocal Rank ◄─────────┘
                                Fusion
                                  │
                          top-k passages
                                  │
                      grounded answer + [n] citations
                       (Anthropic default / OpenAI)
```

- **Ingestion** (`app/ingest.py`): heading-aware, token-windowed chunking
  (`app/chunking.py`, tiktoken), batched embeddings, idempotent upsert keyed on
  source.
- **Retrieval** (`app/retrieval.py`): the two arms + RRF. Pure fusion function
  is unit-tested.
- **Generation** (`app/generate.py`): answers only from context, cites passages,
  says "I don't know" when the context lacks the answer. Provider is switchable.
- **API** (`app/main.py`): FastAPI. `/health`, `/search` (retrieval only),
  `/ask` (full RAG). Same app runs locally on uvicorn and on Lambda via Mangum.

## Stack

Python 3.12, FastAPI, Postgres 17 + pgvector, OpenAI embeddings
(`text-embedding-3-small`, 1536-dim), Anthropic or OpenAI for generation,
Terraform for the AWS deploy (RDS + container Lambda + API Gateway).

## Quickstart (local)

```bash
make install            # venv + deps
cp .env.example .env     # add OPENAI_API_KEY and ANTHROPIC_API_KEY
make db-up               # Postgres 17 + pgvector in Docker
make seed                # clone a docs corpus and index it
make serve               # http://localhost:8000
```

Ask it something:

```bash
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"query":"How do I declare a request body?"}' | jq
```

Inspect retrieval without generation:

```bash
curl -s localhost:8000/search -H 'content-type: application/json' \
  -d '{"query":"background tasks", "top_k": 5}' | jq
```

The default corpus is a slice of the FastAPI documentation. Point `make seed`
at any markdown docs (`SEED_REPO`, `SEED_SUBDIR`) or ingest URLs:

```bash
python -m scripts.ingest_docs --url https://example.com/docs/page
```

## Tests

```bash
make test
```

Covers the fusion math, the chunker, and the eval metrics (pure, no DB or network).

## Evaluation

`evals/` measures retrieval and answer quality instead of trusting vibes.
`make eval` runs a labeled query set through all three strategies and reports
document-level recall@k, hit@k, MRR, and nDCG@k; `make eval-judge` adds an
LLM-as-judge pass for answer faithfulness and relevance.

Results on the sample corpus (FastAPI docs, 28 queries, k=5):

| strategy | recall@5 | MRR | nDCG@5 |
|---|---|---|---|
| hybrid | 0.964 | 0.911 | 0.919 |
| vector | 0.982 | 1.000 | 0.986 |
| keyword | 0.500 | 0.449 | 0.451 |

Honest finding: on this clean, well-written corpus, dense retrieval alone is
strong enough that hybrid does not beat it. The keyword arm mostly adds noise on
paraphrase queries, and even on exact-symbol queries the embedding model already
retrieves perfectly. Hybrid earns its keep on corpora full of rare exact tokens
that embeddings garble (error codes, part numbers, identifiers, jargon), which
this corpus is not. The harness exists to make that call per corpus, with
weighted or query-adaptive fusion as the next tuning lever, rather than
cargo-culting hybrid. Details in `evals/README.md`.

## Deploy

`make package` builds a Lambda zip; the container path and full Terraform
(RDS + Lambda + API Gateway) are in `infra/` and `DEPLOY.md`. RDS is a paid
resource, so deploy is deliberate.

## Design notes / scope

- One Postgres for everything keeps ops simple and the data colocated. At larger
  scale you would tune HNSW (`m`, `ef_construction`, `ef_search`) and likely
  pre-filter by metadata before the vector scan.
- Chunking is heading-aware then token-windowed with overlap, a deliberate
  middle ground between naive fixed-size splits and full semantic chunking.
- RRF over a learned reranker is a cost choice: no extra model call on the hot
  path. A cross-encoder reranker is the natural next upgrade.
- Embeddings are an API call (no local model), which keeps the Lambda image
  small and cold starts reasonable.
