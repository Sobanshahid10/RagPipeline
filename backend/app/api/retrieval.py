"""Authenticated retrieval API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.retrieval.engine import retrieve

router = APIRouter(prefix=f"{settings.API_V1_STR}/retrieval", tags=["Retrieval"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


@router.post("/search", response_model=list[dict[str, Any]])
async def search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Return the top five tenant-isolated, compressed retrieval results."""
    return await retrieve(request.query, str(current_user.tenant_id))
