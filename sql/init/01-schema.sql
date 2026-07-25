-- Applied AI Lab schema. Runs once, on a fresh pgdata volume.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS documents (
    id           BIGSERIAL PRIMARY KEY,
    source_uri   TEXT NOT NULL,
    content_hash TEXT UNIQUE NOT NULL,
    doc_type     TEXT,
    title        TEXT,
    metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every parse failure is recorded. A pipeline that silently drops documents
-- produces eval scores that lie to you.
CREATE TABLE IF NOT EXISTS ingest_failures (
    id          BIGSERIAL PRIMARY KEY,
    source_uri  TEXT NOT NULL,
    stage       TEXT NOT NULL,
    error_class TEXT,
    error       TEXT,
    failed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           BIGSERIAL PRIMARY KEY,
    document_id  BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    collection   TEXT NOT NULL DEFAULT 'default',
    chunk_index  INT NOT NULL,
    content      TEXT NOT NULL,
    token_count  INT,
    embedding    vector(1024),
    metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (document_id, collection, chunk_index)
);

-- Build HNSW after bulk load, not before.
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_content_trgm
    ON chunks USING gin (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS chunks_collection_idx ON chunks (collection);

-- Eval run history. Never mutate a metric definition in place; version it,
-- so historical results stay comparable.
CREATE TABLE IF NOT EXISTS eval_runs (
    id             BIGSERIAL PRIMARY KEY,
    project        TEXT NOT NULL,
    dataset        TEXT NOT NULL,
    dataset_ver    TEXT NOT NULL,
    config         JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics        JSONB NOT NULL DEFAULT '{}'::jsonb,
    total_cost_usd NUMERIC(10,4),
    git_sha        TEXT,
    run_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
