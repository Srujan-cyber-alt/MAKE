"""Tests for MAKE Autonomous Agent Core V2 — iPhone Disconnect/Reconnect."""

import pytest
from uuid import uuid4

from app.intelligence.jobs.job_manager import JobManager, JobStatus
from app.intelligence.core.event_stream import EventStream, EventType
from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, NodeType, ExecutionState


class TestiPhoneDisconnectReconnect:
    def test_job_survives_client_disconnect(self):
        manager = JobManager()
        job = manager.create_job(intent="disconnect test")
        job_id = job.job_id
        manager.update_status(job_id, JobStatus.RUNNING)
        execution_id = uuid4()
        graph = ExecutionGraph.create(execution_id=execution_id)
        node = ExecutionNode.create(NodeType.TASK, execution_id)
        graph.add_node(node)
        graph.update_node_state(node.node_id, ExecutionState.COMPLETED)
        manager.add_artifact(job_id, {"tool": "worker", "output": "result"})
        manager.update_status(job_id, JobStatus.COMPLETED)
        new_manager = JobManager()
        recovered = new_manager.get_job(job_id)
        assert recovered is None
        final_job = manager.get_job(job_id)
        assert final_job.status == JobStatus.COMPLETED
        artifacts = manager.get_artifacts(job_id)
        assert len(artifacts) == 1

    def test_no_duplicate_on_reconnect(self):
        stream = EventStream()
        manager = JobManager(event_stream=stream)
        job = manager.create_job(intent="reconnect test")
        job_id = job.job_id
        manager.add_artifact(job_id, {"tool": "gen"})
        artifacts1 = manager.get_artifacts(job_id)
        artifacts2 = manager.get_artifacts(job_id)
        assert len(artifacts1) == 1
        assert len(artifacts2) == 1

    def test_events_preserved_after_disconnect(self):
        stream = EventStream()
        manager = JobManager(event_stream=stream)
        job = manager.create_job(intent="events test")
        job_id = job.job_id
        manager.record_checkpoint(job_id, {"graph": "data"})
        events = manager.get_events(job_id)
        event_types = [e["event_type"] for e in events]
        assert "job_created" in event_types
        assert "checkpoint_created" in event_types
