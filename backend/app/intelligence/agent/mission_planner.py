from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from .goal_decomposer import TaskDefinition, TaskType, TaskPriority, ResourceEstimate


class MissionStatus(str, Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionStrategy(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PRIORITY = "priority"
    RESOURCE_OPTIMIZED = "resource_optimized"


@dataclass
class MissionPlan:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    goal: str = ""
    status: MissionStatus = MissionStatus.DRAFT
    strategy: MissionStrategy = MissionStrategy.SEQUENTIAL
    tasks: Dict[UUID, TaskDefinition] = field(default_factory=dict)
    dependencies: Dict[UUID, List[UUID]] = field(default_factory=dict)
    estimated_duration_seconds: float = 0.0
    estimated_resources: ResourceEstimate = field(default_factory=ResourceEstimate)
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    risk_assessment: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class MissionPlanner:
    def create_plan(self, tasks: List[TaskDefinition], constraints: Dict[str, Any]) -> MissionPlan:
        plan = MissionPlan(
            name=constraints.get("mission_name", "Unnamed Mission"),
            description=constraints.get("description", ""),
            goal=constraints.get("goal", ""),
            strategy=self._select_strategy(tasks, constraints),
            metadata=constraints,
        )
        for task in tasks:
            plan.tasks[task.id] = task
            plan.dependencies[task.id] = task.dependencies
        plan.estimated_duration_seconds = self._estimate_duration(tasks)
        plan.estimated_resources = self._estimate_resources(tasks)
        return plan

    def _select_strategy(self, tasks: List[TaskDefinition], constraints: Dict[str, Any]) -> MissionStrategy:
        if constraints.get("parallel"):
            return MissionStrategy.PARALLEL
        if constraints.get("resource_optimized"):
            return MissionStrategy.RESOURCE_OPTIMIZED
        if constraints.get("priority"):
            return MissionStrategy.PRIORITY
        return MissionStrategy.SEQUENTIAL

    def _estimate_duration(self, tasks: List[TaskDefinition]) -> float:
        return sum(t.resource_requirements.estimated_duration_seconds for t in tasks)

    def _estimate_resources(self, tasks: List[TaskDefinition]) -> ResourceEstimate:
        total_cpu = sum(t.resource_requirements.cpu_cores for t in tasks)
        total_mem = sum(t.resource_requirements.memory_mb for t in tasks)
        total_disk = sum(t.resource_requirements.disk_mb for t in tasks)
        max_duration = max((t.resource_requirements.estimated_duration_seconds for t in tasks), default=0.0)
        return ResourceEstimate(
            cpu_cores=total_cpu,
            memory_mb=total_mem,
            disk_mb=total_disk,
            estimated_duration_seconds=max_duration,
        )
