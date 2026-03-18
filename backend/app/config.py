from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Server
    debug: bool = False


settings = Settings()
