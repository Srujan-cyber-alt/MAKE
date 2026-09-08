from typing import Any, Dict, List, Optional
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum
from .task_graph import TaskGraph, GraphNode
from .mission_planner import MissionPlan, TaskDefinition


class DependencyStatus(str, Enum):
    PENDING = "pending"
    SATISFIED = "satisfied"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass
class DependencyCheckResult:
    task_id: str
    status: DependencyStatus
    missing_dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DependencyEngine:
    def __init__(self) -> None:
        self._resolution_cache: Dict[str, DependencyCheckResult] = {}

    def validate_graph(self, graph: TaskGraph) -> bool:
        return not graph.has_cycle()

    def get_ready_tasks(self, graph: TaskGraph) -> List[str]:
        return graph.get_ready_tasks()

    def check_dependencies(self, graph: TaskGraph, task_id: str) -> DependencyCheckResult:
        cache_key = f"{task_id}"
        if cache_key in self._resolution_cache:
            return self._resolution_cache[cache_key]
        node = graph.get_node(task_id)
        if not node:
            return DependencyCheckResult(task_id=task_id, status=DependencyStatus.BLOCKED, missing_dependencies=[task_id])
        deps = graph.get_dependencies(task_id)
        missing = [d for d in deps if graph.get_node(d) is None]
        if missing:
            result = DependencyCheckResult(task_id=task_id, status=DependencyStatus.BLOCKED, missing_dependencies=missing)
        else:
            result = DependencyCheckResult(task_id=task_id, status=DependencyStatus.SATISFIED)
        self._resolution_cache[cache_key] = result
        return result

    def get_critical_path(self, graph: TaskGraph) -> List[str]:
        return graph.get_critical_path()

    def get_parallel_batches(self, graph: TaskGraph) -> List[List[str]]:
        return graph.get_parallel_batches()

    def get_downstream_impact(self, graph: TaskGraph, task_id: str) -> List[str]:
        impacted = []
        queue = [task_id]
        visited = set()
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            dependents = graph.get_dependents(current)
            impacted.extend(dependents)
            queue.extend(dependents)
        return list(set(impacted))
