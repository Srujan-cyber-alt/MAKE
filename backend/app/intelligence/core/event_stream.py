"""
MAKE Autonomous Agent Core V2 — Event Stream.

Persistent job events with replay capability.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime


class EventType(str, Enum):
    JOB_CREATED = "job_created"
    INTENT_PARSED = "intent_parsed"
    PLAN_CREATED = "plan_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    CHECKPOINT_CREATED = "checkpoint_created"
    OBSERVATION_CREATED = "observation_created"
    CRITIQUE_CREATED = "critique_created"
    REVISION_CREATED = "revision_created"
    ARTIFACT_CREATED = "artifact_created"
    QUALITY_DECISION = "quality_decision"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    JOB_RESUMED = "job_resumed"


@dataclass
class EventRecord:
    event_id: UUID
    job_id: UUID
    event_type: EventType
    payload: Dict[str, Any]
    created_at: datetime
    sequence: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "job_id": str(self.job_id),
            "event_type": self.event_type.value,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "sequence": self.sequence,
            "metadata": self.metadata,
        }


class EventStream:
    def __init__(self) -> None:
        self._events: Dict[UUID, List[EventRecord]] = {}
        self._sequences: Dict[UUID, int] = {}

    def emit(self, job_id: UUID, event_type: EventType, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> EventRecord:
        seq = self._sequences.get(job_id, 0) + 1
        self._sequences[job_id] = seq
        event = EventRecord(
            event_id=uuid4(),
            job_id=job_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.utcnow(),
            sequence=seq,
            metadata=metadata or {},
        )
        self._events.setdefault(job_id, []).append(event)
        return event

    def get_events(self, job_id: UUID, after_sequence: int = 0) -> List[EventRecord]:
        events = self._events.get(job_id, [])
        return [e for e in events if e.sequence > after_sequence]

    def get_all_events(self, job_id: UUID) -> List[EventRecord]:
        return list(self._events.get(job_id, []))

    def get_latest_sequence(self, job_id: UUID) -> int:
        return self._sequences.get(job_id, 0)
