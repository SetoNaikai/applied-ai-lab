"""Ingestion pipeline for RAG corpus."""

from __future__ import annotations

from .ingest import ingest_files
from .models import DocumentSource, IngestConfig, IngestFailure, IngestResult

__all__ = ["DocumentSource", "IngestConfig", "IngestFailure", "IngestResult", "ingest_files"]
