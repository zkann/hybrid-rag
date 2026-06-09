-- Schema for hybrid (keyword + vector) RAG over a document corpus.
-- Idempotent: safe to run repeatedly.
-- Vector dim 1536 matches OpenAI text-embedding-3-small. Change both together.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source      TEXT NOT NULL,            -- file path or URL
    title       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source)
);

CREATE TABLE IF NOT EXISTS chunks (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id  BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ord          INT NOT NULL,            -- chunk order within the document
    content      TEXT NOT NULL,
    embedding    vector(1536),
    -- generated full-text column powers the keyword half of hybrid retrieval
    tsv          tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

-- Vector half: HNSW index for fast approximate cosine nearest-neighbour.
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);

-- Keyword half: GIN index over the generated tsvector.
CREATE INDEX IF NOT EXISTS chunks_tsv_gin
    ON chunks USING gin (tsv);

CREATE INDEX IF NOT EXISTS chunks_document_id
    ON chunks (document_id);
