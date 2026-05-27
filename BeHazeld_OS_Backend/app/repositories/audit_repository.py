"""
AuditRepository — read-only access to audit.activity_log.

Rules
-----
* Every query is tenant-scoped (tenant_id first arg).
* All filtering is done in SQL — no Python-side loops over full result sets.
* The table is append-only; this repository never writes.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_logs(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: Optional[uuid.UUID] = None,
        endpoint_search: Optional[str] = None,
        method: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        """
        Return audit log rows for a tenant, newest-first.

        Filters
        -------
        user_id        : exact match on performing user
        endpoint_search: case-insensitive substring match on endpoint path
        method         : exact match on HTTP method (POST, DELETE, …)
        """
        q = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if user_id is not None:
            q = q.where(AuditLog.user_id == user_id)
        if endpoint_search:
            q = q.where(AuditLog.endpoint.ilike(f"%{endpoint_search}%"))
        if method:
            q = q.where(AuditLog.method == method.upper())

        q = q.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(q))
