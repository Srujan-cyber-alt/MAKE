import asyncio
import time
import uuid
from typing import Optional, Dict, Any, List, Set
from app.providers.base import (
    VideoProviderAdapter, GenerationRequest, GenerationResponse,
    ProviderHealth, ProviderCapability, ModelInfo, ModelLimits
)


class TestVideoProvider(VideoProviderAdapter):
    def __init__(self):
        super().__init__(
            name="test-provider",
            api_base="http://localhost:9999",
            api_key="test-key",
        )
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._should_fail = False
        self._fail_error = "Simulated provider failure"

    def configure_failure(self, should_fail: bool = True, error_message: str = "Simulated failure"):
        self._should_fail = should_fail
        self._fail_error = error_message

    async def health_check(self) -> ProviderHealth:
        await asyncio.sleep(0.01)
        if self._should_fail:
            return ProviderHealth(status="error", error=self._fail_error)
        return ProviderHealth(status="active", latency_ms=1.0)

    async def submit_generation(self, request: GenerationRequest, model_id: str) -> GenerationResponse:
        if self._should_fail:
            raise ValueError(self._fail_error)
        job_id = f"test-job-{uuid.uuid4().hex[:8]}"
        self._jobs[job_id] = {
            "status": "queued",
            "request": request,
            "model_id": model_id,
            "created_at": time.time(),
        }
        return GenerationResponse(
            provider_job_id=job_id,
            status="queued",
            metadata={"model": model_id},
        )

    async def check_status(self, provider_job_id: str) -> GenerationResponse:
        job = self._jobs.get(provider_job_id)
        if not job:
            return GenerationResponse(provider_job_id=provider_job_id, status="failed", metadata={"error": "not_found"})
        elapsed = time.time() - job["created_at"]
        if elapsed > 0.5:
            job["status"] = "completed"
            return GenerationResponse(
                provider_job_id=provider_job_id,
                status="completed",
                video_url=f"http://localhost:9999/videos/{provider_job_id}/output.mp4",
                thumbnail_url=f"http://localhost:9999/videos/{provider_job_id}/thumb.jpg",
                duration_seconds=4.0,
                width=1280,
                height=720,
                fps=24,
                metadata={"model": job["model_id"], "simulated": True},
            )
        return GenerationResponse(provider_job_id=provider_job_id, status="processing")

    async def cancel_job(self, provider_job_id: str) -> bool:
        job = self._jobs.get(provider_job_id)
        if job:
            job["status"] = "cancelled"
            return True
        return False

    async def get_result(self, provider_job_id: str) -> Optional[GenerationResponse]:
        status = await self.check_status(provider_job_id)
        if status.status == "completed":
            return status
        return None

    def get_capabilities(self) -> Set[ProviderCapability]:
        return {
            ProviderCapability.TEXT_TO_VIDEO,
            ProviderCapability.IMAGE_TO_VIDEO,
            ProviderCapability.VIDEO_TO_VIDEO,
            ProviderCapability.VIDEO_EDITING,
            ProviderCapability.TRIM,
            ProviderCapability.CUT,
            ProviderCapability.RESIZE,
            ProviderCapability.ASPECT_RATIO,
            ProviderCapability.DURATION_CONTROL,
            ProviderCapability.SPEED_CHANGE,
            ProviderCapability.MUTE_AUDIO,
            ProviderCapability.OBJECT_REMOVAL,
            ProviderCapability.BACKGROUND_REPLACEMENT,
            ProviderCapability.MOTION_GENERATION,
            ProviderCapability.FACE_ANIMATION,
            ProviderCapability.INPAINTING,
            ProviderCapability.OUTPAINTING,
            ProviderCapability.VFX_GENERATION,
            ProviderCapability.STYLE_TRANSFER,
            ProviderCapability.CAMERA_CONTROL,
            ProviderCapability.IDENTITY_PRESERVATION,
            ProviderCapability.REFERENCE_IMAGES,
        }

    def get_supported_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                id="test-model-1",
                name="Test Model 1",
                description="Deterministic test model for automated tests",
                capabilities=self.get_capabilities(),
                limits=ModelLimits(
                    max_duration_seconds=10.0,
                    min_duration_seconds=1.0,
                    max_width=1920,
                    max_height=1080,
                    supported_aspect_ratios=["16:9", "9:16", "1:1", "4:5"],
                    max_input_images=1,
                    max_reference_images=3,
                    supports_seed=True,
                    supports_negative_prompt=True,
                    supports_guidance_scale=False,
                    cost_per_second=0.0,
                ),
            ),
        ]
