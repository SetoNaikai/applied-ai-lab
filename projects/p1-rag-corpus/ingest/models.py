"""Pydantic models for ingestion pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentSource(BaseModel):
    """Source document metadata."""

    uri: str = Field(..., description="Public source URI (e.g., SEC filing URL)")
    license: str = Field(..., description="License identifier (e.g., 'CC-BY-4.0')")
    retrieval_date: datetime = Field(..., description="When the document was fetched")


class IngestConfig(BaseModel):
    """Configuration for the ingestion pipeline."""

    source_paths: List[str] = Field(
        ...,
        description="List of source file paths to ingest (glob patterns OK)",
    )
    chunk_size: int = Field(512, description="Size of each chunk in tokens")
    chunk_overlap: int = Field(64, description="Overlap between chunks in tokens")
    max_concurrent_tasks: int = Field(4, description="Maximum concurrent ingestion tasks")


class IngestResult(BaseModel):
    """Result of the ingestion pipeline."""

    total_files: int = Field(..., description="Total number of files processed")
    total_chunks: int = Field(..., description="Total number of chunks created")
    failed_files: List[tuple[str, str]] = Field(
        default_factory=list,
        description="List of (file_path, error_message) for failures",
    )


class IngestFailure(BaseModel):
    """Single failure record."""

    file_path: str = Field(..., description="Absolute path to the failed file")
    error_message: str = Field(..., description="Human-readable error message")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the failure occurred")
