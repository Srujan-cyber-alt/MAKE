"""Tests for MAKE Autonomous Agent Core V2 — Execution Graph."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.execution_graph import (
    ExecutionGraph,
    ExecutionNode,
    ExecutionState,
    NodeType,
)


class TestExecutionNode:
    def test_create_node(self):
        node = ExecutionNode.create(
            node_type=NodeType.TASK,
            execution_id=uuid4(),
        )
        assert node.node_id is not None
        assert node.node_type == NodeType.TASK
        assert node.state == ExecutionState.CREATED
        assert node.retry_count == 0
        assert node.branch == "main"

    def test_node_to_dict_roundtrip(self):
        execution_id = uuid4()
        parent_id = uuid4()
        dep_id = uuid4()
        node = ExecutionNode(
            node_id=uuid4(),
            node_type=NodeType.TASK,
            state=ExecutionState.RUNNING,
            parent_id=parent_id,
            dependency_ids=[dep_id],
            inputs={"param": "value"},
            outputs={"result": "ok"},
            provenance={"source": "test"},
            retry_count=2,
            error_info={"error": "test"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={"key": "val"},
            execution_id=execution_id,
            branch="main",
        )
        data = node.to_dict()
        restored = ExecutionNode.from_dict(data)
        assert restored.node_id == node.node_id
        assert restored.node_type == NodeType.TASK
        assert restored.state == ExecutionState.RUNNING
        assert restored.parent_id == parent_id
        assert restored.dependency_ids == [dep_id]
        assert restored.inputs == {"param": "value"}
        assert restored.outputs == {"result": "ok"}
        assert restored.retry_count == 2
        assert restored.error_info == {"error": "test"}


class TestExecutionGraph:
    def test_create_graph(self):
        graph = ExecutionGraph.create()
        assert graph.execution_id is not None
        assert graph.root_node_id is None
        assert graph.nodes == {}
        assert graph.edges == {}
        assert not graph.completed

    def test_add_node_sets_root(self):
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(node_type=NodeType.INTENT, execution_id=graph.execution_id)
        graph.add_node(node)
        assert graph.root_node_id == node.node_id
        assert node.node_id in graph.nodes

    def test_add_node_creates_edges(self):
        graph = ExecutionGraph.create()
        parent = ExecutionNode.create(node_type=NodeType.PLAN, execution_id=graph.execution_id)
        graph.add_node(parent)
        child = ExecutionNode.create(
            node_type=NodeType.TASK,
            execution_id=graph.execution_id,
            parent_id=parent.node_id,
            dependency_ids=[parent.node_id],
        )
        graph.add_node(child)
        assert parent.node_id in graph.edges
        assert child.node_id in graph.edges[parent.node_id]

    def test_get_children(self):
        graph = ExecutionGraph.create()
        parent = ExecutionNode.create(node_type=NodeType.PLAN, execution_id=graph.execution_id)
        graph.add_node(parent)
        child1 = ExecutionNode.create(node_type=NodeType.TASK, execution_id=graph.execution_id, dependency_ids=[parent.node_id])
        child2 = ExecutionNode.create(node_type=NodeType.TASK, execution_id=graph.execution_id, dependency_ids=[parent.node_id])
        graph.add_node(child1)
        graph.add_node(child2)
        children = graph.get_children(parent.node_id)
        assert len(children) == 2
        assert child1.node_id in [c.node_id for c in children]
        assert child2.node_id in [c.node_id for c in children]

    def test_get_ready_nodes(self):
        graph = ExecutionGraph.create()
        intent = ExecutionNode.create(node_type=NodeType.INTENT, execution_id=graph.execution_id)
        graph.add_node(intent)
        task = ExecutionNode.create(node_type=NodeType.TASK, execution_id=graph.execution_id, dependency_ids=[intent.node_id])
        graph.add_node(task)
        graph.update_node_state(intent.node_id, ExecutionState.COMPLETED)
        ready = graph.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].node_id == task.node_id

    def test_update_node_state(self):
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(node_type=NodeType.TASK, execution_id=graph.execution_id)
        graph.add_node(node)
        graph.update_node_state(node.node_id, ExecutionState.RUNNING, outputs={"status": "ok"})
        updated = graph.get_node(node.node_id)
        assert updated.state == ExecutionState.RUNNING
        assert updated.outputs == {"status": "ok"}

    def test_graph_roundtrip(self):
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(node_type=NodeType.ARTIFACT, execution_id=graph.execution_id)
        graph.add_node(node)
        graph.update_node_state(node.node_id, ExecutionState.COMPLETED, outputs={"artifact_id": "123"})
        graph.final_artifact_id = node.node_id
        data = graph.to_dict()
        restored = ExecutionGraph.from_dict(data)
        assert restored.execution_id == graph.execution_id
        assert restored.root_node_id == graph.root_node_id
        assert len(restored.nodes) == 1
        assert restored.completed is False
        assert restored.final_artifact_id == node.node_id
