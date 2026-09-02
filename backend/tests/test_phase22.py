"""
Phase 22 Competitive & Dominance Tests.
"""

import pytest
from tests.conftest import client, get_auth_headers, create_project


class TestCompetitive:
    def test_competitive_gaps(self):
        headers = get_auth_headers("comp1@example.com", "testpass123")
        response = client.get("/api/v1/competitive/competitive/gaps", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "gaps" in data
        assert "summary" in data

    def test_capability_matrix(self):
        headers = get_auth_headers("comp2@example.com", "testpass123")
        response = client.get("/api/v1/competitive/competitive/matrix", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "make" in data

    def test_benchmark_cases(self):
        headers = get_auth_headers("comp3@example.com", "testpass123")
        response = client.get("/api/v1/competitive/benchmark/cases", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "cases" in data
        assert len(data["cases"]) >= 1

    def test_benchmark_summary(self):
        headers = get_auth_headers("comp4@example.com", "testpass123")
        response = client.get("/api/v1/competitive/benchmark/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data


class TestCompetitiveServices:
    def test_gap_engine(self):
        from app.services.competitive_gap_engine import competitive_gap_engine
        make_cap = {"name": "text_to_video", "status": "requires_external_provider"}
        comp_cap = {"name": "text_to_video", "status": "implemented"}
        gap = competitive_gap_engine.analyze_gap(make_cap, comp_cap)
        assert gap["gap"] == "not_comparable"

    def test_capability_matrix(self):
        from app.services.competitive_capability_matrix import competitive_capability_matrix
        matrix = competitive_capability_matrix.build_matrix()
        assert "make" in matrix
        assert "higgsfield" in matrix

    def test_benchmark_cases(self):
        from app.services.competitor_benchmark import competitor_benchmark
        cases = competitor_benchmark.get_benchmark_cases(50)
        assert len(cases) >= 1
        assert all("case_id" in c for c in cases)

    def test_benchmark_summary(self):
        from app.services.competitor_benchmark import competitor_benchmark
        results = [
            {"overall_score": 0.8},
            {"overall_score": 0.9},
            {"overall_score": 0.7},
        ]
        summary = competitor_benchmark.summarize_results(results)
        assert summary["avg_score"] == pytest.approx(0.8)
        assert summary["pass_rate"] == pytest.approx(1.0)

    def test_extended_camera_controls(self):
        from app.services.camera_control_engine import CameraControlEngine
        camera = CameraControlEngine.parse_natural_language("cinematic anamorphic lens, vertigo dolly zoom, arc movement, slow push in")
        assert camera.lens == "anamorphic"
        assert camera.vertigo is True
        assert camera.arc is True
        assert camera.push_in is True
        assert camera.sensor_look == "cinematic"

    def test_product_integrity(self):
        from app.services.product_system import ProductSystem
        import asyncio
        result = asyncio.run(ProductSystem.validate_product_integrity("prod1", {
            "geometry": {"shape": "box"},
            "logo_detected": True,
            "color_drift": False,
        }))
        assert "consistent" in result
        assert "issues" in result

    def test_world_lock(self):
        from app.services.world_system import WorldSystem
        import asyncio
        lock = asyncio.run(WorldSystem.create_world_lock("world1"))
        assert "error" in lock or lock.get("locked") is True
