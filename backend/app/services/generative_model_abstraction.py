from typing import Optional, List, Dict, Any
from app.schemas.phase9 import (
    GenerativeModelInfo,
    ModelCapabilityDetail,
)
from app.providers.base import (
    VideoProviderAdapter,
    ProviderRegistry,
    ModelInfo,
    ModelLimits,
    ProviderCapability,
    ProviderHealth,
)
import logging

logger = logging.getLogger(__name__)


class GenerativeModelAbstraction:
    CAPABILITY_MAP = {
        ModelCapabilityDetail.TEXT_TO_VIDEO: ProviderCapability.TEXT_TO_VIDEO,
        ModelCapabilityDetail.IMAGE_TO_VIDEO: ProviderCapability.IMAGE_TO_VIDEO,
        ModelCapabilityDetail.VIDEO_TO_VIDEO: ProviderCapability.VIDEO_TO_VIDEO,
        ModelCapabilityDetail.VIDEO_EXTENSION: ProviderCapability.VIDEO_EXTENSION,
        ModelCapabilityDetail.REFERENCE_IMAGE: ProviderCapability.REFERENCE_IMAGES,
        ModelCapabilityDetail.CHARACTER_CONSISTENCY: ProviderCapability.IDENTITY_PRESERVATION,
        ModelCapabilityDetail.PRODUCT_CONSISTENCY: ProviderCapability.IDENTITY_PRESERVATION,
        ModelCapabilityDetail.MOTION_TRANSFER: ProviderCapability.MOTION_GENERATION,
        ModelCapabilityDetail.CAMERA_CONTROL: ProviderCapability.CAMERA_CONTROL,
        ModelCapabilityDetail.STYLE_TRANSFER: ProviderCapability.STYLE_TRANSFER,
        ModelCapabilityDetail.INPAINTING: ProviderCapability.INPAINTING,
        ModelCapabilityDetail.OUTPAINTING: ProviderCapability.OUTPAINTING,
        ModelCapabilityDetail.UPSCALE: ProviderCapability.UPSCALING,
        ModelCapabilityDetail.LIP_SYNC: ProviderCapability.FACE_ANIMATION,
        ModelCapabilityDetail.AUDIO_GENERATION: ProviderCapability.MUTE_AUDIO,
        ModelCapabilityDetail.IMAGE_GENERATION: ProviderCapability.IMAGE_GENERATION,
    }

    @staticmethod
    def convert_provider_model(model: ModelInfo, provider_id: str) -> GenerativeModelInfo:
        capabilities = []
        for cap in ModelCapabilityDetail:
            mapped = GenerativeModelAbstraction.CAPABILITY_MAP.get(cap)
            if mapped and mapped in model.capabilities:
                capabilities.append(cap)

        quality_score = getattr(model, "quality_score", 0.0) or 0.0
        speed_score = getattr(model, "speed_score", 0.0) or 0.0
        cost_per_sec = getattr(model.limits, "cost_per_second", None)
        cost_score = 0.0
        if cost_per_sec is not None:
            cost_score = max(0.0, 1.0 - min(cost_per_sec / 1.0, 1.0))

        return GenerativeModelInfo(
            model_id=model.id,
            provider_id=provider_id,
            name=model.name,
            description=model.description,
            capabilities=capabilities,
            quality_score=quality_score,
            speed_score=speed_score,
            cost_score=cost_score,
            max_duration_seconds=model.limits.max_duration_seconds,
            min_duration_seconds=model.limits.min_duration_seconds,
            supported_resolutions=[f"{model.limits.max_width}x{model.limits.max_height}"],
            supported_aspect_ratios=model.limits.supported_aspect_ratios,
            max_reference_images=model.limits.max_reference_images,
            input_types=["text", "image", "video"],
            output_types=["video"],
            temporal_consistency=ProviderCapability.VIDEO_TO_VIDEO in model.capabilities,
            identity_capability=ProviderCapability.IDENTITY_PRESERVATION in model.capabilities,
            motion_capability=ProviderCapability.MOTION_GENERATION in model.capabilities,
            camera_control=ProviderCapability.CAMERA_CONTROL in model.capabilities,
            audio_capability=ProviderCapability.MUTE_AUDIO in model.capabilities,
            v2v_capability=ProviderCapability.VIDEO_TO_VIDEO in model.capabilities,
            extension_capability=ProviderCapability.VIDEO_EXTENSION in model.capabilities,
            metadata=model.metadata,
        )

    @staticmethod
    async def get_all_models(provider_registry: ProviderRegistry) -> List[GenerativeModelInfo]:
        models = []
        for provider_id, provider in provider_registry.get_all().items():
            try:
                for model in provider.get_supported_models():
                    models.append(GenerativeModelAbstraction.convert_provider_model(model, provider_id))
            except Exception as e:
                logger.warning(f"Failed to load models from provider {provider_id}: {e}")
        return models

    @staticmethod
    async def get_models_by_capability(
        provider_registry: ProviderRegistry,
        capability: ModelCapabilityDetail,
    ) -> List[GenerativeModelInfo]:
        all_models = await GenerativeModelAbstraction.get_all_models(provider_registry)
        return [m for m in all_models if capability in m.capabilities]
