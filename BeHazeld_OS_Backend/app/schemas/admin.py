import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CreateTenantRequest(BaseModel):
    name: str
    slug: str


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class CreateUserRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    tenant_id: uuid.UUID
    is_superuser: bool = False


class UserListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    tenant_id: uuid.UUID
    created_at: datetime


class UpdateUserRequest(BaseModel):
    is_active: bool | None = None
    is_superuser: bool | None = None
