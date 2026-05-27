"""
main.py — FastAPI application factory.

Production topology (Windows Server + IIS):
  Internet → IIS (HTTPS 443, ARR reverse proxy)
           → uvicorn on 127.0.0.1:8000 (this app)
           → MS SQL Server on localhost:1433

ProxyHeadersMiddleware trusts IIS as the single upstream proxy so that
request.client.host and request.url.scheme reflect the real client,
not 127.0.0.1 / http.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.database import db_ping
from app.routers import checkout, customers, collections, products
from app.routers.admin import auth as admin_auth
from app.routers.admin import collections as admin_collections
from app.routers.admin import products as admin_products

# ── CORS origins ──────────────────────────────────────────────────────
# Comma-separated list from env; falls back to localhost for local dev.
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="BeHAZEL'd API",
    description="Dynamic luxury couture store — products, collections, orders.",
    version="2.0.0",
    # Disable docs in production (set ENVIRONMENT=production to hide)
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs",
    redoc_url=None if os.getenv("ENVIRONMENT") == "production" else "/redoc",
)

# Trust IIS as the single reverse proxy sitting in front of uvicorn.
# This makes request.client.host and request.url.scheme accurate.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["127.0.0.1", "::1"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Public endpoints ──────────────────────────────────────────────────
app.include_router(collections.router)   # GET /collections/  and  /collections/{slug}
app.include_router(products.router)      # GET /products/      and  /products/{slug}
app.include_router(checkout.router)      # POST /checkout/
app.include_router(customers.router)

# ── Admin endpoints (all require Bearer JWT) ──────────────────────────
app.include_router(admin_auth.router)           # POST /admin/auth/token
app.include_router(admin_collections.router)    # CRUD /admin/collections/
app.include_router(admin_products.router)       # CRUD /admin/products/ + variants + images


# ── Health endpoint ───────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
def health_check():
    """
    Liveness + DB connectivity check.
    IIS ARR can poll this to detect backend failures.
    Returns 200 when healthy, 503 when the DB is unreachable.
    """
    from fastapi.responses import JSONResponse

    db_ok = db_ping()
    payload = {
        "status": "ok" if db_ok else "degraded",
        "version": "2.0.0",
        "database": "connected" if db_ok else "unreachable",
    }
    return JSONResponse(
        content=payload,
        status_code=200 if db_ok else 503,
    )
