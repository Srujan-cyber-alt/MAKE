import pytest
from tests.conftest import client, get_auth_headers, create_project, upload_asset


class TestGenerativeModelAbstraction:
    def test_list_all_models(self):
        headers = get_auth_headers("model@example.com", "testpass123")
        response = client.get("/api/v1/phase9/models", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_smart_model_router(self):
        headers = get_auth_headers("router@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/route",
            json={"required_capabilities": ["text_to_video"], "duration_seconds": 5.0},
            headers=headers,
        )
        assert response.status_code in (200, 422)


class TestAdvancedPromptCompiler:
    def test_compile_cinematic_prompt(self):
        headers = get_auth_headers("prompt@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/compile-prompt",
            params={"prompt": "Make this into a cinematic night scene with rain"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "compiled_prompt" in data

    def test_compile_preserves_continuity(self):
        headers = get_auth_headers("prompt2@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/compile-prompt",
            params={"prompt": "Keep the person's identity and make it look premium"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "preserve_identity" in data.get("continuity", [])


class TestTemporalConsistencyEngine:
    def test_analyze_temporal(self):
        headers = get_auth_headers("temp@example.com", "testpass123")
        project = create_project(headers, "Temporal Project")
        asset = upload_asset(headers, project["id"])
        response = client.get(
            f"/api/v1/phase9/temporal/{asset['id']}?project_id={project['id']}",
            headers=headers,
        )
        assert response.status_code in (200, 404)


class TestIdentityLockV2:
    def test_create_identity_profile(self):
        headers = get_auth_headers("id@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/identity",
            params={"entity_type": "person", "name": "Test Person", "reference_asset_ids": []},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "profile_id" in data


class TestCharacterSystem:
    def test_create_character(self):
        headers = get_auth_headers("char@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/characters",
            params={"name": "Hero"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "character_id" in data
        assert data["name"] == "Hero"


class TestProductSystem:
    def test_create_product(self):
        headers = get_auth_headers("prod@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/products",
            params={"name": "SuperSoda"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "product_id" in data
        assert data["name"] == "SuperSoda"


class TestCameraControlEngine:
    def test_parse_orbit_camera(self):
        headers = get_auth_headers("cam@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/camera",
            params={"prompt": "make the camera slowly orbit around her"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("movement") == "orbit"

    def test_parse_push_in_camera(self):
        headers = get_auth_headers("cam2@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/camera",
            params={"prompt": "start wide and push into a close-up"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("movement") == "push_in"


class TestMotionEngine:
    def test_parse_walk(self):
        headers = get_auth_headers("mot@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/motion",
            params={"prompt": "make the person walk"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["action"] == "walk"


class TestKeyframeSystemV2:
    def test_parse_grow_keyframes(self):
        headers = get_auth_headers("kf@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/keyframes",
            params={"prompt": "make the logo grow", "frame_range_start": 0, "frame_range_end": 30},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(kf["parameter"] == "scale" for kf in data)


class TestUnifiedQualityScoring:
    def test_quality_score(self):
        headers = get_auth_headers("qual@example.com", "testpass123")
        project = create_project(headers, "Quality Project")
        asset = upload_asset(headers, project["id"])
        response = client.get(
            f"/api/v1/phase9/quality/{asset['id']}?project_id={project['id']}",
            headers=headers,
        )
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert "overall" in data


class TestGenerationIteration:
    def test_create_iteration(self):
        headers = get_auth_headers("iter@example.com", "testpass123")
        project = create_project(headers, "Iteration Project")
        response = client.post(
            "/api/v1/phase9/iterations",
            params={"project_id": project["id"], "prompt": "make it more cinematic"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "iteration_id" in data


class TestCaptionSystem:
    def test_generate_captions(self):
        headers = get_auth_headers("cap@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/captions",
            params={"prompt": "hello world this is a test caption", "duration_seconds": 10.0},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "segments" in data


class TestColorLookEngine:
    def test_apply_cinematic_look(self):
        headers = get_auth_headers("color@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/color-look?source_path=/tmp/test.mp4&output_path=/tmp/test_color.mp4",
            headers=headers,
        )
        assert response.status_code in (200, 500)


class TestAudioSystem:
    def test_create_audio_track(self):
        headers = get_auth_headers("aud@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/audio/track",
            params={"track_id": "track1", "track_type": "music", "source": "/tmp/music.mp3", "volume": 0.8},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["track_id"] == "track1"
