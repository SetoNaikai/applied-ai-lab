"""Ingestion pipeline with failure logging."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

from .models import IngestConfig, IngestResult, IngestFailure

logger = logging.getLogger(__name__)


def _ensure_failure_log_dir(log_dir: str) -> None:
    """Ensure the failure log directory exists."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)


def _write_failure_log(failure: IngestFailure, log_dir: str = "ingest_failures") -> None:
    """Write a single failure to the JSONL log."""
    _ensure_failure_log_dir(log_dir)
    log_path = Path(log_dir) / "failures.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(failure.model_dump_json() + "\n")


async def _process_file(
    file_path: str,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[str, Optional[str]]:
    """Process a single file and return (file_path, error_message | None)."""
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path.as_posix()}")

        if path.suffix not in (".txt", ".md"):
            raise ValueError(f"Unsupported file type: {path.suffix}")

        # Read content
        text = path.read_text(encoding="utf-8")
        
        # Chunk (placeholder - real chunking in libs/retrieval)
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - chunk_overlap)]

        logger.info(f"Processed {path.as_posix()}: {len(chunks)} chunks")
        return path.as_posix(), None
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        return file_path, error_msg


async def ingest_files(
    config: IngestConfig,
    log_dir: str = "ingest_failures",
) -> IngestResult:
    """Ingest files with concurrent processing and failure logging."""
    _ensure_failure_log_dir(log_dir)

    # Expand glob patterns
    source_files: List[str] = []
    for pattern in config.source_paths:
        pattern_path = Path(pattern)
        matches = list(pattern_path.parent.glob(pattern_path.name))
        if not matches:
            logger.warning(f"No files matched pattern: {pattern}")
        source_files.extend(p.as_posix() for p in matches)

    if not source_files:
        raise ValueError("No source files found matching the provided patterns")

    # Process concurrently
    semaphore = asyncio.Semaphore(config.max_concurrent_tasks)

    async def _limited_process(file_path: str) -> tuple[str, Optional[str]]:
        async with semaphore:
            return await _process_file(
                file_path,
                config.chunk_size,
                config.chunk_overlap,
            )

    tasks = [_limited_process(fp) for fp in source_files]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Aggregate results
    total_chunks = 0
    failed_files: List[tuple[str, str]] = []

    for file_path, error_msg in results:
        if error_msg is None:
            # Success - count chunks (placeholder logic)
            path = Path(file_path)
            text = path.read_text(encoding="utf-8")
            total_chunks += len([text[i:i+config.chunk_size] for i in range(0, len(text), config.chunk_size - config.chunk_overlap)])
        else:
            failed_files.append((file_path, error_msg))
            # Log failure
            _write_failure_log(
                IngestFailure(file_path=file_path, error_message=error_msg),
                log_dir,
            )

    return IngestResult(
        total_files=len(source_files),
        total_chunks=total_chunks,
        failed_files=failed_files,
    )
