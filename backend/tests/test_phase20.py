"""
Phase 20 Model Lab Tests.
"""

import pytest
from tests.conftest import client, get_auth_headers, create_project


class TestModelLab:
    def test_create_benchmark(self):
        headers = get_auth_headers("lab1@example.com", "testpass123")
        response = client.post("/api/v1/model-lab/benchmarks", headers=headers)
        assert response.status_code in (200, 201)

    def test_list_benchmarks(self):
        headers = get_auth_headers("lab2@example.com", "testpass123")
        response = client.get("/api/v1/model-lab/benchmarks", headers=headers)
        assert response.status_code == 200

    def test_run_benchmark(self):
        headers = get_auth_headers("lab3@example.com", "testpass123")
        response = client.post("/api/v1/model-lab/benchmarks/bench1/run", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "results" in data

    def test_evaluate_benchmark(self):
        headers = get_auth_headers("lab4@example.com", "testpass123")
        response = client.get("/api/v1/model-lab/benchmarks/bench1/evaluate", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "evaluated_cases" in data

    def test_leaderboard(self):
        headers = get_auth_headers("lab5@example.com", "testpass123")
        response = client.get("/api/v1/model-lab/leaderboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data

    def test_routing_simulate(self):
        headers = get_auth_headers("lab6@example.com", "testpass123")
        response = client.post("/api/v1/model-lab/routing/simulate", json={"task_type": "text_to_video"}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_model_card(self):
        headers = get_auth_headers("lab7@example.com", "testpass123")
        response = client.get("/api/v1/model-lab/models/test_model", params={"provider_id": "test_provider"}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "model_id" in data
        assert "confidence" in data


class TestModelLabServices:
    def test_benchmark_definition(self):
        from app.services.benchmark_definition import benchmark_definition, BenchmarkCase
        cases = BenchmarkCase.get_standard_cases()
        assert len(cases) >= 1
        benchmark = benchmark_definition.create("test", "desc", "general", cases, ["m1"], ["p1"])
        assert benchmark["benchmark_id"]
        assert benchmark["status"] == "created"
        assert benchmark["test_case_count"] == len(cases)

    def test_benchmark_runner(self):
        from app.services.benchmark_runner import benchmark_runner
        import asyncio
        benchmark = {
            "benchmark_id": "b1",
            "cases": [
                {
                    "case_id": "c1",
                    "task_type": "text_to_video",
                    "prompt": "test prompt",
                    "duration_seconds": 5.0,
                    "aspect_ratio": "16:9",
                    "resolution": "1920x1080",
                }
            ],
            "models": ["test_model"],
            "providers": ["test_provider"],
        }
        result = asyncio.run(benchmark_runner.run_benchmark(benchmark, "user1", "proj1"))
        assert result["benchmark_id"] == "b1"
        assert "results" in result
        assert "summary" in result

    def test_benchmark_evaluator(self):
        from app.services.benchmark_evaluator import benchmark_evaluator
        case_result = {
            "case_id": "c1",
            "task_type": "text_to_video",
            "results": [
                {
                    "generation_id": "g1",
                    "model": "m1",
                    "provider": "p1",
                    "status": "completed",
                    "quality_score": {"overall": 0.8, "technical": 0.9, "visual": 0.8, "temporal": 0.85},
                    "technical_validation": {"overall_score": 0.9},
                    "cost": 0.1,
                    "duration": 5.0,
                }
            ],
        }
        evaluated = benchmark_evaluator.evaluate_case(case_result)
        assert "evaluated_results" in evaluated
        assert "best_result" in evaluated
        assert evaluated["best_result"]["model"] == "m1"

    def test_model_leaderboard(self):
        import asyncio
        from app.services.model_leaderboard import model_leaderboard
        lb = asyncio.run(model_leaderboard.build_leaderboard("general", 5))
        assert isinstance(lb, list)
        card = asyncio.run(model_leaderboard.get_model_card("test_model", "test_provider"))
        assert "model_id" in card
        assert "confidence" in card

    def test_routing_benchmark(self):
        from app.services.routing_benchmark import routing_benchmark
        import asyncio
        result = asyncio.run(routing_benchmark.simulate({"task_type": "text_to_video"}))
        assert "status" in result

    def test_benchmark_case_generation(self):
        from app.services.benchmark_definition import BenchmarkCase, BenchmarkTaskType
        case = BenchmarkCase.create(
            task_type=BenchmarkTaskType.CINEMATIC,
            prompt="cinematic product hero shot",
            style="luxury",
            quality_target=0.8,
        )
        assert case["task_type"] == "cinematic"
        assert case["style"] == "luxury"
        assert case["quality_target"] == 0.8

    def test_benchmark_definition_status(self):
        from app.services.benchmark_definition import BenchmarkDefinition, BenchmarkStatus
        bd = BenchmarkDefinition.create("test", "desc", "general", [], ["m1"], ["p1"])
        assert bd["status"] == BenchmarkStatus.CREATED
