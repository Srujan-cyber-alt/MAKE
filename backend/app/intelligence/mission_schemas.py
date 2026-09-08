"""Schemas for MAKE Intelligence Core V2 — Mission Execution Engine.

Defines enums, request/response models, and evidence types for the
persistent autonomous mission lifecycle.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MissionState(str, enum.Enum):
    CREATED = "created"
    DECOMPOSING = "decomposing"
    PLANNING = "planning"
    VALIDATING = "validating"
    READY = "ready"
    RUNNING = "running"
    OBSERVING = "observing"
    EVALUATING = "evaluating"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PAUSED = "paused"
    RETRYING = "retrying"
    REPLANNING = "replanning"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED_EXTERNAL = "blocked_external"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskState(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    PAUSED = "paused"
    RETRYING = "retrying"


class MilestoneState(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class ApprovalState(str, enum.Enum):
    WAITING = "waiting"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class FailureType(str, enum.Enum):
    TRANSIENT = "transient"
    INPUT_ERROR = "input_error"
    PLANNING_ERROR = "planning_error"
    TOOL_ERROR = "tool_error"
    RESOURCE_ERROR = "resource_error"
    QUALITY_ERROR = "quality_error"
    DEPENDENCY_ERROR = "dependency_error"
    STATE_ERROR = "state_error"
    EXTERNAL_BLOCKER = "external_blocker"
    UNKNOWN = "unknown"


class QualityLevel(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    BLOCKED_EXTERNAL = "blocked_external"


class Operator(str, enum.Enum):
    EQ = "eq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    EXISTS = "exists"


class EvidenceType(str, enum.Enum):
    ARTIFACT = "artifact"
    LOG = "log"
    METRIC = "metric"
    STATE = "state"
    OBSERVATION = "observation"


# ---------------------------------------------------------------------------
# Request / Response pydantic models
# ---------------------------------------------------------------------------


class MissionCreate(BaseModel):
    goal: str
    plan: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    priority: int = 0
    max_retries: int = 3
    requires_approval: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)


class MissionResponse(BaseModel):
    mission_id: str
    goal: str
    state: MissionState
    priority: int
    progress: float
    task_count: int
    completed_tasks: int
    failed_tasks: int
    milestone_count: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class MissionStatus(BaseModel):
    mission_id: str
    state: MissionState
    milestones: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    current_milestone: int
    progress: float
    error: Optional[str] = None


class MissionProgress(BaseModel):
    mission_id: str
    state: MissionState
    overall_progress: float
    completed_tasks: int
    failed_tasks: int
    total_tasks: int
    current_step: str
    updated_at: datetime


class PlanStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    action: str
    tool: str
    description: str = ""
    inputs: Dict[str, Any] = Field(default_factory=dict)
    expected_outputs: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    verification: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 300.0
    priority: int = 0
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)


class MissionPlan(BaseModel):
    mission_id: str
    strategy: str
    steps: List[PlanStep]
    expected_artifacts: List[str] = Field(default_factory=list)
    verification_gates: List[Dict[str, Any]] = Field(default_factory=list)
    fallback_strategies: List[Dict[str, Any]] = Field(default_factory=list)
    resource_estimate: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskSummary(BaseModel):
    task_id: str
    mission_id: str
    step_id: str
    state: TaskState
    progress: float
    attempt: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    verification: Optional[QualityLevel] = None


class ApprovalRequest(BaseModel):
    approver: str = "user"
    notes: Optional[str] = None


class ReplanRequest(BaseModel):
    strategy: str = "adaptive"
    reason: Optional[str] = None


class TimelineEvent(BaseModel):
    timestamp: datetime
    actor: str
    action: str
    state: str
    decision: Optional[str] = None
    result: Optional[str] = None


class ExecutionResult(BaseModel):
    success: bool
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)


class VerificationResult(BaseModel):
    verification_id: str
    task_id: str
    evidence: List[Dict[str, Any]]
    checks: List[Dict[str, Any]]
    verdict: QualityLevel
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
