"""Pydantic Settings — single source of config truth, loaded from env."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === App ===
    app_name: str = "Astoka API"
    debug: bool = False

    # === Database ===
    database_url: str = Field(
        default="postgresql+asyncpg://astoka:astoka@localhost:5432/astoka",
        description="SQLAlchemy async DSN.",
    )

    # === Redis ===
    redis_url: str = Field(default="redis://localhost:6379/0")

    # === MinIO ===
    minio_endpoint: str = Field(default="localhost:9000")
    minio_root_user: str = Field(default="astoka")
    minio_root_password: str = Field(default="changeme")
    minio_bucket: str = Field(default="astoka")
    minio_secure: bool = Field(default=False)

    # === Auth ===
    api_secret_key: str = Field(default="changeme-generate-with-openssl-rand-hex-32")
    jwt_algorithm: str = Field(default="HS256")
    jwt_ttl_hours: int = Field(default=24)

    # === CORS ===
    api_cors_origins: str = Field(default="http://localhost:3000")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    # === LLM ===
    llm_provider: Literal["local", "openai_compatible"] = Field(default="local")
    ollama_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.3:8b-instruct-q4_K_M")
    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    openai_model: str = Field(default="gpt-4o-mini")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
