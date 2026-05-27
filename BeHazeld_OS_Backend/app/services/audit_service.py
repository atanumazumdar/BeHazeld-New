"""
AuditService — structured activity logging.

Two usage modes
---------------
1. **Within a service transaction** (flush, no commit):
   Call `log_mutation()` inside the owning service's try block.
   The audit row participates in the same atomic transaction — if the
   service rolls back, the audit row is rolled back too.

   Example (inside SalesService.create_sale, before db.commit()):
       if self._audit_svc is not None:
           self._audit_svc.log_mutation(
               method="POST", endpoint="/api/v1/sales/bills",
               tenant_id=tenant_id, user_id=performed_by_user_id,
               payload=str(req), status_code=201,
           )

2. **HTTP middleware** (separate session, independent commit):
   AuditMiddleware creates its own AuditService with a dedicated session
   so that audit writes never block or fail the primary request.

Payload truncation
------------------
request_payload is capped at _PAYLOAD_MAX chars. Binary/file payloads
are replaced with a placeholder string.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog, _PAYLOAD_MAX


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log_mutation(
        self,
        *,
        method: str,
        endpoint: str,
        response_status: int,
        tenant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        payload: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """
        Write one AuditLog row.  Flushes but does NOT commit so this can
        participate in the caller's transaction (or stand alone when called
        from middleware with its own session).
        """
        truncated: str | None = None
        if payload is not None:
            truncated = payload[:_PAYLOAD_MAX] if len(payload) > _PAYLOAD_MAX else payload

        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            method=method.upper(),
            endpoint=endpoint,
            request_payload=truncated,
            response_status=response_status,
            ip_address=ip_address,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def log_and_commit(
        self,
        *,
        method: str,
        endpoint: str,
        response_status: int,
        tenant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        payload: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """
        Write one AuditLog row and immediately commit.  Used by the HTTP
        middleware which has its own isolated session.
        """
        try:
            self.log_mutation(
                method=method,
                endpoint=endpoint,
                response_status=response_status,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=payload,
                ip_address=ip_address,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            # Audit failures are non-fatal — swallow and continue
