from __future__ import annotations
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Production RAG Engine"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql+asyncpg://rag_user:rag_password@postgres:5432/rag_db"
    REDIS_URL: str = "redis://redis:6379/0"
    JWT_SECRET: str = "super_secret_jwt_key_change_in_production_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # LLM & Embedding API Providers (Groq GPT-OSS / Gemini / Local)
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "gemini"  # "gemini" | "groq" | "local"
    LLM_MODEL: str = "gemini-3.8-flash"  # Change in .env or per public-book request
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536
    HNSW_EF_SEARCH: int = 100
    EMBEDDING_CACHE_TTL: int = 2592000  # 30 days in seconds

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
