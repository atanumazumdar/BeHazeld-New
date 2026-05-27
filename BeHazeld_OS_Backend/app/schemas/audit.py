"""
Audit domain Pydantic schemas.

AuditLogResponse serialises one AuditLog ORM row for the API.
AuditLogFilter carries validated query params for the list endpoint.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    user_id: uuid.UUID | None
    method: str
    endpoint: str
    response_status: int
    ip_address: str | None
    request_payload: str | None
    created_at: datetime
