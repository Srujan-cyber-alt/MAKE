from typing import Any, Dict, List, Optional, Callable, Type
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from .mission_planner import MissionPlan, TaskDefinition, TaskType, TaskPriority
from .task_graph import TaskGraph, GraphNode
from .task_executor import ExecutionResult, TaskExecutor
from .observation_engine import ObservationEngine, ObservationType
from .evaluation_engine import EvaluationEngine, EvaluationResult, EvaluationVerdict
from .resource_manager import ResourceManager, ResourceSnapshot
from .verification_engine import VerificationEngine


class RoleCapability(str, Enum):
    PLAN = "plan"
    EXECUTE = "execute"
    OBSERVE = "observe"
    EVALUATE = "evaluate"
    VERIFY = "verify"
    RECOVER = "recover"
    RESEARCH = "research"


@dataclass
class AgentMessage:
    sender: str
    recipient: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AgentRole:
    def __init__(self, role_name: str, capabilities: List[RoleCapability]) -> None:
        self.role_name = role_name
        self.capabilities = capabilities
        self._message_queue: List[AgentMessage] = []

    def send_message(self, recipient: str, message_type: str, payload: Dict[str, Any]) -> AgentMessage:
        message = AgentMessage(
            sender=self.role_name,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
        )
        self._message_queue.append(message)
        return message

    def receive_message(self, message: AgentMessage) -> None:
        self._message_queue.append(message)

    def process_messages(self) -> List[Dict[str, Any]]:
        results = []
        for msg in self._message_queue:
            results.append(self._handle_message(msg))
        self._message_queue.clear()
        return results

    def _handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        return {"message": message.message_type, "status": "processed"}


class PlannerRole(AgentRole):
    def __init__(self, mission_planner: Optional[MissionPlan] = None) -> None:
        super().__init__("planner", [RoleCapability.PLAN])
        self.mission_planner = mission_planner

    def create_plan(self, goal: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
        return {"goal": goal, "strategy": "sequential", "constraints": constraints}


class ExecutorRole(AgentRole):
    def __init__(self, task_executor: Optional[TaskExecutor] = None) -> None:
        super().__init__("executor", [RoleCapability.EXECUTE])
        self.task_executor = task_executor or TaskExecutor()

    def execute_task(self, task: Any) -> ExecutionResult:
        return self.task_executor.execute(task)


class ObserverRole(AgentRole):
    def __init__(self, observation_engine: Optional[ObservationEngine] = None) -> None:
        super().__init__("observer", [RoleCapability.OBSERVE])
        self.observation_engine = observation_engine or ObservationEngine()

    def observe(self, mission_id: str, task_id: Optional[str], data: Dict[str, Any]) -> Any:
        import asyncio
        return asyncio.run(self.observation_engine.record(
            mission_id=mission_id,
            task_id=task_id,
            actor="observer",
            action="observe",
            state="completed",
            observation_type="task_output",
            data=data,
        ))


class EvaluatorRole(AgentRole):
    def __init__(self, evaluation_engine: Optional[EvaluationEngine] = None) -> None:
        super().__init__("evaluator", [RoleCapability.EVALUATE])
        self.evaluation_engine = evaluation_engine or EvaluationEngine()

    def evaluate(self, task_objective: str, output: Dict[str, Any], checks: List[Dict[str, Any]]) -> EvaluationResult:
        return self.evaluation_engine.evaluate_task_output(task_objective, output, checks)


class VerifierRole(AgentRole):
    def __init__(self, verification_engine: Optional[VerificationEngine] = None) -> None:
        super().__init__("verifier", [RoleCapability.VERIFY])
        self.verification_engine = verification_engine or VerificationEngine()

    def verify(self, task_id: str, execution_output: Dict[str, Any], expected_output: Dict[str, Any], checks: List[Dict[str, Any]]) -> Any:
        return self.verification_engine.verify_task_output(task_id, execution_output, expected_output, checks)


class RecoveryRole(AgentRole):
    def __init__(self) -> None:
        super().__init__("recovery", [RoleCapability.RECOVER])

    def recover(self, failure: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "retry", "reason": "Auto-recovery", "failure": failure}


class ResearchRole(AgentRole):
    def __init__(self) -> None:
        super().__init__("research", [RoleCapability.RESEARCH])

    def research(self, query: str) -> Dict[str, Any]:
        return {"query": query, "results": [], "status": "completed"}
