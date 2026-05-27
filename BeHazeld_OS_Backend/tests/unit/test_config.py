import importlib
import pytest


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    import app.core.config as cfg_module
    importlib.reload(cfg_module)
    from app.core.config import settings
    assert settings.APP_NAME == "BeHazeld E-Commerce OS"
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert settings.UPLOAD_STORAGE_PROVIDER == "local"
    assert settings.CLOUDINARY_CLOUD_NAME == ""


def test_settings_allowed_origins_parses_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")
    monkeypatch.setenv("JWT_SECRET_KEY", "secret")
    monkeypatch.setenv("ALLOWED_ORIGINS_RAW", "http://a.com,http://b.com")
    import app.core.config as cfg_module
    importlib.reload(cfg_module)
    from app.core.config import settings
    assert "http://a.com" in settings.ALLOWED_ORIGINS
    assert "http://b.com" in settings.ALLOWED_ORIGINS
