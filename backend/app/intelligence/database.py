"""Async SQLAlchemy database layer for the MAKE Intelligence Core.

Uses an independent ``MetaData`` so the intelligence core schema never
collides with the existing Video/Image subsystem models.
"""

from __future__ import annotations

import os
from typing import Optional, AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.intelligence.config import intelligence_settings

INTELLIGENCE_METADATA = MetaData()

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _resolve_url() -> str:
    url = intelligence_settings.database_url
    if url.startswith("sqlite"):
        db_path = url.replace("sqlite+aiosqlite:///", "")
        if ":" in db_path and db_path[1] == ":":
            pass  # Windows drive letter or special path
        elif "/" not in db_path and not db_path.startswith(":"):
            db_path = os.path.join(os.getcwd(), db_path)
            intelligence_settings._db_url = f"sqlite+aiosqlite:///{db_path}"
            url = intelligence_settings._db_url
        if not db_path.startswith(":"):
            parent = os.path.dirname(db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
    return url


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(_resolve_url(), echo=False, future=True)
    return _engine


def configure_engine(database_url: Optional[str] = None, storage_path: Optional[str] = None) -> None:
    """Reconfigure and dispose any existing engine.

    Used at startup and in tests to switch databases cleanly. Safe to
    call multiple times; the asyncio dispose is done synchronously via
    the engine's synchronous dispose (no event loop required).
    """
    global _engine, _session_factory
    if _engine is not None:
        try:
            _engine.sync_engine.dispose()
        except Exception:
            pass
    _engine = None
    _session_factory = None
    intelligence_settings.configure(database_url, storage_path)
    if intelligence_settings.storage_path:
        intelligence_settings.ensure_dirs()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        _session_factory = factory
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all intelligence-core tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(INTELLIGENCE_METADATA.create_all)


async def drop_db() -> None:
    """Drop all intelligence-core tables (used by tests)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(INTELLIGENCE_METADATA.drop_all)


def reset_engine_storage() -> None:
    """Hard reset for testing: dispose engine and clear session factory."""
    global _engine, _session_factory
    if _engine is not None:
        try:
            _engine.sync_engine.dispose()
        except Exception:
            pass
    _engine = None
    _session_factory = None
