"""pgvector-backed store with dense, lexical, and hybrid search.

pgvector over a dedicated vector DB is a deliberate choice: SQL is already a
strength, and Postgres is the most common enterprise answer. Qdrant is in the
compose file for a Phase 2 comparison -- see docs/adr/001.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import DictRow, dict_row
from psycopg.types.json import Json

from libs.llm import embed
from libs.retrieval.chunking import Chunk
from libs.retrieval.hybrid import reciprocal_rank_fusion
from libs.settings import get_settings


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    content: str
    score: float
    source_uri: str
    metadata: dict[str, Any]


class PgVectorStore:
    def __init__(self, collection: str = "default", dsn: str | None = None) -> None:
        self.collection = collection
        self.dsn = dsn or get_settings().database_url

    def _conn(self) -> psycopg.Connection[DictRow]:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    # ---- ingestion -------------------------------------------------------

    def add_document(
        self,
        *,
        source_uri: str,
        content: str,
        doc_type: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int | None:
        """Insert a document. Returns None if already ingested (hash collision)."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (source_uri, content_hash, doc_type, title, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (content_hash) DO NOTHING
                RETURNING id
                """,
                (
                    source_uri,
                    content_hash,
                    doc_type,
                    title,
                    Json(metadata or {}),
                ),
            )
            row = cur.fetchone()
            return row["id"] if row else None

    def record_failure(self, source_uri: str, stage: str, error: Exception) -> None:
        """Never let a parse failure vanish. Silent drops corrupt every score downstream."""
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingest_failures (source_uri, stage, error_class, error)
                VALUES (%s, %s, %s, %s)
                """,
                (source_uri, stage, type(error).__name__, str(error)[:2000]),
            )

    async def add_chunks(self, document_id: int, chunks: list[Chunk]) -> int:
        vectors = await embed([c.content for c in chunks])
        with self._conn() as conn, conn.cursor() as cur:
            for chunk, vector in zip(chunks, vectors, strict=True):
                cur.execute(
                    """
                    INSERT INTO chunks
                        (document_id, collection, chunk_index, content, token_count,
                         embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (document_id, collection, chunk_index) DO UPDATE
                        SET content = EXCLUDED.content, embedding = EXCLUDED.embedding
                    """,
                    (
                        document_id,
                        self.collection,
                        chunk.index,
                        chunk.content,
                        chunk.token_count,
                        str(vector),
                        Json(chunk.metadata),
                    ),
                )
        return len(chunks)

    def build_index(self) -> None:
        """Call AFTER bulk load. Building HNSW first makes ingestion crawl."""
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw "
                "ON chunks USING hnsw (embedding vector_cosine_ops)"
            )

    # ---- search ----------------------------------------------------------

    async def search_dense(
        self, query: str, k: int = 10, filters: dict[str, Any] | None = None
    ) -> list[SearchHit]:
        vector = (await embed([query]))[0]
        clause, params = self._filter_clause(filters)
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT c.id, c.document_id, c.content, c.metadata, d.source_uri,
                       1 - (c.embedding <=> %s::vector) AS score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.collection = %s {clause}
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (str(vector), self.collection, *params, str(vector), k),
            )
            return [self._hit(r) for r in cur.fetchall()]

    def search_lexical(
        self, query: str, k: int = 10, filters: dict[str, Any] | None = None
    ) -> list[SearchHit]:
        clause, params = self._filter_clause(filters)
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT c.id, c.document_id, c.content, c.metadata, d.source_uri,
                       ts_rank(to_tsvector('english', c.content),
                               plainto_tsquery('english', %s)) AS score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.collection = %s
                  AND to_tsvector('english', c.content) @@ plainto_tsquery('english', %s)
                  {clause}
                ORDER BY score DESC
                LIMIT %s
                """,
                (query, self.collection, query, *params, k),
            )
            return [self._hit(r) for r in cur.fetchall()]

    async def search_hybrid(
        self,
        query: str,
        k: int = 10,
        *,
        dense_weight: float = 1.0,
        lexical_weight: float = 1.0,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        dense = await self.search_dense(query, k=k * 2, filters=filters)
        lexical = self.search_lexical(query, k=k * 2, filters=filters)
        by_id = {h.chunk_id: h for h in [*dense, *lexical]}
        fused = reciprocal_rank_fusion(
            [[h.chunk_id for h in dense], [h.chunk_id for h in lexical]],
            weights=[dense_weight, lexical_weight],
        )
        out: list[SearchHit] = []
        for chunk_id, score in fused[:k]:
            hit = by_id[chunk_id]
            hit.score = score
            out.append(hit)
        return out

    # ---- helpers ---------------------------------------------------------

    @staticmethod
    def _filter_clause(filters: dict[str, Any] | None) -> tuple[str, tuple[Any, ...]]:
        """Metadata filtering -- the thing enterprises always need and demos omit."""
        if not filters:
            return "", ()
        clauses, params = [], []
        for key, value in filters.items():
            clauses.append("c.metadata->>%s = %s")
            params.extend([key, str(value)])
        return "AND " + " AND ".join(clauses), tuple(params)

    @staticmethod
    def _hit(row: dict[str, Any]) -> SearchHit:
        return SearchHit(
            chunk_id=str(row["id"]),
            document_id=str(row["document_id"]),
            content=row["content"],
            score=float(row["score"] or 0.0),
            source_uri=row["source_uri"],
            metadata=row["metadata"] or {},
        )
