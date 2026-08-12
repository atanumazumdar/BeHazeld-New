"""
Application entry point.

Exception handlers translate domain errors to structured JSON so clients
always receive a consistent { success, error_code, message } envelope.
The global handler catches any unhandled AppError subclass so new
exception types added to core/exceptions.py are automatically covered.
"""
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import admin, audit, auth, catalog, finance, inventory, purchases, reports, sales
from app.api.v1 import public as public_api
from app.core.config import settings
from app.core.exceptions import AppError
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.body_limit_middleware import BodyLimitMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("startup", app=settings.APP_NAME, env=settings.APP_ENV)
    yield
    logger.info("shutdown", app=settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit middleware — logs every POST/PATCH/PUT/DELETE to audit.activity_log.
# Registered AFTER CORS so the audit captures the actual HTTP status.
app.add_middleware(AuditMiddleware)
app.add_middleware(BodyLimitMiddleware, max_body_bytes=settings.MAX_REQUEST_BODY_BYTES)

uploads_path = Path(settings.UPLOAD_LOCAL_PATH).expanduser().resolve()
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    correlation_id = str(uuid.uuid4())
    logger.warning(
        "app_error",
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "correlation_id": correlation_id,
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = str(uuid.uuid4())
    logger.exception(
        "unhandled_error",
        path=request.url.path,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "correlation_id": correlation_id,
        },
    )

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health_check() -> JSONResponse:
    checks = {
        "database": _check_database(),
        "uploads": _check_uploads(),
    }
    is_healthy = all(check["status"] in {"ok", "skipped"} for check in checks.values())
    status_code = 200 if is_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if is_healthy else "error",
            "app": settings.APP_NAME,
            "env": settings.APP_ENV,
            "checks": checks,
        },
    )


@app.get("/health/db", tags=["health"])
def db_health_check() -> JSONResponse:
    """Verifies the database engine can open a connection."""
    result = _check_database()
    return JSONResponse(
        status_code=200 if result["status"] == "ok" else 503,
        content=result,
    )


@app.get("/health/uploads", tags=["health"])
def uploads_health_check() -> JSONResponse:
    """Verifies local image upload storage is writable."""
    result = _check_uploads()
    status_code = 200 if result["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=result)


def _check_database() -> dict[str, Any]:
    from sqlalchemy import text
    from app.db.session import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:  # noqa: BLE001
        logger.error("health_database_failed", error=str(exc))
        return {"status": "error", "database": "unreachable", "detail": str(exc)}


def _check_uploads() -> dict[str, Any]:
    try:
        uploads_path.mkdir(parents=True, exist_ok=True)
        probe = uploads_path / ".healthcheck"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"status": "ok", "uploads": "writable", "path": str(uploads_path)}
    except Exception as exc:  # noqa: BLE001
        logger.error("health_uploads_failed", error=str(exc))
        return {"status": "error", "uploads": "unwritable", "detail": str(exc)}

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(catalog.router, prefix=settings.API_V1_PREFIX)
app.include_router(inventory.router, prefix=settings.API_V1_PREFIX)
app.include_router(purchases.router, prefix=settings.API_V1_PREFIX)
app.include_router(sales.router, prefix=settings.API_V1_PREFIX)
app.include_router(finance.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit.router, prefix=settings.API_V1_PREFIX)
app.include_router(public_api.router, prefix=settings.API_V1_PREFIX)
