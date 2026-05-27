from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str
    correlation_id: str | None = None


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str = "OK"


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    size: int
    pages: int
