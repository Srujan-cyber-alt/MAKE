"""
Phase 19 Genesis & Generation Quality Tests.
"""

import pytest
from tests.conftest import client, get_auth_headers, create_project


class TestGenesisEngine:
    def test_genesis_auto(self):
        headers = get_auth_headers("genesis1@example.com", "testpass123")
        project = create_project(headers, "Genesis Test Project")
        brief = {
            "objective": "Create a luxury watch commercial",
            "duration_seconds": 30,
            "aspect_ratio": "16:9",
            "genre": "commercial",
            "tone": "luxury",
            "platform": "youtube",
        }
        response = client.post(
            f"/api/v1/genesis/projects/{project['id']}/genesis/auto",
            json=brief,
            headers=headers,
        )
        assert response.status_code in (200, 201, 422)

    def test_shot_intelligence(self):
        headers = get_auth_headers("genesis2@example.com", "testpass123")
        project = create_project(headers, "Shot Intelligence Test")
        shot = {
            "shot_id": "shot1",
            "scene_id": "scene1",
            "description": "luxury product close-up macro",
            "duration_seconds": 5.0,
        }
        response = client.post(
            f"/api/v1/genesis/projects/{project['id']}/genesis/shot-intelligence",
            json={"shot": shot, "context": {}},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "priority" in data
        assert "difficulty" in data
        assert "risk_score" in data

    def test_reference_classify(self):
        headers = get_auth_headers("genesis3@example.com", "testpass123")
        project = create_project(headers, "Reference Test")
        references = [
            {"type": "character_image", "url": "http://example.com/char.jpg"},
            {"type": "product_image", "url": "http://example.com/prod.jpg"},
            {"type": "character_image", "url": "http://example.com/char2.jpg", "label": "conflict"},
        ]
        response = client.post(
            f"/api/v1/genesis/projects/{project['id']}/genesis/references/classify",
            json=references,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "classified" in data
        assert "conflicts" in data

    def test_artifact_detection(self):
        headers = get_auth_headers("genesis4@example.com", "testpass123")
        project = create_project(headers, "Artifact Test")
        analysis = {
            "face_drift": True,
            "identity_drift": True,
            "temporal_flicker": True,
            "overall_score": 0.4,
        }
        response = client.post(
            f"/api/v1/genesis/projects/{project['id']}/genesis/artifacts/detect",
            json=analysis,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "artifacts" in data
        assert data["total"] >= 1

    def test_genesis_quality_score(self):
        headers = get_auth_headers("genesis5@example.com", "testpass123")
        project = create_project(headers, "Genesis QC Test")
        production = {
            "shots": [{"quality_score": 0.8, "camera": {"movement": "static"}}],
            "qc_report": {},
        }
        response = client.post(
            f"/api/v1/genesis/projects/{project['id']}/genesis/quality/score",
            json=production,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "dimensions" in data

    def test_technical_validate(self):
        headers = get_auth_headers("genesis6@example.com", "testpass123")
        project = create_project(headers, "Technical Validate Test")
        response = client.post(
            f"/api/v1/genesis/projects/{project['id']}/genesis/technical/validate",
            params={"video_path": "/tmp/deterministic.mp4"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "overall_score" in data


class TestGenesisServices:
    def test_generation_reality_layer(self):
        from app.services.generation_reality_layer import generation_reality_layer
        event = generation_reality_layer.create_generation_event("s1", "p1", "sc1", "model", "provider", "prompt", {})
        assert event["status"] == "started"
        event = generation_reality_layer.mark_completed(event, {"asset_id": "a1"}, cost=0.1)
        assert event["status"] == "completed"
        assert event["cost"] == 0.1
        assert event["duration"] is not None

    def test_technical_validator(self):
        from app.services.technical_validator import technical_validator
        import asyncio
        result = asyncio.run(technical_validator.validate("/tmp/deterministic.mp4"))
        assert "valid" in result
        assert "overall_score" in result

    def test_artifact_detector(self):
        from app.services.artifact_detector import artifact_detector
        analysis = {"face_drift": True, "identity_drift": True}
        artifacts = artifact_detector.classify(analysis)
        assert len(artifacts) >= 1
        assert artifacts[0]["type"] == "face_artifact"

    def test_failure_classifier(self):
        from app.services.failure_classifier import failure_classifier
        ft = failure_classifier.classify(None, {"identity_drift": True})
        assert ft.value == "identity_failure"
        ft = failure_classifier.classify(None, {"overall_score": 0.3})
        assert ft.value == "quality_failure"

    def test_repair_planner(self):
        from app.services.repair_planner import repair_planner
        from app.services.failure_classifier import GenerationFailureType
        plan = repair_planner.plan(GenerationFailureType.IDENTITY_FAILURE, "high", {}, {}, 0)
        assert plan["recommended_strategy"] == "add_reference"
        plan2 = repair_planner.plan(GenerationFailureType.QUALITY_FAILURE, "critical", {}, {}, 3)
        assert plan2["recommended_strategy"] == "manual_review"

    def test_shot_intelligence(self):
        from app.services.shot_intelligence import shot_intelligence
        shot = {"shot_id": "s1", "description": "hero macro product close-up", "shot_type": "close_up", "character_id": "c1", "camera": {"movement": "dolly"}}
        result = shot_intelligence.evaluate(shot, {})
        assert result["priority"] == "hero"
        assert result["difficulty"] in ("high", "medium", "low")
        assert result["suggested_variant_count"] >= 1

    def test_budget_intelligence(self):
        from app.services.budget_intelligence import budget_intelligence
        import asyncio
        shots = [
            {"shot_id": "s1", "priority": "hero"},
            {"shot_id": "s2", "priority": "low"},
        ]
        allocation = asyncio.run(budget_intelligence.allocate(shots, 1000.0))
        assert "allocated" in allocation
        assert allocation["allocated"]["s1"]["budget"] > allocation["allocated"]["s2"]["budget"]

    def test_reference_intelligence(self):
        from app.services.reference_intelligence import reference_intelligence
        refs = [
            {"type": "character_image", "url": "http://example.com/a.jpg"},
            {"type": "character_image", "url": "http://example.com/b.jpg", "label": "diff"},
        ]
        classified = reference_intelligence.classify(refs)
        assert len(classified) == 2
        conflicts = reference_intelligence.detect_conflicts(refs)
        assert len(conflicts) >= 1

    def test_genesis_engine_stages(self):
        from app.services.genesis_engine import make_genesis
        import asyncio
        result = asyncio.run(make_genesis.execute(
            user_id="user1",
            project_id="proj1",
            brief={"objective": "test", "duration_seconds": 30},
            goal="commercial",
            mode="balanced",
        ))
        assert "genesis_id" in result
        assert result["status"] == "completed"
        assert "shot_intelligence" in result
        assert "budget_allocation" in result
        assert "generation_results" in result
