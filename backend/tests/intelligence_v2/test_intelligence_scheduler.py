"""Tests for MAKE Autonomous Agent Core V2 — Scheduler."""

import pytest
from uuid import UUID, uuid4

from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, ExecutionState, NodeType


class TestScheduler:
    def test_sequential_execution(self):
        graph = ExecutionGraph.create()
        node1 = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        node2 = ExecutionNode.create(NodeType.TASK, graph.execution_id, dependency_ids=[node1.node_id])
        graph.add_node(node1)
        graph.add_node(node2)
        graph.update_node_state(node1.node_id, ExecutionState.COMPLETED)
        ready = graph.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].node_id == node2.node_id

    def test_parallel_independent_nodes(self):
        graph = ExecutionGraph.create()
        node1 = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        node2 = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        graph.add_node(node1)
        graph.add_node(node2)
        ready = graph.get_ready_nodes()
        assert len(ready) == 2
        ready_ids = {n.node_id for n in ready}
        assert ready_ids == {node1.node_id, node2.node_id}

    def test_dependency_aware_scheduling(self):
        graph = ExecutionGraph.create()
        a = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        b = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        c = ExecutionNode.create(NodeType.TASK, graph.execution_id, dependency_ids=[a.node_id, b.node_id])
        graph.add_node(a)
        graph.add_node(b)
        graph.add_node(c)
        graph.update_node_state(a.node_id, ExecutionState.COMPLETED)
        ready = graph.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].node_id == b.node_id
        graph.update_node_state(b.node_id, ExecutionState.COMPLETED)
        ready = graph.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].node_id == c.node_id

    def test_no_premature_execution(self):
        graph = ExecutionGraph.create()
        parent = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        child = ExecutionNode.create(NodeType.TASK, graph.execution_id, dependency_ids=[parent.node_id])
        graph.add_node(parent)
        graph.add_node(child)
        ready = graph.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].node_id == parent.node_id
        assert child.node_id not in [n.node_id for n in ready]
