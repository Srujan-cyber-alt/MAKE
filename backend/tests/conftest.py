"""Combined test conftest.

Provides:
    - ffmpeg/imageio_ffmpeg in PATH (autouse, per-test) for tests that shell
      out to ffmpeg directly.
    - A fresh, clean test database (reset at session start) so tests are
      isolated from committed/polluted DB state.
    - ``client`` (TestClient for FastAPI), ``get_auth_headers``, ``create_project``
      and ``upload_asset`` (used by test_api.py, test_studio.py, the phase tests,
      etc.).

The helper functions accept an optional ``_client`` keyword (defaulting to the
module-level ``client``) passed LAST so that the primary, commonly-positional
arguments (``email``/``password``, ``headers``/``name``, ``headers``/``project_id``)
line up with how the tests call them.
"""

from __future__ import annotations

import io
import os
import shutil
from typing import Any, Dict, Optional

# Configure a deterministic test environment BEFORE importing the application,
# so that settings read these values (env vars win over .env) and the app's
# engine points at an isolated test database that we reset per session.
os.environ["APP_ENV"] = "test"
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/1"
os.environ["STORAGE_TYPE"] = "local"
os.environ["STORAGE_LOCAL_PATH"] = "/tmp/makeai_test_storage"
os.environ["RATE_LIMIT_DEFAULT"] = "10000/minute"
os.environ["RATE_LIMIT_GENERATION"] = "10000/hour"
os.environ["DEFAULT_VIDEO_PROVIDER"] = "test"

import pytest  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.providers.base import ProviderRegistry  # noqa: E402
from app.providers.local_provider import LocalProvider  # noqa: E402
from app.providers.registry import set_provider_registry  # noqa: E402
from app.providers.test_provider import TestVideoProvider  # noqa: E402


def _resolve_ffmpeg() -> Optional[str]:
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


@pytest.fixture(autouse=True)
def _ensure_ffmpeg_in_path(monkeypatch, tmp_path):
    ffmpeg = _resolve_ffmpeg()
    if ffmpeg:
        if ffmpeg != "ffmpeg" or shutil.which("ffmpeg") is None:
            bin_dir = tmp_path / "_bin"
            bin_dir.mkdir(exist_ok=True)
            try:
                os.symlink(ffmpeg, str(bin_dir / "ffmpeg"))
            except Exception:
                pass
            try:
                os.symlink(ffmpeg, str(bin_dir / "ffprobe"))
            except Exception:
                pass
            env_path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
            monkeypatch.setenv("PATH", env_path)
    yield


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db():
    """Reset the test database at session start for isolation."""
    import asyncio

    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())
    yield


# Rebuild a clean provider registry for tests (ensures ``test-provider`` is
# present regardless of make_model checkpoint availability).
_test_registry = ProviderRegistry()
_test_registry.register(LocalProvider())
_test_registry.register(TestVideoProvider())
set_provider_registry(_test_registry)


def _get_client():
    from fastapi.testclient import TestClient

    return TestClient(app)


try:
    client = _get_client()
except Exception:
    client = None


def _resolve_client(_client=None):
    c = _client or client
    if c is None:
        raise RuntimeError("TestClient not initialised")
    return c


def get_auth_headers(
    email: str = "test@example.com",
    password: str = "testpass123",
    _client=None,
) -> Dict[str, str]:
    c = _resolve_client(_client)
    # Register (tolerate already-registered) then log in.
    c.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email},
    )
    r = c.post("/api/v1/auth/token", data={"username": email, "password": password})
    if r.status_code != 200:
        raise RuntimeError(f"login failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    token = data.get("access_token") or data.get("token") or data.get("accessToken")
    if not token:
        raise RuntimeError(f"no token in response: {data}")
    return {"Authorization": f"Bearer {token}"}


def create_project(
    headers: Optional[Dict[str, str]] = None,
    name: str = "Test Project",
    _client=None,
) -> Dict[str, Any]:
    c = _resolve_client(_client)
    r = c.post(
        "/api/v1/projects",
        json={"name": name, "description": f"Auto-created {name}"},
        headers=headers or {},
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"create project failed: {r.status_code} {r.text[:200]}")
    return r.json()


def upload_asset(
    headers: Optional[Dict[str, str]] = None,
    project_id: str = "",
    name: str = "test.mp4",
    data: bytes = b"fake video content",
    content_type: str = "video/mp4",
    _client=None,
) -> Dict[str, Any]:
    c = _resolve_client(_client)
    r = c.post(
        "/api/v1/assets/upload",
        files={"file": (name, io.BytesIO(data), content_type)},
        data={"project_id": project_id, "asset_type": "video"},
        headers=headers or {},
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"upload asset failed: {r.status_code} {r.text[:200]}")
    return r.json()


@pytest.fixture(scope="session")
def client_session():
    return client
