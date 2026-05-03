from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM Provider（支持任意 OpenAI 兼容 API）
    openai_api_key: str = ""
    openai_base_url: str = ""  # 留空则使用官方，填入自定义 endpoint

    # Embedding Provider（留空则复用上面的 openai 配置）
    embedding_api_key: str = ""
    embedding_base_url: str = ""

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536  # Must match embedding_model output dimension

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 64

    # LLM
    llm_model: str = "gpt-4o-mini"

    # Database
    database_url: str = "postgresql://ara:ara@localhost:5432/ara"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Tavily Web Search（可选）
    tavily_api_key: str = ""

    # Server
    debug: bool = False


settings = Settings()
