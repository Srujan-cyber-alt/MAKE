import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.core.database import get_db, Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def get_auth_headers(email: str, password: str) -> dict:
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
    })
    response = client.post("/api/v1/auth/token", data={
        "username": email,
        "password": password,
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestHealth:
    def test_health(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readiness(self):
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200


class TestAuth:
    def test_register(self):
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data

    def test_login(self):
        client.post("/api/v1/auth/register", json={
            "email": "login@example.com",
            "password": "testpass123",
        })
        response = client.post("/api/v1/auth/token", data={
            "username": "login@example.com",
            "password": "testpass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data


class TestProjects:
    def test_create_project(self):
        headers = get_auth_headers("proj@example.com", "testpass123")
        response = client.post("/api/v1/projects", json={
            "name": "Test Project",
            "description": "A test project",
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"

    def test_list_projects(self):
        headers = get_auth_headers("list@example.com", "testpass123")
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200

    def test_get_project_not_found(self):
        headers = get_auth_headers("np@example.com", "testpass123")
        response = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000", headers=headers)
        assert response.status_code == 404


class TestAssets:
    def test_upload_asset(self):
        headers = get_auth_headers("asset@example.com", "testpass123")
        project_resp = client.post("/api/v1/projects", json={"name": "Asset Project"}, headers=headers)
        project_id = project_resp.json()["id"]

        response = client.post(
            "/api/v1/assets/upload",
            data={"project_id": project_id, "asset_type": "reference"},
            files={"file": ("test.png", b"fake-image-data", "image/png")},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.png"

    def test_list_assets_empty(self):
        headers = get_auth_headers("la@example.com", "testpass123")
        project_resp = client.post("/api/v1/projects", json={"name": "List Asset Project"}, headers=headers)
        project_id = project_resp.json()["id"]
        response = client.get(f"/api/v1/assets/project/{project_id}", headers=headers)
        assert response.status_code == 200
        assert response.json() == []


class TestJobs:
    def test_create_job(self):
        headers = get_auth_headers("job@example.com", "testpass123")
        project_resp = client.post("/api/v1/projects", json={"name": "Job Project"}, headers=headers)
        project_id = project_resp.json()["id"]

        response = client.post("/api/v1/jobs", json={
            "prompt": "A cinematic shot of a futuristic city",
            "job_type": "text_to_video",
            "project_id": project_id,
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"

    def test_list_jobs_empty(self):
        headers = get_auth_headers("lj@example.com", "testpass123")
        response = client.get("/api/v1/jobs", headers=headers)
        assert response.status_code == 200
        assert response.json() == []


class TestProviders:
    def test_list_providers(self):
        response = client.get("/api/v1/providers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_provider_health_not_found(self):
        response = client.get("/api/v1/providers/nonexistent/health")
        assert response.status_code == 404
