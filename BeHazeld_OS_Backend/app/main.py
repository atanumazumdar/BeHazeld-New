"""
Application entry point.

Exception handlers translate domain errors to structured JSON so clients
always receive a consistent { success, error_code, message } envelope.
The global handler catches any unhandled AppError subclass so new
exception types added to core/exceptions.py are automatically covered.
"""
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import admin, audit, auth, catalog, finance, inventory, purchases, reports, sales
from app.api.v1 import public as public_api
from app.core.config import settings
from app.core.exceptions import AppError
from app.middleware.audit_middleware import AuditMiddleware

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
def health_check() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@app.get("/health/db", tags=["health"])
def db_health_check() -> dict:
    """Verifies the database engine can open a connection."""
    from sqlalchemy import text
    from app.db.session import engine
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:  # noqa: BLE001
        logger.error("db_health_check_failed", error=str(exc))
        return JSONResponse(  # type: ignore[return-value]
            status_code=503,
            content={"status": "error", "database": "unreachable", "detail": str(exc)},
        )

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
