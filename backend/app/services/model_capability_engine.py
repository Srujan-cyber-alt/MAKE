"""
Model Capability Engine for MAKE AI Video Phase 16.

Evaluates generation requests against model capabilities.
Implements hard requirement elimination and soft requirement scoring.
"""

from typing import Optional, Dict, List, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from app.services.universal_model_registry import UniversalModelRegistry, ModelInfo, ModelStatus
from app.services.canonical_provider_registry import CanonicalProviderRegistry
from app.providers.base import ProviderCapability

logger = logging.getLogger(__name__)


class RequirementType(str, Enum):
    HARD = "hard"
    SOFT = "soft"


class RequirementCategory(str, Enum):
    MODALITY = "modality"
    INPUT_TYPE = "input_type"
    OUTPUT_TYPE = "output_type"
    DURATION = "duration"
    RESOLUTION = "resolution"
    ASPECT_RATIO = "aspect_ratio"
    REFERENCE_SUPPORT = "reference_support"
    CAMERA_REQUIREMENTS = "camera_requirements"
    MOTION_REQUIREMENTS = "motion_requirements"
    EXTENSION_REQUIREMENTS = "extension_requirements"
    V2V_REQUIREMENTS = "v2v_requirements"
    QUALITY = "quality"
    SPEED = "speed"
    COST = "cost"
    CINEMATIC = "cinematic"
    STABILITY = "stability"
    PROVIDER_PREFERENCE = "provider_preference"
    HISTORICAL_SUCCESS = "historical_success"


@dataclass
class CapabilityRequirement:
    category: RequirementCategory
    requirement_type: RequirementType
    value: Any
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityEvaluationResult:
    model_id: str
    provider_id: str
    compatible: bool
    eliminated_reasons: List[str] = field(default_factory=list)
    soft_scores: Dict[str, float] = field(default_factory=dict)
    total_soft_score: float = 0.0
    hard_requirements_met: int = 0
    total_hard_requirements: int = 0


class ModelCapabilityEngine:
    def __init__(self, model_registry: UniversalModelRegistry, provider_registry: CanonicalProviderRegistry):
        self.model_registry = model_registry
        self.provider_registry = provider_registry

    def extract_requirements(self, request) -> List[CapabilityRequirement]:
        requirements = []
        modality = getattr(request, 'modality', 'video')
        duration = getattr(request, 'duration_seconds', None)
        resolution = getattr(request, 'resolution', None)
        aspect_ratio = getattr(request, 'aspect_ratio', None)
        references = getattr(request, 'references', [])
        camera = getattr(request, 'camera', None)
        motion = getattr(request, 'motion', None)
        quality_mode = getattr(request, 'quality_mode', 'auto')
        routing_mode = getattr(request, 'routing_mode', 'auto')

        requirements.append(CapabilityRequirement(
            category=RequirementCategory.MODALITY,
            requirement_type=RequirementType.HARD,
            value=modality,
            weight=1.0,
        ))

        if duration is not None:
            requirements.append(CapabilityRequirement(
                category=RequirementCategory.DURATION,
                requirement_type=RequirementType.HARD,
                value=duration,
                weight=1.0,
            ))

        if resolution:
            requirements.append(CapabilityRequirement(
                category=RequirementCategory.RESOLUTION,
                requirement_type=RequirementType.HARD,
                value=resolution,
                weight=1.0,
            ))

        if aspect_ratio:
            requirements.append(CapabilityRequirement(
                category=RequirementCategory.ASPECT_RATIO,
                requirement_type=RequirementType.HARD,
                value=aspect_ratio,
                weight=1.0,
            ))

        if references:
            requirements.append(CapabilityRequirement(
                category=RequirementCategory.REFERENCE_SUPPORT,
                requirement_type=RequirementType.HARD,
                value={"count": len(references), "types": [r.get("type", "image") for r in references]},
                weight=1.0,
            ))

        if camera:
            requirements.append(CapabilityRequirement(
                category=RequirementCategory.CAMERA_REQUIREMENTS,
                requirement_type=RequirementType.HARD,
                value=camera,
                weight=1.0,
            ))

        if motion:
            requirements.append(CapabilityRequirement(
                category=RequirementCategory.MOTION_REQUIREMENTS,
                requirement_type=RequirementType.HARD,
                value=motion,
                weight=1.0,
            ))

        if routing_mode != "auto":
            requirements.append(CapabilityRequirement(
                category=RequirementCategory.SPEED,
                requirement_type=RequirementType.SOFT,
                value=routing_mode,
                weight=0.8,
            ))

        if quality_mode in ("quality", "cinematic"):
            requirements.append(CapabilityRequirement(
                category=RequirementCategory.QUALITY if quality_mode == "quality" else RequirementCategory.CINEMATIC,
                requirement_type=RequirementType.SOFT,
                value=quality_mode,
                weight=1.0,
            ))

        return requirements

    def evaluate_model(self, model: ModelInfo, requirements: List[CapabilityRequirement]) -> CapabilityEvaluationResult:
        result = CapabilityEvaluationResult(
            model_id=model.id,
            provider_id=model.provider,
            compatible=True,
        )

        if model.status != ModelStatus.AVAILABLE and model.status != ModelStatus.OPTIONAL:
            result.compatible = False
            result.eliminated_reasons.append(f"Model status is {model.status.value}")

        hard_reqs = [r for r in requirements if r.requirement_type == RequirementType.HARD]
        soft_reqs = [r for r in requirements if r.requirement_type == RequirementType.SOFT]
        result.total_hard_requirements = len(hard_reqs)

        for req in hard_reqs:
            if not self._check_hard_requirement(model, req):
                result.compatible = False
                result.eliminated_reasons.append(
                    f"Hard requirement failed: {req.category.value} = {req.value}"
                )
            else:
                result.hard_requirements_met += 1

        for req in soft_reqs:
            score = self._score_soft_requirement(model, req)
            result.soft_scores[req.category.value] = score
            result.total_soft_score += score * req.weight

        return result

    def evaluate_all_models(self, request) -> List[CapabilityEvaluationResult]:
        requirements = self.extract_requirements(request)
        results = []
        for model in self.model_registry.get_all_models():
            result = self.evaluate_model(model, requirements)
            results.append(result)
        return results

    def get_compatible_models(self, request) -> List[Tuple[ModelInfo, CapabilityEvaluationResult]]:
        results = self.evaluate_all_models(request)
        compatible = []
        for model in self.model_registry.get_all_models():
            for result in results:
                if result.model_id == model.id and result.compatible:
                    compatible.append((model, result))
                    break
        return compatible

    def _check_hard_requirement(self, model: ModelInfo, req: CapabilityRequirement) -> bool:
        category = req.category
        value = req.value

        if category == RequirementCategory.MODALITY:
            modality_capabilities = {
                "video": model.video_support or model.t2v or model.i2v or model.v2v,
                "image": model.image_support,
                "audio": model.audio_support,
                "text": True,
            }
            return modality_capabilities.get(value, False)

        elif category == RequirementCategory.DURATION:
            max_dur = model.limits.max_duration_seconds
            min_dur = model.limits.min_duration_seconds
            if isinstance(value, (int, float)):
                return min_dur <= value <= max_dur
            return False

        elif category == RequirementCategory.RESOLUTION:
            if isinstance(value, tuple) and len(value) == 2:
                w, h = value
                return w <= model.limits.max_width and h <= model.limits.max_height
            return False

        elif category == RequirementCategory.ASPECT_RATIO:
            if isinstance(value, str) and model.limits.supported_aspect_ratios:
                return value in model.limits.supported_aspect_ratios
            return False

        elif category == RequirementCategory.REFERENCE_SUPPORT:
            if isinstance(value, dict):
                count = value.get("count", 0)
                types = value.get("types", [])
                if count > 0 and model.limits.max_reference_images <= 0:
                    return False
                if count > model.limits.max_reference_images:
                    return False
                if "first_frame" in types and not model.first_frame:
                    return False
                if "last_frame" in types and not model.last_frame:
                    return False
                if "image" in types and not model.image_support and not model.i2v:
                    return False
                if "video" in types and not model.video_support and not model.v2v:
                    return False
            return True

        elif category == RequirementCategory.CAMERA_REQUIREMENTS:
            if value and model.camera_control is False:
                return False
            return True

        elif category == RequirementCategory.MOTION_REQUIREMENTS:
            if value and model.motion_control is False:
                return False
            return True

        elif category == RequirementCategory.EXTENSION_REQUIREMENTS:
            if value and model.extension is False:
                return False
            return True

        elif category == RequirementCategory.V2V_REQUIREMENTS:
            if value and model.v2v is False:
                return False
            return True

        return True

    def _score_soft_requirement(self, model: ModelInfo, req: CapabilityRequirement) -> float:
        category = req.category
        value = req.value

        if category == RequirementCategory.QUALITY:
            return model.quality_profile.quality_score if model.quality_profile else 0.5

        elif category == RequirementCategory.SPEED:
            if value == "fast":
                return model.quality_profile.speed_score if model.quality_profile else 0.5
            return 0.5

        elif category == RequirementCategory.COST:
            if value == "cheap":
                return model.quality_profile.cost_score if model.quality_profile else 0.5
            return 0.5

        elif category == RequirementCategory.CINEMATIC:
            return model.quality_profile.cinematic_score if model.quality_profile else 0.5

        elif category == RequirementCategory.STABILITY:
            return model.quality_profile.stability_score if model.quality_profile else 0.5

        elif category == RequirementCategory.HISTORICAL_SUCCESS:
            return model.quality_profile.stability_score if model.quality_profile else 0.5

        return 0.5

    def get_capability_gaps(self, model: ModelInfo, request) -> List[str]:
        requirements = self.extract_requirements(request)
        gaps = []
        for req in requirements:
            if req.requirement_type == RequirementType.HARD and not self._check_hard_requirement(model, req):
                gaps.append(f"{req.category.value}: {req.value}")
        return gaps

    def explain_incompatibility(self, model: ModelInfo, request) -> str:
        requirements = self.extract_requirements(request)
        reasons = []
        for req in requirements:
            if req.requirement_type == RequirementType.HARD and not self._check_hard_requirement(model, req):
                reasons.append(f"Does not support {req.category.value} = {req.value}")
        return "; ".join(reasons) if reasons else "Compatible"
