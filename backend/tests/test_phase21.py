"""
Phase 21 MAKE ONE Tests.
"""

import pytest
from tests.conftest import client, get_auth_headers, create_project


class TestMakeOne:
    def test_make_one_generate(self):
        headers = get_auth_headers("one1@example.com", "testpass123")
        project = create_project(headers, "MakeOne Test Project")
        response = client.post(
            f"/api/v1/make-one/projects/{project['id']}/make-one",
            json={"prompt": "Create a cinematic product commercial"},
            headers=headers,
        )
        assert response.status_code in (200, 201, 422)

    def test_make_one_edit(self):
        headers = get_auth_headers("one2@example.com", "testpass123")
        project = create_project(headers, "MakeOne Edit Test")
        response = client.post(
            f"/api/v1/make-one/projects/{project['id']}/make-one",
            json={"prompt": "Edit this video to be more cinematic"},
            headers=headers,
        )
        assert response.status_code in (200, 201, 422)

    def test_make_one_cancel(self):
        headers = get_auth_headers("one3@example.com", "testpass123")
        project = create_project(headers, "MakeOne Cancel Test")
        response = client.post(
            f"/api/v1/make-one/projects/{project['id']}/make-one/one123/cancel",
            headers=headers,
        )
        assert response.status_code == 200

    def test_make_one_retry(self):
        headers = get_auth_headers("one4@example.com", "testpass123")
        project = create_project(headers, "MakeOne Retry Test")
        response = client.post(
            f"/api/v1/make-one/projects/{project['id']}/make-one/one123/retry",
            headers=headers,
        )
        assert response.status_code == 200


class TestMakeOneServices:
    def test_make_one_service(self):
        from app.services.make_one import make_one
        import asyncio
        result = asyncio.run(make_one.execute(
            user_id="user1",
            project_id="proj1",
            prompt="Create a luxury watch commercial",
            mode="auto",
        ))
        assert "one_id" in result
        assert "status" in result
        assert "results" in result

    def test_make_one_clarification(self):
        from app.services.make_one import make_one
        import asyncio
        result = asyncio.run(make_one.execute(
            user_id="user1",
            project_id="proj1",
            prompt="",
            mode="auto",
        ))
        assert result["status"] == "awaiting_clarification"
        assert "clarification_questions" in result

    def test_make_one_integration(self):
        from app.services.make_one import make_one
        from app.services.universal_command_engine import UniversalCommandEngine
        parsed = UniversalCommandEngine.parse("Create a cinematic sneaker commercial")
        plan = UniversalCommandEngine.to_execution_plan(parsed)
        assert plan["status"] == "ready"
        assert "execution_steps" in plan
