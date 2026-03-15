from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key: str = ""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "scriptures"
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o"
    embedding_dimension: int = 1536
    top_k_results: int = 8
    batch_size: int = 20
    # Comma-separated list of allowed CORS origins
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Rate limiting: requests per minute per IP
    rate_limit: str = "30/minute"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
