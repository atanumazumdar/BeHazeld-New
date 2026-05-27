from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _database_url() -> str:
    """Normalize provider URLs into SQLAlchemy's PostgreSQL psycopg2 dialect."""
    if settings.DATABASE_URL.startswith("postgres://"):
        return settings.DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if settings.DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
        return settings.DATABASE_URL
    raise ValueError("DATABASE_URL must use postgresql:// or postgresql+psycopg2://")


engine = create_engine(
    _database_url(),
    echo=settings.APP_ENV == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
