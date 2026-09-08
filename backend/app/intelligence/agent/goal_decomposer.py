from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from .types import ExecutionStatus


class TaskType(str, Enum):
    COMPUTE = "compute"
    DATA_FETCH = "data_fetch"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"
    IO_OPERATION = "io_operation"
    RESEARCH = "research"
    INTEGRATION = "integration"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ResourceEstimate:
    cpu_cores: float = 0.0
    memory_mb: int = 0
    disk_mb: int = 0
    estimated_duration_seconds: float = 0.0
    network_mb: float = 0.0


@dataclass
class TaskDefinition:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    task_type: TaskType = TaskType.COMPUTE
    priority: TaskPriority = TaskPriority.MEDIUM
    objective: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[UUID] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    resource_requirements: ResourceEstimate = field(default_factory=ResourceEstimate)
    verification_requirements: Dict[str, Any] = field(default_factory=dict)
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    timeout_seconds: Optional[float] = None
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GoalDecomposer:
    def __init__(self) -> None:
        self._decomposition_rules: Dict[str, List[TaskType]] = {
            "campaign": [TaskType.RESEARCH, TaskType.COMPUTE, TaskType.TRANSFORMATION, TaskType.VALIDATION],
            "web": [TaskType.RESEARCH, TaskType.COMPUTE, TaskType.TRANSFORMATION, TaskType.VALIDATION, TaskType.INTEGRATION],
            "data": [TaskType.DATA_FETCH, TaskType.TRANSFORMATION, TaskType.VALIDATION],
            "report": [TaskType.DATA_FETCH, TaskType.COMPUTE, TaskType.TRANSFORMATION],
            "default": [TaskType.RESEARCH, TaskType.COMPUTE, TaskType.VALIDATION],
        }

    def decompose(self, goal: str, constraints: Optional[Dict[str, Any]] = None) -> List[TaskDefinition]:
        constraints = constraints or {}
        goal_lower = goal.lower()
        task_types = self._select_task_types(goal_lower)
        tasks = []
        for idx, task_type in enumerate(task_types):
            task = TaskDefinition(
                name=f"{task_type.value.title()} Task {idx + 1}",
                description=f"Auto-generated {task_type.value} task for: {goal}",
                task_type=task_type,
                priority=TaskPriority.HIGH if idx == 0 else TaskPriority.MEDIUM,
                objective=f"Execute {task_type.value} for goal: {goal}",
                constraints=constraints,
            )
            tasks.append(task)
        return tasks

    def _select_task_types(self, goal_lower: str) -> List[TaskType]:
        for keyword, types in self._decomposition_rules.items():
            if keyword in goal_lower:
                return types
        return self._decomposition_rules["default"]
