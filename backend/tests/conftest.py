"""Combined test conftest.

Provides:
    - ffmpeg in PATH (for tests that shell out to ffmpeg directly)
    - client (TestClient for FastAPI), get_auth_headers, create_project,
      upload_asset (used by test_api.py, test_studio.py, etc.)
"""

from __future__ import annotations

import io
import os
import shutil
from typing import Any, Dict, Optional

os.environ.setdefault("TESTING", "true")

import pytest


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
        env_path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        monkeypatch.setenv("PATH", env_path)
    yield


@pytest.fixture(autouse=True)
async def _reset_db():
    from app.core.database import engine
    from app.models.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


# ---- FastAPI test helpers (used by test_api.py, test_studio.py, etc.) ----

def _get_client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


try:
    client = _get_client()
except Exception:
    client = None


def get_auth_headers(email: str = "test@example.com", password: str = "testpass123", *, _client=None) -> Dict[str, str]:
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


def create_project(headers: Optional[Dict[str, str]] = None, name: str = "Test Project", *, _client=None) -> Dict[str, Any]:
    c = _client or client
    if c is None:
        raise RuntimeError("TestClient not initialised")
    r = c.post(
        "/api/v1/projects",
        json={"name": name, "description": f"Auto-created {name}"},
        headers=headers or {},
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"create project failed: {r.status_code} {r.text[:200]}")
    return r.json()


def upload_asset(headers: Optional[Dict[str, str]] = None, project_id: str = "", name: str = "asset.png", data: bytes = b"\x89PNG", *, _client=None) -> Dict[str, Any]:
    c = _client or client
    if c is None:
        raise RuntimeError("TestClient not initialised")
    r = c.post(
        "/api/v1/assets/upload",
        data={"project_id": project_id},
        files={"file": (name, io.BytesIO(data), "image/png")},
        headers=headers or {},
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"upload asset failed: {r.status_code} {r.text[:200]}")
    return r.json()


@pytest.fixture(scope="session")
def client_session():
    return _get_client()
