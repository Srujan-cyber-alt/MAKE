import pytest
import asyncio
import os
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

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop_policy().get_event_loop().run_until_complete(_setup()) if False else None
    import asyncio as _aio
    _aio.run(_setup())
    yield


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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
from app.providers.registry import set_provider_registry
set_provider_registry(registry)

client = TestClient(app)


def get_auth_headers(email: str, password: str) -> dict:
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = client.post("/api/v1/auth/token", data={"username": email, "password": password})
    assert response.status_code == 200, f"Auth failed: {response.status_code} {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_project(headers: dict, name: str = "Test Project") -> dict:
    response = client.post("/api/v1/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201, f"Project create failed: {response.status_code} {response.text}"
    return response.json()


def upload_asset(headers: dict, project_id: str, filename: str = "test.mp4") -> dict:
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": (filename, b"fake video content", "video/mp4")},
        data={"project_id": project_id, "asset_type": "video"},
        headers=headers,
    )
    assert response.status_code == 201, f"Upload failed: {response.status_code} {response.text}"
    return response.json()
