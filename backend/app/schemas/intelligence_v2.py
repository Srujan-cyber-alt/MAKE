"""
MAKE Autonomous Agent Core V2 — Schemas.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from uuid import UUID
from datetime import datetime


class JobStatusSchema(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"
    CHECKPOINTED = "checkpointed"


class QualityDecisionSchema(str, Enum):
    PASS = "pass"
    REVISE = "revise"
    FAIL = "fail"


class ExecutionStateSchema(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    CHECKPOINTED = "checkpointed"
    OBSERVING = "observing"
    CRITIQUING = "critiquing"
    REVISING = "revising"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreateJobRequest(BaseModel):
    intent: str = Field(..., min_length=1, max_length=10000)
    project_id: Optional[UUID] = None
    max_iterations: int = Field(default=5, ge=1, le=20)
    metadata: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None
    owner: Optional[str] = None


class JobResponse(BaseModel):
    job_id: UUID
    project_id: Optional[UUID]
    user_id: Optional[str]
    intent: str
    status: JobStatusSchema
    iterations: int
    max_iterations: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    owner: Optional[str]
    metadata: Dict[str, Any]


class ExecutionGraphResponse(BaseModel):
    execution_id: UUID
    root_node_id: Optional[UUID]
    nodes: Dict[str, Any]
    edges: Dict[str, List[str]]
    completed: bool
    final_artifact_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class ArtifactResponse(BaseModel):
    artifact_id: str
    job_id: str
    execution_id: str
    parent_artifact: Optional[str]
    version: int
    tool: str
    parameters: Dict[str, Any]
    provenance: Dict[str, Any]
    content_hash: Optional[str]
    storage_path: Optional[str]
    status: str
    created_at: datetime


class QualityDecisionResponse(BaseModel):
    decision_id: UUID
    execution_id: UUID
    decision: QualityDecisionSchema
    reason: str
    evidence: Dict[str, Any]
    created_at: datetime


class EventResponse(BaseModel):
    event_id: UUID
    job_id: UUID
    event_type: str
    payload: Dict[str, Any]
    created_at: datetime
    sequence: int


class ProjectStateResponse(BaseModel):
    project_id: UUID
    entities: Dict[str, Any]
    versions: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
