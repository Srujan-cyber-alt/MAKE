"""
MAKE Autonomous Agent Core V2 — Database Models.

SQLAlchemy models for persistent intelligence state.
"""

from __future__ import annotations
from sqlalchemy import (
    Column, String, DateTime, Float, Integer, Boolean,
    ForeignKey, Text, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.sqlite import BLOB
from typing import Any, Dict
from uuid import UUID

Base = declarative_base()


class IntelligentJobDB(Base):
    __tablename__ = "intelligent_jobs"

    job_id = Column(String(36), primary_key=True)
    project_id = Column(String(36), nullable=True)
    user_id = Column(String(36), nullable=True)
    intent = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    current_execution_id = Column(String(36), nullable=True)
    iterations = Column(Integer, default=0)
    max_iterations = Column(Integer, default=5)
    checkpoint_data = Column(Text, nullable=True)
    artifacts = Column(Text, nullable=True)
    events = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    record_metadata = Column(Text, nullable=True)
    idempotency_key = Column(String(255), nullable=True, unique=True)
    owner = Column(String(255), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "intent": self.intent,
            "status": self.status,
            "current_execution_id": self.current_execution_id,
            "iterations": self.iterations,
            "max_iterations": self.max_iterations,
            "checkpoint_data": json.loads(self.checkpoint_data) if self.checkpoint_data else {},
            "artifacts": json.loads(self.artifacts) if self.artifacts else [],
            "events": json.loads(self.events) if self.events else [],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": json.loads(self.record_metadata) if self.record_metadata else {},
            "idempotency_key": self.idempotency_key,
            "owner": self.owner,
        }


class ExecutionGraphDB(Base):
    __tablename__ = "execution_graphs"

    graph_id = Column(String(36), primary_key=True)
    execution_id = Column(String(36), nullable=False, unique=True)
    root_node_id = Column(String(36), nullable=True)
    graph_data = Column(Text, nullable=False)
    completed = Column(Boolean, default=False)
    final_artifact_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            "graph_id": self.graph_id,
            "execution_id": self.execution_id,
            "root_node_id": self.root_node_id,
            "graph_data": json.loads(self.graph_data),
            "completed": self.completed,
            "final_artifact_id": self.final_artifact_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ArtifactDB(Base):
    __tablename__ = "intelligent_artifacts"

    artifact_id = Column(String(36), primary_key=True)
    job_id = Column(String(36), nullable=False)
    execution_id = Column(String(36), nullable=False)
    parent_artifact = Column(String(36), nullable=True)
    version = Column(Integer, default=1)
    tool = Column(String(100), nullable=False)
    parameters = Column(Text, nullable=True)
    provenance = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True)
    storage_path = Column(Text, nullable=True)
    status = Column(String(50), default="created")
    created_at = Column(DateTime, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            "artifact_id": self.artifact_id,
            "job_id": self.job_id,
            "execution_id": self.execution_id,
            "parent_artifact": self.parent_artifact,
            "version": self.version,
            "tool": self.tool,
            "parameters": json.loads(self.parameters) if self.parameters else {},
            "provenance": json.loads(self.provenance) if self.provenance else {},
            "content_hash": self.content_hash,
            "storage_path": self.storage_path,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProjectMemoryDB(Base):
    __tablename__ = "project_memory"

    memory_id = Column(String(36), primary_key=True)
    project_id = Column(String(36), nullable=False, unique=True)
    state_data = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            "memory_id": self.memory_id,
            "project_id": self.project_id,
            "state_data": json.loads(self.state_data),
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EventDB(Base):
    __tablename__ = "intelligence_events"

    event_id = Column(String(36), primary_key=True)
    job_id = Column(String(36), nullable=False, index=True)
    execution_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    payload = Column(Text, nullable=True)
    sequence_number = Column(Integer, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            "event_id": self.event_id,
            "job_id": self.job_id,
            "execution_id": self.execution_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "payload": json.loads(self.payload) if self.payload else {},
            "sequence_number": self.sequence_number,
        }
