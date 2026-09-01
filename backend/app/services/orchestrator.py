import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.models.models import Job, JobStatus
from app.providers.base import VideoProviderAdapter, GenerationRequest, GenerationResponse
from app.core.config import settings


class JobOrchestrator:
    def __init__(self, provider_registry, db_session_factory, storage_service):
        self.provider_registry = provider_registry
        self.db_session_factory = db_session_factory
        self.storage_service = storage_service
        self._running = False

    async def start(self):
        self._running = True
        while self._running:
            try:
                await self._process_next_job()
                await asyncio.sleep(1)
            except Exception as e:
                await asyncio.sleep(5)

    async def stop(self):
        self._running = False

    async def _process_next_job(self):
        async with self.db_session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Job).where(
                    Job.status == JobStatus.QUEUED,
                    Job.retry_count < Job.max_retries,
                ).order_by(Job.priority.desc(), Job.created_at.asc()).limit(1)
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            await session.commit()
            await session.refresh(job)

        try:
            await self._execute_job(job)
        except Exception as e:
            async with self.db_session_factory() as session:
                job = await session.get(Job, job.id)
                if job:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.retry_count += 1
                    await session.commit()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
    )
    async def _execute_job(self, job: Job):
        provider_name = job.provider or settings.default_video_provider
        provider = self.provider_registry.get(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} not found")

        async with self.db_session_factory() as session:
            job.status = JobStatus.GENERATING
            await session.commit()

        request = GenerationRequest(
            prompt=job.prompt or "",
            negative_prompt=job.negative_prompt,
            duration_seconds=job.parameters.get("duration_seconds") if job.parameters else None,
            width=job.parameters.get("width") if job.parameters else None,
            height=job.parameters.get("height") if job.parameters else None,
            fps=job.parameters.get("fps") if job.parameters else None,
            input_images=[a.get("url") for a in job.input_assets if a.get("type") == "image"] if job.input_assets else None,
            input_video_url=next((a.get("url") for a in job.input_assets if a.get("type") == "video"), None) if job.input_assets else None,
            reference_images=job.parameters.get("reference_images") if job.parameters else None,
            parameters=job.parameters,
        )

        model_id = job.model or provider.get_supported_models()[0].id if provider.get_supported_models() else None
        if not model_id:
            raise ValueError(f"No model specified and provider {provider_name} has no default model")

        response = await provider.submit_generation(request, model_id=model_id)

        async with self.db_session_factory() as session:
            job = await session.get(Job, job.id)
            if not job:
                return
            job.result = {
                "provider_job_id": response.provider_job_id,
                "status": response.status,
            }
            await session.commit()

        max_polls = 300
        for _ in range(max_polls):
            await asyncio.sleep(5)
            status = await provider.check_status(response.provider_job_id)
            if status.status in ("completed", "failed", "cancelled"):
                break

            async with self.db_session_factory() as session:
                job = await session.get(Job, job.id)
                if job and job.status == JobStatus.CANCELLED:
                    await provider.cancel_job(response.provider_job_id)
                    return

        result = await provider.get_result(response.provider_job_id)

        async with self.db_session_factory() as session:
            job = await session.get(Job, job.id)
            if not job:
                return

            if result and result.video_url:
                job.status = JobStatus.COMPLETED
                job.output_assets = [{"type": "video", "url": result.video_url, "thumbnail_url": result.thumbnail_url}]
                job.result = {
                    "provider_job_id": result.provider_job_id,
                    "video_url": result.video_url,
                    "duration_seconds": result.duration_seconds,
                    "width": result.width,
                    "height": result.height,
                    "fps": result.fps,
                    "seed": result.seed,
                    "metadata": result.metadata,
                }
            else:
                job.status = JobStatus.FAILED
                job.error = "Generation did not complete successfully"

            job.completed_at = datetime.utcnow()
            await session.commit()

    async def cancel_job(self, job_id: uuid.UUID) -> bool:
        async with self.db_session_factory() as session:
            job = await session.get(Job, job_id)
            if not job:
                return False
            job.status = JobStatus.CANCELLED
            await session.commit()

        provider = self.provider_registry.get(job.provider) if job.provider else None
        if provider and job.result and job.result.get("provider_job_id"):
            return await provider.cancel_job(job.result["provider_job_id"])
        return True
