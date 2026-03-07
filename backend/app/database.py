"""
SAR Guardian — Database Engine & Session Management
Uses async SQLAlchemy for non-blocking DB operations.
Supports PostgreSQL (production) and SQLite (local development).
"""

import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

from app.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Build engine kwargs based on backend
_engine_kwargs: dict = {
    "echo": False,
}
if not _is_sqlite:
    # Connection pooling for PostgreSQL production workloads
    _engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })
    # Supabase / PgBouncer compatibility: disable prepared statement caching
    _engine_kwargs["connect_args"] = {"prepared_statement_cache_size": 0}

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# Enable WAL mode and foreign key enforcement for SQLite
if _is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory — each request gets its own session
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields a database session.
    Automatically commits on success, rolls back on error, and closes.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
