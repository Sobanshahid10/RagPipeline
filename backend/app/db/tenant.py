"""Transaction-scoped tenant context for every standalone PostgreSQL connection."""

from contextlib import asynccontextmanager
from uuid import UUID

import asyncpg
from app.config import settings


@asynccontextmanager
async def tenant_connection(tenant_id: str):
    tenant = str(UUID(str(tenant_id)))
    conn = await asyncpg.connect(
        settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('app.current_tenant_id', $1, true)", tenant
            )
            await conn.execute(
                "SELECT set_config('statement_timeout', $1, true)", "30000"
            )
            yield conn
    finally:
        await conn.close()
