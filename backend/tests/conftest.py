"""Combined test conftest.

Provides:
    - ffmpeg in PATH (for tests that shell out to ffmpeg directly)
    - test database setup with dependency override
    - client (TestClient for FastAPI), get_auth_headers, create_project,
      upload_asset (used by test_api.py, test_studio.py, etc.)
"""

from __future__ import annotations

import io
import os
import shutil
from typing import Any, Dict, Optional

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/1"
os.environ["RATE_LIMIT_DEFAULT"] = "1000/minute"
os.environ["RATE_LIMIT_GENERATION"] = "1000/hour"
os.environ["APP_ENV"] = "test"
os.environ["TESTING"] = "true"

from app.main import app
from app.core.database import get_db, Base
from app.providers.test_provider import TestVideoProvider
from app.providers.local_provider import LocalProvider
from app.providers.base import ProviderRegistry
from app.providers.registry import set_provider_registry

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    db_path = os.path.join(os.path.dirname(__file__), "..", "test.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(_setup())
    yield


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db

registry = ProviderRegistry()
registry.register(LocalProvider())
registry.register(TestVideoProvider())
set_provider_registry(registry)

client = TestClient(app)


def _resolve_ffmpeg() -> Optional[str]:
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


@pytest.fixture(autouse=True)
def _ensure_ffmpeg_in_path(monkeypatch, tmp_path):
    ffmpeg = _resolve_ffmpeg()
    if ffmpeg and ffmpeg != "ffmpeg":
        bin_dir = tmp_path / "_bin"
        bin_dir.mkdir(exist_ok=True)
        link = bin_dir / "ffmpeg"
        try:
            os.symlink(ffmpeg, str(link))
        except Exception:
            pass
        try:
            os.symlink(ffmpeg, str(bin_dir / "ffprobe"))
        except Exception:
            pass
        env_path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        monkeypatch.setenv("PATH", env_path)
    yield


def get_auth_headers(email: str, password: str, _client=None) -> Dict[str, str]:
    c = _client or client
    if c is None:
        raise RuntimeError("TestClient not initialised")
    r = c.post("/api/v1/auth/register", json={"email": email, "password": password, "name": email})
    if r.status_code not in (200, 201, 400):
        r.raise_for_status()
    r = c.post("/api/v1/auth/token", data={"username": email, "password": password})
    if r.status_code != 200:
        raise RuntimeError(f"login failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    token = data.get("access_token") or data.get("token") or data.get("accessToken")
    if not token:
        raise RuntimeError(f"no token in response: {data}")
    return {"Authorization": f"Bearer {token}"}


def create_project(headers: Dict[str, str], name: str = "Test Project", _client=None) -> Dict[str, Any]:
    c = _client or client
    if c is None:
        raise RuntimeError("TestClient not initialised")
    r = c.post(
        "/api/v1/projects",
        json={"name": name, "description": f"Auto-created {name}"},
        headers=headers,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"create project failed: {r.status_code} {r.text[:200]}")
    return r.json()


def upload_asset(headers: Dict[str, str], project_id: str, name: str = "test.mp4", data: bytes = b"fake video content", _client=None) -> Dict[str, Any]:
    c = _client or client
    if c is None:
        raise RuntimeError("TestClient not initialised")
    r = c.post(
        "/api/v1/assets/upload",
        files={"file": (name, io.BytesIO(data), "video/mp4")},
        data={"project_id": project_id, "asset_type": "video"},
        headers=headers,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"upload asset failed: {r.status_code} {r.text[:200]}")
    return r.json()


@pytest.fixture(scope="session")
def client_session():
    return client
