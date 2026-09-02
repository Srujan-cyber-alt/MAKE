import pytest
from tests.conftest import client, get_auth_headers, create_project


class TestStudioRouter:
    def test_get_studio_project(self):
        headers = get_auth_headers("studio1@example.com", "testpass123")
        project = create_project(headers, "Studio Test")
        response = client.get(f"/api/v1/studio/projects/{project['id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "modes" in data
        assert len(data["modes"]) == 7

    def test_execute_studio_command_auto(self):
        headers = get_auth_headers("studio2@example.com", "testpass123")
        project = create_project(headers, "Studio Auto Test")
        response = client.post(
            f"/api/v1/studio/projects/{project['id']}/command",
            json={
                "command": "Create a cinematic 30-second advertisement for a luxury sneaker",
                "mode": "auto",
                "context": {},
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_execute_studio_command_create(self):
        headers = get_auth_headers("studio3@example.com", "testpass123")
        project = create_project(headers, "Studio Create Test")
        response = client.post(
            f"/api/v1/studio/projects/{project['id']}/command",
            json={
                "command": "Create a product commercial",
                "mode": "create",
                "context": {},
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "create"
        assert "creative_plan" in data or "status" in data

    def test_execute_studio_command_empty(self):
        headers = get_auth_headers("studio4@example.com", "testpass123")
        project = create_project(headers, "Studio Empty Test")
        response = client.post(
            f"/api/v1/studio/projects/{project['id']}/command",
            json={"command": "", "mode": "auto", "context": {}},
            headers=headers,
        )
        assert response.status_code == 400

    def test_get_studio_capabilities(self):
        headers = get_auth_headers("studio5@example.com", "testpass123")
        project = create_project(headers, "Studio Caps Test")
        response = client.get(f"/api/v1/studio/projects/{project['id']}/capabilities", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "ffmpeg" in data
        assert "providers" in data

    def test_get_studio_assets(self):
        headers = get_auth_headers("studio6@example.com", "testpass123")
        project = create_project(headers, "Studio Assets Test")
        response = client.get(f"/api/v1/studio/projects/{project['id']}/assets", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_studio_versions(self):
        headers = get_auth_headers("studio7@example.com", "testpass123")
        project = create_project(headers, "Studio Versions Test")
        response = client.get(f"/api/v1/studio/projects/{project['id']}/versions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_studio_version(self):
        headers = get_auth_headers("studio8@example.com", "testpass123")
        project = create_project(headers, "Studio Create Version Test")
        response = client.post(
            f"/api/v1/studio/projects/{project['id']}/versions",
            json={"name": "Test Version", "description": "Test"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Version"

    def test_studio_undo_redo(self):
        headers = get_auth_headers("studio9@example.com", "testpass123")
        project = create_project(headers, "Studio Undo Redo Test")
        undo_response = client.post(f"/api/v1/studio/projects/{project['id']}/undo", headers=headers)
        assert undo_response.status_code == 200
        redo_response = client.post(f"/api/v1/studio/projects/{project['id']}/redo", headers=headers)
        assert redo_response.status_code == 200

    def test_create_job_variation(self):
        headers = get_auth_headers("studio10@example.com", "testpass123")
        project = create_project(headers, "Studio Variation Test")
        asset = upload_asset(headers, project["id"])
        job_response = client.post(
            "/api/v1/jobs",
            json={"project_id": project["id"], "job_type": "text_to_video", "prompt": "test"},
            headers=headers,
        )
        assert job_response.status_code == 201
        job_id = job_response.json()["id"]
        response = client.post(f"/api/v1/studio/jobs/{job_id}/variation", headers=headers)
        assert response.status_code == 200
