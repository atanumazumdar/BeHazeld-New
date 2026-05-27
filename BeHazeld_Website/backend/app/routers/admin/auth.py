"""
POST /admin/auth/token

Exchange the ADMIN_API_KEY for a short-lived JWT.
The JWT is then used as a Bearer token for all other admin endpoints.
"""

from fastapi import APIRouter, HTTPException, status

from app.routers.admin.dependencies import (
    ADMIN_API_KEY,
    ADMIN_JWT_EXPIRY,
    create_access_token,
)
from app.schemas.admin import TokenRequest, TokenResponse

router = APIRouter(prefix="/admin/auth", tags=["admin — auth"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Exchange API key for a JWT",
    description=(
        "Send `{\"api_key\": \"<your ADMIN_API_KEY>\"}` to receive a Bearer token "
        "valid for 24 hours. Include it as `Authorization: Bearer <token>` on all "
        "subsequent admin requests."
    ),
)
def get_token(body: TokenRequest) -> TokenResponse:
    if body.api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return TokenResponse(
        access_token=create_access_token(),
        expires_in=ADMIN_JWT_EXPIRY,
    )
