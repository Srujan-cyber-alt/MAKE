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
