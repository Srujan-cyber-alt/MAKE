import httpx
from typing import Optional, Dict, Any, List
from app.providers.base import (
    VideoProviderAdapter, GenerationRequest, GenerationResponse,
    ProviderHealth, ProviderCapability
)
from app.core.config import settings


class RunwayProvider(VideoProviderAdapter):
    def __init__(self):
        super().__init__(
            name="runway",
            api_base=settings.runway_api_base,
            api_key=settings.runway_api_key or None,
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

    async def submit_generation(self, request: GenerationRequest) -> GenerationResponse:
        if not self.api_key:
            raise ValueError("Runway API key not configured")
        async with httpx.AsyncClient() as client:
            payload = {
                "prompt": request.prompt,
                "duration": request.duration_seconds or 4,
                "width": request.width or 1280,
                "height": request.height or 720,
                "fps": request.fps or 24,
            }
            if request.negative_prompt:
                payload["negative_prompt"] = request.negative_prompt
            if request.input_images:
                payload["input_images"] = request.input_images
            if request.seed is not None:
                payload["seed"] = request.seed
            if request.guidance_scale is not None:
                payload["guidance_scale"] = request.guidance_scale
            if request.reference_images:
                payload["reference_images"] = request.reference_images

            response = await client.post(
                f"{self.api_base}/generations",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return GenerationResponse(
                provider_job_id=data.get("id"),
                status=data.get("status", "queued"),
                video_url=data.get("output", {}).get("video_url"),
                thumbnail_url=data.get("output", {}).get("thumbnail_url"),
                duration_seconds=data.get("output", {}).get("duration"),
                width=data.get("output", {}).get("width"),
                height=data.get("output", {}).get("height"),
                fps=data.get("output", {}).get("fps"),
                seed=data.get("output", {}).get("seed"),
                metadata=data.get("output"),
            )

    async def check_status(self, provider_job_id: str) -> GenerationResponse:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/generations/{provider_job_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return GenerationResponse(
                provider_job_id=provider_job_id,
                status=data.get("status", "unknown"),
                video_url=data.get("output", {}).get("video_url"),
                thumbnail_url=data.get("output", {}).get("thumbnail_url"),
                metadata=data,
            )

    async def cancel_job(self, provider_job_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/generations/{provider_job_id}/cancel",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10.0,
            )
            return response.status_code == 200

    async def get_result(self, provider_job_id: str) -> Optional[GenerationResponse]:
        status = await self.check_status(provider_job_id)
        if status.status == "completed" and status.video_url:
            return status
        return None

    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.TEXT_TO_VIDEO,
            ProviderCapability.IMAGE_TO_VIDEO,
            ProviderCapability.MOTION_GENERATION,
        ]

    def get_supported_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": "gen3a_turbo", "name": "Gen-3 Alpha Turbo", "capabilities": [ProviderCapability.TEXT_TO_VIDEO, ProviderCapability.IMAGE_TO_VIDEO]},
            {"id": "gen2", "name": "Gen-2", "capabilities": [ProviderCapability.TEXT_TO_VIDEO, ProviderCapability.IMAGE_TO_VIDEO]},
        ]
