import httpx
from typing import Optional, Dict, Any, List, Set
from app.providers.base import (
    VideoProviderAdapter, GenerationRequest, GenerationResponse,
    ProviderHealth, ProviderCapability, ModelInfo, ModelLimits
)
from app.core.config import settings


class PikaProvider(VideoProviderAdapter):
    def __init__(self):
        super().__init__(
            name="pika",
            api_base=settings.pika_api_base,
            api_key=settings.pika_api_key or None,
        )

    async def health_check(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(status="inactive", error="API key not configured")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/status",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return ProviderHealth(status="active", latency_ms=response.elapsed.total_seconds() * 1000)
                return ProviderHealth(status="error", error=f"HTTP {response.status_code}")
        except Exception as e:
            return ProviderHealth(status="error", error=str(e))

    async def submit_generation(self, request: GenerationRequest, model_id: str) -> GenerationResponse:
        if not self.api_key:
            raise ValueError("Pika API key not configured")
        async with httpx.AsyncClient() as client:
            payload = {
                "prompt": request.prompt,
                "model": model_id,
                "duration": request.duration_seconds or 4,
                "aspect_ratio": request.aspect_ratio or "16:9",
            }
            if request.input_images:
                payload["image_url"] = request.input_images[0]
            if request.input_video_url:
                payload["video_url"] = request.input_video_url
            if request.negative_prompt:
                payload["negative_prompt"] = request.negative_prompt
            if request.parameters:
                payload.update(request.parameters)

            response = await client.post(
                f"{self.api_base}/videos",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return GenerationResponse(
                provider_job_id=data.get("id"),
                status=data.get("status", "queued"),
                video_url=data.get("url"),
                metadata=data,
            )

    async def check_status(self, provider_job_id: str) -> GenerationResponse:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/videos/{provider_job_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return GenerationResponse(
                provider_job_id=provider_job_id,
                status=data.get("status", "unknown"),
                video_url=data.get("url"),
                metadata=data,
            )

    async def cancel_job(self, provider_job_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/videos/{provider_job_id}/cancel",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10.0,
            )
            return response.status_code == 200

    async def get_result(self, provider_job_id: str) -> Optional[GenerationResponse]:
        status = await self.check_status(provider_job_id)
        if status.status == "completed" and status.video_url:
            return status
        return None

    def get_capabilities(self) -> Set[ProviderCapability]:
        return {
            ProviderCapability.TEXT_TO_VIDEO,
            ProviderCapability.IMAGE_TO_VIDEO,
            ProviderCapability.VIDEO_TO_VIDEO,
            ProviderCapability.ASPECT_RATIO,
            ProviderCapability.DURATION_CONTROL,
        }

    def get_supported_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                id="pika-1.0",
                name="Pika 1.0",
                description="Standard video generation with image and text inputs",
                capabilities={
                    ProviderCapability.TEXT_TO_VIDEO,
                    ProviderCapability.IMAGE_TO_VIDEO,
                    ProviderCapability.ASPECT_RATIO,
                    ProviderCapability.DURATION_CONTROL,
                },
                limits=ModelLimits(
                    max_duration_seconds=4.0,
                    max_width=1920,
                    max_height=1080,
                    supported_aspect_ratios=["16:9", "9:16", "1:1", "4:5"],
                    max_input_images=1,
                    max_reference_images=0,
                    supports_seed=False,
                    supports_negative_prompt=True,
                    supports_guidance_scale=False,
                ),
            ),
            ModelInfo(
                id="pika-1.5",
                name="Pika 1.5",
                description="Advanced video generation with video-to-video support",
                capabilities={
                    ProviderCapability.TEXT_TO_VIDEO,
                    ProviderCapability.IMAGE_TO_VIDEO,
                    ProviderCapability.VIDEO_TO_VIDEO,
                    ProviderCapability.ASPECT_RATIO,
                    ProviderCapability.DURATION_CONTROL,
                    ProviderCapability.VIDEO_EXTENSION,
                },
                limits=ModelLimits(
                    max_duration_seconds=8.0,
                    max_width=1920,
                    max_height=1080,
                    supported_aspect_ratios=["16:9", "9:16", "1:1", "4:5"],
                    max_input_images=1,
                    max_reference_images=0,
                    supports_seed=False,
                    supports_negative_prompt=True,
                    supports_guidance_scale=False,
                ),
            ),
        ]
