import pytest
from datetime import timedelta


def test_hash_and_verify_password() -> None:
    from app.core.security import hash_password, verify_password
    hashed = hash_password("mysecret")
    assert hashed != "mysecret"
    assert verify_password("mysecret", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_access_token() -> None:
    from app.core.security import create_access_token, decode_token
    data = {"sub": "user-123", "tenant_id": "tenant-abc", "permissions": ["catalog.view"]}
    token = create_access_token(data)
    assert isinstance(token, str)
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["tenant_id"] == "tenant-abc"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "jti" in payload


def test_create_and_decode_refresh_token() -> None:
    from app.core.security import create_refresh_token, decode_token
    token = create_refresh_token({"sub": "user-123", "tenant_id": "t-1"})
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert payload["sub"] == "user-123"


def test_decode_invalid_token_raises() -> None:
    from app.core.security import decode_token
    from app.core.exceptions import InvalidCredentialsError
    with pytest.raises(InvalidCredentialsError):
        decode_token("not.a.valid.token")


def test_decode_expired_token_raises() -> None:
    from app.core.security import create_access_token, decode_token
    from app.core.exceptions import InvalidCredentialsError
    token = create_access_token({"sub": "u"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(InvalidCredentialsError):
        decode_token(token)


def test_exception_hierarchy() -> None:
    from app.core.exceptions import (
        AppError, NotFoundError, InvalidCredentialsError,
        PermissionDeniedError, ConflictError, TenantNotFoundError,
        StockNotAvailableError,
    )
    assert issubclass(NotFoundError, AppError)
    assert issubclass(InvalidCredentialsError, AppError)
    assert issubclass(PermissionDeniedError, AppError)
    assert issubclass(ConflictError, AppError)
    assert issubclass(TenantNotFoundError, NotFoundError)
    assert issubclass(StockNotAvailableError, AppError)
    err = NotFoundError("Widget 42 not found")
    assert err.status_code == 404
    assert err.error_code == "NOT_FOUND"
    assert "Widget 42" in err.message
