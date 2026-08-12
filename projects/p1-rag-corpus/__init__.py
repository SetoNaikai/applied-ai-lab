"""P1 RAG Corpus project."""
from __future__ import annotations

from ingest.ingest import ingest_files
from ingest.models import DocumentSource, IngestConfig, IngestFailure, IngestResult

__all__ = ["DocumentSource", "IngestConfig", "IngestFailure", "IngestResult", "ingest_files"]