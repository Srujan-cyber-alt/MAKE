"""Tests for the Intelligence Core HTTP API — iPhone-controlled operation."""

import pytest

from fastapi.testclient import TestClient
from app.intelligence.api import router, _jm
from app.main import app
from app.intelligence.config import intelligence_settings
from app.intelligence.database import configure_engine, init_db, reset_engine_storage


@pytest.fixture(scope="module")
def api_client():
    """TestClient for the full FastAPI app with Intelligence router registered."""
    # The intelligence router is already registered in main.py
    return TestClient(app)


class TestIntelligenceAPIHealth:
    def test_intelligence_router_exists(self):
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        intel_routes = [r for r in routes if "/intelligence" in r]
        assert len(intel_routes) > 0


class TestJobAPI:
    @pytest.fixture(autouse=True)
    async def _setup_db(self, intel_db):
        """Ensure DB is clean before each test."""
        pass

    def test_create_job(self, api_client):
        resp = api_client.post("/api/v1/intelligence/", json={"request": "create a cinematic video of a person"})
        assert resp.status_code == 201
        data = resp.json()
        assert "job_id" in data
        assert data["state"] == "queued"
        assert "created_at" in data

    def test_get_job(self, api_client):
        # Create first
        resp = api_client.post("/api/v1/intelligence/", json={"request": "create a video"})
        job_id = resp.json()["job_id"]
        # Get
        resp = api_client.get(f"/api/v1/intelligence/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert data["state"] == "queued"
        assert "progress" in data
        assert "created_at" in data

    def test_get_nonexistent_job(self, api_client):
        resp = api_client.get("/api/v1/intelligence/nonexistent-id")
        assert resp.status_code == 404

    def test_list_jobs(self, api_client):
        api_client.post("/api/v1/intelligence/", json={"request": "task 1"})
        api_client.post("/api/v1/intelligence/", json={"request": "task 2"})
        resp = api_client.get("/api/v1/intelligence/list")
        assert resp.status_code == 200
        jobs = resp.json()
        assert len(jobs) >= 2

    def test_cancel_job(self, api_client):
        resp = api_client.post("/api/v1/intelligence/", json={"request": "test task"})
        job_id = resp.json()["job_id"]
        resp = api_client.post(f"/api/v1/intelligence/{job_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["state"] == "cancelled"

    def test_cancel_completed_job(self, api_client):
        resp = api_client.post("/api/v1/intelligence/", json={"request": "create a cinematic video of a person"})
        job_id = resp.json()["job_id"]
        api_client.post(f"/api/v1/intelligence/{job_id}/run")
        cancel_resp = api_client.post(f"/api/v1/intelligence/{job_id}/cancel")
        assert cancel_resp.status_code == 404

    def test_cancel_nonexistent_job(self, api_client):
        resp = api_client.post("/api/v1/intelligence/nonexistent-id/cancel")
        assert resp.status_code == 404


class TestPlanningAPI:
    def test_parse_intent(self, api_client):
        resp = api_client.post("/api/v1/intelligence/intent", json={"request": "create a cinematic video"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "creative"
        assert "raw_request" in data

    def test_generate_plan(self, api_client):
        resp = api_client.post("/api/v1/intelligence/plan", json={"request": "create a cinematic video of a person"})
        assert resp.status_code == 200
        data = resp.json()
        assert "plan" in data
        assert "consistency_report" in data
        assert data["consistency_report"]["passed"] is True

    def test_critique_plan(self, api_client):
        from app.intelligence.schemas import Plan, PlanStep, ToolType
        plan = Plan(intent_id="test", steps=[
            PlanStep(id="s1", action="validate_request", tool=ToolType.REASONING),
        ])
        resp = api_client.post("/api/v1/intelligence/plan/critique", json=plan.model_dump())
        assert resp.status_code == 200
        data = resp.json()
        assert "issues" in data
        assert len(data["issues"]) > 0
        assert data["was_revised"] is True


class TestCreativeAPI:
    def test_creative_direct(self, api_client):
        resp = api_client.post("/api/v1/intelligence/creative/direct", json={"prompt": "cinematic video of a person at sunset"})
        assert resp.status_code == 200
        data = resp.json()
        assert "composition" in data
        assert "lighting" in data
        assert "mood" in data

    def test_visual_plan(self, api_client):
        resp = api_client.post("/api/v1/intelligence/creative/visual-plan", json={"prompt": "create a cinematic video"})
        assert resp.status_code == 200
        data = resp.json()
        assert "scenes" in data
        assert len(data["scenes"]) >= 1


class TestToolsAPI:
    def test_list_tools(self, api_client):
        resp = api_client.get("/api/v1/intelligence/tools")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_tools_health(self, api_client):
        resp = api_client.get("/api/v1/intelligence/tools/health")
        assert resp.status_code == 200


class TestMemoryAPI:
    def test_create_entity(self, api_client):
        resp = api_client.post("/api/v1/intelligence/memory/entity", json={
            "entity_type": "person", "name": "Alice", "attributes": {"age": 30}, "consent": True
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Alice"

    def test_create_entity_no_consent_fails(self, api_client):
        resp = api_client.post("/api/v1/intelligence/memory/entity", json={
            "entity_type": "person", "name": "Bob", "consent": False
        })
        assert resp.status_code == 403

    def test_list_entities(self, api_client):
        api_client.post("/api/v1/intelligence/memory/entity", json={
            "entity_type": "person", "name": "Alice", "consent": True
        })
        resp = api_client.get("/api/v1/intelligence/memory/entities?entity_type=person")
        assert resp.status_code == 200
        entities = resp.json()
        assert len(entities) >= 1


class TestGraphAPI:
    def test_create_node(self, api_client):
        resp = api_client.post("/api/v1/intelligence/graph/node", json={
            "name": "Alice", "entity_type": "Person"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Alice"

    def test_create_edge(self, api_client):
        n1 = api_client.post("/api/v1/intelligence/graph/node", json={"name": "A", "entity_type": "Object"}).json()
        n2 = api_client.post("/api/v1/intelligence/graph/node", json={"name": "B", "entity_type": "Object"}).json()
        resp = api_client.post("/api/v1/intelligence/graph/edge", json={
            "source_node_id": n1["id"], "target_node_id": n2["id"], "relation_type": "connected"
        })
        assert resp.status_code == 200


class TestArtifactAPI:
    def test_get_artifacts_for_completed_job(self, api_client):
        resp = api_client.post("/api/v1/intelligence/", json={"request": "create a cinematic video of a person"})
        job_id = resp.json()["job_id"]
        api_client.post(f"/api/v1/intelligence/{job_id}/run")
        resp = api_client.get(f"/api/v1/intelligence/artifacts/job/{job_id}")
        assert resp.status_code == 200
        artifacts = resp.json()
        assert len(artifacts) >= 1


class TestContextAPI:
    def test_store_and_approve_context(self, api_client):
        resp = api_client.post("/api/v1/intelligence/context", json={
            "key": "theme", "data": {"dark": True}, "auto_approve": True
        })
        assert resp.status_code == 200
        resp = api_client.post("/api/v1/intelligence/context", json={
            "key": "full_name", "data": {"value": "Alice"}, "auto_approve": False
        })
        assert resp.status_code == 200
        resp = api_client.get("/api/v1/intelligence/context/pending")
        pending = resp.json()
        assert len(pending) >= 1
        entry_id = pending[0]["id"]
        resp = api_client.post(f"/api/v1/intelligence/context/{entry_id}/approve")
        assert resp.status_code == 200

    def test_pending_not_in_approved(self, api_client):
        api_client.post("/api/v1/intelligence/context", json={"key": "pending_key", "data": {"v": 1}})
        resp = api_client.get("/api/v1/intelligence/context/approved")
        approved = resp.json()
        assert all(r["status"] == "approved" for r in approved)


class TestRecoveryAPI:
    def test_get_interrupted_jobs(self, api_client):
        resp = api_client.get("/api/v1/intelligence/recovery/interrupted")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_recover_nonexistent_job(self, api_client):
        resp = api_client.post("/api/v1/intelligence/recovery/recover/nonexistent-id")
        assert resp.status_code == 404


class TestSchedulerAPI:
    def test_scheduler_status(self, api_client):
        resp = api_client.get("/api/v1/intelligence/scheduler/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "available_slots" in data


class TestDecisionTraceAPI:
    def test_get_decisions_for_job(self, api_client):
        resp = api_client.post("/api/v1/intelligence/", json={"request": "create a cinematic video of a person"})
        job_id = resp.json()["job_id"]
        api_client.post(f"/api/v1/intelligence/{job_id}/run")
        resp = api_client.get(f"/api/v1/intelligence/decisions/{job_id}")
        assert resp.status_code == 200
        decisions = resp.json()
        assert len(decisions) > 0
