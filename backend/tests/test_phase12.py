import pytest
from tests.conftest import client, get_auth_headers, create_project, upload_asset


class TestUniversalCommandEngine:
    def test_parse_remove_object_command(self):
        headers = get_auth_headers("cmd1@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase12/command",
            json={"command": "Remove the person in the background", "context": {}},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "remove_object"
        assert data["target"] == "person"
        assert data["confidence"] > 0.5

    def test_parse_camera_command(self):
        headers = get_auth_headers("cmd2@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase12/command",
            json={"command": "Make the camera slowly orbit around her", "context": {}},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "change_camera"
        assert data["parameters"].get("camera_movement") == "orbit"

    def test_parse_extend_command(self):
        headers = get_auth_headers("cmd3@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase12/command",
            json={"command": "Continue this scene for 8 seconds", "context": {}},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "extend_video"
        assert data["parameters"].get("duration_seconds") == 8

    def test_parse_variant_command(self):
        headers = get_auth_headers("cmd4@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase12/command",
            json={"command": "Create 5 different versions", "context": {}},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "create_variants"
        assert data["parameters"].get("count") == 5

    def test_parse_unknown_command(self):
        headers = get_auth_headers("cmd5@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase12/command",
            json={"command": "Hello world", "context": {}},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["needs_clarification"] is True


class TestMediaUnderstanding:
    def test_understand_asset(self):
        headers = get_auth_headers("mu1@example.com", "testpass123")
        project = create_project(headers, "Understanding Test")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/phase12/understand-asset",
            params={"asset_id": asset["id"], "asset_type": "video"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "understanding_id" in data
        assert "visual" in data
        assert "embeddings" in data


class TestVideoExtension:
    def test_extend_video(self):
        headers = get_auth_headers("ve1@example.com", "testpass123")
        project = create_project(headers, "Extension Test")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/phase12/extend-video",
            params={
                "source_asset_id": asset["id"],
                "project_id": project["id"],
                "extend_position": "end",
                "extend_duration_seconds": 5.0,
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "extension_id" in data
        assert data["status"] == "completed"


class TestImageToVideo:
    def test_image_to_video(self):
        headers = get_auth_headers("i2v1@example.com", "testpass123")
        project = create_project(headers, "I2V Test")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/phase12/image-to-video",
            params={
                "source_asset_id": asset["id"],
                "project_id": project["id"],
                "prompt": "Make this image into a cinematic video",
                "duration_seconds": 5.0,
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


class TestVideoToVideo:
    def test_video_to_video(self):
        headers = get_auth_headers("v2v1@example.com", "testpass123")
        project = create_project(headers, "V2V Test")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/phase12/video-to-video",
            params={
                "source_asset_id": asset["id"],
                "project_id": project["id"],
                "prompt": "Make this scene cyberpunk but keep the person",
                "preserve_person": True,
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


class TestCharacterPerformance:
    def test_plan_performance(self):
        headers = get_auth_headers("cp1@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase12/character-performance",
            params={
                "character_id": "test-character",
                "prompt": "Make him walk and smile",
                "duration_seconds": 5.0,
            },
            headers=headers,
        )
        assert response.status_code in (200, 404)


class TestMakeAuto:
    def test_make_auto_generation(self):
        headers = get_auth_headers("auto1@example.com", "testpass123")
        project = create_project(headers, "AUTO Test")
        response = client.post(
            "/api/v1/phase12/make-auto",
            params={
                "project_id": project["id"],
                "prompt": "Create a cinematic 30-second advertisement for a luxury sneaker",
                "approval_mode": "auto",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "auto_id" in data
        assert data["status"] == "completed"

    def test_make_auto_with_assets(self):
        headers = get_auth_headers("auto2@example.com", "testpass123")
        project = create_project(headers, "AUTO Test 2")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/phase12/make-auto",
            params={
                "project_id": project["id"],
                "prompt": "Make this product into a commercial",
                "source_asset_ids": [asset["id"]],
            },
            headers=headers,
        )
        assert response.status_code == 200


class TestAssetIntelligence:
    def test_classify_asset(self):
        headers = get_auth_headers("ai1@example.com", "testpass123")
        project = create_project(headers, "Intelligence Test")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/phase12/asset-intelligence",
            params={"asset_id": asset["id"], "asset_type": "video"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "classification" in data
        assert "tags" in data
