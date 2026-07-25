# 0001. Use pgvector as the primary vector store

- **Status:** accepted
- **Date:** 2026-08-03
- **Project:** P1 (and everything downstream)

## Context

Every project from P1 onward needs vector storage and retrieval. The choice constrains the
whole repo, so it is worth deciding deliberately rather than defaulting to whatever the
tutorial used.

Two constraints are specific to this situation:
- SQL and data modelling are existing strengths (15 years of warehouse and BI work). Time
  spent learning a new query language is time not spent on the actual gaps.
- The portfolio needs to look like enterprise engineering, not a hobby project.

## Options considered

**pgvector on Postgres.** Vector search as a Postgres extension. Hybrid search possible in
a single query alongside `pg_trgm`/full-text. Metadata filtering is just SQL `WHERE`.
Downside: at very large scale, dedicated engines index faster and offer richer filtering
primitives.

**Pinecone / Weaviate (managed).** Fastest to a working demo, good ergonomics. Downsides:
ongoing cost, a network hop per query, an external dependency in a portfolio that should
be self-contained and free to run, and less transparency into what retrieval is doing.

**Qdrant (self-hosted).** Strong filtering, good performance, easy to run in Docker. A
genuine alternative rather than a straw man — the main cost is a second data model and
query language to learn for a capability Postgres already covers at this scale.

**Chroma.** Easiest local start, weakest fit for demonstrating enterprise-grade work.

## Decision

**pgvector as primary. Qdrant kept in `docker-compose.yml` for a Phase 2 comparison.**

The deciding factor is skill transfer. Existing SQL depth converts directly into
retrieval-debugging ability, which is the actual goal — and hybrid search plus metadata
filtering in one query is a real engineering advantage, not just a convenience. pgvector is
also the most common answer in enterprises that already run Postgres, which makes it the
more relevant thing to be fluent in.

## Consequences

**Easier:** hybrid search in one query. Metadata filtering with no special syntax. One
backup story. Debugging retrieval with `EXPLAIN ANALYZE`. Everything runs locally, free.

**Harder:** HNSW index builds must happen after bulk load — building first makes ingestion
crawl. Embedding dimension is pinned in DDL (`vector(1024)`), so changing models means a
new collection rather than an in-place update. At P7's 5,000+ document scale, index build
time will need measuring; if it becomes the bottleneck, that finding is itself worth
writing up.

**Revisit if:** corpus exceeds ~1M chunks, or filtering needs outgrow SQL.

## Evidence

Decided on judgment about skill transfer, not benchmarks — no comparative numbers existed
at decision time. The Phase 2 Qdrant comparison is the planned evidence, and this ADR
should be updated with those results.
