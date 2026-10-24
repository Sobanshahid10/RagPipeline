from __future__ import annotations
import secrets
from typing import Optional, Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Production RAG Engine"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql+asyncpg://rag_runtime@postgres:5432/rag_db"
    REDIS_URL: str = "redis://redis:6379/0"
    JWT_SECRET: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:3005"]
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024
    MAX_EXPANDED_BYTES: int = 100 * 1024 * 1024
    MAX_DOCUMENT_PAGES: int = 500
    MAX_DOCUMENT_CHARS: int = 2_000_000
    MAX_DOCUMENT_CHUNKS: int = 4000
    MAX_GRAPH_CHUNKS: int = 128
    GRAPH_EXTRACTION_TIMEOUT_SECONDS: float = Field(default=45, gt=0, le=300)
    MAX_TENANT_STORAGE_BYTES: int = 1024 * 1024 * 1024
    PII_REQUIRED: bool = True
    MAX_ANSWER_CHARS: int = 24000
    ANSWER_TIMEOUT_SECONDS: float = Field(default=45, gt=0, le=300)
    QUERY_BUDGET_PER_DAY: int = 1000

    @model_validator(mode="after")
    def production_settings(self):
        if self.ENVIRONMENT == "production":
            if (
                "JWT_SECRET" not in self.model_fields_set
                or len(self.JWT_SECRET) < 32
                or "change_in_production" in self.JWT_SECRET
            ):
                raise ValueError(
                    "Production requires a unique JWT_SECRET of at least 32 characters"
                )
            if not self.CORS_ORIGINS or any(
                not origin.startswith("https://") for origin in self.CORS_ORIGINS
            ):
                raise ValueError("Production CORS_ORIGINS must use HTTPS")
            if not self.PII_REQUIRED:
                raise ValueError("Production requires PII_REQUIRED=true")
        return self

    ALGORITHM: Literal["HS256"] = "HS256"
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
        extra="ignore",
    )


settings = Settings()
