from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_NAME: str = "BeHazeld E-Commerce OS"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    UPLOAD_STORAGE_PROVIDER: str = "local"
    UPLOAD_LOCAL_PATH: str = "./var/uploads"
    PUBLIC_BASE_URL: str = "http://127.0.0.1:8000"
    INVOICE_STORAGE_PATH: str = "./var/invoices"
    MAX_REQUEST_BODY_BYTES: int = 10 * 1024 * 1024
    # Stored as comma-separated string; use .ALLOWED_ORIGINS for the list
    ALLOWED_ORIGINS_RAW: str = "http://localhost:3000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS_RAW.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
