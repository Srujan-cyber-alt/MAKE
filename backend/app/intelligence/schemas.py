"""Shared enumerations and Pydantic schemas for the MAKE Intelligence Core."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class JobState(str, enum.Enum):
    """Lifecycle states for a persistent intelligence job."""

    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    CHECKPOINTED = "checkpointed"
    COMPLETED = "completed"

    # failure / control states
    PAUSED = "paused"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERABLE = "recoverable"


class JobFailureState(str, enum.Enum):
    """Explicit failure sub-states recorded by the failure-recovery layer."""

    PAUSED = "paused"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERABLE = "recoverable"


class IntentCategory(str, enum.Enum):
    CREATIVE = "creative"
    EDITING = "editing"
    ANALYSIS = "analysis"
    MEMORY = "memory"
    CONVERSATION = "conversation"
    REASONING = "reasoning"
    UNKNOWN = "unknown"


class EntityType(str, enum.Enum):
    PERSON = "person"
    IDENTITY = "identity"
    OBJECT = "object"
    LOCATION = "location"
    PROJECT = "project"
    SCENE = "scene"
    ASSET = "asset"
    PREFERENCE = "preference"
    DECISION = "decision"
    RELATIONSHIP = "relationship"
    JOB = "job"


class RelationType(str, enum.Enum):
    OWNS = "owns"
    LOCATED_AT = "located_at"
    BELONGS_TO = "belongs_to"
    CONTAINS = "contains"
    PRODUCED = "produced"
    REFERENCES = "references"
    DEPENDS_ON = "depends_on"
    APPEARS_IN = "appears_in"
    LOCATED_IN = "located_in"
    MEMBER_OF = "member_of"
    CUSTOM = "custom"


class PlanStatus(str, enum.Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    CRITIQUED = "critiqued"
    EXECUTABLE = "executable"
    FAILED = "failed"


class ToolType(str, enum.Enum):
    MAKE_VIDEO = "make_video"
    MAKE_IMAGE = "make_image"
    IMAGE_EDITING = "image_editing"
    VISUAL_ANALYSIS = "visual_analysis"
    SEARCH_KNOWLEDGE = "search_knowledge"
    MEMORY = "memory"
    REASONING = "reasoning"
    OTHER = "other"


class ArtifactStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PersonalContextStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Intent Engine
# ---------------------------------------------------------------------------


class ConstraintSpec(BaseModel):
    kind: str
    description: str
    value: Optional[Any] = None
    severity: str = "error"


class EntityRef(BaseModel):
    type: EntityType
    name: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class Intent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    category: IntentCategory
    raw_request: str
    description: str = ""
    priority: int = 0
    constraints: List[ConstraintSpec] = Field(default_factory=list)
    entities: List[EntityRef] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required_capabilities: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IntentResult(BaseModel):
    intent: Intent
    clarity: float = 1.0
    requires_clarification: bool = False
    clarification_questions: List[str] = Field(default_factory=list)
    alternative_interpretations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Reasoning Engine
# ---------------------------------------------------------------------------


class PlanStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    action: str
    tool: ToolType
    description: str = ""
    inputs: Dict[str, Any] = Field(default_factory=dict)
    expected_outputs: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 120.0


class Plan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    intent_id: str
    status: PlanStatus = PlanStatus.DRAFT
    steps: List[PlanStep] = Field(default_factory=list)
    constraints: List[ConstraintSpec] = Field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_duration_seconds: float = 0.0
    rationale: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Consistency Engine
# ---------------------------------------------------------------------------


class DiagnosticSeverity(str, enum.Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ConsistencyDiagnostic(BaseModel):
    code: str
    severity: DiagnosticSeverity
    message: str
    affected_step_ids: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class ConsistencyReport(BaseModel):
    plan_id: str
    passed: bool
    diagnostics: List[ConsistencyDiagnostic] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Creative Director
# ---------------------------------------------------------------------------


class CreativeDecision(BaseModel):
    composition: Dict[str, Any] = Field(default_factory=dict)
    camera: Dict[str, Any] = Field(default_factory=dict)
    lighting: Dict[str, Any] = Field(default_factory=dict)
    materials: Dict[str, Any] = Field(default_factory=dict)
    environment: Dict[str, Any] = Field(default_factory=dict)
    subject: Dict[str, Any] = Field(default_factory=dict)
    mood: str = ""
    realism: str = ""
    cinematic_intent: str = ""
    rationale: str = ""
    notes: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Visual Planning Engine
# ---------------------------------------------------------------------------


class ShotPlan(BaseModel):
    shot_number: int
    description: str
    duration_seconds: float
    camera_movement: str = "static"
    composition: Dict[str, Any] = Field(default_factory=dict)
    creative_notes: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)


class ScenePlan(BaseModel):
    scene_number: int
    description: str
    shots: List[ShotPlan] = Field(default_factory=list)
    creative_decision: Optional[CreativeDecision] = None


class VisualPlan(BaseModel):
    scenes: List[ScenePlan] = Field(default_factory=list)
    overall_notes: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tool Router
# ---------------------------------------------------------------------------


class RoutingDecision(BaseModel):
    tool: ToolType
    reason: str
    confidence: float
    selected_model: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    alternative_tools: List[ToolType] = Field(default_factory=list)


class ExecutionRequest(BaseModel):
    tool: ToolType
    action: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 120.0


class ExecutionResult(BaseModel):
    tool: ToolType
    success: bool
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Persistent Job System
# ---------------------------------------------------------------------------


class JobCreate(BaseModel):
    request: str
    intent_category: Optional[IntentCategory] = None
    priority: int = 0
    inputs: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    max_retries: int = 3
    timeout_seconds: float = 300.0
    parent_job_id: Optional[str] = None
    requires_approval: bool = False


class CheckpointSpec(BaseModel):
    step_id: str
    state: Dict[str, Any] = Field(default_factory=dict)
    progress: float = 0.0
    completed_steps: List[str] = Field(default_factory=list)
    notes: str = ""


class JobResponse(BaseModel):
    job_id: str
    state: JobState
    progress: float
    created_at: datetime
    updated_at: datetime
    intent: Optional[Intent] = None
    plan: Optional[Plan] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Artifact Manager
# ---------------------------------------------------------------------------


class ArtifactRecord(BaseModel):
    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    type: str
    path: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    model_version: Optional[str] = None
    input_digest: Optional[str] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    execution_state: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class PersonalContextRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    key: str
    scope: str
    data: Dict[str, Any] = Field(default_factory=dict)
    status: PersonalContextStatus = PersonalContextStatus.PENDING_APPROVAL
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryEntityRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    entity_type: EntityType
    name: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    scope: str = "default"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GraphNodeRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    entity_type: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_node_id: str
    target_node_id: str
    relation_type: str
    weight: float = 1.0
    attributes: Dict[str, Any] = Field(default_factory=dict)


class DecisionRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: Optional[str] = None
    step: str
    decision: str
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)
