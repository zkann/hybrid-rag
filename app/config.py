from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://rag:rag@localhost:5433/rag"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # Generation provider: "anthropic" (default) or "openai".
    gen_provider: str = "anthropic"
    anthropic_model: str = "claude-haiku-4-5-20251001"
    openai_model: str = "gpt-4o-mini"

    # Chunking (token-based, via tiktoken cl100k_base).
    chunk_tokens: int = 512
    chunk_overlap: int = 64

    # Retrieval. We pull candidate_k from each arm, fuse with RRF, return top_k.
    candidate_k: int = 30
    top_k: int = 8
    rrf_k: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
