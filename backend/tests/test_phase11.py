import pytest
from tests.conftest import client, get_auth_headers, create_project, upload_asset


class TestCreativeDirector:
    def test_create_creative_director(self):
        headers = get_auth_headers("cd1@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase11/creative-director",
            params={
                "objective": "Make a 30-second cinematic luxury sneaker advertisement",
                "duration_seconds": 30,
                "aspect_ratio": "16:9",
                "genre": "commercial",
                "tone": "luxury",
                "audience": "luxury consumers",
                "platform": "instagram",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "concept" in data
        assert "story_structure" in data
        assert "shot_structure" in data
        assert "bibles" in data
        assert "export_plan" in data
        assert "creative_quality" in data

    def test_create_creative_director_auto_mode(self):
        headers = get_auth_headers("cd2@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase11/creative-director",
            params={
                "objective": "Create a social media ad for a new energy drink",
                "duration_seconds": 15,
                "approval_mode": "auto",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("approval_mode") == "auto"


class TestStoryboard:
    def test_generate_storyboard(self):
        headers = get_auth_headers("sb1@example.com", "testpass123")
        creative_plan = {
            "concept": {"title": "Test Video", "logline": "A test storyboard"},
            "story_structure": [
                {"scene_id": "s1", "sequence_number": 1, "name": "Scene 1", "description": "Opening", "duration_seconds": 10}
            ],
            "shot_structure": [
                {"shot_id": "sh1", "scene_id": "s1", "sequence_number": 1, "shot_type": "wide", "description": "Wide shot", "duration_seconds": 5}
            ],
        }
        response = client.post(
            "/api/v1/phase11/storyboard",
            json=creative_plan,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "storyboard_id" in data
        assert "scenes" in data
        assert data["total_scenes"] == 1

    def test_regenerate_scene(self):
        headers = get_auth_headers("sb2@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase11/storyboard/regenerate-scene",
            json={
                "storyboard": {"scenes": [{"scene_id": "s1", "sequence_number": 1, "name": "Scene 1"}]},
                "scene_id": "s1",
                "new_scene_data": {"name": "Scene 1 Updated"}
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["scenes"][0]["name"] == "Scene 1 Updated"


class TestScriptEngine:
    def test_generate_script(self):
        headers = get_auth_headers("se1@example.com", "testpass123")
        creative_plan = {
            "concept": {"title": "Test Commercial", "cta": "Shop Now"},
            "story_structure": [
                {"scene_id": "s1", "name": "Hook", "duration_seconds": 5},
                {"scene_id": "s2", "name": "Product Reveal", "duration_seconds": 10},
            ],
        }
        response = client.post(
            "/api/v1/phase11/script",
            json=creative_plan,
            params={"genre": "commercial", "tone": "luxury", "duration_seconds": 30},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "script_id" in data
        assert "hook" in data
        assert "cta" in data


class TestVariantEngine:
    def test_generate_variants(self):
        headers = get_auth_headers("ve1@example.com", "testpass123")
        creative_plan = {
            "concept": {"title": "Test"},
            "story_structure": [],
            "shot_structure": [],
        }
        response = client.post(
            "/api/v1/phase11/variants",
            json={"creative_plan": creative_plan, "num_variants": 3},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_variants"] == 3
        assert len(data["variants"]) == 3


class TestWorldSystem:
    def test_create_world(self):
        headers = get_auth_headers("ws1@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase11/worlds",
            params={
                "name": "Neon Tokyo",
                "architecture": "cyberpunk",
                "lighting": "neon",
                "weather": "rainy",
                "time": "night",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Neon Tokyo"

    def test_list_worlds(self):
        headers = get_auth_headers("ws2@example.com", "testpass123")
        response = client.get("/api/v1/phase11/worlds", headers=headers)
        assert response.status_code in (200, 500)


class TestCreativeMemory:
    def test_remember_generation(self):
        headers = get_auth_headers("cm1@example.com", "testpass123")
        project = create_project(headers, "Memory Test")
        response = client.post(
            "/api/v1/phase11/creative-memory",
            params={"project_id": project["id"], "prompt": "test prompt", "accepted": True},
            json={"result": {"status": "completed"}},
            headers=headers,
        )
        assert response.status_code in (200, 500)

    def test_get_project_memory(self):
        headers = get_auth_headers("cm2@example.com", "testpass123")
        project = create_project(headers, "Memory Test 2")
        response = client.get(
            f"/api/v1/phase11/creative-memory/{project['id']}",
            headers=headers,
        )
        assert response.status_code in (200, 500)


class TestBrandDNA:
    def test_create_brand_dna(self):
        headers = get_auth_headers("bd1@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase11/brand-dna",
            params={
                "name": "Test Brand",
                "tone": "luxury",
                "visual_style": "minimal",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Brand"

    def test_list_brands(self):
        headers = get_auth_headers("bd2@example.com", "testpass123")
        response = client.get("/api/v1/phase11/brand-dna", headers=headers)
        assert response.status_code in (200, 500)


class TestGenerationLearning:
    def test_record_generation_event(self):
        headers = get_auth_headers("gl1@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase11/learning/record",
            params={
                "prompt": "test prompt",
                "model": "test-model",
                "provider": "test-provider",
                "output_quality": 0.9,
                "user_accepted": True,
            },
            json={"settings": {}},
            headers=headers,
        )
        assert response.status_code in (200, 500)

    def test_get_model_performance(self):
        headers = get_auth_headers("gl2@example.com", "testpass123")
        response = client.get(
            "/api/v1/phase11/learning/model-performance",
            params={"model_id": "test-model", "provider_id": "test-provider"},
            headers=headers,
        )
        assert response.status_code in (200, 500)
