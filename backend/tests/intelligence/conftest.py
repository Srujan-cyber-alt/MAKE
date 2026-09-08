"""Test bootstrap for MAKE Intelligence Core tests.

Provides an isolated SQLite database per test session and helpers to
reset/recreate state so tests are deterministic and independent.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from typing import AsyncIterator, Optional

import pytest

from app.intelligence.config import intelligence_settings
from app.intelligence.database import (
    configure_engine, reset_engine_storage, init_db,
    get_session_factory,
)
from app.intelligence.jobs.job_manager import JobManager


@pytest.fixture(scope="session")
def _intelligence_test_env():
    """Session-scoped temp directory and database for all intelligence tests."""
    tmp_dir = tempfile.mkdtemp(prefix="make-intel-test-")
    db_path = os.path.join(tmp_dir, "intelligence.db")
    storage_path = os.path.join(tmp_dir, "intel_storage")
    os.makedirs(storage_path, exist_ok=True)

    reset_engine_storage()
    configure_engine(
        database_url=f"sqlite+aiosqlite:///{db_path}",
        storage_path=storage_path,
    )

    yield {"db_path": db_path, "storage_path": storage_path, "tmp_dir": tmp_dir}

    reset_engine_storage()
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def _init_intelligence_db(_intelligence_test_env):
    """Create all tables once at session start."""
    asyncio.get_event_loop().run_until_complete(init_db())
    yield


@pytest.fixture
async def intel_db():
    """Per-test: yield the session factory and clean tables between tests."""
    factory = get_session_factory()

    # Clean all tables before each test for isolation
    async with factory() as session:
        from app.intelligence.models import (
            IntelligenceJob, JobCheckpointOrm, JobLogOrm,
            MemoryEntityOrm, MemoryRelationOrm,
            GraphNodeOrm, GraphEdgeOrm,
            DecisionRecordOrm, ArtifactRecordOrm, PersonalContextOrm,
        )
        for model in [
            ArtifactRecordOrm, JobCheckpointOrm, JobLogOrm,
            DecisionRecordOrm, PersonalContextOrm,
            MemoryRelationOrm, MemoryEntityOrm,
            GraphEdgeOrm, GraphNodeOrm, IntelligenceJob,
        ]:
            await session.execute(__import__("sqlalchemy").delete(model))
        await session.commit()

    yield factory

    # Clean up after test too
    async with factory() as session:
        from app.intelligence.models import (
            IntelligenceJob, JobCheckpointOrm, JobLogOrm,
            MemoryEntityOrm, MemoryRelationOrm,
            GraphNodeOrm, GraphEdgeOrm,
            DecisionRecordOrm, ArtifactRecordOrm, PersonalContextOrm,
        )
        for model in [
            ArtifactRecordOrm, JobCheckpointOrm, JobLogOrm,
            DecisionRecordOrm, PersonalContextOrm,
            MemoryRelationOrm, MemoryEntityOrm,
            GraphEdgeOrm, GraphNodeOrm, IntelligenceJob,
        ]:
            await session.execute(__import__("sqlalchemy").delete(model))
        await session.commit()

    # Clean storage dirs
    for subdir in ("checkpoints", "artifacts", "logs"):
        d = os.path.join(intelligence_settings.storage_path, subdir)
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def job_manager(intel_db) -> JobManager:
    """Fresh JobManager for each test."""
    from app.intelligence.core.tool_router import ToolRouter
    return JobManager(tool_router=ToolRouter())


@pytest.fixture
async def jm(job_manager: JobManager, intel_db):
    """Convenience alias for job_manager with DB initialized."""
    return job_manager
