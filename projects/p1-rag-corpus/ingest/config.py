import os
import logging
from typing import List, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class IngestConfig(BaseModel):
    """Configuration for the ingestion pipeline."""
    
    source_paths: List[str] = Field(..., description="List of source file paths to ingest.")
    chunk_size: int = Field(512, description="Size of each chunk in tokens.")
    chunk_overlap: int = Field(64, description="Overlap between chunks in tokens.")
    max_concurrent_tasks: int = Field(4, description="Maximum number of concurrent ingestion tasks.")
    

class IngestResult(BaseModel):
    """Result of the ingestion pipeline."""
    
    total_files: int = Field(..., description="Total number of files ingested.")
    total_chunks: int = Field(..., description="Total number of chunks created.")
    failed_files: List[Tuple[str, str]] = Field(..., description="List of failed files and error messages.")


def load_config(config_path: str) -> IngestConfig:
    """Load configuration from a YAML file."""
    
    with open(config_path, "r") as f:
        config = IngestConfig(**yaml.safe_load(f))
    
    return config


def save_config(config: IngestConfig, config_path: str) -> None:
    """Save configuration to a YAML file."""
    
    with open(config_path, "w") as f:
        yaml.safe_dump(config.dict(), f)


def log_failure(file_path: str, error: str) -> None:
    """Log a failure to the failure log."""
    
    # Create failure log directory if it doesn't exist
    os.makedirs("failure_log", exist_ok=True)
    
    # Write failure to log file
    with open(os.path.join("failure_log", "failure.log"), "a") as f:
        f.write(f"{file_path}: {error}\n")


def main():
    """Main entry point for the ingestion pipeline."""
    
    # Load configuration
    config = load_config("config.yaml")
    
    # Initialize database client
    db_client = chunking.ChunkDBClient(
        db_url="postgresql://user:password@localhost:5432/rag_db",
        collection_name="corpus_chunks",
    )
    
    # Run ingestion pipeline
    result = ingest(config=config, db_client=db_client)
    
    # Print results
    print(f"Ingested {result.total_files} files and {result.total_chunks} chunks.")
    if result.failed_files:
        print(f"Failed to ingest {len(result.failed_files)} files:")
        for file_path, error_message in result.failed_files:
            print(f"  - {file_path}: {error_message}")
            log_failure(file_path, error_message)

if __name__ == "__main__":
    main()