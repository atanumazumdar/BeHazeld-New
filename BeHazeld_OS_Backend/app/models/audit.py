"""
Audit domain model — immutable activity log.

Design decisions
----------------
* tenant_id and user_id are nullable so unauthenticated (public) endpoint
  calls are still captured.
* request_payload is TEXT; the middleware truncates to 4000 chars to prevent
  giant payloads (file uploads, bulk imports) from bloating the log.
* created_at uses server_default="SYSDATETIME()" so SQL Server's clock governs
  the timestamp — no Python clock drift.
* AuditLog rows are NEVER updated or deleted.  The table is append-only.
"""
from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_SCHEMA = "audit"
_PAYLOAD_MAX = 4000   # chars; truncated before insert to keep rows small


class AuditLog(Base):
    """One row per HTTP mutation captured by AuditMiddleware."""

    __tablename__ = "activity_log"
    __table_args__ = (
        Index("ix_audit_log_tenant",  "tenant_id"),
        Index("ix_audit_log_created", "created_at"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    request_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[str] = mapped_column(
        DateTime, nullable=False, server_default="SYSDATETIME()"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog {self.method} {self.endpoint!r} → {self.response_status}>"
        )
