import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

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
        register_response = client.post("/api/v1/auth/register", json={
            "email": "proj@example.com",
            "password": "testpass123",
        })
        token = register_response.cookies.get("access_token")
        if not token:
            login_response = client.post("/api/v1/auth/token", data={
                "username": "proj@example.com",
                "password": "testpass123",
            })
            token = login_response.cookies.get("access_token")

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/v1/projects", json={
            "name": "Test Project",
            "description": "A test project",
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"

    def test_list_projects(self):
        register_response = client.post("/api/v1/auth/register", json={
            "email": "list@example.com",
            "password": "testpass123",
        })
        login_response = client.post("/api/v1/auth/token", data={
            "username": "list@example.com",
            "password": "testpass123",
        })
        token = login_response.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200


class TestJobs:
    def test_create_job(self):
        register_response = client.post("/api/v1/auth/register", json={
            "email": "job@example.com",
            "password": "testpass123",
        })
        login_response = client.post("/api/v1/auth/token", data={
            "username": "job@example.com",
            "password": "testpass123",
        })
        token = login_response.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        project_response = client.post("/api/v1/projects", json={
            "name": "Job Project",
        }, headers=headers)
        project_id = project_response.json()["id"]

        response = client.post("/api/v1/jobs", json={
            "prompt": "A cinematic shot of a futuristic city",
            "job_type": "text_to_video",
            "project_id": project_id,
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"


class TestProviders:
    def test_list_providers(self):
        response = client.get("/api/v1/providers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
