import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from app.schemas.director import GenerationRequirement, ShotPlan
from app.providers.base import (
    VideoProviderAdapter,
    ProviderRegistry,
    ModelInfo,
    ModelLimits,
    ProviderCapability,
    ProviderHealth,
)


@dataclass
class ModelSelection:
    provider_id: str
    model_id: str
    score: float
    reasons: List[str] = field(default_factory=list)
    estimated_cost: Optional[float] = None
    estimated_duration: Optional[float] = None
    capabilities: List[str] = field(default_factory=list)
    fallback_models: List[Dict[str, Any]] = field(default_factory=list)
    model_info: Optional[ModelInfo] = None


class ModelRouter:
    CAPABILITY_MAP = {
        "TEXT_TO_VIDEO": ProviderCapability.TEXT_TO_VIDEO,
        "IMAGE_TO_VIDEO": ProviderCapability.IMAGE_TO_VIDEO,
        "VIDEO_TO_VIDEO": ProviderCapability.VIDEO_TO_VIDEO,
        "REFERENCE_GENERATION": ProviderCapability.REFERENCE_IMAGES,
        "GENERATIVE_TRANSFORMATION": ProviderCapability.MOTION_GENERATION,
    }

    def __init__(self, provider_registry: ProviderRegistry):
        self.provider_registry = provider_registry

    async def route(
        self,
        generation_requirement: GenerationRequirement,
        shot: ShotPlan,
        preferences: Dict[str, Any] = None,
    ) -> ModelSelection:
        preferences = preferences or {}
        candidates = await self._get_candidate_models(generation_requirement, shot)
        if not candidates:
            raise ValueError("No available models match the generation requirements")

        scored = await self._score_candidates(candidates, generation_requirement, shot, preferences)
        scored.sort(key=lambda x: x.score, reverse=True)

        best = scored[0]
        best.fallback_models = [
            {"provider_id": s.provider_id, "model_id": s.model_id, "score": s.score, "reasons": s.reasons}
            for s in scored[1:4]
        ]
        return best

    async def _get_candidate_models(
        self, requirement: GenerationRequirement, shot: ShotPlan
    ) -> List[tuple[VideoProviderAdapter, ModelInfo]]:
        candidates = []
        providers = self.provider_registry.get_all().values()

        for provider in providers:
            try:
                health = await provider.health_check()
                if health.status == "error":
                    continue
            except Exception:
                continue

            for model in provider.get_supported_models():
                if self._model_matches_requirements(model, requirement, shot):
                    candidates.append((provider, model))

        return candidates

    def _model_matches_requirements(
        self, model: ModelInfo, requirement: GenerationRequirement, shot: ShotPlan
    ) -> bool:
        required_capabilities = set(requirement.required_capabilities)
        model_capabilities = {c.value for c in model.capabilities}

        for req_cap in required_capabilities:
            cap = self.CAPABILITY_MAP.get(req_cap)
            if cap and cap.value not in model_capabilities:
                return False

        if requirement.method == "IMAGE_TO_VIDEO":
            if ProviderCapability.IMAGE_TO_VIDEO.value not in model_capabilities:
                return False

        if requirement.method == "VIDEO_TO_VIDEO":
            if ProviderCapability.VIDEO_TO_VIDEO.value not in model_capabilities:
                return False

        if requirement.method == "TEXT_TO_VIDEO":
            if ProviderCapability.TEXT_TO_VIDEO.value not in model_capabilities:
                return False

        duration = shot.duration_seconds if shot else 0
        if duration > 0:
            if duration < model.limits.min_duration_seconds or duration > model.limits.max_duration_seconds:
                return False

        aspect_ratio = shot.aspect_ratio if shot and hasattr(shot, 'aspect_ratio') else None
        if aspect_ratio and model.limits.supported_aspect_ratios:
            if aspect_ratio not in model.limits.supported_aspect_ratios:
                return False

        return True

    async def _score_candidates(
        self,
        candidates: List[tuple[VideoProviderAdapter, ModelInfo]],
        generation_requirement: GenerationRequirement,
        shot: ShotPlan,
        preferences: Dict[str, Any],
    ) -> List[ModelSelection]:
        scored = []
        quality_pref = preferences.get("quality_preference", "balanced")
        speed_pref = preferences.get("speed_preference", "balanced")
        cost_pref = preferences.get("cost_preference", "balanced")

        for provider, model in candidates:
            score = 0.0
            reasons = []

            required_caps = set(generation_requirement.required_capabilities)
            model_caps = {c.value for c in model.capabilities}
            for cap in required_caps:
                mapped = self.CAPABILITY_MAP.get(cap)
                if mapped and mapped.value in model_caps:
                    score += 30
                    reasons.append(f"Supports {cap}")

            duration = shot.duration_seconds if shot else 0
            if duration > 0 and duration <= model.limits.max_duration_seconds:
                score += 20
                reasons.append("Duration compatible")

            if model.limits.supported_aspect_ratios:
                score += 10
                reasons.append("Aspect ratio supported")

            if model.limits.max_reference_images > 0 and shot.references:
                score += 15
                reasons.append("Supports references")

            try:
                health = await provider.health_check()
            except Exception:
                health = ProviderHealth(status="error")

            if health.status == "active":
                score += 10
                reasons.append("Provider healthy")
            elif health.status == "degraded":
                score += 5
                reasons.append("Provider degraded")
            else:
                score -= 50
                reasons.append("Provider unavailable")

            if model.limits.cost_per_second is not None:
                estimated_cost = model.limits.cost_per_second * duration
                if cost_pref == "cost_optimized" and estimated_cost == 0:
                    score += 20
                    reasons.append("Free model")
                elif cost_pref == "quality" and estimated_cost > 0:
                    score += 10
                    reasons.append("Premium quality")
            else:
                estimated_cost = None

            scored.append(ModelSelection(
                provider_id=provider.name,
                model_id=model.id,
                score=score,
                reasons=reasons,
                estimated_cost=estimated_cost,
                estimated_duration=duration,
                capabilities=[c.value for c in model.capabilities],
                model_info=model,
            ))

        return scored
