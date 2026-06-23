"""
Auth router — stateless login, token rotation, logout, and profile.

All mutation endpoints return HTTP 200 (not 201) because they either
produce tokens (not a created resource) or perform actions on existing
resources.  POST /logout returns 204 — no body needed.

Cookie strategy (Phase 7):
  - login and refresh set two httpOnly cookies: access_token, refresh_token
  - logout clears both cookies
  - All endpoints remain backward-compatible: body still returned alongside cookies
  - refresh and logout accept token from cookie OR request body (cookie takes priority)
"""
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_tenant
from app.core.config import settings
from app.db.session import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_ACCESS_MAX_AGE  = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60   # seconds
_REFRESH_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400  # seconds
_SECURE          = settings.APP_ENV == "production"


def _set_auth_cookies(response: Response, tokens: TokenResponse) -> None:
    """Write access_token and refresh_token as httpOnly cookies."""
    _cookie_kwargs = dict(httponly=True, secure=_SECURE, samesite="lax", path="/")
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        max_age=_ACCESS_MAX_AGE,
        **_cookie_kwargs,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        max_age=_REFRESH_MAX_AGE,
        **_cookie_kwargs,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Expire both auth cookies immediately."""
    for key in ("access_token", "refresh_token"):
        response.delete_cookie(key=key, path="/", httponly=True, secure=_SECURE, samesite="lax")


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    tokens = AuthService(db).login(body.email, body.password)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    token = AuthService(db).request_password_reset(body.email)
    return ForgotPasswordResponse(
        message="If the account exists, a password reset token has been generated.",
        reset_token=token,
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    AuthService(db).reset_password(body.reset_token, body.new_password)
    return MessageResponse(message="Password has been reset. Please sign in.")


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    cookie_refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
    body: Optional[RefreshRequest] = None,
) -> TokenResponse:
    token = cookie_refresh_token or (body.refresh_token if body else None)
    if not token:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="No refresh token provided")
    tokens = AuthService(db).refresh(token)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    cookie_refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
    body: Optional[RefreshRequest] = None,
) -> None:
    token = cookie_refresh_token or (body.refresh_token if body else None)
    if token:
        AuthService(db).logout(token)
    _clear_auth_cookies(response)


@router.get("/me", response_model=UserResponse)
def me(
    ctx: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> UserResponse:
    return AuthService(db).get_current_user(ctx.user_id)
