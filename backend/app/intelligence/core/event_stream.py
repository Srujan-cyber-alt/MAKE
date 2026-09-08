"""
MAKE Autonomous Agent Core V2 — Event Stream.

Persistent job events with replay capability.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime

if TYPE_CHECKING:
    from app.intelligence.core.persistence import IntelligencePersistence


class EventType(str, Enum):
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    INTENT_PARSED = "intent_parsed"
    PLAN_CREATED = "plan_created"
    NODE_CREATED = "node_created"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    NODE_RETRIED = "node_retried"
    CHECKPOINT_CREATED = "checkpoint_created"
    JOB_PAUSED = "job_paused"
    JOB_RESUMED = "job_resumed"
    JOB_CANCELLED = "job_cancelled"
    ARTIFACT_CREATED = "artifact_created"
    ARTIFACT_VERIFIED = "artifact_verified"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    CRITIQUE_CREATED = "critique_created"
    PLAN_REVISED = "plan_revised"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    QUALITY_DECISION = "quality_decision"


@dataclass
class EventRecord:
    event_id: UUID
    job_id: UUID
    execution_id: UUID
    event_type: EventType
    payload: Dict[str, Any]
    created_at: datetime
    sequence: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "job_id": str(self.job_id),
            "execution_id": str(self.execution_id),
            "event_type": self.event_type.value,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "sequence": self.sequence,
            "metadata": self.metadata,
        }


class EventStream:
    def __init__(self, persistence: Optional[IntelligencePersistence] = None) -> None:
        self._events: Dict[UUID, List[EventRecord]] = {}
        self._sequences: Dict[UUID, int] = {}
        self.persistence = persistence

    def emit(self, job_id: UUID, event_type: EventType, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None, execution_id: Optional[UUID] = None) -> EventRecord:
        seq = self._sequences.get(job_id, 0) + 1
        self._sequences[job_id] = seq
        execution_id = execution_id or job_id
        event = EventRecord(
            event_id=uuid4(),
            job_id=job_id,
            execution_id=execution_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.utcnow(),
            sequence=seq,
            metadata=metadata or {},
        )
        self._events.setdefault(job_id, []).append(event)
        if self.persistence:
            try:
                self.persistence.save_event(event.to_dict())
            except Exception:
                pass
        return event

    def get_events(self, job_id: UUID, after_sequence: int = 0) -> List[EventRecord]:
        events = self._events.get(job_id, [])
        return [e for e in events if e.sequence > after_sequence]

    def get_all_events(self, job_id: UUID) -> List[EventRecord]:
        return list(self._events.get(job_id, []))

    def get_latest_sequence(self, job_id: UUID) -> int:
        return self._sequences.get(job_id, 0)
