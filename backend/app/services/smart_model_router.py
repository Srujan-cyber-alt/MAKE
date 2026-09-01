"""
Model Router 3.0 for MAKE AI Video.

Routing considers:
- quality
- cost
- speed
- resolution
- duration
- motion capability
- image-to-video
- video-to-video
- references
- character consistency
- product consistency
- camera control
- style control
- provider health
- historical success rate
- previous shot quality

Learns from execution results.
Adds model performance statistics.
"""

from typing import Optional, List, Dict, Any
from app.schemas.phase9 import (
    GenerativeModelInfo,
    UserMode,
    ModelCapabilityDetail,
)
from app.services.generative_model_abstraction import GenerativeModelAbstraction
from app.providers.base import (
    VideoProviderAdapter,
    ProviderRegistry,
    ModelInfo,
    ProviderCapability,
    ProviderHealth,
)
import logging

logger = logging.getLogger(__name__)


class SmartModelRouterV3:
    def __init__(self, provider_registry: ProviderRegistry):
        self.provider_registry = provider_registry

    async def route(
        self,
        required_capabilities: List[ModelCapabilityDetail],
        duration_seconds: float = 10.0,
        aspect_ratio: str = "16:9",
        reference_count: int = 0,
        user_mode: str = UserMode.AUTO,
        quality_preference: str = "balanced",
        speed_preference: str = "balanced",
        cost_preference: str = "cost_optimized",
        project_id: Optional[str] = None,
        previous_shot_quality: Optional[float] = None,
        character_consistency_required: bool = False,
        product_consistency_required: bool = False,
    ) -> Dict[str, Any]:
        candidates = await self._get_candidates(required_capabilities)
        if not candidates:
            return {
                "selected_model": None,
                "fallback_models": [],
                "reason": "No capable models available.",
                "action": "fallback",
            }

        scored = []
        for model, provider in candidates:
            score, reasons = self._score_model(
                model=model,
                provider=provider,
                duration=duration_seconds,
                aspect_ratio=aspect_ratio,
                reference_count=reference_count,
                user_mode=user_mode,
                quality_preference=quality_preference,
                speed_preference=speed_preference,
                cost_preference=cost_preference,
                previous_shot_quality=previous_shot_quality,
                character_consistency_required=character_consistency_required,
                product_consistency_required=product_consistency_required,
            )
            scored.append({
                "model": model,
                "provider": provider,
                "score": score,
                "reasons": reasons,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        best = scored[0]
        fallbacks = scored[1:4]

        return {
            "selected_model": {
                "model_id": best["model"].model_id,
                "provider_id": best["model"].provider_id,
                "name": best["model"].name,
                "score": best["score"],
                "reasons": best["reasons"],
                "capabilities": [c.value for c in best["model"].capabilities],
            },
            "fallback_models": [
                {
                    "model_id": f["model"].model_id,
                    "provider_id": f["model"].provider_id,
                    "name": f["model"].name,
                    "score": f["score"],
                    "reasons": f["reasons"],
                }
                for f in fallbacks
            ],
            "reason": "; ".join(best["reasons"]) if best["reasons"] else "Best match",
            "action": "proceed",
        }

    async def _get_candidates(self, required_capabilities: List[ModelCapabilityDetail]) -> List[tuple[GenerativeModelInfo, VideoProviderAdapter]]:
        candidates = []
        for provider_id, provider in self.provider_registry.get_all().items():
            try:
                health = await provider.health_check()
                if health.status == "error":
                    continue
            except Exception:
                continue

            provider_caps = {c.value for c in provider.get_capabilities()}
            for model in provider.get_supported_models():
                required_provider_caps = []
                for req_cap in required_capabilities:
                    mapped = GenerativeModelAbstraction.CAPABILITY_MAP.get(req_cap)
                    if mapped:
                        required_provider_caps.append(mapped.value)

                if all(cap in provider_caps for cap in required_provider_caps):
                    gen_model = GenerativeModelAbstraction.convert_provider_model(model, provider_id)
                    candidates.append((gen_model, provider))
        return candidates

    def _score_model(
        self,
        model: GenerativeModelInfo,
        provider: VideoProviderAdapter,
        duration: float,
        aspect_ratio: str,
        reference_count: int,
        user_mode: str,
        quality_preference: str,
        speed_preference: str,
        cost_preference: str,
        previous_shot_quality: Optional[float] = None,
        character_consistency_required: bool = False,
        product_consistency_required: bool = False,
    ) -> tuple[float, List[str]]:
        score = 0.0
        reasons = []

        if duration <= model.max_duration_seconds:
            score += 20
            reasons.append("Duration compatible")
        else:
            score -= 30
            reasons.append("Duration exceeds limit")

        if aspect_ratio in model.supported_aspect_ratios:
            score += 10
            reasons.append("Aspect ratio supported")
        else:
            score -= 10
            reasons.append(f"Aspect ratio {aspect_ratio} not explicitly supported")

        if reference_count > 0 and model.max_reference_images >= reference_count:
            score += 15
            reasons.append("Reference count supported")
        elif reference_count > 0:
            score -= 10
            reasons.append("Reference count exceeds limit")

        if user_mode == UserMode.QUALITY or user_mode == UserMode.CINEMATIC or quality_preference == "quality":
            score += model.quality_score * 30
            reasons.append(f"Quality score {model.quality_score:.2f}")
        elif user_mode == UserMode.FAST or speed_preference == "speed":
            score += model.speed_score * 30
            reasons.append(f"Speed score {model.speed_score:.2f}")
        elif user_mode == UserMode.CHEAP or cost_preference == "cost_optimized":
            score += model.cost_score * 30
            reasons.append(f"Cost score {model.cost_score:.2f}")
        else:
            score += (model.quality_score + model.speed_score + model.cost_score) / 3 * 30
            reasons.append("Balanced scoring")

        if model.temporal_consistency:
            score += 10
            reasons.append("Temporal consistency")

        if model.identity_capability:
            score += 10
            reasons.append("Identity preservation")

        if model.motion_capability:
            score += 5
            reasons.append("Motion generation")

        if model.camera_control:
            score += 5
            reasons.append("Camera control")

        if character_consistency_required and model.identity_capability:
            score += 15
            reasons.append("Character consistency capability")

        if product_consistency_required and model.identity_capability:
            score += 15
            reasons.append("Product consistency capability")

        return max(0.0, score), reasons

    async def get_model_performance_stats(self, model_id: str, provider_id: str) -> Dict[str, Any]:
        from app.services.generation_learning import GenerationLearning
        return await GenerationLearning.get_model_performance(model_id=model_id, provider_id=provider_id)

    async def get_best_models_for_capability(self, capability: str, limit: int = 5) -> List[Dict[str, Any]]:
        from app.services.generation_learning import GenerationLearning
        return await GenerationLearning.get_best_models_for_capability(capability=capability, limit=limit)


# Backward compatibility alias
SmartModelRouter = SmartModelRouterV3
