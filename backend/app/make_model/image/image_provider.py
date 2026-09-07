"""
MAKE proprietary local image provider — production implementation.

Mirrors the MakeLocalNeuralProvider (video) but produces images via
the DDPM sampler on a real MAKE checkpoint. Reports availability
honestly: unavailable when no checkpoint is registered.

Generated images are real neural samples. The provider reports its
native generation resolution explicitly and refuses to claim 4K / 2K
generation when only 32x32 native samples exist.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Set

from app.providers.base import (
    VideoProviderAdapter, ProviderCapability, LegacyModelInfo,
    LegacyModelLimits, LegacyGenerationRequest, LegacyGenerationResponse,
    LegacyProviderHealth, ProviderStatus, GenerationStage,
)


DEFAULT_IMAGE_SIZE = 32
DEFAULT_INFERENCE_STEPS = 25
SUPPORTED_SIZES = (16, 24, 32, 48, 64)


class MakeLocalImageProvider(VideoProviderAdapter):
    """Image-generation provider, registered alongside the video providers.

    The existing provider registry is video-shaped (VideoProviderAdapter),
    so we re-use it but tag the metadata as image-generation. The
    generation_response uses image_url instead of video_url.
    """

    name = "make_local_image"
    kind = "image"

    def __init__(self) -> None:
        super().__init__(name=self.name, api_base="make://image", api_key=None)

    def get_capabilities(self) -> Set[ProviderCapability]:
        # We expose TEXT_TO_VIDEO as a stand-in for the closest capability.
        # The registry treats this as a text-conditioned generation adapter.
        return {ProviderCapability.TEXT_TO_VIDEO}

    def get_supported_models(self) -> List[LegacyModelInfo]:
        try:
            from app.make_model.registry import get_registry
            from app.make_model.image.registry_bridge import ImageRegistryBridge
            reg = get_registry()
            cps = reg.list_checkpoints(model_name=ImageRegistryBridge.IMAGE_MODEL_NAME)
            note = f"MAKE proprietary image denoiser (CPU-only). checkpoints={len(cps)}."
            limits = LegacyModelLimits(
                max_duration_seconds=0.0,
                min_duration_seconds=0.0,
                max_width=max(SUPPORTED_SIZES),
                max_height=max(SUPPORTED_SIZES),
                supported_aspect_ratios=["1:1"],
                max_input_images=0,
                max_reference_images=0,
                supports_seed=True,
                supports_negative_prompt=False,
                supports_guidance_scale=False,
                cost_per_second=0.0,
            )
            return [LegacyModelInfo(
                id=ImageRegistryBridge.IMAGE_MODEL_NAME,
                name=f"{ImageRegistryBridge.IMAGE_MODEL_NAME} (cpu-only)",
                description=note,
                capabilities=list(self.get_capabilities()),
                limits=limits,
                metadata={
                    "owner": "MAKE",
                    "kind": "image",
                    "no_cloud": True,
                    "no_gpu_required": True,
                    "checkpoint_count": len(cps),
                    "native_resolution": DEFAULT_IMAGE_SIZE,
                    "interpolation_disabled": True,
                    "arch_version": ImageRegistryBridge.ARCH_VERSION,
                },
            )]
        except Exception:
            return []

    async def health_check(self) -> LegacyProviderHealth:
        try:
            from app.make_model.registry import get_registry
            from app.make_model.image.registry_bridge import ImageRegistryBridge
            reg = get_registry()
            cps = reg.list_checkpoints(model_name=ImageRegistryBridge.IMAGE_MODEL_NAME)
            if cps:
                return LegacyProviderHealth(status=ProviderStatus.AVAILABLE.value)
            return LegacyProviderHealth(
                status=ProviderStatus.UNAVAILABLE.value,
                error="MAKE image model has no registered checkpoint.",
            )
        except Exception as e:
            return LegacyProviderHealth(status=ProviderStatus.UNAVAILABLE.value, error=str(e))

    async def submit_generation(self, request: LegacyGenerationRequest, model_id: str) -> LegacyGenerationResponse:
        return self._do_generate(request, model_id)

    async def check_status(self, provider_job_id: str) -> LegacyGenerationResponse:
        return LegacyGenerationResponse(
            provider_job_id=provider_job_id,
            status=GenerationStage.COMPLETED.value,
        )

    async def cancel_job(self, provider_job_id: str) -> bool:
        return True

    async def get_result(self, provider_job_id: str) -> Optional[LegacyGenerationResponse]:
        return LegacyGenerationResponse(
            provider_job_id=provider_job_id,
            status=GenerationStage.COMPLETED.value,
        )

    def health(self) -> LegacyProviderHealth:
        try:
            from app.make_model.registry import get_registry
            from app.make_model.image.registry_bridge import ImageRegistryBridge
            reg = get_registry()
            cps = reg.list_checkpoints(model_name=ImageRegistryBridge.IMAGE_MODEL_NAME)
            if cps:
                return LegacyProviderHealth(status=ProviderStatus.AVAILABLE.value)
            return LegacyProviderHealth(
                status=ProviderStatus.UNAVAILABLE.value,
                error="MAKE image model has no registered checkpoint.",
            )
        except Exception as e:
            return LegacyProviderHealth(status=ProviderStatus.UNAVAILABLE.value, error=str(e))

    def list_models(self) -> List[LegacyModelInfo]:
        return self.get_supported_models()

    def _do_generate(self, request: LegacyGenerationRequest, model_id: str) -> LegacyGenerationResponse:
        from app.make_model.registry import get_registry
        from app.make_model.image.registry_bridge import ImageRegistryBridge
        from app.make_model.image.inference.sampler import ImageSampler, SamplerConfig
        reg = get_registry()
        cps = reg.list_checkpoints(model_name=ImageRegistryBridge.IMAGE_MODEL_NAME)
        if not cps:
            return LegacyGenerationResponse(
                provider_job_id=f"make-img-{int(time.time())}",
                status=GenerationStage.FAILED.value,
                metadata={
                    "code": "MAKE_MODEL_UNTRAINED",
                    "model_id": model_id,
                    "error": "no registered checkpoint",
                },
            )
        cp = sorted(cps, key=lambda c: c.get("created_at", ""))[-1]
        size = DEFAULT_IMAGE_SIZE
        try:
            req_w = int(request.width or 0) if request.width else 0
            req_h = int(request.height or 0) if request.height else 0
            req_size = max(req_w, req_h)
            if req_size > 0:
                size = min(req_size, max(SUPPORTED_SIZES))
                if size not in SUPPORTED_SIZES:
                    size = max(s for s in SUPPORTED_SIZES if s <= size)
        except Exception:
            pass
        scfg = SamplerConfig(
            model_name=ImageRegistryBridge.IMAGE_MODEL_NAME,
            checkpoint_path=cp["path"],
            prompt=request.prompt or "",
            seed=int(request.seed or 0),
            num_inference_steps=DEFAULT_INFERENCE_STEPS,
            image_size=size,
            output_format="png",
        )
        try:
            res = ImageSampler().sample(scfg)
        except Exception as e:
            return LegacyGenerationResponse(
                provider_job_id=f"make-img-{int(time.time())}",
                status=GenerationStage.FAILED.value,
                metadata={"code": "MAKE_IMAGE_ERROR", "error": str(e)},
            )
        if not res.ok:
            return LegacyGenerationResponse(
                provider_job_id=f"make-img-{int(time.time())}",
                status=GenerationStage.FAILED.value,
                metadata={"code": "MAKE_IMAGE_FAIL", "error": res.message},
            )
        ImageRegistryBridge().mark_inference_ready(res.output_path, res.output_sha256)
        # The LegacyGenerationResponse dataclass only exposes video_url;
        # we use it for the image URL and additionally set a typed flag
        # in metadata so consumers can dispatch on `kind == "image"`.
        return LegacyGenerationResponse(
            provider_job_id=res.checkpoint_path or f"make-img-{int(time.time())}",
            status=GenerationStage.COMPLETED.value,
            video_url=res.output_path,
            duration_seconds=float(res.elapsed_seconds),
            width=res.width,
            height=res.height,
            seed=res.seed,
            metadata={
                "kind": "image",
                "output_url": res.output_path,
                "model_name": res.model_name,
                "checkpoint_id": res.checkpoint_path,
                "checkpoint_sha256": res.checkpoint_sha256,
                "generation_resolution_native": res.generation_resolution_native,
                "refinement_resolution_native": res.refinement_resolution_native,
                "interpolation_note": res.interpolation_note,
                "inference_steps": res.inference_steps,
                "elapsed_seconds": res.elapsed_seconds,
                "output_sha256": res.output_sha256,
                "output_bytes": res.output_bytes,
            },
        )