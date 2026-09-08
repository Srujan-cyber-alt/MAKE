from typing import Optional, Dict, Any, List, Callable
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession

from .goal_decomposer import GoalDecomposer, TaskDefinition
from .mission_planner import MissionPlanner, MissionPlan
from .task_graph import TaskGraph, GraphNode, GraphEdge
from .task_executor import TaskExecutor, ExecutionResult
from .observation_engine import ObservationEngine
from .evaluation_engine import EvaluationEngine, EvaluationResult
from .verification_engine import VerificationEngine
from .self_correction import SelfCorrectionEngine
from .failure_intelligence import FailureIntelligence, FailureClassification
from .strategy_engine import StrategyEngine
from .resource_manager import ResourceManager, ResourceSnapshot
from .dependency_engine import DependencyEngine
from .experiment_engine import ExperimentEngine
from .decision_memory import DecisionMemory
from .approval_gate import ApprovalGate, ApprovalState
from .replay_engine import ReplayEngine
from .mission_manager import MissionManager, MissionState, Mission
from .agent_roles import (
    PlannerRole, ExecutorRole, ObserverRole, EvaluatorRole,
    VerifierRole, RecoveryRole, ResearchRole, AgentRole
)


class AgentEvent(str, Enum):
    MISSION_CREATED = "mission_created"
    MISSION_STARTED = "mission_started"
    MISSION_COMPLETED = "mission_completed"
    MISSION_FAILED = "mission_failed"
    MISSION_PAUSED = "mission_paused"
    MISSION_RESUMED = "mission_resumed"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    STRATEGY_SELECTED = "strategy_selected"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"


@dataclass
class AgentContext:
    mission_id: UUID
    plan: MissionPlan
    graph: TaskGraph
    resource_manager: ResourceManager
    dependency_engine: DependencyEngine
    session: AsyncSession
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class AgentController:
    def __init__(self, mission_manager: Optional[MissionManager] = None) -> None:
        self.mission_manager = mission_manager
        self.goal_decomposer = GoalDecomposer()
        self.mission_planner = MissionPlanner()
        self.task_graph = TaskGraph()
        self.task_executor = TaskExecutor()
        self.observation_engine = ObservationEngine()
        self.evaluation_engine = EvaluationEngine()
        self.verification_engine = VerificationEngine()
        self.self_correction = SelfCorrectionEngine()
        self.failure_intelligence = FailureIntelligence()
        self.strategy_engine = StrategyEngine()
        self.resource_manager = ResourceManager()
        self.dependency_engine = DependencyEngine()
        self.experiment_engine = ExperimentEngine()
        self.decision_memory = DecisionMemory()
        self.approval_gate = ApprovalGate()
        self.replay_engine = ReplayEngine()
        self._event_handlers: Dict[AgentEvent, List[Callable]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        self._event_handlers[AgentEvent.TASK_FAILED] = [self._on_task_failed]
        self._event_handlers[AgentEvent.MISSION_COMPLETED] = [self._on_mission_completed]

    def _on_task_failed(self, context: AgentContext, task_id: str, result: ExecutionResult) -> None:
        pass

    def _on_mission_completed(self, context: AgentContext) -> None:
        pass

    async def _emit(self, event: AgentEvent, context: AgentContext, **kwargs: Any) -> None:
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                await handler(context, **kwargs)
            except Exception:
                pass

    async def create_mission(self, goal: str, constraints: Dict[str, Any]) -> AgentContext:
        tasks = self.goal_decomposer.decompose(goal, constraints=constraints)
        plan = self.mission_planner.create_plan(tasks, constraints)
        graph = TaskGraph()
        for task in tasks:
            graph.add_node(str(task.id), task.name)
        for task in tasks:
            for dep_id in task.dependencies:
                graph.add_edge(str(dep_id), str(task.id))
        context = AgentContext(
            mission_id=uuid4(),
            plan=plan,
            graph=graph,
            resource_manager=self.resource_manager,
            dependency_engine=self.dependency_engine,
            session=None,
            metadata=constraints,
        )
        return context

    async def execute_mission(self, mission_id: UUID) -> Dict[str, Any]:
        mission = self.mission_manager.get_mission(mission_id) if self.mission_manager else None
        if not mission:
            return {"error": "Mission not found"}
        results = {}
        for task_id, task in mission.plan.tasks.items():
            result = await self._execute_single_task(mission, task)
            results[str(task_id)] = result
        return results

    async def _execute_single_task(self, mission: Mission, task: TaskDefinition) -> ExecutionResult:
        return ExecutionResult(
            task_id=str(task.id),
            status=ExecutionStatus.SUCCESS,
            output={"task": task.name, "status": "completed"},
        )

    async def run_mission(self, mission_id: str) -> Dict[str, Any]:
        if self.mission_manager:
            mission = self.mission_manager.get_mission(UUID(mission_id))
            if not mission:
                return {"error": "Mission not found"}
            results = {}
            for task_id, task in mission.plan.tasks.items():
                result = ExecutionResult(
                    task_id=str(task_id),
                    status=ExecutionStatus.SUCCESS,
                    output={"task": task.name},
                )
                results[str(task_id)] = result
            return results
        return {"error": "Mission manager not initialized"}
