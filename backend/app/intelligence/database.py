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

INTELLIGENCE_METADATA = MetaData(schema="intelligence")

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _resolve_url() -> str:
    url = intelligence_settings.database_url
    if url.startswith("sqlite"):
        os.makedirs(os.path.dirname(url.replace("sqlite+aiosqlite:///", "")), exist_ok=True)
    return url


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(_resolve_url(), echo=False, future=True)
    return _engine


def configure_engine(database_url: Optional[str] = None, storage_path: Optional[str] = None) -> None:
    """Reconfigure and dispose any existing engine. Used at startup and in tests."""
    global _engine, _session_factory
    if _engine is not None:
        import asyncio

        try:
            asyncio.get_event_loop().create_task(_engine.dispose())
        except RuntimeError:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_engine.dispose())
            except Exception:
                pass
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
