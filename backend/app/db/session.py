from __future__ import annotations
import uuid
from typing import AsyncGenerator, Optional, Union
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

# Engine setup
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    future=True
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def set_tenant_context(session: AsyncSession, tenant_id: Union[str, uuid.UUID]) -> None:
    """Sets PostgreSQL session variable for Row Level Security (RLS) tenant isolation."""
    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": str(tenant_id)}
    )


async def get_db(tenant_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session and manages its lifecycle."""
    async with AsyncSessionLocal() as session:
        try:
            if tenant_id:
                await set_tenant_context(session, tenant_id)
            yield session
        finally:
            await session.close()
