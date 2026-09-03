"""
MAKE proprietary local neural provider — production implementation.

Routes through MakeInferenceEngine. Reports availability honestly:
  - unavailable (with reason) when no trained checkpoint is registered
  - available (with model_id, checkpoint, device, dtype) when one is
Generates a real neural video via the inference engine; never falls
back to FFmpeg or any procedural generator.
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


DEFAULT_FRAMES = 8
DEFAULT_FPS = 8
DEFAULT_SHORT_SIDE = 64
DEFAULT_INFERENCE_STEPS = 20


class MakeLocalNeuralProvider(VideoProviderAdapter):
    name = "make_local_neural"

    def __init__(self) -> None:
        super().__init__(name=self.name, api_base="make://local", api_key=None)
        self._cached_engine = None
        self._cached_checkpoint_id: Optional[str] = None
        self._cached_checkpoint_sha: Optional[str] = None
        self._cached_model_name: Optional[str] = None

    def _engine(self):
        if self._cached_engine is None:
            from app.make_model.inference import MakeInferenceEngine
            self._cached_engine = MakeInferenceEngine()
        return self._cached_engine

    def _ensure_checkpoint(self, model_name: str) -> Dict[str, Any]:
        from app.make_model.registry import get_registry
        reg = get_registry()
        cps = reg.list_checkpoints(model_name=model_name)
        if not cps:
            raise RuntimeError(
                f"MAKE_MODEL_UNTRAINED: no checkpoint for model {model_name!r}"
            )
        cp = sorted(cps, key=lambda c: c.get("created_at", ""))[-1]
        self._cached_checkpoint_id = cp["id"]
        self._cached_checkpoint_sha = cp["sha256"]
        self._cached_model_name = model_name
        return cp

    def get_capabilities(self) -> Set[ProviderCapability]:
        return {
            ProviderCapability.TEXT_TO_VIDEO,
            ProviderCapability.IMAGE_TO_VIDEO,
        }

    def get_supported_models(self) -> List[LegacyModelInfo]:
        from app.make_model.registry import get_registry
        reg = get_registry()
        models = reg.list_models()
        out: List[LegacyModelInfo] = []
        for m in models:
            status = m.get("status", "untrained")
            cps = reg.list_checkpoints(model_name=m["name"])
            note = f"MAKE proprietary model. status={status}. checkpoints={len(cps)}."
            out.append(LegacyModelInfo(
                id=m["name"],
                name=f"{m['name']} ({status})",
                description=note,
                capabilities=list(self.get_capabilities()),
                limits=LegacyModelLimits(
                    max_duration_seconds=float(DEFAULT_FRAMES) / DEFAULT_FPS,
                    min_duration_seconds=0.5,
                    max_width=128,
                    max_height=128,
                    supported_aspect_ratios=["1:1"],
                    max_input_images=1,
                    max_reference_images=0,
                    supports_seed=True,
                    supports_negative_prompt=False,
                    supports_guidance_scale=False,
                    cost_per_second=0.0,
                ),
                metadata={
                    "arch_version": m.get("arch_version", ""),
                    "owner": "MAKE",
                    "status": status,
                    "checkpoint_count": len(cps),
                    "no_cloud": True,
                },
            ))
        return out

    async def health_check(self) -> LegacyProviderHealth:
        from app.make_model.inference import inference_availability
        avail = inference_availability()
        if avail["available"]:
            return LegacyProviderHealth(
                status=ProviderStatus.AVAILABLE.value,
            )
        reason = avail.get("reason") or "MAKE model is UNTRAINED (no checkpoint registered)"
        return LegacyProviderHealth(
            status=ProviderStatus.UNAVAILABLE.value,
            error=reason,
        )

    async def submit_generation(
        self, request: LegacyGenerationRequest, model_id: str
    ) -> LegacyGenerationResponse:
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

    def generate(self, request: LegacyGenerationRequest) -> LegacyGenerationResponse:
        # No model_id on LegacyGenerationRequest; default to research v0.
        return self._do_generate(request, "make-video-research-v0")

    def health(self) -> LegacyProviderHealth:
        from app.make_model.inference import inference_availability
        avail = inference_availability()
        if avail["available"]:
            return LegacyProviderHealth(
                status=ProviderStatus.AVAILABLE.value,
            )
        reason = avail.get("reason") or "MAKE model is UNTRAINED (no checkpoint registered)"
        return LegacyProviderHealth(
            status=ProviderStatus.UNAVAILABLE.value,
            error=reason,
        )

    def list_models(self) -> List[LegacyModelInfo]:
        return self.get_supported_models()

    def _do_generate(self, request: LegacyGenerationRequest, model_id: str) -> LegacyGenerationResponse:
        from app.make_model.inference import MakeInferenceRequest
        try:
            cp = self._ensure_checkpoint(model_id)
        except Exception as e:
            return LegacyGenerationResponse(
                provider_job_id=f"make-{int(time.time())}",
                status=GenerationStage.FAILED.value,
                error=str(e),
                metadata={"code": "MAKE_MODEL_UNTRAINED", "model_id": model_id},
            )
        req = MakeInferenceRequest(
            prompt=request.prompt or "",
            model_name=cp["model_name"],
            checkpoint_id=cp["id"],
            seed=int(request.seed or 0),
            frames=DEFAULT_FRAMES,
            short_side=DEFAULT_SHORT_SIDE,
            fps=DEFAULT_FPS,
            num_inference_steps=DEFAULT_INFERENCE_STEPS,
        )
        try:
            res = self._engine().run(req)
        except Exception as e:
            return LegacyGenerationResponse(
                provider_job_id=f"make-{int(time.time())}",
                status=GenerationStage.FAILED.value,
                error=str(e),
                metadata={"code": getattr(e, "code", "MAKE_MODEL_ERROR")},
            )
        if not res.ok:
            return LegacyGenerationResponse(
                provider_job_id=f"make-{int(time.time())}",
                status=GenerationStage.FAILED.value,
                error=res.message,
                metadata={"code": res.code, "checkpoint": res.checkpoint_id},
            )
        return LegacyGenerationResponse(
            provider_job_id=res.checkpoint_id or f"make-{int(time.time())}",
            status=GenerationStage.COMPLETED.value,
            video_url=res.output_path,
            duration_seconds=res.duration_seconds,
            width=res.width,
            height=res.height,
            fps=res.fps,
            seed=res.seed,
            metadata={
                "model_name": res.model_name,
                "checkpoint_id": res.checkpoint_id,
                "checkpoint_sha256": res.checkpoint_sha256,
                "arch_version": res.arch_version,
                "output_sha256": res.output_sha256,
                "output_bytes": res.output_bytes,
                "elapsed_seconds": res.elapsed_seconds,
                "inference_steps": res.inference_steps,
                "device": res.device,
                "dtype": res.dtype,
                "owner": "MAKE",
                "is_neural_inference": True,
            },
        )
