"""SQLAlchemy ORM models for MAKE Intelligence Core V2 - Missions.

All mission tables use the shared ``INTELLIGENCE_METADATA`` so they are
created by ``init_db()`` alongside the existing Core V1 tables.  They use
``IntelligenceBase`` to inherit the common metadata binding and the
``_uuid`` / ``_now`` helpers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    String, Text, Boolean, Float, Integer, DateTime, ForeignKey, JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.intelligence.models import IntelligenceBase, _uuid, _now
from app.intelligence.schemas import JobState
from app.intelligence.mission_schemas import (
    MissionState, TaskState, MilestoneState, ApprovalState, EventType,
    VerificationVerdict, FailureType, QualityGate, GateStatus,
)


class MissionOrm(IntelligenceBase):
    __tablename__ = "intelligence_missions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[MissionState] = mapped_column(
        SQLEnum(MissionState), default=MissionState.CREATED, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_state: Mapped[ApprovalState] = mapped_column(
        SQLEnum(ApprovalState), default=ApprovalState.PENDING, nullable=False
    )
    plan_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    milestones: Mapped[List["MissionMilestoneOrm"]] = relationship(
        "MissionMilestoneOrm", back_populates="mission",
        cascade="all, delete-orphan", order_by="MissionMilestoneOrm.index",
    )
    tasks: Mapped[List["MissionTaskOrm"]] = relationship(
        "MissionTaskOrm", back_populates="mission",
        cascade="all, delete-orphan",
    )
    timeline: Mapped[List["MissionTimelineEventOrm"]] = relationship(
        "MissionTimelineEventOrm", back_populates="mission",
        cascade="all, delete-orphan", order_by="MissionTimelineEventOrm.timestamp",
    )
    checkpoints: Mapped[List["MissionCheckpointOrm"]] = relationship(
        "MissionCheckpointOrm", back_populates="mission",
        cascade="all, delete-orphan", order_by="MissionCheckpointOrm.created_at",
    )
    gates: Mapped[List["MissionGateOrm"]] = relationship(
        "MissionGateOrm", back_populates="mission",
        cascade="all, delete-orphan",
    )


class MissionMilestoneOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[MilestoneState] = mapped_column(
        SQLEnum(MilestoneState), default=MilestoneState.PENDING, nullable=False
    )
    index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    mission: Mapped["MissionOrm"] = relationship("MissionOrm", back_populates="milestones")
    tasks: Mapped[List["MissionTaskOrm"]] = relationship(
        "MissionTaskOrm", back_populates="milestone",
    )


class MissionTaskOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    milestone_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parent_task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    tool_type: Mapped[str] = mapped_column(String(50), default="reasoning", nullable=False)
    resource: Mapped[str] = mapped_column(String(50), default="cpu", nullable=False)
    state: Mapped[TaskState] = mapped_column(
        SQLEnum(TaskState), default=TaskState.PENDING, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    inputs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    outputs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    verification_criteria: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    constraints: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    depends_on: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    execution_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    mission: Mapped["MissionOrm"] = relationship("MissionOrm", back_populates="tasks")
    milestone: Mapped[Optional["MissionMilestoneOrm"]] = relationship(
        "MissionMilestoneOrm", back_populates="tasks",
    )
    observations: Mapped[List["MissionObservationOrm"]] = relationship(
        "MissionObservationOrm", back_populates="task",
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[List["MissionArtifactOrm"]] = relationship(
        "MissionArtifactOrm", back_populates="task",
        cascade="all, delete-orphan",
    )
    verifications: Mapped[List["MissionVerificationOrm"]] = relationship(
        "MissionVerificationOrm", back_populates="task",
        cascade="all, delete-orphan",
    )


class MissionDependencyOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_dependencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    from_task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    to_task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class MissionTimelineEventOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_timeline"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    mission: Mapped["MissionOrm"] = relationship("MissionOrm", back_populates="timeline")


class MissionCheckpointOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    current_task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    completed_task_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    failed_task_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    pending_task_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    retry_counts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    plan_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    observations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    decisions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    resource_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class MissionGateOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_gates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    gate_name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[GateStatus] = mapped_column(
        SQLEnum(GateStatus), default=GateStatus.NOT_RUN, nullable=False
    )
    evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class MissionObservationOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    execution_state: Mapped[str] = mapped_column(String(50), nullable=False)
    artifacts: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    errors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resource_usage: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tool_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    provenance: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    task: Mapped[Optional["MissionTaskOrm"]] = relationship("MissionTaskOrm", back_populates="observations")


class MissionArtifactOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    try:
        from sqlalchemy.orm import Mapped as _M  # noqa: F811
    except Exception:
        pass
    artifact_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    input_digest: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provenance: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    task: Mapped["MissionTaskOrm"] = relationship("MissionTaskOrm", back_populates="artifacts")


class MissionVerificationOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    verification_id: Mapped[str] = mapped_column(String(36), nullable=False)
    verdict: Mapped[VerificationVerdict] = mapped_column(
        SQLEnum(VerificationVerdict), nullable=False
    )
    evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    checks: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    failure_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class MissionAttemptOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    strategy: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class MissionDecisionOrm(IntelligenceBase):
    __tablename__ = "intelligence_mission_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_missions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(255), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
