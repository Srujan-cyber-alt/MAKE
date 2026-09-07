from tests.conftest import client, get_auth_headers, create_project


class TestHealth:
    def test_health(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_readiness(self):
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

    def test_liveness(self):
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200


class TestAuth:
    def test_register(self):
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User",
        })
        assert response.status_code == 201

    def test_register_duplicate_email(self):
        client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "testpass123"})
        response = client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "testpass123"})
        assert response.status_code == 400

    def test_login(self):
        client.post("/api/v1/auth/register", json={"email": "login@example.com", "password": "testpass123"})
        response = client.post("/api/v1/auth/token", data={"username": "login@example.com", "password": "testpass123"})
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_invalid_password(self):
        response = client.post("/api/v1/auth/token", data={"username": "wrong@example.com", "password": "wrong"})
        assert response.status_code == 401

    def test_protected_endpoint(self):
        headers = get_auth_headers(email="protected@example.com", password="testpass123")
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200


class TestProjects:
    def test_create_project(self):
        headers = get_auth_headers(email="create@example.com", password="testpass123")
        response = client.post("/api/v1/projects", json={"name": "My Project"}, headers=headers)
        assert response.status_code == 201
        assert response.json()["name"] == "My Project"

    def test_list_projects(self):
        headers = get_auth_headers(email="list@example.com", password="testpass123")
        client.post("/api/v1/projects", json={"name": "Project 1"}, headers=headers)
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_project(self):
        headers = get_auth_headers(email="get@example.com", password="testpass123")
        project = create_project(headers=headers, name="Get Project")
        response = client.get(f"/api/v1/projects/{project['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == project["id"]

    def test_get_project_not_found(self):
        headers = get_auth_headers(email="getnf@example.com", password="testpass123")
        response = client.get("/api/v1/projects/nonexistent-id", headers=headers)
        assert response.status_code == 404

    def test_update_project(self):
        headers = get_auth_headers(email="update@example.com", password="testpass123")
        project = create_project(headers=headers, name="Old Name")
        response = client.patch(f"/api/v1/projects/{project['id']}", json={"name": "New Name"}, headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_delete_project(self):
        headers = get_auth_headers(email="delete@example.com", password="testpass123")
        project = create_project(headers=headers, name="Delete Me")
        response = client.delete(f"/api/v1/projects/{project['id']}", headers=headers)
        assert response.status_code == 204


class TestAssets:
    def test_upload_asset(self):
        headers = get_auth_headers(email="upload@example.com", password="testpass123")
        project = create_project(headers=headers, name="Upload Project")
        response = client.post(
            "/api/v1/assets/upload",
            files={"file": ("test.mp4", b"fake video content", "video/mp4")},
            data={"project_id": project["id"], "asset_type": "video"},
            headers=headers,
        )
        assert response.status_code == 201

    def test_list_assets_empty(self):
        headers = get_auth_headers(email="listassets@example.com", password="testpass123")
        project = create_project(headers=headers, name="Asset Project")
        response = client.get(f"/api/v1/assets/project/{project['id']}", headers=headers)
        assert response.status_code == 200

    def test_delete_asset(self):
        headers = get_auth_headers(email="delasset@example.com", password="testpass123")
        project = create_project(headers=headers, name="Del Asset Project")
        response = client.post(
            "/api/v1/assets/upload",
            files={"file": ("del.mp4", b"fake video content", "video/mp4")},
            data={"project_id": project["id"], "asset_type": "video"},
            headers=headers,
        )
        asset_id = response.json()["id"]
        response = client.delete(f"/api/v1/assets/{asset_id}", headers=headers)
        assert response.status_code == 204


class TestJobs:
    def test_create_job(self):
        headers = get_auth_headers(email="createjob@example.com", password="testpass123")
        project = create_project(headers=headers, name="Job Project")
        response = client.post("/api/v1/jobs", json={"project_id": project["id"], "prompt": "test video", "job_type": "text_to_video"}, headers=headers)
        assert response.status_code == 201

    def test_list_jobs_empty(self):
        headers = get_auth_headers(email="listjobs@example.com", password="testpass123")
        response = client.get("/api/v1/jobs", headers=headers)
        assert response.status_code == 200

    def test_cancel_job(self):
        headers = get_auth_headers(email="deljob@example.com", password="testpass123")
        project = create_project(headers=headers, name="Del Job Project")
        response = client.post("/api/v1/jobs", json={"project_id": project["id"], "prompt": "test video", "job_type": "text_to_video"}, headers=headers)
        job_id = response.json()["id"]
        response = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
        assert response.status_code == 200


class TestVersions:
    def test_create_version(self):
        headers = get_auth_headers(email="version@example.com", password="testpass123")
        project = create_project(headers=headers, name="Version Project")
        response = client.post(f"/api/v1/projects/{project['id']}/versions", json={"name": "v1"}, headers=headers)
        assert response.status_code == 201

    def test_list_versions(self):
        headers = get_auth_headers(email="listver@example.com", password="testpass123")
        project = create_project(headers=headers, name="List Ver Project")
        client.post(f"/api/v1/projects/{project['id']}/versions", json={"name": "v1"}, headers=headers)
        response = client.get(f"/api/v1/projects/{project['id']}/versions", headers=headers)
        assert response.status_code == 200

    def test_restore_version(self):
        headers = get_auth_headers(email="restore@example.com", password="testpass123")
        project = create_project(headers=headers, name="Restore Project")
        response = client.post(f"/api/v1/projects/{project['id']}/versions", json={"name": "v1"}, headers=headers)
        assert response.status_code == 201
        version_id = response.json()["id"]
        response = client.post(f"/api/v1/projects/versions/{version_id}/restore", headers=headers)
        assert response.status_code == 200


class TestReferences:
    def test_add_reference(self):
        headers = get_auth_headers(email="addref@example.com", password="testpass123")
        project = create_project(headers=headers, name="Ref Project")
        asset_response = client.post(
            "/api/v1/assets/upload",
            files={"file": ("ref.mp4", b"fake ref content", "video/mp4")},
            data={"project_id": project["id"], "asset_type": "reference"},
            headers=headers,
        )
        assert asset_response.status_code == 201
        asset_id = asset_response.json()["id"]
        response = client.post(f"/api/v1/projects/{project['id']}/references", json={"asset_id": asset_id, "role": "character"}, headers=headers)
        assert response.status_code == 201

    def test_list_references(self):
        headers = get_auth_headers(email="listref@example.com", password="testpass123")
        project = create_project(headers=headers, name="List Ref Project")
        asset_response = client.post(
            "/api/v1/assets/upload",
            files={"file": ("ref.mp4", b"fake ref content", "video/mp4")},
            data={"project_id": project["id"], "asset_type": "reference"},
            headers=headers,
        )
        asset_id = asset_response.json()["id"]
        client.post(f"/api/v1/projects/{project['id']}/references", json={"asset_id": asset_id, "role": "character"}, headers=headers)
        response = client.get(f"/api/v1/projects/{project['id']}/references", headers=headers)
        assert response.status_code == 200


class TestContext:
    def test_update_and_get_context(self):
        headers = get_auth_headers(email="ctx@example.com", password="testpass123")
        project = create_project(headers=headers, name="Context Project")
        client.post(f"/api/v1/projects/{project['id']}/context", json={"context": {"key": "value"}}, headers=headers)
        response = client.get(f"/api/v1/projects/{project['id']}/context", headers=headers)
        assert response.status_code == 200
        assert response.json()["context"]["key"] == "value"


class TestTimelines:
    def test_create_timeline(self):
        headers = get_auth_headers(email="timeline@example.com", password="testpass123")
        project = create_project(headers=headers, name="Timeline Project")
        response = client.post(f"/api/v1/timelines/{project['id']}", json={"name": "Main", "tracks": []}, headers=headers)
        assert response.status_code == 201

    def test_list_timelines(self):
        headers = get_auth_headers(email="listtl@example.com", password="testpass123")
        project = create_project(headers=headers, name="List TL Project")
        client.post(f"/api/v1/timelines/{project['id']}", json={"name": "Main", "tracks": []}, headers=headers)
        response = client.get(f"/api/v1/timelines/{project['id']}", headers=headers)
        assert response.status_code == 200


class TestSecurity:
    def test_cross_user_project_access(self):
        headers1 = get_auth_headers(email="sec1@example.com", password="testpass123")
        headers2 = get_auth_headers(email="sec2@example.com", password="testpass123")
        project = create_project(headers=headers1, name="Secret Project")
        response = client.get(f"/api/v1/projects/{project['id']}", headers=headers2)
        assert response.status_code == 404

    def test_cross_user_asset_access(self):
        headers1 = get_auth_headers(email="sec3@example.com", password="testpass123")
        headers2 = get_auth_headers(email="sec4@example.com", password="testpass123")
        project = create_project(headers=headers1, name="Asset Secret")
        response = client.post(
            "/api/v1/assets/upload",
            files={"file": ("secret.mp4", b"fake secret content", "video/mp4")},
            data={"project_id": project["id"], "asset_type": "video"},
            headers=headers1,
        )
        asset_id = response.json()["id"]
        response = client.get(f"/api/v1/assets/{asset_id}", headers=headers2)
        assert response.status_code == 404

    def test_unauthenticated_access(self):
        response = client.get("/api/v1/projects")
        assert response.status_code == 401


class TestGenerationWorkflow:
    def test_generation_endpoint_validation(self):
        headers = get_auth_headers(email="genval@example.com", password="testpass123")
        response = client.post("/api/v1/generation", json={}, headers=headers)
        assert response.status_code == 422

    def test_generation_with_provider_model(self):
        headers = get_auth_headers(email="genprov@example.com", password="testpass123")
        project = create_project(headers=headers, name="Gen Project")
        response = client.post("/api/v1/generation?project_id=" + project["id"], json={"prompt": "test", "provider": "test", "model": "test"}, headers=headers)
        assert response.status_code == 201


class TestProviderRegistry:
    def test_list_providers(self):
        headers = get_auth_headers(email="prov@example.com", password="testpass123")
        response = client.get("/api/v1/providers", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_provider_capabilities(self):
        headers = get_auth_headers(email="provcap@example.com", password="testpass123")
        response = client.get("/api/v1/providers", headers=headers)
        providers = response.json()
        test_provider = next((p for p in providers if p["name"] == "test-provider"), None)
        assert test_provider is not None

    def test_provider_status(self):
        headers = get_auth_headers(email="provstat@example.com", password="testpass123")
        response = client.get("/api/v1/providers", headers=headers)
        providers = response.json()
        for p in providers:
            assert "name" in p
            assert "api_base" in p

    def test_provider_registry_initialization(self):
        from app.providers.registry import get_provider_registry
        registry = get_provider_registry()
        assert registry is not None
        providers = registry.get_all()
        assert len(providers) >= 1

    def test_provider_health_check(self):
        headers = get_auth_headers(email="provhealth@example.com", password="testpass123")
        response = client.get("/api/v1/providers", headers=headers)
        providers = response.json()
        for p in providers:
            assert "capabilities" in p
            assert isinstance(p["capabilities"], list)


class TestModelInfo:
    def test_get_model_info(self):
        headers = get_auth_headers(email="modelinfo@example.com", password="testpass123")
        response = client.get("/api/v1/providers", headers=headers)
        assert response.status_code == 200

    def test_model_capabilities(self):
        headers = get_auth_headers(email="modelcap@example.com", password="testpass123")
        response = client.get("/api/v1/providers", headers=headers)
        providers = response.json()
        assert any("capabilities" in p for p in providers)

    def test_model_types(self):
        headers = get_auth_headers(email="modeltypes@example.com", password="testpass123")
        response = client.get("/api/v1/providers", headers=headers)
        providers = response.json()
        assert len(providers) >= 1


class TestCommandInterpreter:
    def test_trim_command(self):
        headers = get_auth_headers(email="cmd@example.com", password="testpass123")
        project = create_project(headers=headers, name="Cmd Project")
        response = client.post("/api/v1/editing/execute?project_id=" + project["id"], json={"command": "trim 0:05 to 0:10"}, headers=headers)
        assert response.status_code == 200
        assert "operations" in response.json() or "job_id" in response.json()

    def test_cut_command(self):
        headers = get_auth_headers(email="cut@example.com", password="testpass123")
        project = create_project(headers=headers, name="Cut Project")
        response = client.post("/api/v1/editing/execute?project_id=" + project["id"], json={"command": "cut at 0:15"}, headers=headers)
        assert response.status_code == 200

    def test_concatenate_command(self):
        headers = get_auth_headers(email="concat@example.com", password="testpass123")
        project = create_project(headers=headers, name="Concat Project")
        response = client.post("/api/v1/editing/execute?project_id=" + project["id"], json={"command": "concatenate clips"}, headers=headers)
        assert response.status_code == 200

    def test_unsupported_command(self):
        headers = get_auth_headers(email="unsup@example.com", password="testpass123")
        project = create_project(headers=headers, name="Unsup Project")
        response = client.post("/api/v1/editing/execute?project_id=" + project["id"], json={"command": "fly to moon"}, headers=headers)
        assert response.status_code == 200

    def test_command_with_context(self):
        headers = get_auth_headers(email="ctxcmd@example.com", password="testpass123")
        project = create_project(headers=headers, name="Ctx Cmd Project")
        response = client.post("/api/v1/editing/execute?project_id=" + project["id"], json={"command": "trim 0:05 to 0:10", "context": {"timeline": 1}}, headers=headers)
        assert response.status_code == 200

    def test_empty_command(self):
        headers = get_auth_headers(email="emptycmd@example.com", password="testpass123")
        project = create_project(headers=headers, name="Empty Cmd Project")
        response = client.post("/api/v1/editing/execute?project_id=" + project["id"], json={"command": ""}, headers=headers)
        assert response.status_code == 200

    def test_command_confidence(self):
        headers = get_auth_headers(email="conf@example.com", password="testpass123")
        project = create_project(headers=headers, name="Conf Project")
        response = client.post("/api/v1/editing/execute?project_id=" + project["id"], json={"command": "trim 0:05 to 0:10"}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "confidence" in data or "job_id" in data
        if "confidence" in data:
            assert 0 <= data["confidence"] <= 1


class TestVideoProvider:
    def test_generate_video(self):
        headers = get_auth_headers(email="genvideo@example.com", password="testpass123")
        project = create_project(headers=headers, name="Video Gen Project")
        response = client.post("/api/v1/generation?project_id=" + project["id"], json={"prompt": "test video", "provider": "test", "model": "test"}, headers=headers)
        assert response.status_code == 201

    def test_generation_status(self):
        headers = get_auth_headers(email="genstat@example.com", password="testpass123")
        project = create_project(headers=headers, name="Gen Status Project")
        response = client.post("/api/v1/generation?project_id=" + project["id"], json={"prompt": "test", "provider": "test", "model": "test"}, headers=headers)
        job_id = response.json()["id"]
        response = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert response.status_code == 200

    def test_list_generations(self):
        headers = get_auth_headers(email="listgen@example.com", password="testpass123")
        response = client.get("/api/v1/jobs", headers=headers)
        assert response.status_code == 200

    def test_cancel_generation(self):
        headers = get_auth_headers(email="cancelgen@example.com", password="testpass123")
        project = create_project(headers=headers, name="Cancel Gen Project")
        response = client.post("/api/v1/generation?project_id=" + project["id"], json={"prompt": "test", "provider": "test", "model": "test"}, headers=headers)
        job_id = response.json()["id"]
        response = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
        assert response.status_code == 200

    def test_provider_integration(self):
        headers = get_auth_headers(email="provint@example.com", password="testpass123")
        response = client.get("/api/v1/providers", headers=headers)
        assert response.status_code == 200
        providers = response.json()
        assert any(p["name"] == "test-provider" for p in providers)
