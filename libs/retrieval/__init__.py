"""Retrieval: chunking, hybrid search, and the pgvector store.

`PgVectorStore` is imported lazily so that pure-logic tests (chunking, RRF)
run without a database driver installed. See AGENTS.md (Python conventions).
"""

from typing import TYPE_CHECKING, Any

from libs.retrieval.chunking import Chunk, ChunkStrategy, chunk_document
from libs.retrieval.hybrid import reciprocal_rank_fusion

if TYPE_CHECKING:
    from libs.retrieval.store import PgVectorStore, SearchHit

__all__ = [
    "Chunk",
    "ChunkStrategy",
    "PgVectorStore",
    "SearchHit",
    "chunk_document",
    "reciprocal_rank_fusion",
]

_LAZY = {"PgVectorStore", "SearchHit"}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from libs.retrieval import store

        return getattr(store, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
