def test_user_model_has_required_columns() -> None:
    from app.models.identity import User
    cols = {c.key for c in User.__table__.columns}
    assert {"id", "email", "username", "hashed_password", "is_active",
            "is_superuser", "tenant_id", "created_at", "updated_at"}.issubset(cols)


def test_tenant_model_has_required_columns() -> None:
    from app.models.tenant import Tenant
    cols = {c.key for c in Tenant.__table__.columns}
    assert {"id", "name", "slug", "is_active", "created_at", "updated_at"}.issubset(cols)


def test_company_model_has_required_columns() -> None:
    from app.models.tenant import Company
    cols = {c.key for c in Company.__table__.columns}
    assert {"id", "tenant_id", "name", "is_active", "created_at", "updated_at"}.issubset(cols)


def test_location_model_has_required_columns() -> None:
    from app.models.tenant import Location
    cols = {c.key for c in Location.__table__.columns}
    assert {"id", "tenant_id", "company_id", "name", "is_active"}.issubset(cols)


def test_user_relationships_defined() -> None:
    from app.models.identity import User
    assert hasattr(User, "tenant")
    assert hasattr(User, "roles")
    assert hasattr(User, "refresh_tokens")


def test_role_model_has_required_columns() -> None:
    from app.models.identity import Role
    cols = {c.key for c in Role.__table__.columns}
    assert {"id", "name", "tenant_id"}.issubset(cols)


def test_permission_model_has_required_columns() -> None:
    from app.models.identity import Permission
    cols = {c.key for c in Permission.__table__.columns}
    assert {"id", "name", "code"}.issubset(cols)


def test_refresh_token_is_valid_property() -> None:
    from app.models.identity import RefreshToken
    from datetime import datetime, timezone, timedelta
    rt = RefreshToken()
    rt.revoked_at = None
    rt.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    assert rt.is_valid is True
    rt.revoked_at = datetime.now(timezone.utc)
    assert rt.is_valid is False


def test_refresh_token_expired_is_invalid() -> None:
    from app.models.identity import RefreshToken
    from datetime import datetime, timezone, timedelta
    rt = RefreshToken()
    rt.revoked_at = None
    rt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert rt.is_valid is False


def test_models_init_exports_all() -> None:
    import app.models as m
    for name in ("Tenant", "Company", "Location", "User", "Role", "Permission", "RefreshToken"):
        assert hasattr(m, name), f"app.models missing {name}"


def test_user_table_uses_identity_schema() -> None:
    from app.models.identity import User
    assert User.__table__.schema == "identity"


def test_tenant_table_uses_tenant_schema() -> None:
    from app.models.tenant import Tenant
    assert Tenant.__table__.schema == "tenant"
