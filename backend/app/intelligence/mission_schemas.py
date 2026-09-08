"""Pydantic schemas and enums for MAKE Intelligence Core V2 - Missions."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.intelligence.schemas import JobState


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
    RETRYING = "retrying"
    REPLANNING = "replanning"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED_EXTERNAL = "blocked_external"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskState(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    CHECKPOINTED = "checkpointed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    BLOCKED_EXTERNAL = "blocked_external"
    WAITING_APPROVAL = "waiting_approval"


class MilestoneState(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalState(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Operator(str, enum.Enum):
    EQ = "eq"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    EXISTS = "exists"
    CONTAINS = "contains"


class EventType(str, enum.Enum):
    STATE_CHANGE = "state_change"
    CHECKPOINT = "checkpoint"
    APPROVAL = "approval"
    FAILURE = "failure"
    RECOVERY = "recovery"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


class VerificationVerdict(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    BLOCKED_EXTERNAL = "blocked_external"


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


class QualityGate(str, enum.Enum):
    PLAN_GATE = "plan_gate"
    INPUT_GATE = "input_gate"
    RESOURCE_GATE = "resource_gate"
    EXECUTION_GATE = "execution_gate"
    ARTIFACT_GATE = "artifact_gate"
    QUALITY_GATE = "quality_gate"
    VERIFICATION_GATE = "verification_gate"
    COMPLETION_GATE = "completion_gate"


class GateStatus(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED_EXTERNAL = "blocked_external"
    NOT_RUN = "not_run"


class CriterionSpec(BaseModel):
    metric: str
    operator: Operator = Operator.EQ
    threshold: Any = None
    description: str = ""


class TaskSpec(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_task_id: Optional[str] = None
    milestone_index: int = 0
    objective: str
    tool: str = "reasoning"
    resource: str = "cpu"
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    priority: int = 0
    max_retries: int = 3
    retry_count: int = 0
    verification_criteria: List[CriterionSpec] = Field(default_factory=list)


class MissionPlan(BaseModel):
    strategy: str = "default"
    tasks: List[TaskSpec] = Field(default_factory=list)
    fallback_strategies: List[str] = Field(default_factory=list)
    expected_artifacts: List[str] = Field(default_factory=list)
    verification_gates: List[str] = Field(default_factory=list)
    resource_estimate: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class MissionCreate(BaseModel):
    goal: str
    plan: Optional[List[Dict[str, Any]]] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    priority: int = 0
    max_retries: int = 3
    requires_approval: bool = False
    parameters: Optional[Dict[str, Any]] = None


class MissionResponse(BaseModel):
    mission_id: str
    goal: str
    state: MissionState
    priority: int
    progress: float
    milestone_count: int
    task_count: int
    completed_tasks: int
    failed_tasks: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
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
    progress: float
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    pending_tasks: int
    running_tasks: int
    milestones_total: int
    milestones_completed: int


class ApprovalRequest(BaseModel):
    approver: str
    notes: Optional[str] = None


class ReplanRequest(BaseModel):
    strategy: str = "adapt"
    reason: Optional[str] = None


class TimelineEvent(BaseModel):
    timestamp: datetime
    actor: str
    action: str
    state: str
    result: Optional[str] = None
