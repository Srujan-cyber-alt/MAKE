"""
Phase 18 Cinema & Generative Production Engine Tests.
"""

import pytest
from tests.conftest import client, get_auth_headers, create_project


class TestProductionEngine:
    def test_create_production(self):
        headers = get_auth_headers("cinema1@example.com", "testpass123")
        project = create_project(headers, "Cinema Test Project")
        brief = {
            "objective": "Create a luxury watch commercial",
            "duration_seconds": 30,
            "aspect_ratio": "16:9",
            "genre": "commercial",
            "tone": "luxury",
            "platform": "youtube",
        }
        response = client.post(
            f"/api/v1/cinema/projects/{project['id']}/cinema/auto",
            json=brief,
            headers=headers,
        )
        assert response.status_code in (200, 201, 422)

    def test_production_templates(self):
        headers = get_auth_headers("cinema2@example.com", "testpass123")
        response = client.get("/api/v1/cinema/templates", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) >= 1

    def test_get_template(self):
        headers = get_auth_headers("cinema3@example.com", "testpass123")
        response = client.get("/api/v1/cinema/templates/product_ad", headers=headers)
        assert response.status_code in (200, 404)

    def test_approval_gate(self):
        headers = get_auth_headers("cinema4@example.com", "testpass123")
        project = create_project(headers, "Approval Test")
        response = client.post(
            f"/api/v1/cinema/projects/{project['id']}/cinema/approve",
            params={"stage": "storyboard", "notes": "Looks good"},
            headers=headers,
        )
        assert response.status_code in (200, 201, 422)

    def test_continuity_check(self):
        headers = get_auth_headers("cinema5@example.com", "testpass123")
        project = create_project(headers, "Continuity Test")
        response = client.get(f"/api/v1/cinema/projects/{project['id']}/cinema/continuity", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "consistent" in data
        assert "score" in data

    def test_quality_score(self):
        headers = get_auth_headers("cinema6@example.com", "testpass123")
        project = create_project(headers, "Quality Test")
        production = {"shots": [{"quality_score": 0.8, "camera": {"movement": "static"}}]}
        response = client.post(
            f"/api/v1/cinema/projects/{project['id']}/cinema/quality",
            json=production,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "dimensions" in data

    def test_shot_plan(self):
        headers = get_auth_headers("cinema7@example.com", "testpass123")
        project = create_project(headers, "Shot Plan Test")
        shot = {
            "shot_id": "shot1",
            "scene_id": "scene1",
            "description": "A person walking through a city",
            "duration_seconds": 5.0,
            "camera": {"movement": "tracking"},
        }
        response = client.post(
            f"/api/v1/cinema/projects/{project['id']}/cinema/shot-plan",
            json={"shot": shot, "production_context": {"brief": {"aspect_ratio": "16:9"}}},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "shot_id" in data
        assert "prompt" in data


class TestProductionServices:
    def test_production_engine_create(self):
        from app.services.production_engine import production_engine
        import asyncio
        result = asyncio.run(production_engine.create_production(
            project_id="proj1",
            user_id="user1",
            brief={"objective": "test", "duration_seconds": 30},
            goal="commercial",
        ))
        assert "production_id" in result
        assert result["status"] == "draft"

    def test_production_graph(self):
        from app.services.production_graph import production_graph
        graph = production_graph.create_graph("prod1")
        assert "graph_id" in graph
        node = production_graph.add_node(graph, "shot", "shot1", {"data": "test"})
        assert node["node_id"] == "shot1"
        production_graph.update_node_status(graph, "shot1", "completed")
        ready = production_graph.get_ready_nodes(graph)
        assert isinstance(ready, list)

    def test_shot_generation_planner(self):
        from app.services.shot_generation_planner import shot_generation_planner
        shot = {
            "shot_id": "s1",
            "scene_id": "sc1",
            "description": "luxury product close-up",
            "duration_seconds": 5.0,
        }
        plan = shot_generation_planner.create_shot_plan(shot, {
            "brief": {"aspect_ratio": "16:9", "resolution": "1920x1080", "tone": "luxury"},
        })
        assert plan["shot_id"] == "s1"
        assert plan["input_mode"] == "text_to_video"
        assert "prompt" in plan

    def test_continuity_engine(self):
        from app.services.continuity_engine import continuity_engine
        shots = [
            {"character_id": "char1", "lighting": "soft"},
            {"character_id": "char1", "lighting": "soft"},
        ]
        result = continuity_engine.validate_shot_continuity(shots, {})
        assert "consistent" in result
        assert "score" in result

    def test_cinematic_quality_score(self):
        from app.services.cinematic_quality_score import cinematic_quality_score
        production = {
            "shots": [{"quality_score": 0.8, "camera": {"movement": "static"}}],
            "qc_report": {},
        }
        result = cinematic_quality_score.score_production(production)
        assert "overall" in result
        assert "dimensions" in result
        assert "passed" in result

    def test_production_templates(self):
        from app.services.production_templates import production_templates
        template = production_templates.get_template("product_ad")
        assert template is not None
        assert template["template_id"] == "product_ad"
        assert template["aspect_ratio"] == "16:9"

    def test_approval_gate(self):
        from app.services.approval_gate import approval_gate
        gate = approval_gate.create_gate("prod1", "storyboard")
        assert gate["stage"] == "storyboard"
        assert gate["status"] == "pending"
        approved = approval_gate.approve(gate, "user1", "Looks good")
        assert approved["status"] == "approved"
        assert approved["decided_by"] == "user1"

    def test_make_auto_cinema_stages(self):
        from app.services.make_auto_cinema import make_auto_cinema
        stages = make_auto_cinema._run_pipeline.__code__.co_varnames
        assert "production" in stages
        assert "graph" in stages
        assert "context" in stages
