"""Tests for MAKE Autonomous Agent Core V2 — Execution Graph."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.execution_graph import (
    ExecutionGraph, ExecutionNode, ExecutionState, NodeType
)


class TestExecutionGraph:
    def test_create_graph(self):
        graph = ExecutionGraph.create()
        assert graph.execution_id is not None
        assert graph.root_node_id is None
        assert graph.nodes == {}
        assert graph.edges == {}

    def test_add_node_sets_root(self):
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(node_type=NodeType.INTENT, execution_id=graph.execution_id)
        graph.add_node(node)
        assert graph.root_node_id == node.node_id

    def test_dependency_ordering(self):
        graph = ExecutionGraph.create()
        intent = ExecutionNode.create(NodeType.INTENT, graph.execution_id)
        plan = ExecutionNode.create(NodeType.PLAN, graph.execution_id, dependency_ids=[intent.node_id])
        task = ExecutionNode.create(NodeType.TASK, graph.execution_id, dependency_ids=[plan.node_id])
        graph.add_node(intent)
        graph.add_node(plan)
        graph.add_node(task)
        ready = graph.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].node_id == intent.node_id
        graph.update_node_state(intent.node_id, ExecutionState.COMPLETED)
        ready = graph.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].node_id == plan.node_id

    def test_cycle_detection(self):
        graph = ExecutionGraph.create()
        node_a = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        node_b = ExecutionNode.create(NodeType.TASK, graph.execution_id, dependency_ids=[node_a.node_id])
        graph.add_node(node_a)
        graph.add_node(node_b)
        node_a.dependency_ids = [node_b.node_id]
        with pytest.raises(ValueError):
            graph.add_node(node_a)

    def test_no_duplicate_execution_after_recovery(self):
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(NodeType.ARTIFACT, graph.execution_id)
        graph.add_node(node)
        graph.update_node_state(node.node_id, ExecutionState.COMPLETED)
        data = graph.to_dict()
        restored = ExecutionGraph.from_dict(data)
        assert restored.get_node(node.node_id).state == ExecutionState.COMPLETED
        graph.update_node_state(node.node_id, ExecutionState.RUNNING)
        restored2 = ExecutionGraph.from_dict(data)
        assert restored2.get_node(node.node_id).state == ExecutionState.COMPLETED

    def test_node_states(self):
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        graph.add_node(node)
        assert node.state == ExecutionState.CREATED
        graph.update_node_state(node.node_id, ExecutionState.QUEUED)
        assert graph.get_node(node.node_id).state == ExecutionState.QUEUED
        graph.update_node_state(node.node_id, ExecutionState.RUNNING)
        assert graph.get_node(node.node_id).state == ExecutionState.RUNNING
        graph.update_node_state(node.node_id, ExecutionState.COMPLETED)
        assert graph.get_node(node.node_id).state == ExecutionState.COMPLETED

    def test_retry_state(self):
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        graph.add_node(node)
        assert node.retry_count == 0
        node.retry_count += 1
        graph.update_node_state(node.node_id, ExecutionState.RUNNING)
        assert graph.get_node(node.node_id).retry_count == 1
