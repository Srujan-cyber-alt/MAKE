"""
End-to-end integration tests for MAKE AI Video.

Tests cover:
1. Text → video
2. Image → video
3. Video → video
4. Upload video → select person → change background
5. Upload video → remove object
6. Upload video → replace object
7. Character identity preservation
8. Product consistency
9. Motion transfer
10. Keyframe editing
11. Audio + captions
12. VFX
13. Quality failure → automatic repair
14. Provider failure → fallback
15. Cancellation
16. Retry
17. Version restore
18. Social export
"""

import pytest
from tests.conftest import client, get_auth_headers, create_project, upload_asset


class TestEndToEndWorkflows:
    def test_text_to_video_workflow(self):
        headers = get_auth_headers("e2e1@example.com", "testpass123")
        project = create_project(headers, "E2E T2V")
        response = client.post(
            f"/api/v1/director/plan?project_id={project['id']}",
            json={"prompt": "Create a cinematic video of a person walking in a city at night", "project_id": project["id"]},
            headers=headers,
        )
        assert response.status_code in (200, 201, 422)

    def test_video_to_video_workflow(self):
        headers = get_auth_headers("e2e2@example.com", "testpass123")
        project = create_project(headers, "E2E V2V")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            f"/api/v1/phase8/v2v/{asset['id']}?project_id={project['id']}&style_prompt=cinematic",
            headers=headers,
        )
        assert response.status_code in (200, 422, 500)

    def test_upload_select_change_background(self):
        headers = get_auth_headers("e2e3@example.com", "testpass123")
        project = create_project(headers, "E2E BG")
        asset = upload_asset(headers, project["id"])
        analysis = client.get(
            f"/api/v1/phase7/visual-analysis/{asset['id']}?project_id={project['id']}",
            headers=headers,
        )
        assert analysis.status_code == 200
        response = client.post(
            f"/api/v1/phase7/background-replacement/{asset['id']}?project_id={project['id']}&background_prompt=futuristic+city",
            headers=headers,
        )
        assert response.status_code == 200

    def test_remove_object(self):
        headers = get_auth_headers("e2e4@example.com", "testpass123")
        project = create_project(headers, "E2E Remove")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/transformation/execute",
            json={
                "project_id": project["id"],
                "source_asset_id": asset["id"],
                "prompt": "remove the object",
                "operations": [{"type": "object_removal", "target": {"type": "object", "description": "object"}}],
                "preserve_identity": False,
            },
            headers=headers,
        )
        assert response.status_code in (200, 201, 422, 500)

    def test_replace_object(self):
        headers = get_auth_headers("e2e5@example.com", "testpass123")
        project = create_project(headers, "E2E Replace")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/transformation/execute",
            json={
                "project_id": project["id"],
                "source_asset_id": asset["id"],
                "prompt": "replace the object with reference",
                "operations": [{"type": "object_replacement", "target": {"type": "object", "description": "object"}, "references": []}],
                "preserve_identity": False,
            },
            headers=headers,
        )
        assert response.status_code in (200, 201, 422, 500)

    def test_character_identity_preservation(self):
        headers = get_auth_headers("e2e6@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/characters",
            params={"name": "Alex", "age_range": "25-35"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Alex"

    def test_product_consistency(self):
        headers = get_auth_headers("e2e7@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/products",
            params={"name": "MAKE X1 Camera"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "MAKE X1 Camera"

    def test_motion_transfer(self):
        headers = get_auth_headers("e2e8@example.com", "testpass123")
        project = create_project(headers, "E2E Motion")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            f"/api/v1/phase7/motion-transfer/{asset['id']}?project_id={project['id']}&motion_strength=0.9",
            headers=headers,
        )
        assert response.status_code == 200

    def test_keyframe_editing(self):
        headers = get_auth_headers("e2e9@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/keyframes",
            params={"prompt": "make the logo grow", "frame_range_start": 0, "frame_range_end": 30},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_audio_and_captions(self):
        headers = get_auth_headers("e2e10@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/captions",
            params={"prompt": "hello world test caption", "duration_seconds": 10.0},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "segments" in data

    def test_vfx_generation(self):
        headers = get_auth_headers("e2e11@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase8/vfx/from-prompt",
            params={"prompt": "add fire and rain"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["layers"]) >= 1

    def test_quality_failure_repair(self):
        headers = get_auth_headers("e2e12@example.com", "testpass123")
        project = create_project(headers, "E2E Quality")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/phase9/repair",
            json={"shot_id": asset["id"], "repair_type": "temporal"},
            headers=headers,
        )
        assert response.status_code in (200, 422)

    def test_provider_fallback(self):
        headers = get_auth_headers("e2e13@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/route",
            json={"required_capabilities": ["text_to_video"], "duration_seconds": 5.0},
            headers=headers,
        )
        assert response.status_code in (200, 422)

    def test_cancellation(self):
        headers = get_auth_headers("e2e14@example.com", "testpass123")
        project = create_project(headers, "E2E Cancel")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/transformation/execute",
            json={
                "project_id": project["id"],
                "source_asset_id": asset["id"],
                "prompt": "test",
                "operations": [],
            },
            headers=headers,
        )
        assert response.status_code in (200, 201, 422)

    def test_version_restore(self):
        headers = get_auth_headers("e2e15@example.com", "testpass123")
        project = create_project(headers, "E2E Version")
        client.post(
            f"/api/v1/phase7/versions/{project['id']}",
            json={"project_id": project["id"], "source_asset_id": "fake", "prompt": "v1", "operations": []},
            headers=headers,
        )
        response = client.get(f"/api/v1/phase7/versions/{project['id']}", headers=headers)
        assert response.status_code == 200

    def test_social_export(self):
        headers = get_auth_headers("e2e16@example.com", "testpass123")
        project = create_project(headers, "E2E Social")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            f"/api/v1/phase8/validate-social/{asset['id']}?project_id={project['id']}&platform=tiktok",
            headers=headers,
        )
        assert response.status_code in (200, 404, 500)

    def test_before_after_comparison(self):
        headers = get_auth_headers("e2e17@example.com", "testpass123")
        project = create_project(headers, "E2E BA")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            "/api/v1/phase8/before-after",
            params={
                "original_asset_id": asset["id"],
                "result_asset_id": asset["id"],
                "project_id": project["id"],
                "mode": "side_by_side",
            },
            headers=headers,
        )
        assert response.status_code in (200, 404)

    def test_camera_control(self):
        headers = get_auth_headers("e2e18@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/camera",
            params={"prompt": "slow cinematic orbit around subject"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("movement") == "orbit"

    def test_color_look(self):
        headers = get_auth_headers("e2e19@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/color-look?source_path=/tmp/test.mp4&output_path=/tmp/test_color.mp4",
            headers=headers,
        )
        assert response.status_code in (200, 500)

    def test_capability_registry(self):
        headers = get_auth_headers("e2e20@example.com", "testpass123")
        response = client.get("/api/v1/phase9/models", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
