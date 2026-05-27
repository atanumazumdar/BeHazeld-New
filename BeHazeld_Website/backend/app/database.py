"""
database.py — SQLAlchemy engine & session factory.

Supports both SQLite (local dev) and MS SQL Server (production on Windows/IIS).
Switch via the DATABASE_URL environment variable — no code changes required.

SQLite  (dev):   sqlite:///./store.db
MSSQL (prod):   mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
"""

import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./store.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")
_is_mssql  = DATABASE_URL.startswith("mssql")

# ── Engine ────────────────────────────────────────────────────────────
if _is_sqlite:
    # SQLite: single-file, threading workaround required
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
else:
    # MS SQL Server (production): connection pool with health-check
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,     # drop stale connections before handing out
        pool_recycle=1800,      # recycle every 30 min (before SQL Server kills idle)
        pool_timeout=30,
        echo=False,
    )

# ── MSSQL-specific: enable fast_executemany for bulk inserts ─────────
if _is_mssql:
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
        if executemany:
            cursor.fast_executemany = True

# ── Session factory ───────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Health helper — called by /health endpoint ────────────────────────
def db_ping() -> bool:
    """Return True if the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
