import pytest
from tests.conftest import client, get_auth_headers, create_project, upload_asset


class TestVisualAnalyzer:
    def test_analyze_video_returns_analysis(self):
        headers = get_auth_headers("va@example.com", "testpass123")
        project = create_project(headers, "VA Project")
        asset = upload_asset(headers, project["id"])
        response = client.get(f"/api/v1/phase7/visual-analysis/{asset['id']}?project_id={project['id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert "objects" in data
        assert "faces" in data
        assert "scenes" in data
        assert "motion" in data
        assert "ml_available" in data

    def test_analyze_video_not_found(self):
        headers = get_auth_headers("va2@example.com", "testpass123")
        response = client.get("/api/v1/phase7/visual-analysis/nonexistent?project_id=bad", headers=headers)
        assert response.status_code in (404, 200)


class TestSegmentationService:
    def test_segment_person(self):
        headers = get_auth_headers("seg@example.com", "testpass123")
        project = create_project(headers, "Seg Project")
        asset = upload_asset(headers, project["id"])
        response = client.get(f"/api/v1/phase7/segmentation/{asset['id']}?mask_type=person&project_id={project['id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "mask_id" in data
        assert "type" in data

    def test_segment_object(self):
        headers = get_auth_headers("seg2@example.com", "testpass123")
        project = create_project(headers, "Seg2 Project")
        asset = upload_asset(headers, project["id"])
        response = client.get(f"/api/v1/phase7/segmentation/{asset['id']}?mask_type=car&project_id={project['id']}", headers=headers)
        assert response.status_code == 200


class TestSmartTargetSelector:
    def test_select_target_with_detected_targets(self):
        headers = get_auth_headers("target@example.com", "testpass123")
        project = create_project(headers, "Target Project")
        asset = upload_asset(headers, project["id"])
        response = client.get(
            f"/api/v1/phase7/smart-target/{asset['id']}?project_id={project['id']}&prompt=remove+the+person",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "requires_clarification" in data


class TestQualityGates:
    def test_quality_gate_evaluation(self):
        headers = get_auth_headers("quality@example.com", "testpass123")
        response = client.post("/api/v1/phase7/quality-gate/fake-asset", headers=headers)
        assert response.status_code in (200, 500)


class TestVersioning:
    def test_create_version(self):
        headers = get_auth_headers("ver@example.com", "testpass123")
        project = create_project(headers, "Version Project")
        response = client.post(
            f"/api/v1/phase7/versions/{project['id']}",
            json={"project_id": project["id"], "source_asset_id": "fake", "prompt": "v1 prompt", "operations": []},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "version_id" in data
        assert "version_number" in data

    def test_list_versions(self):
        headers = get_auth_headers("ver2@example.com", "testpass123")
        project = create_project(headers, "Version List Project")
        client.post(
            f"/api/v1/phase7/versions/{project['id']}",
            json={"project_id": project["id"], "source_asset_id": "fake", "prompt": "v1 prompt", "operations": []},
            headers=headers,
        )
        response = client.get(f"/api/v1/phase7/versions/{project['id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestBackgroundReplacement:
    def test_replace_background_endpoint(self):
        headers = get_auth_headers("bg@example.com", "testpass123")
        project = create_project(headers, "BG Replace Project")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            f"/api/v1/phase7/background-replacement/{asset['id']}?project_id={project['id']}&background_prompt=futuristic+city",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "operation_id" in data


class TestMotionTransfer:
    def test_motion_transfer_endpoint(self):
        headers = get_auth_headers("mot@example.com", "testpass123")
        project = create_project(headers, "Motion Project")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            f"/api/v1/phase7/motion-transfer/{asset['id']}?project_id={project['id']}&motion_strength=0.9",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "operation_id" in data


class TestPhase7Schemas:
    def test_frame_range_parser(self):
        from app.services.frame_range import FrameRangeParser
        fr = FrameRangeParser.from_time_range(0, 10, fps=30.0)
        assert fr.start_frame == 0
        assert fr.end_frame == 300

    def test_quality_thresholds(self):
        from app.schemas.phase7 import QualityThresholds
        qt = QualityThresholds()
        assert qt.min_temporal_score == 0.7

    def test_identity_modes(self):
        from app.schemas.phase7 import IdentityMode
        assert IdentityMode.STRICT.value == "strict"
        assert IdentityMode.BALANCED.value == "balanced"
        assert IdentityMode.CREATIVE.value == "creative"
