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
    from app.api.documents import get_document_status, get_document_file, list_documents
    from fastapi import HTTPException

    # Test get_document_status with non-UUID
    with pytest.raises(HTTPException) as exc_info:
        await get_document_status("pubbook-fee51ebe1fd3d0d1")
    assert exc_info.value.status_code == 404

    # Test get_document_file with non-UUID
    with pytest.raises(HTTPException) as exc_info:
        await get_document_file("not-a-valid-uuid")
    assert exc_info.value.status_code == 404

    # Test list_documents with invalid tenant_id
    with pytest.raises(HTTPException) as exc_info:
        await list_documents(tenant_id="invalid-tenant-uuid")
    assert exc_info.value.status_code == 400

    # Test delete_document with non-UUID
    from app.api.documents import delete_document
    with pytest.raises(HTTPException) as exc_info:
        await delete_document("not-a-valid-uuid")
    assert exc_info.value.status_code == 404

