"""Tests for MAKE Autonomous Agent Core V2 — Approval Gates."""

import asyncio
import pytest
from uuid import UUID, uuid4

from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, NodeType, ExecutionState
from app.intelligence.core.event_stream import EventStream, EventType
from app.intelligence.core.execution_runtime import ExecutionRuntime


class TestApprovalGates:
    def test_approval_required_event(self):
        stream = EventStream()
        runtime = ExecutionRuntime(event_stream=stream)
        execution_id = uuid4()
        graph = ExecutionGraph.create(execution_id=execution_id)
        node = ExecutionNode.create(NodeType.APPROVAL, execution_id, inputs={"action": "publish"})
        graph.add_node(node)
        result = asyncio.get_event_loop().run_until_complete(runtime._handle_approval(node, graph, execution_id))
        assert result.success is True
        events = stream.get_events(execution_id)
        assert any(e.event_type == EventType.APPROVAL_REQUIRED for e in events)

    def test_approval_pauses_execution(self):
        runtime = ExecutionRuntime()
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(NodeType.APPROVAL, graph.execution_id)
        graph.add_node(node)
        graph.update_node_state(node.node_id, ExecutionState.WAITING)
        assert graph.get_node(node.node_id).state == ExecutionState.WAITING

    def test_approval_state_survives_checkpoint(self):
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(NodeType.APPROVAL, graph.execution_id)
        graph.add_node(node)
        graph.update_node_state(node.node_id, ExecutionState.WAITING)
        data = graph.to_dict()
        restored = ExecutionGraph.from_dict(data)
        assert restored.get_node(node.node_id).state == ExecutionState.WAITING
