from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class ReplayStatus(str, Enum):
    PENDING = "pending"
    REPLAYING = "replaying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReplayResult:
    replay_id: UUID
    mission_id: UUID
    status: ReplayStatus
    replayed_tasks: List[str]
    replayed_results: Dict[str, Any]
    fidelity_score: Optional[float] = None
    validated: bool = False
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class ReplayEngine:
    def __init__(self, db_session_factory=None) -> None:
        self.db_session_factory = db_session_factory
        self._evidence_store: Dict[str, Dict[str, Any]] = {}

    def store_evidence(self, mission_id: str, evidence: Dict[str, Any]) -> None:
        self._evidence_store[mission_id] = evidence

    def get_evidence(self, mission_id: str) -> Dict[str, Any]:
        return self._evidence_store.get(mission_id, {})

    async def replay_mission(self, mission_id: str) -> ReplayResult:
        replay_id = uuid4()
        evidence = self.get_evidence(mission_id)
        if not evidence:
            return ReplayResult(
                replay_id=replay_id,
                mission_id=UUID(mission_id) if mission_id else uuid4(),
                status=ReplayStatus.FAILED,
                replayed_tasks=[],
                replayed_results={},
                error="No evidence found for mission",
            )
        replayed_tasks = evidence.get("tasks", [])
        replayed_results = evidence.get("results", {})
        fidelity = evidence.get("fidelity_score", 1.0)
        return ReplayResult(
            replay_id=replay_id,
            mission_id=UUID(mission_id),
            status=ReplayStatus.COMPLETED,
            replayed_tasks=replayed_tasks,
            replayed_results=replayed_results,
            fidelity_score=fidelity,
            validated=True,
        )
