import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db, set_tenant_context
from app.models.user import User

# OAuth2 scheme configured with the login endpoint URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """FastAPI dependency to extract and validate the authenticated user from JWT.

    Decodes the token, verifies the user in PostgreSQL, and configures the tenant
    session variable for RLS enforcement.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    except (ValueError, TypeError):
        raise credentials_exception

    stmt = select(User).options(selectinload(User.tenant)).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # SQLite unit tests do not implement PostgreSQL session settings.
    if db.bind.dialect.name == "postgresql":
        await set_tenant_context(db, user.tenant_id)
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


async def require_writer(current_user: User = Depends(get_current_user)) -> User:
    if not set(current_user.roles or []) & {"admin", "editor"}:
        raise HTTPException(
            status_code=403,
            detail="Document changes require an editor or administrator role",
        )
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if "admin" not in (current_user.roles or []):
        raise HTTPException(status_code=403, detail="Administrator role required")
    return current_user
