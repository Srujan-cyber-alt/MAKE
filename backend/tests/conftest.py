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
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

# Use a per-session fresh sqlite DB to avoid state pollution across test runs.
import uuid
_TEST_DB = _BACKEND_DIR / f"make_test_{uuid.uuid4().hex[:8]}.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}"

# Disable / raise rate limits for tests so creating many users in a single run works.
os.environ["TESTING"] = "true"


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
        # also symlink ffprobe (imageio's ffmpeg binary supports ffprobe-like args)
        try:
            os.symlink(ffmpeg, str(bin_dir / "ffprobe"))
        except Exception:
            pass
        env_path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        monkeypatch.setenv("PATH", env_path)
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


@pytest.fixture(autouse=True, scope="session")
def _ensure_db_tables():
    try:
        from app.core.database import init_db, engine
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(init_db())
    except Exception:
        pass
    yield


def get_auth_headers(test_client=None, email: str = "test@example.com", password: str = "testpass123") -> Dict[str, str]:
    c = client if test_client is None else test_client
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


def create_project(headers: Optional[Dict[str, str]] = None, name: str = "Test Project", test_client=None) -> Dict[str, Any]:
    c = client if test_client is None else test_client
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


def upload_asset(headers: Optional[Dict[str, str]] = None, project_id: str = "", name: str = "asset.png", data: bytes = b"\x89PNG", test_client=None) -> Dict[str, Any]:
    c = client if test_client is None else test_client
    if c is None:
        raise RuntimeError("TestClient not initialised")
    r = c.post(
        "/api/v1/assets/upload",
        files={"file": (name, io.BytesIO(data), "image/png")},
        data={"project_id": project_id, "asset_type": "image"},
        headers=headers or {},
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"upload asset failed: {r.status_code} {r.text[:200]}")
    return r.json()


@pytest.fixture(scope="session")
def client_session():
    return _get_client()
