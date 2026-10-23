import asyncio
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import Tenant, User
from app.schemas.auth import Token, UserCreate, UserProfile

router = APIRouter()


def slugify(text: str) -> str:
    """Generate a clean URL-safe slug from a string."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return cleaned or f"tenant-{uuid.uuid4().hex[:8]}"


@router.post(
    "/register",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Register new tenant and admin user",
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)) -> Any:
    """Create a new tenant organization and its primary administrator account."""
    normalized_email = user_in.email.strip().lower()

    # Check for existing user
    stmt = select(User).where(User.email == normalized_email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # Fit VARCHAR(50) and avoid a check-then-insert race for identical names.
    slug = f"{slugify(user_in.tenant_name)[:37]}-{uuid.uuid4().hex[:12]}"
    password_hash = await asyncio.to_thread(hash_password, user_in.password)

    # Create tenant
    tenant = Tenant(name=user_in.tenant_name.strip(), slug=slug)
    db.add(tenant)
    try:
        await db.flush()  # Flush to populate tenant.id

        # Create user associated with the new tenant
        user = User(
            tenant_id=tenant.id,
            email=normalized_email,
            hashed_password=password_hash,
            roles=["admin"],
            is_active=True,
        )
        db.add(user)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            409,
            "Registration conflicts with an existing account. Please sign in or try again.",
        ) from exc
    await db.refresh(user)
    await db.refresh(tenant)
    user.tenant = tenant

    return user


@router.post(
    "/login", response_model=Token, summary="Authenticate user and obtain JWT token"
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> Any:
    """OAuth2 compatible token login, returns Bearer JWT access token."""
    normalized_email = form_data.username.strip().lower()

    stmt = select(User).where(User.email == normalized_email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not await asyncio.to_thread(
        verify_password, form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email,
            "roles": user.roles,
        }
    )

    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me", response_model=UserProfile, summary="Get current authenticated user profile"
)
async def read_current_user(current_user: User = Depends(get_current_user)) -> Any:
    """Fetch profile data for the currently authenticated user session."""
    return current_user
