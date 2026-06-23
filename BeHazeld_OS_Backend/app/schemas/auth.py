import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    tenant_id: uuid.UUID


class TokenData(BaseModel):
    sub: str
    tenant_id: str
    permissions: list[str] = []
    type: str = "access"
