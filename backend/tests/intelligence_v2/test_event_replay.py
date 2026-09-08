"""Tests for MAKE Autonomous Agent Core V2 — Event Replay."""

import pytest
from uuid import UUID, uuid4

from app.intelligence.core.event_stream import EventStream, EventType
from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, ExecutionState, NodeType
from app.intelligence.core.execution_runtime import ExecutionRuntime


class TestEventReplay:
    def test_replay_reconstructs_state(self):
        stream = EventStream()
        runtime = ExecutionRuntime(event_stream=stream)
        execution_id = uuid4()
        graph = ExecutionGraph.create(execution_id=execution_id)
        intent = ExecutionNode.create(NodeType.INTENT, execution_id, inputs={"intent": "test"})
        graph.add_node(intent)
        task = ExecutionNode.create(NodeType.TASK, execution_id, dependency_ids=[intent.node_id])
        graph.add_node(task)
        graph.update_node_state(intent.node_id, ExecutionState.COMPLETED)
        graph.update_node_state(task.node_id, ExecutionState.COMPLETED)
        graph.completed = True
        stream.emit(execution_id, EventType.JOB_STARTED, {})
        stream.emit(execution_id, EventType.NODE_COMPLETED, {"node_id": str(intent.node_id)})
        stream.emit(execution_id, EventType.NODE_COMPLETED, {"node_id": str(task.node_id)})
        stream.emit(execution_id, EventType.JOB_COMPLETED, {})
        events = stream.get_all_events(execution_id)
        assert len(events) == 4
        assert events[0].event_type == EventType.JOB_STARTED
        assert events[-1].event_type == EventType.JOB_COMPLETED
        for i, event in enumerate(events):
            assert event.sequence == i + 1

    def test_replay_after_crash(self):
        stream = EventStream()
        execution_id = uuid4()
        stream.emit(execution_id, EventType.JOB_STARTED, {"execution_id": str(execution_id)})
        stream.emit(execution_id, EventType.NODE_STARTED, {"node_id": "1"})
        stream.emit(execution_id, EventType.NODE_COMPLETED, {"node_id": "1"})
        stream.emit(execution_id, EventType.CHECKPOINT_CREATED, {})
        new_runtime = ExecutionRuntime(event_stream=stream)
        events = stream.get_events(execution_id)
        assert len(events) == 4
        assert events[0].event_type == EventType.JOB_STARTED
        assert events[1].event_type == EventType.NODE_STARTED
        assert events[2].event_type == EventType.NODE_COMPLETED
        assert events[3].event_type == EventType.CHECKPOINT_CREATED

    def test_deterministic_replay(self):
        stream = EventStream()
        execution_id = uuid4()
        for i in range(10):
            stream.emit(execution_id, EventType.NODE_COMPLETED, {"i": i})
        first_run = [e.payload["i"] for e in stream.get_events(execution_id)]
        second_run = [e.payload["i"] for e in stream.get_all_events(execution_id)]
        assert first_run == second_run

    def test_event_stream_survives_manager_recreation(self):
        stream = EventStream()
        execution_id = uuid4()
        runtime1 = ExecutionRuntime(event_stream=stream)
        runtime1.event_stream.emit(execution_id, EventType.JOB_CREATED, {})
        runtime1.event_stream.emit(execution_id, EventType.PLAN_CREATED, {})
        del runtime1
        runtime2 = ExecutionRuntime(event_stream=stream)
        events = runtime2.event_stream.get_all_events(execution_id)
        assert len(events) == 2
        assert events[0].event_type == EventType.JOB_CREATED
        assert events[1].event_type == EventType.PLAN_CREATED
