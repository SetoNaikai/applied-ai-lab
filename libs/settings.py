"""Central configuration. Loaded from .env; never hardcode keys."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Providers
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None

    # Local inference
    ollama_base_url: str = "http://localhost:11434"
    local_model: str = "llama3.1:8b"
    local_multilingual_model: str = "qwen2.5:7b"
    embedding_model: str = "bge-m3"
    embedding_dim: int = 1024

    # Defaults
    default_frontier_model: str = "claude-sonnet-4-6"
    judge_model: str = "claude-sonnet-4-6"

    # Stores
    database_url: str = "postgresql://lab:changeme_locally@localhost:5432/lab"
    qdrant_url: str = "http://localhost:6333"

    # Observability
    langfuse_host: str = "http://localhost:3001"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    # Cost guardrails (USD)
    max_cost_per_run: float = Field(default=2.00)
    max_cost_per_eval_suite: float = Field(default=10.00)


@lru_cache
def get_settings() -> Settings:
    return Settings()
