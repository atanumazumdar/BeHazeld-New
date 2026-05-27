"""
Identity repository tests.
All tests use a MagicMock session — no live database required.
The repository is responsible ONLY for data access; business rules live in services.
"""
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, call

import pytest


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


# ── get_by_id ────────────────────────────────────────────────────────────────

def test_get_by_id_returns_user(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    from app.models.identity import User
    expected = MagicMock(spec=User)
    mock_db.scalar.return_value = expected
    assert UserRepository(mock_db).get_by_id(uuid.uuid4()) is expected


def test_get_by_id_raises_not_found_when_missing(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    from app.core.exceptions import NotFoundError
    mock_db.scalar.return_value = None
    with pytest.raises(NotFoundError):
        UserRepository(mock_db).get_by_id(uuid.uuid4())


# ── get_by_email ─────────────────────────────────────────────────────────────

def test_get_by_email_returns_user(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    from app.models.identity import User
    expected = MagicMock(spec=User)
    mock_db.scalar.return_value = expected
    assert UserRepository(mock_db).get_by_email("a@b.com") is expected


def test_get_by_email_returns_none_when_missing(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    mock_db.scalar.return_value = None
    assert UserRepository(mock_db).get_by_email("no@b.com") is None


# ── create ───────────────────────────────────────────────────────────────────

def test_create_user_raises_conflict_when_email_taken(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    from app.models.identity import User
    from app.core.exceptions import ConflictError
    mock_db.scalar.return_value = MagicMock(spec=User)  # email exists
    with pytest.raises(ConflictError):
        UserRepository(mock_db).create(
            email="taken@b.com", username="u", hashed_password="h", tenant_id=uuid.uuid4()
        )


def test_create_user_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    mock_db.scalar.return_value = None  # email not taken
    user = UserRepository(mock_db).create(
        email="new@b.com", username="newuser", hashed_password="hash", tenant_id=uuid.uuid4()
    )
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert user.email == "new@b.com"
    assert user.is_superuser is False


def test_create_superuser_sets_flag(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    mock_db.scalar.return_value = None
    user = UserRepository(mock_db).create(
        email="super@b.com", username="super", hashed_password="h",
        tenant_id=uuid.uuid4(), is_superuser=True,
    )
    assert user.is_superuser is True


# ── set_active ───────────────────────────────────────────────────────────────

def test_set_active_updates_flag_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    from app.models.identity import User
    user = MagicMock(spec=User)
    mock_db.scalar.return_value = user
    UserRepository(mock_db).set_active(uuid.uuid4(), False)
    assert user.is_active is False
    mock_db.flush.assert_called_once()


# ── count_active_superusers_in_tenant ────────────────────────────────────────

def test_count_active_superusers_returns_integer(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    mock_db.scalar.return_value = 2
    count = UserRepository(mock_db).count_active_superusers_in_tenant(uuid.uuid4())
    assert count == 2


def test_count_active_superusers_returns_zero_on_none(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    mock_db.scalar.return_value = None  # SQL COUNT returns NULL on empty set via some drivers
    count = UserRepository(mock_db).count_active_superusers_in_tenant(uuid.uuid4())
    assert count == 0


# ── refresh token management ─────────────────────────────────────────────────

def test_store_refresh_token_hashes_token(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    raw = "raw-token-value"
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    rt = UserRepository(mock_db).store_refresh_token(uuid.uuid4(), raw, expires)
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert rt.token_hash == hashlib.sha256(raw.encode()).hexdigest()
    assert rt.expires_at == expires


def test_get_refresh_token_by_raw_value(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    from app.models.identity import RefreshToken
    stored = MagicMock(spec=RefreshToken)
    mock_db.scalar.return_value = stored
    result = UserRepository(mock_db).get_refresh_token("raw-token")
    assert result is stored


def test_revoke_refresh_token_sets_revoked_at(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    from app.models.identity import RefreshToken
    rt = MagicMock(spec=RefreshToken)
    mock_db.scalar.return_value = rt
    UserRepository(mock_db).revoke_refresh_token("some-token")
    assert rt.revoked_at is not None
    mock_db.flush.assert_called_once()


def test_revoke_refresh_token_noop_when_not_found(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    mock_db.scalar.return_value = None
    UserRepository(mock_db).revoke_refresh_token("ghost-token")  # must not raise
    mock_db.flush.assert_not_called()


def test_revoke_all_refresh_tokens_executes_bulk_update(mock_db: MagicMock) -> None:
    from app.repositories.identity_repository import UserRepository
    mock_result = MagicMock()
    mock_result.rowcount = 3
    mock_db.execute.return_value = mock_result
    count = UserRepository(mock_db).revoke_all_refresh_tokens_for_user(uuid.uuid4())
    mock_db.execute.assert_called_once()
    mock_db.flush.assert_called_once()
    assert count == 3
