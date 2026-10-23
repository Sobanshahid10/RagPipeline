import pytest
from app.main import get_health, get_info
from app.config import settings


@pytest.mark.asyncio
async def test_health_endpoint():
    response = await get_health()
    assert response.status == "healthy"
    assert response.version == "1.0.0"


@pytest.mark.asyncio
async def test_system_info_endpoint():
    response = await get_info()
    assert response.project == settings.PROJECT_NAME
    assert response.environment == "development"


@pytest.mark.asyncio
async def test_invalid_uuid_handling_in_documents():
    from app.main import app
    from app.core.dependencies import get_current_user
    from types import SimpleNamespace
    from httpx import AsyncClient, ASGITransport

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        tenant_id="tenant"
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for suffix in ("", "/file"):
                response = await client.get(
                    "/api/v1/documents/pubbook-not-a-document" + suffix
                )
                assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
