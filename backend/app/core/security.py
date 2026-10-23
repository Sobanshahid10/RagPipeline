from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
from fastapi import HTTPException, status
import jwt
from jwt import PyJWTError as JWTError

from app.config import settings


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    pwd_bytes = plain.encode("utf-8")
    if len(pwd_bytes) > 72:
        raise ValueError("Password exceeds bcrypt byte limit")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Generate a signed JWT access token containing arbitrary payload data."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": int(expire.timestamp()), "iat": int(now.timestamp())})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Raises:
        HTTPException: 401 Unauthorized if token is expired, invalid, or malformed.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
        return payload
    except JWTError:
        raise credentials_exception
