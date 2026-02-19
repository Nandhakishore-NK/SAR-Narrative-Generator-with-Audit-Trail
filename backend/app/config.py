"""
SAR Guardian — Application Configuration
Loads all settings from environment variables with validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Centralized configuration loaded from environment.
    Every deployment-sensitive value is externalized.
    """

    # ------- Database -------
    DATABASE_URL: str = "sqlite+aiosqlite:///./sar_guardian.db"
    # Synchronous URL for Alembic migrations
    DATABASE_URL_SYNC: str = "sqlite:///./sar_guardian.db"

    # ------- JWT Authentication -------
    JWT_SECRET_KEY: str = "replace-with-256-bit-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ------- LLM Configuration -------
    OPENAI_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.2

    # ------- Redis -------
    REDIS_URL: str = "redis://redis:6379/0"

    # ------- ChromaDB -------
    CHROMA_PERSIST_DIR: str = "./data/chromadb"

    # ------- Application -------
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
