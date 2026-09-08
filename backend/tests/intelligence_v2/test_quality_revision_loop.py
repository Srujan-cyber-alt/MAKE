"""Tests for MAKE Autonomous Agent Core V2 — Quality/Revision Loop."""

import pytest
from uuid import uuid4

from app.intelligence.core.quality_decision import QualityDecisionEngine, QualityInput, QualityDecision
from app.intelligence.core.revision_engine import RevisionEngine, RevisionStrategy
from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, ExecutionState, NodeType


class TestQualityRevisionLoop:
    def test_pass_completes(self):
        engine = QualityDecisionEngine()
        input_data = QualityInput(
            execution_id=uuid4(),
            intent="test",
            requirements=[],
            execution_result={"status": "ok"},
            observations=[],
            quality_metrics={"snr": 30.0},
            previous_attempts=[],
        )
        decision = engine.evaluate(input_data)
        assert decision.decision == QualityDecision.PASS

    def test_revise_creates_revision(self):
        engine = RevisionEngine()
        graph = ExecutionGraph.create()
        intent = ExecutionNode.create(NodeType.INTENT, graph.execution_id)
        graph.add_node(intent)
        graph.update_node_state(intent.node_id, ExecutionState.COMPLETED)
        revision = engine.create_revision(
            graph.execution_id, uuid4(), RevisionStrategy.RETRY_TOOL,
            "failed", {}, preserved_components=[intent.node_id]
        )
        new_graph = engine.apply_revision_to_graph(graph, revision)
        assert intent.node_id in new_graph.nodes

    def test_fail_after_max_retries(self):
        engine = QualityDecisionEngine()
        input_data = QualityInput(
            execution_id=uuid4(),
            intent="test",
            requirements=[],
            execution_result={"status": "error"},
            observations=[{"category": "failure", "description": "fail"}],
            quality_metrics={},
            previous_attempts=[{"attempt": i} for i in range(5)],
        )
        decision = engine.evaluate(input_data)
        assert decision.decision == QualityDecision.FAIL
