import httpx
from typing import Optional, Dict, Any, List
from app.providers.base import (
    VideoProviderAdapter, GenerationRequest, GenerationResponse,
    ProviderHealth, ProviderCapability
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

    async def submit_generation(self, request: GenerationRequest) -> GenerationResponse:
        if not self.api_key:
            raise ValueError("Pika API key not configured")
        async with httpx.AsyncClient() as client:
            payload = {
                "prompt": request.prompt,
                "duration": request.duration_seconds or 4,
                "aspect_ratio": request.aspect_ratio or "16:9",
            }
            if request.input_images:
                payload["image_url"] = request.input_images[0]
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

    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.TEXT_TO_VIDEO,
            ProviderCapability.IMAGE_TO_VIDEO,
            ProviderCapability.VIDEO_TO_VIDEO,
        ]

    def get_supported_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": "pika-1.0", "name": "Pika 1.0", "capabilities": [ProviderCapability.TEXT_TO_VIDEO, ProviderCapability.IMAGE_TO_VIDEO]},
            {"id": "pika-1.5", "name": "Pika 1.5", "capabilities": [ProviderCapability.TEXT_TO_VIDEO, ProviderCapability.IMAGE_TO_VIDEO, ProviderCapability.VIDEO_TO_VIDEO]},
        ]
