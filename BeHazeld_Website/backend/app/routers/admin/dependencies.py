"""
Admin authentication dependency.

Two accepted credential forms:
  1. Authorization: Bearer <jwt>   — for browser sessions / admin dashboard
  2. X-API-Key: <raw key>          — for scripts, seeding, CI pipelines

Environment variables required:
  ADMIN_API_KEY    — the shared secret used to issue JWTs and for direct API-key auth
  ADMIN_JWT_SECRET — secret used to sign / verify JWTs (default: same as API key)
  ADMIN_JWT_EXPIRY — token lifetime in seconds (default: 86400 = 24h)
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

# ── Config ───────────────────────────────────────────────────────────
ADMIN_API_KEY    = os.getenv("ADMIN_API_KEY", "change-me-before-production")
ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", ADMIN_API_KEY)
ADMIN_JWT_EXPIRY = int(os.getenv("ADMIN_JWT_EXPIRY", "86400"))
ALGORITHM        = "HS256"
TOKEN_SUBJECT    = "behazeld-admin"

# ── Security schemes ─────────────────────────────────────────────────
_bearer  = HTTPBearer(auto_error=False)
_api_key = APIKeyHeader(name="X-API-Key", auto_error=False)


# ── Token helpers ─────────────────────────────────────────────────────
def create_access_token() -> str:
    """Issue a signed JWT valid for ADMIN_JWT_EXPIRY seconds."""
    now     = datetime.now(tz=timezone.utc)
    payload = {
        "sub": TOKEN_SUBJECT,
        "iat": now,
        "exp": now + timedelta(seconds=ADMIN_JWT_EXPIRY),
    }
    return jwt.encode(payload, ADMIN_JWT_SECRET, algorithm=ALGORITHM)


def _verify_jwt(token: str) -> None:
    """Raise 401 if the JWT is invalid or expired."""
    try:
        payload = jwt.decode(token, ADMIN_JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("sub") != TOKEN_SUBJECT:
            raise JWTError("wrong subject")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _verify_api_key(key: str) -> None:
    """Raise 401 if the API key does not match."""
    if key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


# ── FastAPI dependency ────────────────────────────────────────────────
def require_admin(
    bearer:  HTTPAuthorizationCredentials | None = Security(_bearer),
    api_key: str | None                          = Security(_api_key),
) -> None:
    """
    Inject this into any admin endpoint with `Depends(require_admin)`.

    Accepts either:
      • Authorization: Bearer <jwt>
      • X-API-Key: <raw key>

    Raises HTTP 401 if neither is valid.
    """
    if bearer is not None:
        _verify_jwt(bearer.credentials)
        return

    if api_key is not None:
        _verify_api_key(api_key)
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide Bearer token or X-API-Key header",
        headers={"WWW-Authenticate": "Bearer"},
    )
