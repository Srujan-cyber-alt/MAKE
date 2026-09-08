"""SQLAlchemy ORM models for the MAKE Intelligence Core.

These models use an independent ``MetaData`` (``INTELLIGENCE_METADATA``)
so they never collide with the frozen Video/Image subsystem models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, Boolean, Float, Integer, DateTime, ForeignKey, JSON,
    Enum as SQLEnum, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.intelligence.database import INTELLIGENCE_METADATA
from app.intelligence.schemas import (
    JobState, JobFailureState, EntityType, RelationType,
    IntentCategory, PlanStatus, ToolType, PersonalContextStatus,
)


class IntelligenceBase(DeclarativeBase):
    metadata = INTELLIGENCE_METADATA


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class IntelligenceJob(IntelligenceBase):
    __tablename__ = "intelligence_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    parent_job_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("intelligence_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    request: Mapped[str] = mapped_column(Text, nullable=False)
    intent_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    state: Mapped[JobState] = mapped_column(SQLEnum(JobState), default=JobState.QUEUED, nullable=False)
    failure_state: Mapped[Optional[JobFailureState]] = mapped_column(SQLEnum(JobFailureState), nullable=True)

    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=300.0, nullable=False)

    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    inputs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    plan: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    plan_status: Mapped[PlanStatus] = mapped_column(SQLEnum(PlanStatus), default=PlanStatus.DRAFT, nullable=False)
    intent: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resumable_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    selected_tool: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    selected_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    execution_log: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    children: Mapped[list["IntelligenceJob"]] = relationship(
        "IntelligenceJob", backref="parent", remote_side="IntelligenceJob.id"
    )


class JobCheckpointOrm(IntelligenceBase):
    __tablename__ = "intelligence_job_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("intelligence_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(String(36), nullable=False)
    state: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    completed_steps: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class JobLogOrm(IntelligenceBase):
    __tablename__ = "intelligence_job_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("intelligence_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    step: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class MemoryEntityOrm(IntelligenceBase):
    __tablename__ = "intelligence_memory_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_type: Mapped[EntityType] = mapped_column(SQLEnum(EntityType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(100), default="default", nullable=False, index=True)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False, onupdate=_now)
    unique_together = None


class MemoryRelationOrm(IntelligenceBase):
    __tablename__ = "intelligence_memory_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_entity_id: Mapped[str] = mapped_column(
        ForeignKey("intelligence_memory_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_entity_id: Mapped[str] = mapped_column(
        ForeignKey("intelligence_memory_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[RelationType] = mapped_column(SQLEnum(RelationType), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class GraphNodeOrm(IntelligenceBase):
    __tablename__ = "intelligence_graph_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False, onupdate=_now)


class GraphEdgeOrm(IntelligenceBase):
    __tablename__ = "intelligence_graph_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_node_id: Mapped[str] = mapped_column(
        ForeignKey("intelligence_graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[str] = mapped_column(
        ForeignKey("intelligence_graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class DecisionRecordOrm(IntelligenceBase):
    __tablename__ = "intelligence_decision_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    step: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(255), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class ArtifactRecordOrm(IntelligenceBase):
    __tablename__ = "intelligence_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("intelligence_jobs.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    input_digest: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    configuration: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    execution_state: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    provenance: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PersonalContextOrm(IntelligenceBase):
    __tablename__ = "intelligence_personal_context"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(100), default="default", nullable=False, index=True)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[PersonalContextStatus] = mapped_column(
        SQLEnum(PersonalContextStatus), default=PersonalContextStatus.PENDING_APPROVAL, nullable=False
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False, onupdate=_now)
