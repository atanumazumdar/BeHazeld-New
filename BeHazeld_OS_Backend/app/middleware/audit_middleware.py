"""
AuditMiddleware — global HTTP mutation logger.

Intercepts every POST, PATCH, PUT, and DELETE request, captures the
request body and response status, and writes one row to audit.activity_log
using an isolated DB session so audit writes never interfere with the
primary request transaction.

JWT extraction
--------------
Attempts to decode the Bearer token to extract tenant_id and user_id.
Falls back silently to None for unauthenticated (public) requests.

Body capture
------------
FastAPI caches request.body() after the first read, so downstream
handlers still receive the full body after middleware reads it.

Non-fatal design
----------------
If the audit write fails (DB down, schema missing), the exception is
swallowed and the original response is returned unchanged.  Audit loss
is preferable to blocking a real business request.

Excluded paths
--------------
Health-check and docs paths are skipped.  Configurable via AUDIT_SKIP_PATHS.
"""
from __future__ import annotations

import uuid
from typing import Callable

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.audit import _PAYLOAD_MAX
from app.services.audit_service import AuditService

_AUDIT_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

_SKIP_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon",
)


def _try_extract_claims(request: Request) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """
    Attempt to decode the JWT from the Authorization header.
    Returns (tenant_id, user_id) or (None, None) on any failure.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, None
    token = auth[len("Bearer "):]
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        tenant_id_raw = payload.get("tenant_id")
        user_id_raw   = payload.get("sub")
        tenant_id = uuid.UUID(tenant_id_raw) if tenant_id_raw else None
        user_id   = uuid.UUID(user_id_raw)   if user_id_raw   else None
        return tenant_id, user_id
    except (JWTError, ValueError, AttributeError):
        return None, None


def _get_client_ip(request: Request) -> str | None:
    """Extract real client IP, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Log every mutable HTTP request to audit.activity_log.

    Mount order: add AFTER exception-handler registration so we capture
    the final HTTP status, not the raw exception.
    """

    def __init__(self, app: ASGIApp, **kwargs) -> None:
        super().__init__(app, **kwargs)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip non-mutating methods and internal paths
        if request.method not in _AUDIT_METHODS:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        # Read and cache body (FastAPI re-reads from cache; no data loss)
        body_bytes: bytes = await request.body()
        payload_str: str | None = None
        try:
            decoded = body_bytes.decode("utf-8", errors="replace")
            payload_str = decoded[:_PAYLOAD_MAX]
        except Exception:
            payload_str = "<binary payload>"

        # Extract auth context
        tenant_id, user_id = _try_extract_claims(request)
        ip_address = _get_client_ip(request)

        # Execute the request
        response: Response = await call_next(request)

        # Write audit log using a dedicated session (never blocks the response)
        _write_audit_log(
            method=request.method,
            endpoint=str(request.url.path),
            response_status=response.status_code,
            tenant_id=tenant_id,
            user_id=user_id,
            payload=payload_str,
            ip_address=ip_address,
        )

        return response


def _write_audit_log(
    *,
    method: str,
    endpoint: str,
    response_status: int,
    tenant_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    payload: str | None,
    ip_address: str | None,
) -> None:
    """
    Fire-and-forget audit write using an isolated session.
    Swallows all exceptions to avoid blocking the HTTP response.
    """
    try:
        db = SessionLocal()
        try:
            svc = AuditService(db)
            svc.log_and_commit(
                method=method,
                endpoint=endpoint,
                response_status=response_status,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=payload,
                ip_address=ip_address,
            )
        finally:
            db.close()
    except Exception:
        pass   # audit loss is acceptable; never raise from middleware
