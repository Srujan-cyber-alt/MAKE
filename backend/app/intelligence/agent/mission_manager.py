from typing import Any, Dict, List, Optional, Callable
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from .mission_planner import MissionPlan
from .task_graph import TaskGraph
from .task_executor import ExecutionResult
from .evaluation_engine import EvaluationEngine, EvaluationResult
from .observation_engine import ObservationEngine
from .resource_manager import ResourceManager


class MissionState(str, Enum):
    CREATED = "created"
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
    ARCHIVED = "archived"


@dataclass
class Mission:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    goal: str = ""
    state: MissionState = MissionState.CREATED
    plan: Optional[MissionPlan] = None
    graph: Optional[TaskGraph] = None
    execution_results: Dict[str, Any] = field(default_factory=dict)
    evaluation_result: Optional[EvaluationResult] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)


class MissionManager:
    def __init__(self, evaluation_engine: Optional[EvaluationEngine] = None,
                 observation_engine: Optional[ObservationEngine] = None) -> None:
        self.evaluation_engine = evaluation_engine or EvaluationEngine()
        self.observation_engine = observation_engine or ObservationEngine()
        self._missions: Dict[UUID, Mission] = {}
        self._state_handlers: Dict[MissionState, List[Callable]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        self._state_handlers[MissionState.CREATED] = [self._on_created]
        self._state_handlers[MissionState.RUNNING] = [self._on_running]

    def _on_created(self, mission: Mission) -> None:
        mission.metadata["state_transition"] = {"from": "none", "to": "created", "at": datetime.utcnow().isoformat()}

    def _on_running(self, mission: Mission) -> None:
        mission.started_at = datetime.utcnow()
        mission.metadata["state_transition"] = {"from": "ready", "to": "running", "at": datetime.utcnow().isoformat()}

    def create_mission(self, goal: str, plan: MissionPlan, session: AsyncSession) -> Mission:
        mission = Mission(
            name=plan.name,
            description=plan.description,
            goal=goal,
            state=MissionState.CREATED,
            plan=plan,
        )
        self._missions[mission.id] = mission
        return mission

    def get_mission(self, mission_id: UUID) -> Optional[Mission]:
        return self._missions.get(mission_id)

    async def start_mission(self, mission_id: UUID) -> bool:
        mission = self._missions.get(mission_id)
        if not mission:
            return False
        return await self._transition_state(mission, MissionState.RUNNING)

    async def pause_mission(self, mission_id: UUID) -> bool:
        mission = self._missions.get(mission_id)
        if not mission:
            return False
        return await self._transition_state(mission, MissionState.WAITING_APPROVAL)

    async def resume_mission(self, mission_id: UUID) -> bool:
        mission = self._missions.get(mission_id)
        if not mission:
            return False
        return await self._transition_state(mission, MissionState.RUNNING)

    async def complete_mission(self, mission_id: UUID, session: AsyncSession) -> bool:
        mission = self._missions.get(mission_id)
        if not mission:
            return False
        if await self._transition_state(mission, MissionState.COMPLETED):
            mission.completed_at = datetime.utcnow()
            return True
        return False

    async def fail_mission(self, mission_id: UUID, session: AsyncSession) -> bool:
        mission = self._missions.get(mission_id)
        if not mission:
            return False
        return await self._transition_state(mission, MissionState.FAILED)

    async def cancel_mission(self, mission_id: UUID) -> bool:
        mission = self._missions.get(mission_id)
        if not mission:
            return False
        return await self._transition_state(mission, MissionState.CANCELLED)

    async def archive_mission(self, mission_id: UUID) -> bool:
        mission = self._missions.get(mission_id)
        if not mission:
            return False
        return await self._transition_state(mission, MissionState.ARCHIVED)

    async def _transition_state(self, mission: Mission, to_state: MissionState) -> bool:
        from_state = mission.state
        valid_transitions = {
            MissionState.CREATED: [MissionState.RUNNING, MissionState.CANCELLED],
            MissionState.RUNNING: [MissionState.COMPLETED, MissionState.FAILED, MissionState.CANCELLED, MissionState.WAITING_APPROVAL],
            MissionState.WAITING_APPROVAL: [MissionState.RUNNING, MissionState.CANCELLED],
            MissionState.COMPLETED: [MissionState.ARCHIVED],
            MissionState.FAILED: [MissionState.ARCHIVED],
            MissionState.CANCELLED: [MissionState.ARCHIVED],
            MissionState.ARCHIVED: [],
        }
        if to_state not in valid_transitions.get(from_state, []):
            return False
        mission.state = to_state
        mission.updated_at = datetime.utcnow()
        handlers = self._state_handlers.get(to_state, [])
        for handler in handlers:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(handler):
                    await handler(mission)
                else:
                    handler(mission)
            except Exception:
                pass
        return True

    async def create_checkpoint(self, mission_id: UUID) -> Dict[str, Any]:
        mission = self._missions.get(mission_id)
        if not mission:
            return {}
        checkpoint = {
            "mission_id": str(mission.id),
            "state": mission.state.value,
            "plan_version": 1,
            "completed_tasks": list(mission.execution_results.get("completed", {}).keys()),
            "pending_tasks": list(mission.execution_results.get("pending", {}).keys()),
            "failed_tasks": list(mission.execution_results.get("failed", {}).keys()),
            "checkpoint_at": datetime.utcnow().isoformat(),
        }
        mission.checkpoint_data = checkpoint
        return checkpoint

    async def restore_from_checkpoint(self, mission_id: UUID, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        mission = self._missions.get(mission_id)
        if not mission:
            return None
        return mission.checkpoint_data

    def get_active_missions(self) -> List[Mission]:
        return [m for m in self._missions.values() if m.state in [
            MissionState.RUNNING, MissionState.WAITING_APPROVAL
        ]]

    def get_mission_stats(self) -> Dict[str, Any]:
        stats = {state.value: 0 for state in MissionState}
        for mission in self._missions.values():
            stats[mission.state.value] += 1
        return {
            "total_missions": len(self._missions),
            "by_state": stats,
            "active": stats.get(MissionState.RUNNING.value, 0),
            "completed": stats.get(MissionState.COMPLETED.value, 0),
            "failed": stats.get(MissionState.FAILED.value, 0),
        }
