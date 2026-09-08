"""Tests for MAKE Autonomous Agent Core V2 — Failure Recovery."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, ExecutionState, NodeType
from app.intelligence.core.execution_runtime import ExecutionRuntime
from app.intelligence.core.event_stream import EventStream, EventType
from app.intelligence.core.quality_decision import QualityDecisionEngine, QualityInput
from app.intelligence.core.revision_engine import RevisionEngine, RevisionStrategy
from app.intelligence.jobs.job_manager import JobManager, JobStatus


class TestFailureRecovery:
    def test_transient_failure_retry(self):
        runtime = ExecutionRuntime()
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        graph.add_node(node)
        graph.update_node_state(node.node_id, ExecutionState.RUNNING)
        graph.update_node_state(node.node_id, ExecutionState.FAILED, error_info={"error": "timeout", "category": "transient"})
        engine = QualityDecisionEngine()
        input_data = QualityInput(
            execution_id=graph.execution_id,
            intent="test",
            requirements=[],
            execution_result={},
            observations=[{"category": "failure", "description": "timeout"}],
            quality_metrics={},
            previous_attempts=[],
        )
        decision = engine.evaluate(input_data)
        assert decision.decision.value == "revise"

    def test_invalid_input_no_retry(self):
        engine = QualityDecisionEngine()
        input_data = QualityInput(
            execution_id=uuid4(),
            intent="test",
            requirements=[],
            execution_result={},
            observations=[{"category": "missing_requirement", "description": "missing input"}],
            quality_metrics={},
            previous_attempts=[],
        )
        decision = engine.evaluate(input_data)
        assert decision.decision.value == "revise"

    def test_max_retries_exhausted(self):
        engine = QualityDecisionEngine()
        input_data = QualityInput(
            execution_id=uuid4(),
            intent="test",
            requirements=[],
            execution_result={},
            observations=[{"category": "failure", "description": "fail"}],
            quality_metrics={},
            previous_attempts=[{"attempt": i} for i in range(5)],
        )
        decision = engine.evaluate(input_data)
        assert decision.decision.value == "fail"

    def test_revision_preserves_successful_components(self):
        graph = ExecutionGraph.create()
        intent = ExecutionNode.create(NodeType.INTENT, graph.execution_id)
        plan = ExecutionNode.create(NodeType.PLAN, graph.execution_id, dependency_ids=[intent.node_id])
        task = ExecutionNode.create(NodeType.TASK, graph.execution_id, dependency_ids=[plan.node_id])
        graph.add_node(intent)
        graph.add_node(plan)
        graph.add_node(task)
        graph.update_node_state(intent.node_id, ExecutionState.COMPLETED)
        graph.update_node_state(plan.node_id, ExecutionState.COMPLETED)
        graph.update_node_state(task.node_id, ExecutionState.FAILED)
        revision_engine = RevisionEngine()
        revision = revision_engine.create_revision(
            graph.execution_id, uuid4(), RevisionStrategy.RETRY_TOOL,
            "task failed", {}, preserved_components=[intent.node_id, plan.node_id]
        )
        new_graph = revision_engine.apply_revision_to_graph(graph, revision)
        assert intent.node_id in new_graph.nodes
        assert plan.node_id in new_graph.nodes
        assert task.node_id not in new_graph.nodes

    def test_event_recorded_on_failure(self):
        stream = EventStream()
        runtime = ExecutionRuntime(event_stream=stream)
        execution_id = uuid4()
        graph = ExecutionGraph.create(execution_id=execution_id)
        node = ExecutionNode.create(NodeType.TASK, execution_id)
        graph.add_node(node)
        graph.update_node_state(node.node_id, ExecutionState.RUNNING)
        graph.update_node_state(node.node_id, ExecutionState.FAILED, error_info={"error": "tool failure"})
        runtime.event_stream.emit(execution_id, EventType.NODE_FAILED, {"node_id": str(node.node_id), "error": "tool failure"})
        events = stream.get_events(execution_id)
        assert len(events) == 1
        assert events[0].event_type == EventType.NODE_FAILED
