"""Test suite for ingestion pipeline."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from ingest.ingest import ingest_files
from ingest.models import IngestConfig


@pytest.mark.asyncio
async def test_ingest_success():
    """Test successful ingestion of valid files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test documents
        doc1 = Path(tmpdir) / "doc1.txt"
        doc2 = Path(tmpdir) / "doc2.txt"

        doc1.write_text("This is document one.")
        doc2.write_text("This is document two. It has more content to test chunking.")

        config = IngestConfig(
            source_paths=[f"{tmpdir}/*.txt"],
            chunk_size=512,
            chunk_overlap=64,
            max_concurrent_tasks=2,
        )

        result = await ingest_files(config)

        assert result.total_files == 2
        assert result.total_chunks > 0
        assert len(result.failed_files) == 0


def test_failure_log_format():
    """Test that failure logs are valid JSONL."""
    # Create a sample failure log entry
    from ingest.models import IngestFailure

    failure = IngestFailure(
        file_path="/fake/path.txt",
        error_message="Simulated error for testing",
    )

    json_str = failure.model_dump_json()
    parsed = json.loads(json_str)

    assert parsed["file_path"] == "/fake/path.txt"
    assert "error_message" in parsed
    assert "timestamp" in parsed


@pytest.mark.asyncio
async def test_ingest_with_failures():
    """Test ingestion with some files failing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create valid and invalid files
        doc1 = Path(tmpdir) / "doc1.txt"
        bad_file = Path(tmpdir) / "bad_file.unknown"

        doc1.write_text("Valid content.")
        bad_file.touch()  # Empty file with unknown extension

        config = IngestConfig(
            source_paths=[f"{tmpdir}/*.txt", f"{tmpdir}/*.unknown"],
            chunk_size=512,
            chunk_overlap=64,
            max_concurrent_tasks=2,
        )

        result = await ingest_files(config)

        assert result.total_files == 2
        assert len(result.failed_files) >= 1  # At least the bad file should fail
