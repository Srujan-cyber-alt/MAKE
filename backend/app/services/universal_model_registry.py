"""
Universal Model Registry for MAKE AI Video Phase 16.

Canonical registry for all models with structured metadata.
Reuses existing ModelInfo where possible, extends with Phase 16 requirements.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
from app.providers.base import (
    ModelInfo as LegacyModelInfo,
    ModelLimits as LegacyModelLimits,
    ProviderCapability,
    VideoProviderAdapter,
    ProviderRegistry,
)
from app.providers.base import ModelStatus

logger = logging.getLogger(__name__)


@dataclass
class ModelCapabilityProfile:
    quality_score: float = 0.5
    speed_score: float = 0.5
    cost_score: float = 0.5
    cinematic_score: float = 0.5
    stability_score: float = 0.5
    temporal_consistency: bool = False
    identity_preservation: bool = False
    motion_quality: bool = False


@dataclass
class ModelInfo:
    id: str
    provider: str
    display_name: str
    family: str
    version: str
    modality: str
    capabilities: List[str]
    limits: LegacyModelLimits
    quality_profile: ModelCapabilityProfile = field(default_factory=ModelCapabilityProfile)
    speed_profile: Dict[str, Any] = field(default_factory=dict)
    cost_profile: Dict[str, Any] = field(default_factory=dict)
    availability: ModelStatus = ModelStatus.UNKNOWN
    status: ModelStatus = ModelStatus.UNKNOWN
    health: Dict[str, Any] = field(default_factory=dict)
    input_requirements: Dict[str, Any] = field(default_factory=dict)
    output_requirements: Dict[str, Any] = field(default_factory=dict)
    supported_formats: List[str] = field(default_factory=lambda: ["mp4"])
    supported_resolutions: List[str] = field(default_factory=lambda: ["1920x1080"])
    supported_aspect_ratios: List[str] = field(default_factory=lambda: ["16:9"])
    supported_durations: List[float] = field(default_factory=list)
    reference_limits: Dict[str, Any] = field(default_factory=dict)
    audio_support: bool = False
    image_support: bool = False
    video_support: bool = True
    i2v: bool = False
    t2v: bool = True
    v2v: bool = False
    extension: bool = False
    motion_control: bool = False
    camera_control: bool = False
    first_frame: bool = False
    last_frame: bool = False
    seed: bool = False
    negative_prompt: bool = False
    webhook_support: bool = False
    polling_support: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class UniversalModelRegistry:
    _instance = None

    def __init__(self, provider_registry: ProviderRegistry):
        self.provider_registry = provider_registry
        self._models: Dict[str, ModelInfo] = {}
        self._legacy_map: Dict[str, ModelInfo] = {}
        self._initialize_default_models()

    @classmethod
    def get_instance(cls, provider_registry: ProviderRegistry = None) -> "UniversalModelRegistry":
        if cls._instance is None and provider_registry:
            cls._instance = cls(provider_registry)
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _initialize_default_models(self):
        for provider in self.provider_registry.get_all().values():
            for legacy_model in provider.get_supported_models():
                universal = self._convert_legacy_model(legacy_model, provider.name)
                self._models[universal.id] = universal
                self._legacy_map[legacy_model.id] = universal

    def _convert_legacy_model(self, legacy: LegacyModelInfo, provider_name: str) -> ModelInfo:
        capabilities = [c.value for c in legacy.capabilities] if legacy.capabilities else []
        return ModelInfo(
            id=f"{provider_name}:{legacy.id}",
            provider=provider_name,
            display_name=legacy.name,
            family=legacy.metadata.get("family", "default"),
            version=legacy.metadata.get("version", "1.0"),
            modality="video",
            capabilities=capabilities,
            limits=legacy.limits,
            quality_profile=ModelCapabilityProfile(
                quality_score=legacy.metadata.get("quality_score", 0.5),
                speed_score=legacy.metadata.get("speed_score", 0.5),
                cost_score=legacy.metadata.get("cost_score", 0.5),
                cinematic_score=legacy.metadata.get("cinematic_score", 0.5),
                stability_score=legacy.metadata.get("stability_score", 0.5),
                temporal_consistency=legacy.metadata.get("temporal_consistency", False),
                identity_preservation=legacy.metadata.get("identity_preservation", False),
                motion_quality=legacy.metadata.get("motion_quality", False),
            ),
            speed_profile=legacy.metadata.get("speed_profile", {}),
            cost_profile=legacy.metadata.get("cost_profile", {}),
            availability=ModelStatus.AVAILABLE,
            status=ModelStatus.AVAILABLE,
            supported_formats=getattr(legacy.limits, 'supported_formats', ["mp4"]),
            supported_resolutions=getattr(legacy.limits, 'supported_resolutions', [f"{legacy.limits.max_width}x{legacy.limits.max_height}"]),
            supported_aspect_ratios=legacy.limits.supported_aspect_ratios,
            supported_durations=getattr(legacy.limits, 'supported_durations', []),
            reference_limits={
                "max_reference_images": legacy.limits.max_reference_images,
                "max_input_images": legacy.limits.max_input_images,
            },
            audio_support=getattr(legacy.limits, 'audio_support', False),
            image_support=getattr(legacy.limits, 'image_support', False),
            video_support=getattr(legacy.limits, 'video_support', True),
            i2v=getattr(legacy.limits, 'i2v_support', False) or ProviderCapability.IMAGE_TO_VIDEO.value in capabilities,
            t2v=ProviderCapability.TEXT_TO_VIDEO.value in capabilities,
            v2v=ProviderCapability.VIDEO_TO_VIDEO.value in capabilities,
            extension=ProviderCapability.VIDEO_EXTENSION.value in capabilities,
            motion_control=ProviderCapability.MOTION_GENERATION.value in capabilities,
            camera_control=ProviderCapability.CAMERA_CONTROL.value in capabilities,
            first_frame=False,
            last_frame=False,
            seed=legacy.limits.supports_seed,
            negative_prompt=legacy.limits.supports_negative_prompt,
            webhook_support=False,
            polling_support=True,
            metadata=legacy.metadata,
        )

    def register_model(self, model: ModelInfo):
        self._models[model.id] = model

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(model_id)

    def get_legacy_model(self, legacy_id: str) -> Optional[ModelInfo]:
        return self._legacy_map.get(legacy_id)

    def get_all_models(self) -> List[ModelInfo]:
        return list(self._models.values())

    def get_models_by_provider(self, provider_id: str) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.provider == provider_id]

    def get_models_by_capability(self, capability: str) -> List[ModelInfo]:
        return [m for m in self._models.values() if capability in m.capabilities]

    def get_models_by_modality(self, modality: str) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.modality == modality]

    def get_models_by_status(self, status: ModelStatus) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.status == status]

    def update_model_status(self, model_id: str, status: ModelStatus, health: Dict[str, Any] = None):
        if model_id in self._models:
            self._models[model_id].status = status
            if health:
                self._models[model_id].health = health

    def update_model_availability(self, model_id: str, availability: ModelStatus):
        if model_id in self._models:
            self._models[model_id].availability = availability

    def refresh_from_providers(self):
        self._models.clear()
        self._legacy_map.clear()
        self._initialize_default_models()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "models": [
                {
                    "id": m.id,
                    "provider": m.provider,
                    "display_name": m.display_name,
                    "family": m.family,
                    "version": m.version,
                    "modality": m.modality,
                    "capabilities": m.capabilities,
                    "status": m.status.value,
                    "availability": m.availability.value,
                    "supported_formats": m.supported_formats,
                    "supported_resolutions": m.supported_resolutions,
                    "supported_aspect_ratios": m.supported_aspect_ratios,
                    "supported_durations": m.supported_durations,
                    "seed": m.seed,
                    "negative_prompt": m.negative_prompt,
                    "i2v": m.i2v,
                    "t2v": m.t2v,
                    "v2v": m.v2v,
                    "extension": m.extension,
                    "motion_control": m.motion_control,
                    "camera_control": m.camera_control,
                    "audio_support": m.audio_support,
                    "image_support": m.image_support,
                    "video_support": m.video_support,
                    "reference_limits": m.reference_limits,
                    "quality_profile": {
                        "quality_score": m.quality_profile.quality_score,
                        "speed_score": m.quality_profile.speed_score,
                        "cost_score": m.quality_profile.cost_score,
                        "cinematic_score": m.quality_profile.cinematic_score,
                        "stability_score": m.quality_profile.stability_score,
                        "temporal_consistency": m.quality_profile.temporal_consistency,
                        "identity_preservation": m.quality_profile.identity_preservation,
                        "motion_quality": m.quality_profile.motion_quality,
                    } if m.quality_profile else None,
                    "cost_profile": m.cost_profile,
                    "speed_profile": m.speed_profile,
                }
                for m in self._models.values()
            ]
        }
