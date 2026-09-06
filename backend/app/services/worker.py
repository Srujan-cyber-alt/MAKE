"""MAKE production worker executors.

Executes queued jobs by delegating to the provider registry.
This module is intentionally lightweight so it can run in a Celery
worker process or any other task runtime.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from uuid import UUID

from app.models.models import Job, JobStatus
from app.providers.base import VideoProviderAdapter, GenerationRequest, GenerationResponse
from app.services.storage import StorageService
from app.services.video_processing import VideoProcessingService

logger = logging.getLogger(__name__)


class JobExecutor:
    """Base executor interface."""

    async def execute(self, job: Job) -> None:
        raise NotImplementedError

    async def cancel(self, job_id: UUID) -> bool:
        raise NotImplementedError


class GenerationExecutor(JobExecutor):
    """Executes generation jobs via the provider registry."""

    def __init__(
        self,
        provider: VideoProviderAdapter,
        storage: StorageService,
        video: VideoProcessingService,
    ) -> None:
        self.provider = provider
        self.storage = storage
        self.video = video

    async def execute(self, job: Job) -> None:
        if job.status == JobStatus.CANCELLED:
            return

        try:
            req = GenerationRequest(
                prompt=job.payload.get("prompt", ""),
                negative_prompt=job.payload.get("negative_prompt", ""),
                duration_seconds=job.payload.get("duration_seconds", 5.0),
                resolution=job.payload.get("resolution", "1280x720"),
                fps=job.payload.get("fps", 24),
                seed=job.payload.get("seed"),
                conditioning=job.payload.get("conditioning", {}),
            )
            response: GenerationResponse = await self.provider.generate(req)

            if response.ok and response.output_url:
                await self.storage.download_to_local(response.output_url, job.id)
                await self.video.post_process(job.id)
            else:
                logger.error("Generation failed for job %s: %s", job.id, response.error)

        except Exception as exc:
            logger.exception("Executor error for job %s", job.id)
            raise


class EditExecutor(JobExecutor):
    """Executes video editing jobs."""

    def __init__(
        self,
        video: VideoProcessingService,
        storage: StorageService,
    ) -> None:
        self.video = video
        self.storage = storage

    async def execute(self, job: Job) -> None:
        if job.status == JobStatus.CANCELLED:
            return

        try:
            operation = job.payload.get("operation", "unknown")
            source_path = job.payload.get("source_path")
            if not source_path:
                logger.error("No source_path for edit job %s", job.id)
                return

            local_path = await self.storage.get_local_path(source_path, job.id)
            result_path = await self.video.apply_edit(
                local_path,
                operation=operation,
                params=job.payload.get("params", {}),
            )
            if result_path:
                await self.storage.upload_result(result_path, job.id)
            else:
                logger.error("Edit failed for job %s", job.id)

        except Exception as exc:
            logger.exception("Edit executor error for job %s", job.id)
            raise

    async def cancel(self, job_id: UUID) -> bool:
        return False


class WorkerPool:
    def __init__(self) -> None:
        self._executors: Dict[str, JobExecutor] = {}

    def register_executor(self, job_type: str, executor: JobExecutor):
        self._executors[job_type] = executor

    def get_executor(self, job_type: str) -> Optional[JobExecutor]:
        return self._executors.get(job_type)
