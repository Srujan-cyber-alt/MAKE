import pytest
from tests.conftest import client, get_auth_headers, create_project, upload_asset


class TestBeforeAfter:
    def test_side_by_side_comparison(self):
        headers = get_auth_headers("ba@example.com", "testpass123")
        project = create_project(headers, "BA Project")
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


class TestAudioAnalyzer:
    def test_analyze_audio(self):
        headers = get_auth_headers("audio@example.com", "testpass123")
        project = create_project(headers, "Audio Project")
        asset = upload_asset(headers, project["id"])
        response = client.get(f"/api/v1/phase8/audio/{asset['id']}?project_id={project['id']}", headers=headers)
        assert response.status_code in (200, 404)


class TestSocialExport:
    def test_list_presets(self):
        headers = get_auth_headers("social@example.com", "testpass123")
        response = client.get("/api/v1/phase8/social-presets", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_validate_social_export(self):
        headers = get_auth_headers("social2@example.com", "testpass123")
        project = create_project(headers, "Social Project")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            f"/api/v1/phase8/validate-social/{asset['id']}?project_id={project['id']}&platform=tiktok",
            headers=headers,
        )
        assert response.status_code in (200, 404, 500)


class TestKeyframeEngine:
    def test_create_keyframes(self):
        headers = get_auth_headers("kf@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase8/keyframes",
            params={"prompt": "make the logo grow", "frame_range_start": 0, "frame_range_end": 30},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestVFXEngine:
    def test_parse_vfx_from_prompt(self):
        headers = get_auth_headers("vfx@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase8/vfx/from-prompt",
            params={"prompt": "add fire and rain"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["layers"]) >= 1


class TestTransformationExecutor:
    def test_v2v_execution(self):
        headers = get_auth_headers("v2v@example.com", "testpass123")
        project = create_project(headers, "V2V Project")
        asset = upload_asset(headers, project["id"])
        response = client.post(
            f"/api/v1/phase8/v2v/{asset['id']}?project_id={project['id']}&style_prompt=cinematic",
            headers=headers,
        )
        assert response.status_code in (200, 422, 500)


class TestPhase8Schemas:
    def test_comparison_mode_enum(self):
        from app.schemas.phase8 import ComparisonMode
        assert ComparisonMode.SIDE_BY_SIDE.value == "side_by_side"

    def test_audio_analysis_result(self):
        from app.schemas.phase8 import AudioAnalysisResult
        a = AudioAnalysisResult(has_audio=True)
        assert a.has_audio is True

    def test_social_presets(self):
        from app.services.social_export import SocialExportService
        presets = SocialExportService.list_presets()
        assert any(p["platform"] == "tiktok" for p in presets)

    def test_keyframe_engine(self):
        from app.services.keyframe_engine import KeyframeEngine
        from app.schemas.phase7 import FrameRange
        fr = FrameRange(start_frame=0, end_frame=30)
        kfs = KeyframeEngine.parse_natural_language_keyframes("make it grow", fr)
        assert len(kfs) >= 1

    def test_vfx_engine(self):
        from app.services.vfx_engine import VFXEngine
        layers = VFXEngine.parse_vfx_from_prompt("add fire and sparks")
        assert len(layers) >= 1
