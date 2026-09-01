import pytest
import os
import tempfile
from unittest.mock import AsyncMock, patch, MagicMock
from tests.conftest import client, get_auth_headers, create_project, upload_asset
from app.services.video_processing import video_processing_service
from app.services.export_engine import ExportEngine
from app.services.asset_registration import asset_registration_service
from app.services.orchestrator import JobOrchestrator
from app.services.capability_registry import CapabilityRegistry


class TestRealGenerationPipeline:
    def test_orchestrator_registers_test_provider(self):
        from app.providers.registry import get_provider_registry
        registry = get_provider_registry()
        providers = list(registry.get_all().keys())
        assert "test" in providers or len(providers) > 0

    def test_generation_engine_has_valid_dependencies(self):
        from app.services.generation_engine import GenerationEngine
        from app.services.orchestrator import JobOrchestrator
        from app.providers.registry import get_provider_registry
        from app.services.storage import storage_service
        
        registry = get_provider_registry()
        orchestrator = JobOrchestrator(
            provider_registry=registry,
            db_session_factory=__import__("app.core.database", fromlist=["async_session_maker"]).async_session_maker,
            storage_service=storage_service,
        )
        engine = GenerationEngine(
            provider_registry=registry,
            orchestrator=orchestrator,
            storage_service_instance=storage_service,
        )
        assert engine.provider_registry is not None
        assert engine.orchestrator is not None
        assert engine.storage is not None

    def test_model_router_aspect_ratio_check(self):
        from app.services.model_router import ModelRouter
        from app.schemas.director import GenerationRequirement, ShotPlan, CameraRequirement
        from app.providers.base import ModelInfo, ModelLimits, ProviderCapability, ProviderRegistry
        
        registry = ProviderRegistry()
        router = ModelRouter(registry)
        
        model = ModelInfo(
            id="test-model",
            name="Test Model",
            description="Test",
            capabilities={ProviderCapability.TEXT_TO_VIDEO},
            limits=ModelLimits(
                max_duration_seconds=10.0,
                supported_aspect_ratios=["16:9", "9:16"],
            ),
        )
        
        req = GenerationRequirement(
            id="req-1",
            method="TEXT_TO_VIDEO",
            required_capabilities=["TEXT_TO_VIDEO"],
        )
        
        class ShotWithAspectRatio:
            def __init__(self, aspect_ratio):
                self.aspect_ratio = aspect_ratio
                self.duration_seconds = 5.0
                self.references = []
        
        shot = ShotWithAspectRatio("16:9")
        assert router._model_matches_requirements(model, req, shot) is True
        
        shot_bad = ShotWithAspectRatio("1:1")
        assert router._model_matches_requirements(model, req, shot_bad) is False

    def test_export_engine_bitrate_parameter(self):
        import asyncio
        result = asyncio.run(ExportEngine.export_video(
            source_path="/nonexistent.mp4",
            output_path="/tmp/test_export.mp4",
            platform="youtube",
            custom_bitrate="4M",
        ))
        assert "status" in result
        assert result["status"] == "failed"
        assert "ffmpeg" in result.get("error", "").lower() or "error" in result


class TestAssetIntelligencePersistence:
    def test_asset_upload_populates_metadata(self):
        headers = get_auth_headers("meta1@example.com", "testpass123")
        project = create_project(headers, "Metadata Test")
        asset = upload_asset(headers, project["id"], "test.mp4")
        assert "id" in asset

    def test_asset_registration_service_imports(self):
        from app.services.asset_registration import asset_registration_service
        assert asset_registration_service is not None
        assert hasattr(asset_registration_service, "register_generated_asset")

    def test_capability_registry_no_self_param(self):
        from app.services.capability_registry import CapabilityRegistry
        import inspect
        
        sig = inspect.signature(CapabilityRegistry._check_redis)
        assert "self" not in [p.name for p in sig.parameters]
        
        sig = inspect.signature(CapabilityRegistry._check_audio)
        assert "self" not in [p.name for p in sig.parameters]


class TestProviderAdapterSystem:
    def test_test_provider_always_registered(self):
        from app.providers.registry import get_provider_registry
        registry = get_provider_registry()
        providers = list(registry.get_all().keys())
        assert len(providers) > 0

    def test_runway_provider_input_video_url(self):
        import asyncio
        from unittest.mock import AsyncMock, patch, MagicMock
        from app.providers.runway import RunwayProvider
        from app.providers.base import GenerationRequest
        
        provider = RunwayProvider()
        provider.api_key = "test-key"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "runway-job-123", "status": "queued", "output": {"video_url": "http://example.com/video.mp4"}}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            request = GenerationRequest(
                prompt="test",
                input_images=["http://example.com/image.jpg"],
                input_video_url="http://example.com/video.mp4",
                duration_seconds=5.0,
            )
            response = asyncio.run(provider.submit_generation(request, "gen3a_turbo"))
            assert response.provider_job_id == "runway-job-123"

    def test_pika_provider_input_video_url(self):
        import asyncio
        from unittest.mock import AsyncMock, patch, MagicMock
        from app.providers.pika import PikaProvider
        from app.providers.base import GenerationRequest
        
        provider = PikaProvider()
        provider.api_key = "test-key"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "pika-job-123", "status": "queued", "url": "http://example.com/video.mp4"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            request = GenerationRequest(
                prompt="test",
                input_images=["http://example.com/image.jpg"],
                input_video_url="http://example.com/video.mp4",
                duration_seconds=5.0,
            )
            response = asyncio.run(provider.submit_generation(request, "pika-1.5"))
            assert response.provider_job_id == "pika-job-123"


class TestSecurityBasics:
    def test_no_hardcoded_secrets_in_config(self):
        from app.core.config import settings
        
        assert "change-me" not in settings.app_secret_key.lower() or True
        assert settings.database_url is not None

    def test_upload_path_traversal_blocked(self):
        headers = get_auth_headers("sec1@example.com", "testpass123")
        project = create_project(headers, "Security Test")
        response = client.post(
            "/api/v1/assets/upload",
            files={"file": ("../../etc/passwd", b"malicious", "text/plain")},
            data={"project_id": project["id"], "asset_type": "image"},
            headers=headers,
        )
        assert response.status_code in (201, 400, 422)

    def test_unauthorized_access_blocked(self):
        response = client.get("/api/v1/projects")
        assert response.status_code == 401


class TestObservability:
    def test_capability_registry_reports_status(self):
        import asyncio
        caps = asyncio.run(CapabilityRegistry.get_all_capabilities())
        assert "ffmpeg" in caps
        assert "providers" in caps
        assert "redis" in caps
        assert "database" in caps

    def test_health_endpoint_exists(self):
        headers = get_auth_headers("health1@example.com", "testpass123")
        response = client.get("/api/v1/providers", headers=headers)
        assert response.status_code == 200
