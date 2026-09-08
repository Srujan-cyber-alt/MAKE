"""
MAKE Autonomous Agent Core V2 — Database persistence layer.

Provides persistent storage for jobs, events, graphs, and artifacts.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
import json

from sqlalchemy import create_engine, select, insert, update, delete
from sqlalchemy.orm import sessionmaker, Session

from app.models.intelligence_v2 import (
    IntelligentJobDB,
    ExecutionGraphDB,
    ArtifactDB,
    ProjectMemoryDB,
    EventDB,
    Base as IntelligenceBase,
)


class IntelligencePersistence:
    def __init__(self, database_url: str = "sqlite:///intelligence_v2.db") -> None:
        self.engine = create_engine(database_url, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        IntelligenceBase.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def save_job(self, job_data: Dict[str, Any]) -> None:
        with self.get_session() as session:
            db_job = session.get(IntelligentJobDB, job_data["job_id"])
            allowed_keys = {
                "job_id", "project_id", "user_id", "intent", "status",
                "current_execution_id", "iterations", "max_iterations",
                "checkpoint_data", "artifacts", "events",
                "started_at", "completed_at", "created_at", "updated_at",
                "record_metadata", "idempotency_key", "owner",
            }
            datetime_fields = {"started_at", "completed_at", "created_at", "updated_at"}
            if db_job:
                for key, value in job_data.items():
                    if key not in allowed_keys:
                        continue
                    if key == "checkpoint_data" and value is not None:
                        value = json.dumps(value)
                    elif key == "artifacts" and value is not None:
                        value = json.dumps(value)
                    elif key == "events" and value is not None:
                        value = json.dumps(value)
                    elif key == "metadata" and value is not None:
                        value = json.dumps(value)
                        key = "record_metadata"
                    if key in datetime_fields and isinstance(value, str):
                        value = datetime.fromisoformat(value)
                    setattr(db_job, key, value)
            else:
                job_data_copy = {k: v for k, v in job_data.items() if k in allowed_keys}
                for key in datetime_fields:
                    if key in job_data_copy and isinstance(job_data_copy[key], str):
                        job_data_copy[key] = datetime.fromisoformat(job_data_copy[key])
                job_data_copy["checkpoint_data"] = json.dumps(job_data_copy.get("checkpoint_data"))
                job_data_copy["artifacts"] = json.dumps(job_data_copy.get("artifacts", []))
                job_data_copy["events"] = json.dumps(job_data_copy.get("events", []))
                job_data_copy["record_metadata"] = json.dumps(job_data_copy.pop("metadata", {}))
                db_job = IntelligentJobDB(**job_data_copy)
                session.add(db_job)
            session.commit()

    def load_job(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            db_job = session.get(IntelligentJobDB, str(job_id))
            if not db_job:
                return None
            return db_job.to_dict()

    def load_all_jobs(self) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            jobs = session.execute(select(IntelligentJobDB)).scalars().all()
            return [j.to_dict() for j in jobs]

    def delete_job(self, job_id: UUID) -> bool:
        with self.get_session() as session:
            db_job = session.get(IntelligentJobDB, str(job_id))
            if not db_job:
                return False
            session.delete(db_job)
            session.commit()
            return True

    def save_graph(self, graph_data: Dict[str, Any]) -> None:
        with self.get_session() as session:
            graph_id = graph_data["execution_id"]
            db_graph = session.get(ExecutionGraphDB, graph_id)
            graph_json = json.dumps(graph_data)
            if db_graph:
                db_graph.graph_data = graph_json
                db_graph.completed = graph_data.get("completed", False)
                db_graph.final_artifact_id = graph_data.get("final_artifact_id")
                db_graph.updated_at = datetime.utcnow()
            else:
                db_graph = ExecutionGraphDB(
                    graph_id=graph_id,
                    execution_id=graph_data["execution_id"],
                    root_node_id=graph_data.get("root_node_id"),
                    graph_data=graph_json,
                    completed=graph_data.get("completed", False),
                    final_artifact_id=graph_data.get("final_artifact_id"),
                    created_at=datetime.fromisoformat(graph_data["created_at"]),
                    updated_at=datetime.fromisoformat(graph_data["updated_at"]),
                )
                session.add(db_graph)
            session.commit()

    def load_graph(self, execution_id: UUID) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            db_graph = session.get(ExecutionGraphDB, str(execution_id))
            if not db_graph:
                return None
            return json.loads(db_graph.graph_data)

    def save_artifact(self, artifact_data: Dict[str, Any]) -> None:
        with self.get_session() as session:
            db_artifact = session.get(ArtifactDB, artifact_data["artifact_id"])
            artifact_copy = dict(artifact_data)
            artifact_copy["parameters"] = json.dumps(artifact_copy.get("parameters", {}))
            artifact_copy["provenance"] = json.dumps(artifact_copy.get("provenance", {}))
            if db_artifact:
                for key, value in artifact_copy.items():
                    setattr(db_artifact, key, value)
            else:
                db_artifact = ArtifactDB(**artifact_copy)
                session.add(db_artifact)
            session.commit()

    def load_artifacts(self, job_id: UUID) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            artifacts = session.execute(select(ArtifactDB).where(ArtifactDB.job_id == str(job_id))).scalars().all()
            return [a.to_dict() for a in artifacts]

    def save_event(self, event_data: Dict[str, Any]) -> None:
        with self.get_session() as session:
            db_event = EventDB(
                event_id=event_data["event_id"],
                job_id=event_data["job_id"],
                execution_id=event_data["execution_id"],
                event_type=event_data["event_type"],
                timestamp=datetime.fromisoformat(event_data["created_at"]) if isinstance(event_data["created_at"], str) else event_data["created_at"],
                payload=json.dumps(event_data.get("payload", {})),
                sequence_number=event_data["sequence"],
            )
            session.add(db_event)
            session.commit()

    def load_events(self, job_id: UUID, after_sequence: int = 0) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            events = session.execute(
                select(EventDB)
                .where(EventDB.job_id == str(job_id))
                .where(EventDB.sequence_number > after_sequence)
                .order_by(EventDB.sequence_number)
            ).scalars().all()
            return [e.to_dict() for e in events]

    def load_all_events(self, job_id: UUID) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            events = session.execute(
                select(EventDB)
                .where(EventDB.job_id == str(job_id))
                .order_by(EventDB.sequence_number)
            ).scalars().all()
            return [e.to_dict() for e in events]
