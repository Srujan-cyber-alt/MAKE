import pytest
from tests.conftest import client, get_auth_headers, create_project


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


def upload_asset(headers: dict, project_id: str, filename: str = "test.mp4") -> dict:
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": (filename, b"fake video content", "video/mp4")},
        data={"project_id": project_id, "asset_type": "video"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


class TestTransformationAnalyzer:
    def test_object_removal_detection(self):
        headers = get_auth_headers("rem@example.com", "testpass123")
        project = create_project(headers, "Removal Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/analyze", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Remove the person in the background.",
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["confidence"] > 0
        assert len(data["suggested_operations"]) >= 1
        assert data["suggested_operations"][0]["type"] == "object_removal"

    def test_background_replacement_detection(self):
        headers = get_auth_headers("bg@example.com", "testpass123")
        project = create_project(headers, "BG Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/analyze", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Replace the background with a futuristic city.",
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert any(op["type"] == "background_replacement" for op in data["suggested_operations"])

    def test_vfx_detection(self):
        headers = get_auth_headers("vfx@example.com", "testpass123")
        project = create_project(headers, "VFX Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/analyze", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Add fire and rain to the scene.",
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        vfx_types = [op["type"] for op in data["suggested_operations"]]
        assert "vfx_apply" in vfx_types

    def test_identity_preservation_detection(self):
        headers = get_auth_headers("id@example.com", "testpass123")
        project = create_project(headers, "Identity Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/analyze", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Keep the person's face exactly the same but change the background.",
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert any(op.get("preserve_identity") for op in data["suggested_operations"])

    def test_requires_clarification_on_ambiguous_prompt(self):
        headers = get_auth_headers("ambig@example.com", "testpass123")
        project = create_project(headers, "Ambiguous Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/analyze", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Fix it.",
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["requires_clarification"] is True
        assert len(data["clarification_questions"]) > 0


class TestTransformationPlanner:
    def test_plan_creation(self):
        headers = get_auth_headers("plan@example.com", "testpass123")
        project = create_project(headers, "Plan Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/plan", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Remove the object and replace the background.",
            "operations": [
                {"type": "object_removal", "strength": 0.9},
                {"type": "background_replacement", "strength": 0.8},
            ],
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project["id"]
        assert data["source_asset_id"] == asset["id"]
        assert len(data["operations"]) == 2

    def test_plan_ordering(self):
        headers = get_auth_headers("order@example.com", "testpass123")
        project = create_project(headers, "Order Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/plan", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Remove object, replace background, add fire.",
            "operations": [
                {"type": "vfx_apply", "strength": 0.8},
                {"type": "object_removal", "strength": 0.9},
                {"type": "background_replacement", "strength": 0.8},
            ],
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        types = [op["type"] for op in data["operations"]]
        assert types.index("object_removal") < types.index("background_replacement")
        assert types.index("background_replacement") < types.index("vfx_apply")


class TestTransformationAPI:
    def test_execute_transformation(self):
        headers = get_auth_headers("exec@example.com", "testpass123")
        project = create_project(headers, "Execute Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/execute", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Apply a cinematic style transfer.",
            "operations": [
                {"type": "style_transfer", "strength": 0.7, "preserve_identity": True},
            ],
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] in ["queued", "processing", "completed"]
        assert data["project_id"] == project["id"]

    def test_get_transformation_status(self):
        headers = get_auth_headers("stat@example.com", "testpass123")
        project = create_project(headers, "Status Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/execute", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Make it cinematic.",
            "operations": [{"type": "style_transfer", "strength": 0.7}],
        }, headers=headers)
        assert response.status_code == 201
        transformation_id = response.json()["id"]

        status_response = client.get(f"/api/v1/transformation/{transformation_id}/status", headers=headers)
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["id"] == transformation_id
        assert "status" in data

    def test_cancel_transformation(self):
        headers = get_auth_headers("cancel@example.com", "testpass123")
        project = create_project(headers, "Cancel Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/execute", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Style transfer.",
            "operations": [{"type": "style_transfer", "strength": 0.7}],
        }, headers=headers)
        assert response.status_code == 201
        transformation_id = response.json()["id"]

        cancel_response = client.post(f"/api/v1/transformation/{transformation_id}/cancel", headers=headers)
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"

    def test_list_project_transformations(self):
        headers = get_auth_headers("list@example.com", "testpass123")
        project = create_project(headers, "List Transform Project")
        asset = upload_asset(headers, project["id"])
        client.post("/api/v1/transformation/execute", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Style transfer.",
            "operations": [{"type": "style_transfer", "strength": 0.7}],
        }, headers=headers)

        response = client.get(f"/api/v1/transformation/projects/{project['id']}", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_batch_transformation(self):
        headers = get_auth_headers("batch@example.com", "testpass123")
        project = create_project(headers, "Batch Project")
        asset1 = upload_asset(headers, project["id"], "test1.mp4")
        asset2 = upload_asset(headers, project["id"], "test2.mp4")
        response = client.post("/api/v1/transformation/batch", json={
            "project_id": project["id"],
            "source_asset_ids": [asset1["id"], asset2["id"]],
            "prompt": "Apply cinematic style.",
            "operations": [{"type": "style_transfer", "strength": 0.7}],
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2

    def test_unauthorized_project_access(self):
        headers1 = get_auth_headers("sec1@example.com", "testpass123")
        headers2 = get_auth_headers("sec2@example.com", "testpass123")
        project = create_project(headers1, "Secret Transform Project")
        asset = upload_asset(headers1, project["id"])

        response = client.post("/api/v1/transformation/execute", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "Steal this transformation.",
            "operations": [{"type": "style_transfer", "strength": 0.7}],
        }, headers=headers2)
        assert response.status_code == 404

    def test_mask_creation(self):
        headers = get_auth_headers("mask@example.com", "testpass123")
        project = create_project(headers, "Mask Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/mask", json={
            "asset_id": asset["id"],
            "mask_type": "person",
            "feather": 5,
            "expand": 0,
            "invert": False,
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == asset["id"]
        assert data["mask_type"] == "person"


class TestTransformationValidation:
    def test_missing_source_asset(self):
        headers = get_auth_headers("miss@example.com", "testpass123")
        project = create_project(headers, "Missing Asset Project")
        response = client.post("/api/v1/transformation/execute", json={
            "project_id": project["id"],
            "source_asset_id": "nonexistent-asset",
            "prompt": "Transform this.",
            "operations": [{"type": "style_transfer", "strength": 0.7}],
        }, headers=headers)
        assert response.status_code == 201

    def test_empty_prompt(self):
        headers = get_auth_headers("empty@example.com", "testpass123")
        project = create_project(headers, "Empty Prompt Project")
        asset = upload_asset(headers, project["id"])
        response = client.post("/api/v1/transformation/execute", json={
            "project_id": project["id"],
            "source_asset_id": asset["id"],
            "prompt": "",
            "operations": [{"type": "style_transfer", "strength": 0.7}],
        }, headers=headers)
        assert response.status_code == 422
