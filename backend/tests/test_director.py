import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db, Base
<<<<<<< ours
from app.models.models import User, Project
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import asyncio

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_director.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


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
=======
>>>>>>> theirs

client = TestClient(app)


<<<<<<< ours
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


=======
>>>>>>> theirs
def get_auth_headers(email: str, password: str) -> dict:
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = client.post("/api/v1/auth/token", data={"username": email, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_project(headers: dict, name: str = "Test Project") -> dict:
    response = client.post("/api/v1/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


class TestDirectorPlanCreation:
    def test_simple_prompt(self):
        headers = get_auth_headers("simple@example.com", "testpass123")
        project = create_project(headers, "Simple Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a video about a product.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "draft"
        assert len(data["scenes"]) >= 1

    def test_commercial_prompt(self):
        headers = get_auth_headers("commercial@example.com", "testpass123")
        project = create_project(headers, "Commercial Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a 30 second cinematic luxury watch advertisement. Show the watch with water droplets, orbit around it, and end with the logo.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["intent"]["content_type"] == "commercial"
        assert data["intent"]["tone"] == "premium"
        assert data["export_requirements"]["aspect_ratio"] == "16:9"
        assert len(data["scenes"]) >= 2

    def test_cinematic_prompt(self):
        headers = get_auth_headers("cinematic@example.com", "testpass123")
        project = create_project(headers, "Cinematic Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Make a cinematic scene of a person walking through a city at night with dramatic lighting.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["intent"]["content_type"] == "cinematic"
        assert "person" in data["intent"]["characters"]

    def test_social_video_prompt(self):
        headers = get_auth_headers("social@example.com", "testpass123")
        project = create_project(headers, "Social Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a TikTok about this new shoe. Make it fun and energetic.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["intent"]["content_type"] == "social"
        assert data["intent"]["platform"] == "tiktok"
        assert data["export_requirements"]["aspect_ratio"] == "9:16"

    def test_duration_extraction(self):
        headers = get_auth_headers("duration@example.com", "testpass123")
        project = create_project(headers, "Duration Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a 15 second product demo.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["intent"]["total_duration_seconds"] == 15

    def test_aspect_ratio_extraction(self):
        headers = get_auth_headers("aspect@example.com", "testpass123")
        project = create_project(headers, "Aspect Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a vertical video for Instagram Reels.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["intent"]["aspect_ratio"] == "9:16"

    def test_character_detection(self):
        headers = get_auth_headers("char@example.com", "testpass123")
        project = create_project(headers, "Character Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Make a video with a person walking in the city.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert "person" in data["intent"]["characters"]

    def test_product_detection(self):
        headers = get_auth_headers("prod@example.com", "testpass123")
        project = create_project(headers, "Product Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a luxury watch commercial.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert "product" in data["intent"]["products"]

    def test_location_detection(self):
        headers = get_auth_headers("loc@example.com", "testpass123")
        project = create_project(headers, "Location Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a video in Tokyo at night.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert "Tokyo" in data["intent"]["locations"]

    def test_audio_requirement_detection(self):
        headers = get_auth_headers("audio@example.com", "testpass123")
        project = create_project(headers, "Audio Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a video with voiceover and background music.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert len(data["audio_requirements"]) >= 1
        audio_types = [a["type"] for a in data["audio_requirements"]]
        assert "voiceover" in audio_types
        assert "music" in audio_types

    def test_reference_assignment(self):
        headers = get_auth_headers("ref@example.com", "testpass123")
        project = create_project(headers, "Reference Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a video using the uploaded reference.",
            "project_id": project["id"],
            "references": ["ref-1", "ref-2"],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert "ref-1" in data["intent"]["references"]

    def test_unauthorized_project_access(self):
        headers1 = get_auth_headers("user1@example.com", "testpass123")
        headers2 = get_auth_headers("user2@example.com", "testpass123")
        project = create_project(headers1, "Private Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a video.",
            "project_id": project["id"],
        }, headers=headers2)
        assert response.status_code in [403, 404]

    def test_approval_workflow(self):
        headers = get_auth_headers("approval@example.com", "testpass123")
        project = create_project(headers, "Approval Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a product video.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        plan_id = response.json()["id"]

        approve_response = client.post(f"/api/v1/director/plans/{plan_id}/approve", headers=headers)
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"

    def test_reject_workflow(self):
        headers = get_auth_headers("reject@example.com", "testpass123")
        project = create_project(headers, "Reject Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a video.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        plan_id = response.json()["id"]

        reject_response = client.post(f"/api/v1/director/plans/{plan_id}/reject", headers=headers)
        assert reject_response.status_code == 200
        assert reject_response.json()["status"] == "rejected"

    def test_validate_plan(self):
        headers = get_auth_headers("validate@example.com", "testpass123")
        project = create_project(headers, "Validate Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a 30 second commercial.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        plan_id = response.json()["id"]

        validate_response = client.post(f"/api/v1/director/plans/{plan_id}/validate", headers=headers)
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

    def test_list_plans(self):
        headers = get_auth_headers("list@example.com", "testpass123")
        project = create_project(headers, "List Plans Project")
        client.post("/api/v1/director/plan", json={
            "prompt": "Create video 1.",
            "project_id": project["id"],
        }, headers=headers)
        client.post("/api/v1/director/plan", json={
            "prompt": "Create video 2.",
            "project_id": project["id"],
        }, headers=headers)

        response = client.get(f"/api/v1/director/projects/{project['id']}/plans", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_plan(self):
        headers = get_auth_headers("get@example.com", "testpass123")
        project = create_project(headers, "Get Plan Project")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "Create a video.",
            "project_id": project["id"],
        }, headers=headers)
        assert response.status_code == 201
        plan_id = response.json()["id"]

        get_response = client.get(f"/api/v1/director/plans/{plan_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["id"] == plan_id

    def test_empty_prompt_validation(self):
        headers = get_auth_headers("empty@example.com", "testpass123")
        response = client.post("/api/v1/director/plan", json={
            "prompt": "",
            "project_id": None,
        }, headers=headers)
        assert response.status_code == 422
