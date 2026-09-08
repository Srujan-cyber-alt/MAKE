"""Schemas and enums for the MAKE Intelligence Core V2 — Mission subsystem.

These are kept separate from ``app.intelligence.schemas`` to avoid touching
the frozen V1 schemas.  All mission-level enumerations and pydantic models live
here.
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
    """Mission lifecycle states (mirrors spec section 16)."""
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
    """States for individual mission tasks."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    PAUSED = "paused"


class ApprovalState(str, enum.Enum):
    """Approval gate states (spec section 14)."""
    WAITING = "waiting"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Operator(str, enum.Enum):
    """Dependency operators in a task graph."""
    AND = "and"
    OR = "or"


class EvaluationVerdict(str, enum.Enum):
    """Evaluation engine verdicts (spec section 6)."""
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    BLOCKED_EXTERNAL = "blocked_external"


class VerificationVerdict(str, enum.Enum):
    """Verification engine verdicts (spec section 7)."""
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED_EXTERNAL = "blocked_external"


class FailureType(str, enum.Enum):
    """Failure classification (spec section 8)."""
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


class EventType(str, enum.Enum):
    """Timeline / observation event types."""
    CREATED = "created"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRIED = "retried"
    CANCELLED = "cancelled"
    RECOVERED = "recovered"
    CHECKPOINT = "checkpoint"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    REPLANNED = "replan"
    BLOCKED = "blocked"
    RESUMED = "resumed"
    PAUSED = "paused"
    OBSERVATION = "observation"


class QualityGate(str, enum.Enum):
    """Explicit gates (spec section 19)."""
    PLAN_GATE = "plan_gate"
    INPUT_GATE = "input_gate"
    RESOURCE_GATE = "resource_gate"
    EXECUTION_GATE = "execution_gate"
    ARTIFACT_GATE = "artifact_gate"
    QUALITY_GATE = "quality_gate"
    VERIFICATION_GATE = "verification_gate"
    COMPLETION_GATE = "completion_gate"


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class Criterion(BaseModel):
    """A single verification requirement attached to a task."""
    metric: str
    operator: str = "eq"
    target: Any = None
    description: str = ""


class TaskPlan(BaseModel):
    """A task definition produced by the planner."""
    task_id: str = Field(default_factory=lambda: f"task_{uuid4().hex[:8]}")
    parent_task_id: Optional[str] = None
    name: str
    objective: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    priority: int = 0
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    verification: List[Criterion] = Field(default_factory=list)
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    tool: str = "reasoning"


class StrategyCandidate(BaseModel):
    """A scored plan alternative (spec section 18 — agent debate)."""
    name: str
    description: str
    tasks: List[TaskPlan] = Field(default_factory=list)
    score: float = 0.0
    rationale: str = ""
    resource_estimate: Dict[str, Any] = Field(default_factory=dict)


class MissionPlan(BaseModel):
    """Full mission plan output from the planner."""
    strategy: str = ""
    tasks: List[TaskPlan] = Field(default_factory=list)
    expected_artifacts: Dict[str, Any] = Field(default_factory=dict)
    fallback_strategies: List[str] = Field(default_factory=list)
    resource_estimate: Dict[str, Any] = Field(default_factory=dict)
    verification_gates: List[QualityGate] = Field(default_factory=list)
    rationale: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MissionCreate(BaseModel):
    goal: str
    plan: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    priority: int = 0
    max_retries: int = 3
    requires_approval: bool = False
    parameters: Optional[Dict[str, Any]] = None


class MissionResponse(BaseModel):
    mission_id: str
    goal: str
    state: MissionState = MissionState.CREATED
    priority: int = 0
    progress: float = 0.0
    milestone_count: int = 0
    task_count: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True
        use_enum_values = False


class MissionStatus(BaseModel):
    mission_id: str
    state: MissionState
    milestones: List[Dict[str, Any]] = Field(default_factory=list)
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    current_milestone: int = 0
    progress: float = 0.0
    error: Optional[str] = None


class MissionProgress(BaseModel):
    mission_id: str
    state: MissionState
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    skipped_tasks: int
    progress: float
    current_task: Optional[str] = None


class ApprovalRequest(BaseModel):
    approver: str = "user"
    notes: Optional[str] = None


class ReplanRequest(BaseModel):
    strategy: str = "adaptive"
    failed_task_id: Optional[str] = None
    new_plan: Optional[Dict[str, Any]] = None


class TimelineEvent(BaseModel):
    timestamp: datetime
    actor: str
    action: str
    state: str
    details: Dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    verification_id: str
    task_id: str
    verdict: VerificationVerdict
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    checks: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
