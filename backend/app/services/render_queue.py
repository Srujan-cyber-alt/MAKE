"""
Render Queue for MAKE AI Video Phase 17.

Manages render jobs with priority, progress, cancel, retry.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class RenderJobStatus(str, Enum):
    QUEUED = "queued"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RenderJob:
    job_id: str
    project_id: str
    timeline_id: str
    output_path: str
    status: RenderJobStatus = RenderJobStatus.QUEUED
    priority: int = 0
    progress: float = 0.0
    error: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RenderQueue:
    def __init__(self):
        self._jobs: Dict[str, RenderJob] = {}
        self._queue: List[str] = []

    def enqueue(self, project_id: str, timeline_id: str, output_path: str, priority: int = 0, parameters: Dict[str, Any] = None) -> RenderJob:
        job = RenderJob(
            job_id=str(uuid.uuid4()),
            project_id=project_id,
            timeline_id=timeline_id,
            output_path=output_path,
            priority=priority,
            parameters=parameters or {},
        )
        self._jobs[job.job_id] = job
        self._queue.append(job.job_id)
        self._sort_queue()
        return job

    def dequeue(self) -> Optional[RenderJob]:
        if not self._queue:
            return None
        job_id = self._queue.pop(0)
        job = self._jobs.get(job_id)
        if job:
            job.status = RenderJobStatus.RENDERING
        return job

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job and job.status in (RenderJobStatus.QUEUED, RenderJobStatus.RENDERING):
            job.status = RenderJobStatus.CANCELLED
            if job_id in self._queue:
                self._queue.remove(job_id)
            return True
        return False

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "progress": job.progress,
            "error": job.error,
            "output_path": job.output_path,
        }

    def _sort_queue(self):
        self._queue.sort(key=lambda jid: self._jobs.get(jid, RenderJob("", "", "", "")).priority, reverse=True)


render_queue = RenderQueue()
