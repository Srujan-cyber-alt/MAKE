from typing import List, Dict, Any, Optional, Callable
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from .task_graph import GraphNode
from .types import ExecutionResult


class ObservationType(str, Enum):
    TASK_OUTPUT = "task_output"
    SYSTEM_METRIC = "system_metric"
    EXTERNAL_SIGNAL = "external_signal"
    STATE_CHANGE = "state_change"
    ERROR_EVENT = "error_event"
    RESOURCE_EVENT = "resource_event"


@dataclass
class Observation:
    observation_id: UUID = field(default_factory=uuid4)
    mission_id: Optional[UUID] = None
    task_id: Optional[str] = None
    actor: str = ""
    action: str = ""
    state: str = ""
    observation_type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    duration_ms: Optional[float] = None
    resource_usage: Optional[Dict[str, Any]] = None
    tool_response: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class ObservationEngine:
    def __init__(self) -> None:
        self._observations: Dict[str, List[Observation]] = {}
        self._listeners: List[Callable] = []

    def add_listener(self, listener: Callable) -> None:
        self._listeners.append(listener)

    async def record(
        self,
        mission_id: str,
        task_id: Optional[str],
        actor: str,
        action: str,
        state: str,
        observation_type: str,
        data: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        duration_ms: Optional[float] = None,
        resource_usage: Optional[Dict[str, Any]] = None,
        tool_response: Optional[Dict[str, Any]] = None,
    ) -> Observation:
        observation = Observation(
            mission_id=UUID(mission_id) if mission_id else None,
            task_id=task_id,
            actor=actor,
            action=action,
            state=state,
            observation_type=observation_type,
            data=data,
            metrics=metrics,
            errors=errors,
            duration_ms=duration_ms,
            resource_usage=resource_usage,
            tool_response=tool_response,
        )
        self._observations.setdefault(mission_id, []).append(observation)
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(observation)
                else:
                    listener(observation)
            except Exception:
                pass
        return observation

    def get_observations(self, mission_id: str, task_id: Optional[str] = None) -> List[Observation]:
        obs = self._observations.get(mission_id, [])
        if task_id:
            obs = [o for o in obs if o.task_id == task_id]
        return obs

    def get_observation(self, observation_id: str) -> Optional[Observation]:
        for obs_list in self._observations.values():
            for obs in obs_list:
                if str(obs.observation_id) == observation_id:
                    return obs
        return None

    def analyze_failure_patterns(self, mission_id: str) -> Dict[str, Any]:
        obs = self._observations.get(mission_id, [])
        errors = [o for o in obs if o.observation_type == ObservationType.ERROR_EVENT.value]
        return {
            "total_errors": len(errors),
            "error_actors": list({o.actor for o in errors}),
            "error_actions": list({o.action for o in errors}),
        }
