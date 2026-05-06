"""Worker config — mirrors API settings shape, loaded independently from same .env."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    redis_url: str = Field(default="redis://localhost:6379/0")
    database_url: str = Field(
        default="postgresql+asyncpg://astoka:astoka@localhost:5432/astoka",
    )
    minio_endpoint: str = Field(default="localhost:9000")
    minio_root_user: str = Field(default="astoka")
    minio_root_password: str = Field(default="changeme")
    minio_bucket: str = Field(default="astoka")
    minio_secure: bool = Field(default=False)
    ollama_url: str = Field(default="http://localhost:11434")


@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
