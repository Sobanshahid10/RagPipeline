import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class TenantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)


class TenantCreate(TenantBase):
    slug: Optional[str] = None


class TenantOut(TenantBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    created_at: datetime


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=12, max_length=72)
    tenant_name: str = Field(..., min_length=2, max_length=100)

    @field_validator("tenant_name", mode="before")
    @classmethod
    def normalize_tenant_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def password_byte_limit(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class UserLogin(UserBase):
    password: str


class UserProfile(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    roles: List[str] = ["viewer"]
    is_active: bool = True
    created_at: datetime
    tenant: Optional[TenantOut] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: List[str] = []
    exp: Optional[int] = None
