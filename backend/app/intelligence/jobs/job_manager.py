"""
MAKE Autonomous Agent Core V2 — Persistent Job Manager.

Jobs survive:
- application restart
- process crash
- network disconnect
- iPhone disconnect
- API reconnect
- worker failure
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionState, NodeType
from app.intelligence.core.event_stream import EventStream, EventType
from app.intelligence.core.project_memory import ProjectMemory, ProjectState


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"
    CHECKPOINTED = "checkpointed"


@dataclass
class IntelligentJob:
    job_id: UUID
    project_id: Optional[UUID]
    user_id: Optional[str]
    intent: str
    status: JobStatus
    execution_graph: Optional[ExecutionGraph]
    current_execution_id: Optional[UUID]
    iterations: int
    max_iterations: int
    checkpoint_data: Dict[str, Any]
    artifacts: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    metadata: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: Optional[str] = None
    owner: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": str(self.job_id),
            "project_id": str(self.project_id) if self.project_id else None,
            "user_id": self.user_id,
            "intent": self.intent,
            "status": self.status.value,
            "execution_graph": self.execution_graph.to_dict() if self.execution_graph else None,
            "current_execution_id": str(self.current_execution_id) if self.current_execution_id else None,
            "iterations": self.iterations,
            "max_iterations": self.max_iterations,
            "checkpoint_data": self.checkpoint_data,
            "artifacts": self.artifacts,
            "events": self.events,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
            "idempotency_key": self.idempotency_key,
            "owner": self.owner,
        }


class JobManager:
    def __init__(self, event_stream: Optional[EventStream] = None, project_memory: Optional[ProjectMemory] = None) -> None:
        self._jobs: Dict[UUID, IntelligentJob] = {}
        self._idempotency: Dict[str, UUID] = {}
        self.event_stream = event_stream or EventStream()
        self.project_memory = project_memory or ProjectMemory()

    def create_job(
        self,
        intent: str,
        project_id: Optional[UUID] = None,
        user_id: Optional[str] = None,
        max_iterations: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> IntelligentJob:
        if idempotency_key and idempotency_key in self._idempotency:
            existing_job_id = self._idempotency[idempotency_key]
            return self._jobs[existing_job_id]
        job_id = uuid4()
        job = IntelligentJob(
            job_id=job_id,
            project_id=project_id,
            user_id=user_id,
            intent=intent,
            status=JobStatus.PENDING,
            execution_graph=None,
            current_execution_id=None,
            iterations=0,
            max_iterations=max_iterations,
            checkpoint_data={},
            artifacts=[],
            events=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {},
            idempotency_key=idempotency_key,
            owner=owner,
        )
        self._jobs[job_id] = job
        if idempotency_key:
            self._idempotency[idempotency_key] = job_id
        self.event_stream.emit(job_id, EventType.JOB_CREATED, {"intent": intent, "job_id": str(job_id)})
        return job

    def get_job(self, job_id: UUID) -> Optional[IntelligentJob]:
        return self._jobs.get(job_id)

    def update_status(self, job_id: UUID, status: JobStatus) -> Optional[IntelligentJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.status = status
        job.updated_at = datetime.utcnow()
        if status == JobStatus.RUNNING and not job.started_at:
            job.started_at = datetime.utcnow()
        if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            job.completed_at = datetime.utcnow()
        return job

    def record_checkpoint(self, job_id: UUID, checkpoint_data: Dict[str, Any]) -> Optional[IntelligentJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.checkpoint_data = checkpoint_data
        job.status = JobStatus.CHECKPOINTED
        job.updated_at = datetime.utcnow()
        self.event_stream.emit(job_id, EventType.CHECKPOINT_CREATED, {"checkpoint": checkpoint_data})
        return job

    def resume_from_checkpoint(self, job_id: UUID) -> Optional[ExecutionGraph]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        checkpoint = job.checkpoint_data.get("execution_graph")
        if checkpoint:
            graph = ExecutionGraph.from_dict(checkpoint)
            job.execution_graph = graph
            job.status = JobStatus.RUNNING
            job.updated_at = datetime.utcnow()
            self.event_stream.emit(job_id, EventType.JOB_RESUMED, {"from_checkpoint": True})
            return graph
        return None

    def add_artifact(self, job_id: UUID, artifact: Dict[str, Any]) -> Optional[IntelligentJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        artifact["artifact_id"] = str(uuid4())
        artifact["job_id"] = str(job_id)
        artifact["created_at"] = datetime.utcnow().isoformat()
        job.artifacts.append(artifact)
        job.updated_at = datetime.utcnow()
        self.event_stream.emit(job_id, EventType.ARTIFACT_CREATED, artifact)
        return job

    def get_artifacts(self, job_id: UUID) -> List[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        if not job:
            return []
        return list(job.artifacts)

    def get_events(self, job_id: UUID, after_sequence: int = 0) -> List[Dict[str, Any]]:
        events = self.event_stream.get_events(job_id, after_sequence)
        return [e.to_dict() for e in events]

    def cancel_job(self, job_id: UUID) -> Optional[IntelligentJob]:
        return self.update_status(job_id, JobStatus.CANCELLED)

    def list_jobs(self, owner: Optional[str] = None) -> List[IntelligentJob]:
        jobs = list(self._jobs.values())
        if owner:
            jobs = [j for j in jobs if j.owner == owner]
        return jobs
