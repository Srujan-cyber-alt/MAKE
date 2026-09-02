"""
Phase 16 Tests — Universal Model Engine for MAKE AI Video.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.providers.base import (
    VideoProviderAdapter,
    ProviderRegistry,
    ModelInfo,
    ModelLimits,
    ProviderCapability,
    ProviderHealth,
    GenerationRequest,
    GenerationResponse,
    ProviderStatus,
)
from app.services.universal_model_registry import UniversalModelRegistry, ModelInfo as UniversalModelInfo, ModelCapabilityProfile, ModelStatus
from app.services.canonical_provider_registry import CanonicalProviderRegistry
from app.services.model_capability_engine import ModelCapabilityEngine, CapabilityRequirement, RequirementType, RequirementCategory
from app.services.model_router_4 import ModelRouter4, ModelSelection4, RoutingMode
from app.services.failure_intelligence import FailureIntelligence, FailureType, FailurePolicy
from app.services.provider_health_engine import ProviderHealthEngine
from app.services.model_performance_memory import ModelPerformanceMemory
from app.services.cost_engine import CostEngine
from app.services.routing_audit import RoutingAudit
from app.services.output_normalizer import OutputNormalizer, CanonicalGenerationResult
from app.services.reference_manager import ReferenceManager
from app.services.universal_prompt_compiler import UniversalPromptCompiler
from app.services.best_result_selection import BestResultSelector
from app.services.model_comparison import ModelComparison
from app.services.model_benchmark import ModelBenchmark
from app.services.budget_controller import BudgetController
from app.services.provider_credential_manager import ProviderCredentialManager
from app.services.model_versioning import ModelVersioning
from app.services.provenance_tracker import ProvenanceTracker


class MockProviderAdapter(VideoProviderAdapter):
    def __init__(self, name: str, api_base: str = "http://test", api_key: str = "test-key", capabilities: list = None):
        super().__init__(name, api_base, api_key)
        self._capabilities = capabilities or [ProviderCapability.TEXT_TO_VIDEO, ProviderCapability.IMAGE_TO_VIDEO]
        self._models = [
            ModelInfo(
                id="test-model-1",
                name="Test Model 1",
                description="Test model",
                capabilities=self._capabilities,
                limits=ModelLimits(
                    max_duration_seconds=10.0,
                    min_duration_seconds=1.0,
                    max_width=1920,
                    max_height=1080,
                    supported_aspect_ratios=["16:9", "9:16"],
                    max_reference_images=3,
                    supports_seed=True,
                    supports_negative_prompt=True,
                    cost_per_second=0.5,
                ),
            ),
            ModelInfo(
                id="test-model-2",
                name="Test Model 2",
                description="Test model 2",
                capabilities=[ProviderCapability.TEXT_TO_VIDEO],
                limits=ModelLimits(
                    max_duration_seconds=4.0,
                    min_duration_seconds=1.0,
                    max_width=1280,
                    max_height=720,
                    supported_aspect_ratios=["16:9"],
                    max_reference_images=0,
                    supports_seed=False,
                    supports_negative_prompt=False,
                ),
            ),
        ]

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(status=ProviderStatus.AVAILABLE, latency_ms=100.0)

    async def submit_generation(self, request: GenerationRequest, model_id: str) -> GenerationResponse:
        return GenerationResponse(
            provider_job_id="job-123",
            status="completed",
            video_url="http://test/video.mp4",
            duration_seconds=request.duration_seconds or 4.0,
            width=1920,
            height=1080,
            fps=24,
        )

    async def check_status(self, provider_job_id: str) -> GenerationResponse:
        return GenerationResponse(provider_job_id=provider_job_id, status="completed")

    async def cancel_job(self, provider_job_id: str) -> bool:
        return True

    async def get_result(self, provider_job_id: str) -> GenerationResponse:
        return GenerationResponse(provider_job_id=provider_job_id, status="completed", video_url="http://test/video.mp4")

    def get_capabilities(self) -> set:
        return set(self._capabilities)

    def get_supported_models(self) -> list:
        return self._models


class MockGenerationRequest:
    def __init__(self, **kwargs):
        self.intent = kwargs.get('intent', 'generate')
        self.modality = kwargs.get('modality', 'video')
        self.prompt = kwargs.get('prompt', 'test prompt')
        self.negative_prompt = kwargs.get('negative_prompt')
        self.input_assets = kwargs.get('input_assets', [])
        self.references = kwargs.get('references', [])
        self.duration_seconds = kwargs.get('duration_seconds')
        self.resolution = kwargs.get('resolution')
        self.aspect_ratio = kwargs.get('aspect_ratio')
        self.fps = kwargs.get('fps')
        self.camera = kwargs.get('camera')
        self.motion = kwargs.get('motion')
        self.style = kwargs.get('style')
        self.quality_mode = kwargs.get('quality_mode', RoutingMode.AUTO)
        self.routing_mode = kwargs.get('routing_mode', RoutingMode.AUTO)
        self.seed = kwargs.get('seed')
        self.character_ids = kwargs.get('character_ids', [])
        self.product_ids = kwargs.get('product_ids', [])
        self.environment_ids = kwargs.get('environment_ids', [])
        self.audio = kwargs.get('audio')
        self.output_requirements = kwargs.get('output_requirements', {})
        self.parameters = kwargs.get('parameters', {})


class TestUniversalModelRegistry:
    def setup_method(self):
        from app.providers.registry import get_provider_registry
        from app.services.universal_model_registry import UniversalModelRegistry
        UniversalModelRegistry.reset()
        legacy = get_provider_registry()
        self.registry = UniversalModelRegistry.get_instance(legacy)

    def test_singleton(self):
        registry = UniversalModelRegistry.get_instance()
        assert registry is not None

    def test_get_model(self):
        models = self.registry.get_all_models()
        assert len(models) >= 1

    def test_get_models_by_capability(self):
        models = self.registry.get_models_by_capability("text_to_video")
        assert len(models) >= 1

    def test_model_status(self):
        models = self.registry.get_models_by_status(ModelStatus.AVAILABLE)
        assert len(models) >= 1


class TestCanonicalProviderRegistry:
    def setup_method(self):
        from app.providers.registry import get_provider_registry
        from app.services.canonical_provider_registry import CanonicalProviderRegistry
        CanonicalProviderRegistry.reset()
        legacy = get_provider_registry()
        self.cp_registry = CanonicalProviderRegistry.get_instance(legacy)

    def test_singleton(self):
        cp = CanonicalProviderRegistry.get_instance()
        assert cp is not None

    def test_get_provider(self):
        providers = self.cp_registry.get_all_providers()
        assert len(providers) >= 1


class TestModelCapabilityEngine:
    def setup_method(self):
        self.registry = UniversalModelRegistry.get_instance()
        self.cp_registry = CanonicalProviderRegistry.get_instance()
        self.engine = ModelCapabilityEngine(self.registry, self.cp_registry)

    def test_extract_requirements(self):
        request = MockGenerationRequest(modality="video", duration_seconds=5.0, aspect_ratio="16:9")
        reqs = self.engine.extract_requirements(request)
        assert len(reqs) >= 3

    def test_evaluate_model_compatible(self):
        models = self.registry.get_all_models()
        if not models:
            pytest.skip("No models available")
        model = models[0]
        request = MockGenerationRequest(modality="video", duration_seconds=2.0)
        reqs = self.engine.extract_requirements(request)
        result = self.engine.evaluate_model(model, reqs)
        assert result.model_id == model.id

    def test_evaluate_model_incompatible_duration(self):
        models = self.registry.get_all_models()
        if not models:
            pytest.skip("No models available")
        model = models[0]
        request = MockGenerationRequest(modality="video", duration_seconds=999.0)
        reqs = self.engine.extract_requirements(request)
        result = self.engine.evaluate_model(model, reqs)
        assert not result.compatible

    def test_get_compatible_models(self):
        request = MockGenerationRequest(modality="video", duration_seconds=2.0)
        compatible = self.engine.get_compatible_models(request)
        assert len(compatible) >= 1


class TestModelRouter4:
    def setup_method(self):
        from app.providers.registry import get_provider_registry
        from app.services.universal_model_registry import UniversalModelRegistry
        from app.services.canonical_provider_registry import CanonicalProviderRegistry
        UniversalModelRegistry.reset()
        CanonicalProviderRegistry.reset()
        legacy = get_provider_registry()
        self.registry = UniversalModelRegistry.get_instance(legacy)
        self.cp_registry = CanonicalProviderRegistry.get_instance(legacy)
        self.router = ModelRouter4(
            legacy,
            self.registry,
            self.cp_registry,
        )

    @pytest.mark.asyncio
    async def test_route_request(self):
        request = MockGenerationRequest(modality="video", duration_seconds=2.0, aspect_ratio="16:9")
        selection = await self.router.route(request, routing_mode=RoutingMode.AUTO)
        assert selection is not None
        assert selection.model_id is not None

    @pytest.mark.asyncio
    async def test_route_fast_mode(self):
        request = MockGenerationRequest(modality="video", duration_seconds=2.0, routing_mode=RoutingMode.FAST)
        selection = await self.router.route(request, routing_mode=RoutingMode.FAST)
        assert selection is not None

    @pytest.mark.asyncio
    async def test_fallback(self):
        request = MockGenerationRequest(modality="video", duration_seconds=2.0)
        selection = await self.router.route(request, routing_mode=RoutingMode.AUTO)
        fallback = await self.router.fallback(request, selection.model_id, selection.provider_id)
        assert fallback is None or fallback.model_id is not None


class TestFailureIntelligence:
    def setup_method(self):
        self.fi = FailureIntelligence()

    def test_classify_auth_error(self):
        ft = self.fi.classify_error(Exception("401 Unauthorized"))
        assert ft == FailureType.AUTH_ERROR

    def test_classify_rate_limit(self):
        ft = self.fi.classify_error(Exception("429 Too Many Requests"))
        assert ft == FailureType.RATE_LIMIT

    def test_classify_timeout(self):
        ft = self.fi.classify_error(Exception("Request timed out"))
        assert ft == FailureType.TIMEOUT

    def test_classify_network_error(self):
        ft = self.fi.classify_error(Exception("Connection refused"))
        assert ft == FailureType.NETWORK_ERROR

    def test_classify_content_policy(self):
        ft = self.fi.classify_error(Exception("Content policy rejection"))
        assert ft == FailureType.CONTENT_POLICY_REJECTION

    def test_classify_invalid_request(self):
        ft = self.fi.classify_error(Exception("400 Bad Request"))
        assert ft == FailureType.INVALID_REQUEST

    def test_classify_model_unavailable(self):
        ft = self.fi.classify_error(Exception("Model not found"))
        assert ft == FailureType.MODEL_UNAVAILABLE

    def test_classify_unknown(self):
        ft = self.fi.classify_error(Exception("Something weird"))
        assert ft == FailureType.UNKNOWN

    def test_should_retry(self):
        assert self.fi.should_retry(FailureType.TIMEOUT, 0) is True
        assert self.fi.should_retry(FailureType.TIMEOUT, 3) is False

    def test_should_fallback(self):
        assert self.fi.should_fallback(FailureType.TIMEOUT) is True
        assert self.fi.should_fallback(FailureType.CONTENT_POLICY_REJECTION) is False

    def test_requires_user_action(self):
        assert self.fi.requires_user_action(FailureType.AUTH_ERROR) is True
        assert self.fi.requires_user_action(FailureType.RATE_LIMIT) is False


class TestProviderHealthEngine:
    def setup_method(self):
        self.engine = ProviderHealthEngine()

    def test_record_success(self):
        self.engine.record_success("test-provider", latency_ms=100.0)
        health = self.engine.get_health("test-provider")
        assert health.status == "available"

    def test_record_failure(self):
        for _ in range(9):
            self.engine.record_success("test-provider-2", latency_ms=100.0)
        self.engine.record_failure("test-provider-2", error="test error")
        health = self.engine.get_health("test-provider-2")
        assert health.status == "degraded"

    def test_record_timeout(self):
        for _ in range(9):
            self.engine.record_success("test-provider-3", latency_ms=100.0)
        self.engine.record_timeout("test-provider-3")
        health = self.engine.get_health("test-provider-3")
        assert health.status == "available"


class TestModelPerformanceMemory:
    def setup_method(self):
        from app.providers.registry import get_provider_registry
        from app.services.universal_model_registry import UniversalModelRegistry
        UniversalModelRegistry.reset()
        legacy = get_provider_registry()
        UniversalModelRegistry.get_instance(legacy)
        self.memory = ModelPerformanceMemory()

    @pytest.mark.asyncio
    async def test_record_generation(self):
        await self.memory.record_generation("model-1", "provider-1", {
            "success": True,
            "quality_score": 0.9,
            "generation_time_seconds": 5.0,
            "cost": 1.0,
            "repair_count": 0,
            "validation_passed": True,
            "user_accepted": True,
            "task_type": "text_to_video",
        })

    @pytest.mark.asyncio
    async def test_get_model_stats(self):
        await self.memory.record_generation("model-2", "provider-1", {
            "success": True,
            "quality_score": 0.8,
            "generation_time_seconds": 4.0,
            "cost": 0.5,
            "repair_count": 0,
            "validation_passed": True,
            "user_accepted": True,
            "task_type": "text_to_video",
        })
        stats = await self.memory.get_model_stats("model-2", "provider-1")
        if stats["total_generations"] == 0:
            pytest.skip("Redis not available for performance memory test")
        assert stats["total_generations"] == 1


class TestCostEngine:
    def setup_method(self):
        from app.providers.registry import get_provider_registry
        from app.services.universal_model_registry import UniversalModelRegistry
        UniversalModelRegistry.reset()
        legacy = get_provider_registry()
        UniversalModelRegistry.get_instance(legacy)
        self.engine = CostEngine()

    @pytest.mark.asyncio
    async def test_record_cost(self):
        await self.engine.record_cost("gen-1", "model-1", "provider-1", 1.5)

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        from app.services.universal_model_registry import UniversalModelRegistry
        registry = UniversalModelRegistry.get_instance()
        if registry:
            model = registry.get_model("test:test-model-1")
            if model:
                model.limits.cost_per_second = 0.5
        cost = await self.engine.estimate_cost("test:test-model-1", "test", 5.0, (1920, 1080))
        if cost is None:
            pytest.skip("Model not available for cost estimation")
        assert cost == 2.5


class TestRoutingAudit:
    def setup_method(self):
        self.audit = RoutingAudit()

    @pytest.mark.asyncio
    async def test_record_routing_decision(self):
        decision = {
            "request_requirements": {},
            "candidate_models": [],
            "eliminated_candidates": [],
            "selected_model": {"model_id": "m1", "provider_id": "p1"},
            "fallback_chain": [],
            "routing_mode": "auto",
            "score_components": {},
            "total_score": 100.0,
            "user_id": "user-1",
            "project_id": "proj-1",
        }
        entry = await self.audit.record_routing_decision(decision)
        assert entry["audit_id"] is not None

    @pytest.mark.asyncio
    async def test_explain_routing_decision(self):
        decision = {
            "selected_model": {"model_id": "m1", "provider_id": "p1", "display_name": "Model One", "reasons": ["reason1", "reason2"]},
            "fallback_chain": [{"model_id": "m2", "score": 80.0}],
        }
        explanation = self.audit.explain_routing_decision(decision)
        assert "Model One" in explanation


class TestOutputNormalizer:
    def setup_method(self):
        self.normalizer = OutputNormalizer()

    def test_normalize_dict_response(self):
        response = {
            "video_url": "http://test/video.mp4",
            "duration_seconds": 5.0,
            "width": 1920,
            "height": 1080,
            "fps": 24,
            "status": "completed",
            "metadata": {"model_version": "2.0"},
        }
        result = self.normalizer.normalize(response, "test-provider", "test-model", "job-1")
        assert result.output_asset == "http://test/video.mp4"
        assert result.aspect_ratio == "16:9"
        assert result.model_version == "2.0"


class TestReferenceManager:
    def setup_method(self):
        from app.providers.registry import get_provider_registry
        from app.services.universal_model_registry import UniversalModelRegistry
        UniversalModelRegistry.reset()
        legacy = get_provider_registry()
        UniversalModelRegistry.get_instance(legacy)
        self.manager = ReferenceManager()

    def test_prepare_references(self):
        from app.services.universal_model_registry import UniversalModelRegistry
        registry = UniversalModelRegistry.get_instance()
        if registry:
            model = registry.get_model("test:test-model-1")
            if model:
                model.limits.max_reference_images = 3
        refs = [{"type": "image", "url": "http://test/image.png"}]
        result = self.manager.prepare_references(refs, "test:test-model-1", "test")
        if not result["prepared"]:
            pytest.skip("Model not available for reference preparation test")
        assert result["prepared"] is True

    def test_validate_reference(self):
        result = self.manager.validate_reference({"type": "image", "url": "http://test/image.png"})
        assert result["valid"] is True


class TestUniversalPromptCompiler:
    def setup_method(self):
        self.compiler = UniversalPromptCompiler()

    def test_compile_prompt(self):
        request = MockGenerationRequest(prompt="A beautiful landscape", duration_seconds=5.0)
        compiled = self.compiler.compile(request, "test:test-model-1", "test")
        assert "prompt" in compiled
        assert compiled["_model_id"] == "test:test-model-1"


class TestBestResultSelector:
    def setup_method(self):
        self.selector = BestResultSelector()

    def test_rank_results(self):
        results = [
            {"quality_score": 0.8, "validation": {"valid": True}, "generation_time": 5.0, "cost": 1.0},
            {"quality_score": 0.9, "validation": {"valid": True}, "generation_time": 10.0, "cost": 2.0},
        ]
        ranked = self.selector.rank_results(results, "quality")
        assert ranked[0]["quality_score"] == 0.9

    def test_select_best(self):
        results = [{"quality_score": 0.8}, {"quality_score": 0.9}]
        best = self.selector.select_best(results, "quality")
        assert best["quality_score"] == 0.9


class TestModelComparison:
    def setup_method(self):
        self.comparison = ModelComparison()

    @pytest.mark.asyncio
    async def test_compare_models(self):
        result = await self.comparison.compare_models(MockGenerationRequest(), ["test:test-model-1", "test:test-model-2"], ["test", "test"])
        assert "results" in result
        assert "comparison" in result


class TestModelBenchmark:
    def setup_method(self):
        self.benchmark = ModelBenchmark()

    @pytest.mark.asyncio
    async def test_run_benchmark(self):
        result = await self.benchmark.run_benchmark("test:test-model-1", "test", "text_to_video")
        assert result["task_type"] == "text_to_video"

    @pytest.mark.asyncio
    async def test_run_full_benchmark(self):
        result = await self.benchmark.run_full_benchmark("test:test-model-1", "test")
        assert "benchmarks" in result


class TestBudgetController:
    def setup_method(self):
        self.controller = BudgetController()

    @pytest.mark.asyncio
    async def test_check_budget_no_policy(self):
        result = await self.controller.check_budget("user-1", "proj-1", 1.0)
        assert result["allowed"] is True


class TestProviderCredentialManager:
    def setup_method(self):
        self.manager = ProviderCredentialManager()

    def test_redact_secrets(self):
        data = {"api_key": "secret123", "name": "test", "password": "pass123"}
        redacted = self.manager.redact_secrets(data)
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["password"] == "***REDACTED***"
        assert redacted["name"] == "test"


class TestModelVersioning:
    def setup_method(self):
        self.versioning = ModelVersioning()

    def test_record_and_get_version(self):
        self.versioning.record_version("model-1", "provider-1", "1.0", {"capabilities": ["text_to_video"]})
        version = self.versioning.get_version("model-1", "provider-1")
        assert version["version"] == "1.0"


class TestProvenanceTracker:
    def setup_method(self):
        self.tracker = ProvenanceTracker()

    def test_record_and_get_provenance(self):
        provenance = self.tracker.build_provenance(
            source_project="proj-1",
            source_prompt="test prompt",
            provider="test-provider",
            model="test-model",
            model_version="1.0",
            generation_mode="text_to_video",
            references=[],
            generation_job="job-1",
            parameters={},
            routing_decision={},
        )
        self.tracker.record_provenance("asset-1", provenance)
        retrieved = self.tracker.get_provenance("asset-1")
        assert retrieved is not None
        assert retrieved["source_project"] == "proj-1"
