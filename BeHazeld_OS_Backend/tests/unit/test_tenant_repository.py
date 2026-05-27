"""Tenant repository tests — mock session, no live DB."""
import uuid
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


def test_get_by_id_returns_tenant(mock_db: MagicMock) -> None:
    from app.repositories.tenant_repository import TenantRepository
    from app.models.tenant import Tenant
    expected = MagicMock(spec=Tenant)
    mock_db.scalar.return_value = expected
    assert TenantRepository(mock_db).get_by_id(uuid.uuid4()) is expected


def test_get_by_id_raises_not_found(mock_db: MagicMock) -> None:
    from app.repositories.tenant_repository import TenantRepository
    from app.core.exceptions import NotFoundError
    mock_db.scalar.return_value = None
    with pytest.raises(NotFoundError):
        TenantRepository(mock_db).get_by_id(uuid.uuid4())


def test_get_by_slug_returns_none_when_missing(mock_db: MagicMock) -> None:
    from app.repositories.tenant_repository import TenantRepository
    mock_db.scalar.return_value = None
    assert TenantRepository(mock_db).get_by_slug("missing") is None


def test_create_raises_conflict_when_slug_taken(mock_db: MagicMock) -> None:
    from app.repositories.tenant_repository import TenantRepository
    from app.models.tenant import Tenant
    from app.core.exceptions import ConflictError
    mock_db.scalar.return_value = MagicMock(spec=Tenant)
    with pytest.raises(ConflictError):
        TenantRepository(mock_db).create(name="Dupe", slug="taken")


def test_create_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.tenant_repository import TenantRepository
    mock_db.scalar.return_value = None
    tenant = TenantRepository(mock_db).create(name="Acme Corp", slug="acme-corp")
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert tenant.name == "Acme Corp"
    assert tenant.slug == "acme-corp"
    assert tenant.is_active is True


def test_list_all_returns_list(mock_db: MagicMock) -> None:
    from app.repositories.tenant_repository import TenantRepository
    from app.models.tenant import Tenant
    tenants = [MagicMock(spec=Tenant) for _ in range(3)]
    mock_db.scalars.return_value = iter(tenants)
    result = TenantRepository(mock_db).list_all()
    assert len(result) == 3


def test_set_active_updates_flag(mock_db: MagicMock) -> None:
    from app.repositories.tenant_repository import TenantRepository
    from app.models.tenant import Tenant
    tenant = MagicMock(spec=Tenant)
    mock_db.scalar.return_value = tenant
    TenantRepository(mock_db).set_active(uuid.uuid4(), False)
    assert tenant.is_active is False
    mock_db.flush.assert_called_once()
