from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 64

    # LLM
    llm_model: str = "gpt-4o-mini"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Server
    debug: bool = False


settings = Settings()
