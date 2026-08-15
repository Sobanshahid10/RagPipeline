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
