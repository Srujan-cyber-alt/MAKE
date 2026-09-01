import pytest
from fastapi.testclient import TestClient
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


def create_project(headers: dict, name: str = "Test Project") -> dict:
    response = client.post("/api/v1/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


class TestHealth:
    def test_health(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readiness(self):
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

    def test_liveness(self):
        response = client.get("/api/v1/health/live")
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

    def test_register_duplicate_email(self):
        client.post("/api/v1/auth/register", json={
            "email": "dup@example.com",
            "password": "testpass123",
        })
        response = client.post("/api/v1/auth/register", json={
            "email": "dup@example.com",
            "password": "testpass123",
        })
        assert response.status_code == 400

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

    def test_login_invalid_password(self):
        client.post("/api/v1/auth/register", json={
            "email": "badlogin@example.com",
            "password": "testpass123",
        })
        response = client.post("/api/v1/auth/token", data={
            "username": "badlogin@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401


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
        assert data["status"] == "active"

    def test_list_projects(self):
        headers = get_auth_headers("list@example.com", "testpass123")
        client.post("/api/v1/projects", json={"name": "Project 1"}, headers=headers)
        client.post("/api/v1/projects", json={"name": "Project 2"}, headers=headers)
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_project_not_found(self):
        headers = get_auth_headers("np@example.com", "testpass123")
        response = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000", headers=headers)
        assert response.status_code == 404

    def test_update_project(self):
        headers = get_auth_headers("up@example.com", "testpass123")
        project = create_project(headers, "Update Test")
        response = client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"name": "Updated Name", "description": "Updated desc"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_delete_project(self):
        headers = get_auth_headers("del@example.com", "testpass123")
        project = create_project(headers, "Delete Test")
        response = client.delete(f"/api/v1/projects/{project['id']}", headers=headers)
        assert response.status_code == 204
        response = client.get(f"/api/v1/projects/{project['id']}", headers=headers)
        assert response.status_code == 404


class TestAssets:
    def test_upload_asset(self):
        headers = get_auth_headers("asset@example.com", "testpass123")
        project = create_project(headers, "Asset Project")
        response = client.post(
            "/api/v1/assets/upload",
            data={"project_id": project["id"], "asset_type": "reference"},
            files={"file": ("test.png", b"fake-image-data", "image/png")},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.png"
        assert data["status"] == "ready"

    def test_list_assets_empty(self):
        headers = get_auth_headers("la@example.com", "testpass123")
        project = create_project(headers, "List Asset Project")
        response = client.get(f"/api/v1/assets/project/{project['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_delete_asset(self):
        headers = get_auth_headers("da@example.com", "testpass123")
        project = create_project(headers, "Delete Asset Project")
        upload_resp = client.post(
            "/api/v1/assets/upload",
            data={"project_id": project["id"], "asset_type": "reference"},
            files={"file": ("del.png", b"data", "image/png")},
            headers=headers,
        )
        asset_id = upload_resp.json()["id"]
        response = client.delete(f"/api/v1/assets/{asset_id}", headers=headers)
        assert response.status_code == 204


class TestJobs:
    def test_create_job(self):
        headers = get_auth_headers("job@example.com", "testpass123")
        project = create_project(headers, "Job Project")
        response = client.post("/api/v1/jobs", json={
            "prompt": "A cinematic shot of a futuristic city",
            "job_type": "text_to_video",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"
        assert data["provider"] == "runway"

    def test_list_jobs_empty(self):
        headers = get_auth_headers("lj@example.com", "testpass123")
        response = client.get("/api/v1/jobs", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_cancel_job(self):
        headers = get_auth_headers("cj@example.com", "testpass123")
        project = create_project(headers, "Cancel Job Project")
        job_resp = client.post("/api/v1/jobs", json={
            "prompt": "Cancel test",
            "job_type": "text_to_video",
            "project_id": project["id"],
        }, headers=headers)
        job_id = job_resp.json()["id"]
        response = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestProviders:
    def test_list_providers(self):
        response = client.get("/api/v1/providers")
        assert response.status_code == 200
        providers = response.json()
        assert isinstance(providers, list)
        if len(providers) > 0:
            assert "name" in providers[0]
            assert "capabilities" in providers[0]
            assert "models" in providers[0]

    def test_provider_health_not_found(self):
        response = client.get("/api/v1/providers/nonexistent/health")
        assert response.status_code == 404

    def test_providers_by_capability(self):
        response = client.get("/api/v1/providers/capabilities/text_to_video")
        assert response.status_code == 200


class TestVersions:
    def test_create_version(self):
        headers = get_auth_headers("ver@example.com", "testpass123")
        project = create_project(headers, "Version Project")
        response = client.post(
            f"/api/v1/projects/{project['id']}/versions?name=Version+1",
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["version_number"] == 1
        assert "snapshot" in data

    def test_list_versions(self):
        headers = get_auth_headers("lv@example.com", "testpass123")
        project = create_project(headers, "List Versions Project")
        client.post(f"/api/v1/projects/{project['id']}/versions", headers=headers)
        response = client.get(f"/api/v1/projects/{project['id']}/versions", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_restore_version(self):
        headers = get_auth_headers("rv@example.com", "testpass123")
        project = create_project(headers, "Restore Version Project")
        version_resp = client.post(f"/api/v1/projects/{project['id']}/versions", headers=headers)
        version_id = version_resp.json()["id"]
        response = client.post(f"/api/v1/projects/versions/{version_id}/restore", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "restored"


class TestReferences:
    def test_add_reference(self):
        headers = get_auth_headers("ref@example.com", "testpass123")
        project = create_project(headers, "Reference Project")
        upload_resp = client.post(
            "/api/v1/assets/upload",
            data={"project_id": project["id"], "asset_type": "reference"},
            files={"file": ("ref.png", b"data", "image/png")},
            headers=headers,
        )
        asset_id = upload_resp.json()["id"]
        response = client.post(
            f"/api/v1/projects/{project['id']}/references",
            json={"asset_id": asset_id, "role": "character"},
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["role"] == "character"

    def test_list_references(self):
        headers = get_auth_headers("lr@example.com", "testpass123")
        project = create_project(headers, "List References Project")
        upload_resp = client.post(
            "/api/v1/assets/upload",
            data={"project_id": project["id"], "asset_type": "reference"},
            files={"file": ("ref.png", b"data", "image/png")},
            headers=headers,
        )
        asset_id = upload_resp.json()["id"]
        client.post(
            f"/api/v1/projects/{project['id']}/references",
            json={"asset_id": asset_id, "role": "product"},
            headers=headers,
        )
        response = client.get(f"/api/v1/projects/{project['id']}/references", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestContext:
    def test_update_and_get_context(self):
        headers = get_auth_headers("ctx@example.com", "testpass123")
        project = create_project(headers, "Context Project")
        response = client.post(
            f"/api/v1/projects/{project['id']}/context",
            json={"context": {"style": "cinematic", "character": "hero"}},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["context"]["style"] == "cinematic"

        response = client.get(f"/api/v1/projects/{project['id']}/context", headers=headers)
        assert response.status_code == 200
        assert response.json()["context"]["character"] == "hero"


class TestTimelines:
    def test_create_timeline(self):
        headers = get_auth_headers("tl@example.com", "testpass123")
        project = create_project(headers, "Timeline Project")
        response = client.post(
            f"/api/v1/timelines/{project['id']}",
            json={
                "name": "Main Timeline",
                "fps": 30,
                "tracks": [{"type": "video", "clips": []}],
            },
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Main Timeline"

    def test_list_timelines(self):
        headers = get_auth_headers("ltl@example.com", "testpass123")
        project = create_project(headers, "List Timeline Project")
        client.post(
            f"/api/v1/timelines/{project['id']}",
            json={"name": "TL1", "fps": 30, "tracks": []},
            headers=headers,
        )
        response = client.get(f"/api/v1/timelines/{project['id']}", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestSecurity:
    def test_cross_user_project_access(self):
        headers1 = get_auth_headers("user1@example.com", "testpass123")
        headers2 = get_auth_headers("user2@example.com", "testpass123")
        project = create_project(headers1, "Private Project")
        response = client.get(f"/api/v1/projects/{project['id']}", headers=headers2)
        assert response.status_code == 404

    def test_cross_user_asset_access(self):
        headers1 = get_auth_headers("au1@example.com", "testpass123")
        headers2 = get_auth_headers("au2@example.com", "testpass123")
        project = create_project(headers1, "Asset Privacy Project")
        upload_resp = client.post(
            "/api/v1/assets/upload",
            data={"project_id": project["id"], "asset_type": "reference"},
            files={"file": ("secret.png", b"data", "image/png")},
            headers=headers1,
        )
        asset_id = upload_resp.json()["id"]
        response = client.get(f"/api/v1/assets/{asset_id}", headers=headers2)
        assert response.status_code == 404

    def test_unauthorized_access(self):
        response = client.get("/api/v1/projects")
        assert response.status_code == 401

        response = client.post("/api/v1/projects", json={"name": "No Auth"})
        assert response.status_code == 401


class TestGenerationWorkflow:
    def test_generation_endpoint_validation(self):
        headers = get_auth_headers("gen@example.com", "testpass123")
        project = create_project(headers, "Generation Project")
        response = client.post("/api/v1/generation", json={
            "prompt": "",
            "job_type": "text_to_video",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 422

    def test_generation_with_provider_model(self):
        headers = get_auth_headers("genpm@example.com", "testpass123")
        project = create_project(headers, "Provider Model Project")
        response = client.post("/api/v1/generation", json={
            "prompt": "A test video",
            "job_type": "text_to_video",
            "provider": "runway",
            "model": "gen3a_turbo",
            "project_id": project["id"],
            "duration_seconds": 4,
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"
        assert data["provider"] == "runway"
        assert data["model"] == "gen3a_turbo"
