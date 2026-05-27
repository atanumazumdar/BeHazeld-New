"""
Audit router — read-only activity log for the admin panel.

Permission matrix
-----------------
GET /audit/logs : audit.logs.view

All queries are tenant-scoped and strictly read-only.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, require_permission
from app.db.session import get_db
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    user_id: Optional[uuid.UUID] = None,
    endpoint: Optional[str] = Query(default=None, max_length=200),
    method: Optional[str] = Query(default=None, max_length=10),
    ctx: TenantContext = Depends(require_permission("audit.logs.view")),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    """
    Return audit log entries for this tenant.

    Query params
    ------------
    skip           : pagination offset
    limit          : page size (max 200)
    user_id        : filter by performing user UUID
    endpoint       : substring search on endpoint path (e.g. "/sales")
    method         : exact HTTP method filter (POST, DELETE, etc.)
    """
    rows = AuditRepository(db).list_logs(
        ctx.tenant_id,
        user_id=user_id,
        endpoint_search=endpoint,
        method=method,
        skip=skip,
        limit=limit,
    )
    return rows  # type: ignore[return-value]
