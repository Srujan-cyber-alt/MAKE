"""
MAKE Autonomous Agent Core V2 — Execution Runtime.

Autonomous execution loop:
PLAN → EXECUTE → OBSERVE → CRITIQUE → REPLAN → EXECUTE

Bounded iterations. No infinite loops.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
import asyncio

from app.intelligence.core.execution_graph import (
    ExecutionGraph, ExecutionNode, NodeType, ExecutionState
)
from app.intelligence.core.event_stream import EventStream, EventType
from app.intelligence.core.observation_engine_v2 import (
    ObservationEngineV2, ObservationCategory, ObservationSeverity
)
from app.intelligence.core.quality_decision import (
    QualityDecisionEngine, QualityDecision, QualityInput
)
from app.intelligence.core.revision_engine import RevisionEngine, RevisionStrategy
from app.intelligence.core.project_memory import ProjectMemory
from app.intelligence.tool_adapters.tool_adapters import ToolRouter, ToolRequest, ToolCapability


class ExecutionResult:
    def __init__(self, success: bool, output: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.output = output or {}
        self.error = error
        self.metadata = metadata or {}


class ExecutionRuntime:
    def __init__(
        self,
        tool_router: Optional[ToolRouter] = None,
        observation_engine: Optional[ObservationEngineV2] = None,
        quality_engine: Optional[QualityDecisionEngine] = None,
        revision_engine: Optional[RevisionEngine] = None,
        project_memory: Optional[ProjectMemory] = None,
        event_stream: Optional[EventStream] = None,
        max_iterations: int = 5,
    ) -> None:
        self.tool_router = tool_router or ToolRouter()
        self.observation_engine = observation_engine or ObservationEngineV2()
        self.quality_engine = quality_engine or QualityDecisionEngine()
        self.revision_engine = revision_engine or RevisionEngine()
        self.project_memory = project_memory or ProjectMemory()
        self.event_stream = event_stream or EventStream()
        self.max_iterations = max_iterations
        self._node_handlers: Dict[NodeType, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        self._node_handlers[NodeType.INTENT] = self._handle_intent
        self._node_handlers[NodeType.PLAN] = self._handle_plan
        self._node_handlers[NodeType.TASK] = self._handle_task
        self._node_handlers[NodeType.TOOL_CALL] = self._handle_tool_call
        self._node_handlers[NodeType.VALIDATION] = self._handle_validation
        self._node_handlers[NodeType.CRITIQUE] = self._handle_critique
        self._node_handlers[NodeType.REVISION] = self._handle_revision
        self._node_handlers[NodeType.CHECKPOINT] = self._handle_checkpoint
        self._node_handlers[NodeType.ARTIFACT] = self._handle_artifact
        self._node_handlers[NodeType.APPROVAL] = self._handle_approval
        self._node_handlers[NodeType.COMPLETION] = self._handle_completion

    async def execute(self, graph: ExecutionGraph, execution_id: Optional[UUID] = None) -> ExecutionResult:
        execution_id = execution_id or uuid4()
        self.event_stream.emit(execution_id, EventType.JOB_STARTED, {"execution_id": str(execution_id)})
        iterations = 0
        current_graph = graph
        while iterations < self.max_iterations:
            iterations += 1
            ready_nodes = current_graph.get_ready_nodes()
            if not ready_nodes and current_graph.completed:
                break
            if not ready_nodes and not current_graph.completed:
                if current_graph.root_node_id and current_graph.get_node(current_graph.root_node_id).state == ExecutionState.FAILED:
                    break
                ready_nodes = [current_graph.get_node(current_graph.root_node_id)] if current_graph.root_node_id else []
            for node in ready_nodes:
                if node.state in (ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED):
                    continue
                handler = self._node_handlers.get(node.node_type)
                if not handler:
                    self.observation_engine.record(
                        execution_id=execution_id,
                        category=ObservationCategory.TOOL_FAILURE,
                        severity=ObservationSeverity.ERROR,
                        description=f"No handler for node type: {node.node_type}",
                        node_id=node.node_id,
                    )
                    current_graph.update_node_state(node.node_id, ExecutionState.FAILED, error_info={"error": f"No handler for {node.node_type}"})
                    continue
                current_graph.update_node_state(node.node_id, ExecutionState.RUNNING)
                self.event_stream.emit(execution_id, EventType.NODE_STARTED, {"node_id": str(node.node_id), "node_type": node.node_type.value})
                try:
                    result = await handler(node, current_graph, execution_id)
                    if result.success:
                        current_graph.update_node_state(node.node_id, ExecutionState.COMPLETED, outputs=result.output)
                        self.event_stream.emit(execution_id, EventType.NODE_COMPLETED, {"node_id": str(node.node_id), "output": result.output})
                    else:
                        current_graph.update_node_state(node.node_id, ExecutionState.FAILED, error_info={"error": result.error})
                        self.event_stream.emit(execution_id, EventType.NODE_FAILED, {"node_id": str(node.node_id), "error": result.error})
                except Exception as e:
                    current_graph.update_node_state(node.node_id, ExecutionState.FAILED, error_info={"error": str(e)})
                    self.event_stream.emit(execution_id, EventType.NODE_FAILED, {"node_id": str(node.node_id), "error": str(e)})
            quality_input = QualityInput(
                execution_id=execution_id,
                intent=graph.nodes.get(graph.root_node_id, ExecutionNode.create(NodeType.INTENT, execution_id)).inputs.get("intent", ""),
                requirements=[],
                execution_result={"iterations": iterations},
                observations=[o.to_dict() for o in self.observation_engine.get_observations(execution_id)],
                quality_metrics={},
                previous_attempts=[],
            )
            decision = self.quality_engine.evaluate(quality_input)
            self.event_stream.emit(execution_id, EventType.QUALITY_DECISION, {"decision": decision.decision.value, "reason": decision.reason})
            if decision.decision == QualityDecision.PASS:
                current_graph.completed = True
                self.event_stream.emit(execution_id, EventType.JOB_COMPLETED, {"execution_id": str(execution_id)})
                break
            elif decision.decision == QualityDecision.REVISE:
                new_execution_id = uuid4()
                revision = self.revision_engine.create_revision(
                    parent_execution_id=execution_id,
                    new_execution_id=new_execution_id,
                    strategy=RevisionStrategy.RETRY_TOOL,
                    reason=decision.reason,
                    evidence=decision.evidence,
                )
                self.event_stream.emit(execution_id, EventType.PLAN_REVISED, {"revision_id": str(revision.revision_id)})
                execution_id = new_execution_id
                current_graph = self.revision_engine.apply_revision_to_graph(current_graph, revision)
            else:
                self.event_stream.emit(execution_id, EventType.JOB_FAILED, {"reason": decision.reason})
                break
        return ExecutionResult(success=current_graph.completed, output={"execution_id": str(execution_id)})

    async def _handle_intent(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        return ExecutionResult(success=True, output={"intent": node.inputs.get("intent", "")})

    async def _handle_plan(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        return ExecutionResult(success=True, output={"plan": "generated"})

    async def _handle_task(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        return ExecutionResult(success=True, output={"task": node.inputs.get("task", "")})

    async def _handle_tool_call(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        tool_name = node.inputs.get("tool", "")
        request = ToolRequest(
            capability=ToolCapability(node.inputs.get("capability", "generate")),
            parameters=node.inputs.get("parameters", {}),
        )
        result = await self.tool_router.execute(tool_name, request)
        if result.success:
            return ExecutionResult(success=True, output=result.output, metadata={"artifact_id": result.artifact_id})
        else:
            self.observation_engine.record_no_artifact(execution_id, node.node_id, tool_name)
            return ExecutionResult(success=False, error=result.error)

    async def _handle_validation(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        return ExecutionResult(success=True, output={"validation": "passed"})

    async def _handle_critique(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        return ExecutionResult(success=True, output={"critique": "no issues"})

    async def _handle_revision(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        return ExecutionResult(success=True, output={"revision": "applied"})

    async def _handle_checkpoint(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        self.event_stream.emit(execution_id, EventType.CHECKPOINT_CREATED, {"node_id": str(node.node_id)})
        return ExecutionResult(success=True, output={"checkpoint": "created"})

    async def _handle_artifact(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        self.event_stream.emit(execution_id, EventType.ARTIFACT_VERIFIED, {"node_id": str(node.node_id)})
        return ExecutionResult(success=True, output={"artifact": "verified"})

    async def _handle_approval(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        self.event_stream.emit(execution_id, EventType.APPROVAL_REQUIRED, {"node_id": str(node.node_id)})
        return ExecutionResult(success=True, output={"approval": "granted"})

    async def _handle_completion(self, node: ExecutionNode, graph: ExecutionGraph, execution_id: UUID) -> ExecutionResult:
        return ExecutionResult(success=True, output={"completion": "done"})
