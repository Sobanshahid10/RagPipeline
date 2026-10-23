import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.models.base import Base

# Async SQLite in-memory engine for unit and integration testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_async_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create fresh database tables for each test function, yielding a clean async session."""
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """FastAPI AsyncClient fixture overriding get_db dependency with test database session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def offline_providers(monkeypatch):
    """Tests must never use local credentials or consume provider quota."""
    from app.config import settings
    from app.api import query
    from unittest.mock import AsyncMock

    for key in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setattr(settings, key, None)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "PII_REQUIRED", False)
    monkeypatch.setattr(query, "_reserve_query", AsyncMock())

    # Each test has its own limiter state; no dependency on a local Redis server.
    import redis.asyncio
    from unittest.mock import MagicMock

    offline = MagicMock()
    offline.eval = AsyncMock(side_effect=ConnectionError("offline test"))
    offline.mget = AsyncMock(side_effect=ConnectionError("offline test"))
    offline.aclose = AsyncMock()
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *a, **kw: offline)
    middleware = app.middleware_stack
    while middleware:
        if hasattr(middleware, "_history"):
            middleware._history.clear()
            middleware._redis = offline
        middleware = getattr(middleware, "app", None)
