from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_phone_number(value: str | None) -> str | None:
    if value is None or value == "":
        return value

    allowed = set("0123456789 +-()")
    if any(ch not in allowed for ch in value):
        raise ValueError("phone may contain only digits, spaces, +, -, and parentheses")

    digits = "".join(ch for ch in value if ch.isdigit())
    if not 7 <= len(digits) <= 15:
        raise ValueError("phone must contain between 7 and 15 digits")

    return value


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
