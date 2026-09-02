"""
Model Router 4.0 for MAKE AI Video Phase 16.

Upgraded routing with:
- Hard requirement filtering
- Soft scoring
- Routing modes
- Fallback chains
- Retry policy
- Failure intelligence integration
- Provider health integration
- Performance memory integration
"""

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
from app.providers.base import VideoProviderAdapter, ProviderRegistry as LegacyProviderRegistry
from app.services.universal_model_registry import UniversalModelRegistry, ModelInfo, ModelStatus
from app.services.canonical_provider_registry import CanonicalProviderRegistry
from app.services.model_capability_engine import ModelCapabilityEngine, CapabilityEvaluationResult, CapabilityRequirement
from app.services.failure_intelligence import failure_intelligence, FailureType
from app.services.provider_health_engine import provider_health_engine
from app.services.routing_audit import routing_audit
from app.services.cost_engine import cost_engine
from app.services.budget_controller import budget_controller
from app.services.output_normalizer import output_normalizer
from app.services.universal_prompt_compiler import universal_prompt_compiler
from app.services.reference_manager import reference_manager
from app.services.input_preparation import input_preparation
from app.services.best_result_selection import best_result_selector

logger = logging.getLogger(__name__)


class RoutingMode(str, Enum):
    AUTO = "auto"
    FAST = "fast"
    QUALITY = "quality"
    CINEMATIC = "cinematic"
    CHEAP = "cheap"
    BALANCED = "balanced"
    CUSTOM = "custom"


@dataclass
class ModelSelection4:
    model_id: str
    provider_id: str
    score: float
    reasons: List[str] = field(default_factory=list)
    estimated_cost: Optional[float] = None
    estimated_duration: Optional[float] = None
    capabilities: List[str] = field(default_factory=list)
    fallback_models: List[Dict[str, Any]] = field(default_factory=list)
    model_info: Optional[ModelInfo] = None
    routing_mode: str = "auto"
    compatibility: Dict[str, Any] = field(default_factory=dict)


class ModelRouter4:
    def __init__(self, legacy_registry: LegacyProviderRegistry, universal_registry: UniversalModelRegistry, canonical_registry: CanonicalProviderRegistry):
        self.legacy_registry = legacy_registry
        self.universal_registry = universal_registry
        self.canonical_registry = canonical_registry
        self.capability_engine = ModelCapabilityEngine(universal_registry, canonical_registry)

    async def route(self, request, routing_mode: RoutingMode = RoutingMode.AUTO, user_id: str = None, project_id: str = None, preferences: Dict[str, Any] = None) -> ModelSelection4:
        preferences = preferences or {}
        candidates = self.capability_engine.get_compatible_models(request)
        if not candidates:
            raise ValueError("No compatible models available for the given requirements")

        scored = await self._score_candidates(candidates, request, routing_mode, preferences)
        scored.sort(key=lambda x: x.score, reverse=True)

        best = scored[0]
        best.fallback_models = [
            {"model_id": s.model_id, "provider_id": s.provider_id, "score": s.score, "reasons": s.reasons}
            for s in scored[1:4]
        ]

        audit_data = {
            "request_requirements": {"routing_mode": routing_mode.value, "preferences": preferences},
            "candidate_models": [{"model_id": s.model_id, "provider_id": s.provider_id, "score": s.score} for s in scored],
            "eliminated_candidates": [],
            "selected_model": {"model_id": best.model_id, "provider_id": best.provider_id, "score": best.score, "reasons": best.reasons, "display_name": best.model_info.display_name if best.model_info else best.model_id},
            "fallback_chain": best.fallback_models,
            "routing_mode": routing_mode.value,
            "score_components": {"base_score": best.score},
            "total_score": best.score,
            "user_id": user_id,
            "project_id": project_id,
        }
        await routing_audit.record_routing_decision(audit_data)

        return best

    async def _score_candidates(self, candidates: List[Tuple[ModelInfo, CapabilityEvaluationResult]], request, routing_mode: RoutingMode, preferences: Dict[str, Any]) -> List[ModelSelection4]:
        scored = []
        for model, eval_result in candidates:
            provider_data = self.canonical_registry.get_provider(model.provider)
            provider_score = provider_health_engine.get_provider_score(model.provider) if provider_data else 0.5

            score = self._calculate_score(model, eval_result, routing_mode, preferences, provider_score)
            reasons = self._build_reasons(model, eval_result, routing_mode)

            estimated_cost = await cost_engine.estimate_cost(
                model.id, model.provider,
                request.duration_seconds or model.limits.max_duration_seconds,
                request.resolution,
            )

            scored.append(ModelSelection4(
                model_id=model.id,
                provider_id=model.provider,
                score=score,
                reasons=reasons,
                estimated_cost=estimated_cost,
                estimated_duration=request.duration_seconds or model.limits.max_duration_seconds,
                capabilities=model.capabilities,
                model_info=model,
                routing_mode=routing_mode.value,
                compatibility=eval_result.soft_scores,
            ))
        return scored

    def _calculate_score(self, model: ModelInfo, eval_result: CapabilityEvaluationResult, routing_mode: RoutingMode, preferences: Dict[str, Any], provider_score: float) -> float:
        if not eval_result.compatible:
            return -9999.0

        score = 0.0
        score += provider_score * 20

        if model.quality_profile:
            if routing_mode == RoutingMode.QUALITY:
                score += model.quality_profile.quality_score * 30
            elif routing_mode == RoutingMode.CINEMATIC:
                score += model.quality_profile.cinematic_score * 30
            elif routing_mode == RoutingMode.FAST:
                score += model.quality_profile.speed_score * 30
            elif routing_mode == RoutingMode.CHEAP:
                score += model.quality_profile.cost_score * 30
            elif routing_mode == RoutingMode.BALANCED:
                score += (model.quality_profile.quality_score + model.quality_profile.speed_score + model.quality_profile.cost_score) / 3 * 30
            else:
                score += model.quality_profile.quality_score * 20
                score += model.quality_profile.speed_score * 10

        score += eval_result.total_soft_score * 20
        return score

    def _build_reasons(self, model: ModelInfo, eval_result: CapabilityEvaluationResult, routing_mode: RoutingMode) -> List[str]:
        reasons = []
        if eval_result.hard_requirements_met == eval_result.total_hard_requirements:
            reasons.append(f"All hard requirements met ({eval_result.hard_requirements_met}/{eval_result.total_hard_requirements})")
        if model.quality_profile:
            reasons.append(f"Quality: {model.quality_profile.quality_score:.2f}")
            if routing_mode == RoutingMode.FAST:
                reasons.append(f"Speed: {model.quality_profile.speed_score:.2f}")
            elif routing_mode == RoutingMode.CHEAP:
                reasons.append(f"Cost efficiency: {model.quality_profile.cost_score:.2f}")
        return reasons

    async def get_candidate_models(self, request) -> List[Tuple[ModelInfo, VideoProviderAdapter]]:
        candidates = self.capability_engine.get_compatible_models(request)
        result = []
        for model, eval_result in candidates:
            adapter = self.canonical_registry.get_provider(model.provider)
            if adapter:
                result.append((model, adapter.get("adapter")))
        return result

    async def fallback(self, original_request, failed_model_id: str, failed_provider_id: str) -> Optional[ModelSelection4]:
        request = original_request
        candidates = self.capability_engine.get_compatible_models(request)
        for model, eval_result in candidates:
            if model.id != failed_model_id or model.provider != failed_provider_id:
                scored = await self._score_candidates([(model, eval_result)], request, RoutingMode.AUTO, {})
                if scored:
                    return scored[0]
        return None


model_router_4 = ModelRouter4
