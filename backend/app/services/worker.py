from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from uuid import UUID
from app.models.models import Job
from app.providers.base import VideoProviderAdapter, GenerationRequest, GenerationResponse
from app.services.storage import StorageService
from app.services.video_processing import VideoProcessingService


class JobExecutor(ABC):
    @abstractmethod
    async def execute(self, job: Job) -> None:
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, job_id: UUID) -> bool:
        raise NotImplementedError


class GenerationExecutor(JobExecutor):
    def __init__(self, provider: VideoProviderAdapter, storage: StorageService, video: VideoProcessingService):
        self.provider = provider
        self.storage = storage
        self.video = video

    async def execute(self, job: Job) -> None:
        pass


class EditExecutor(JobExecutor):
    def __init__(self, video: VideoProcessingService, storage: StorageService):
        self.video = video
        self.storage = storage

    async def execute(self, job: Job) -> None:
        pass


class WorkerPool:
    def __init__(self):
        self._executors: Dict[str, JobExecutor] = {}

    def register_executor(self, job_type: str, executor: JobExecutor):
        self._executors[job_type] = executor

    def get_executor(self, job_type: str) -> Optional[JobExecutor]:
        return self._executors.get(job_type)
