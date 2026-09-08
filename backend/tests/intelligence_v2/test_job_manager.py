"""Tests for MAKE Autonomous Agent Core V2 — Job Manager."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.jobs.job_manager import JobManager, JobStatus
from app.intelligence.core.event_stream import EventType


class TestJobManager:
    def test_create_job(self):
        manager = JobManager()
        job = manager.create_job(intent="test intent")
        assert job.job_id is not None
        assert job.intent == "test intent"
        assert job.status == JobStatus.PENDING
        assert job.iterations == 0
        assert job.max_iterations == 5

    def test_create_job_with_project(self):
        manager = JobManager()
        project_id = uuid4()
        job = manager.create_job(intent="test", project_id=project_id)
        assert job.project_id == project_id

    def test_get_job(self):
        manager = JobManager()
        job = manager.create_job(intent="test")
        retrieved = manager.get_job(job.job_id)
        assert retrieved is not None
        assert retrieved.job_id == job.job_id

    def test_get_job_not_found(self):
        manager = JobManager()
        assert manager.get_job(uuid4()) is None

    def test_update_status(self):
        manager = JobManager()
        job = manager.create_job(intent="test")
        manager.update_status(job.job_id, JobStatus.RUNNING)
        updated = manager.get_job(job.job_id)
        assert updated.status == JobStatus.RUNNING
        assert updated.started_at is not None

    def test_record_checkpoint(self):
        manager = JobManager()
        job = manager.create_job(intent="test")
        checkpoint = {"graph": "data", "completed": ["task1"]}
        manager.record_checkpoint(job.job_id, checkpoint)
        updated = manager.get_job(job.job_id)
        assert updated.checkpoint_data == checkpoint
        assert updated.status == JobStatus.CHECKPOINTED

    def test_resume_from_checkpoint(self):
        manager = JobManager()
        job = manager.create_job(intent="test")
        from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, NodeType
        graph = ExecutionGraph.create()
        node = ExecutionNode.create(NodeType.INTENT, graph.execution_id)
        graph.add_node(node)
        checkpoint = {"execution_graph": graph.to_dict()}
        manager.record_checkpoint(job.job_id, checkpoint)
        resumed = manager.resume_from_checkpoint(job.job_id)
        assert resumed is not None
        assert resumed.execution_id == graph.execution_id
        updated = manager.get_job(job.job_id)
        assert updated.status == JobStatus.RUNNING

    def test_add_artifact(self):
        manager = JobManager()
        job = manager.create_job(intent="test")
        artifact = {"tool": "video_gen", "parameters": {"prompt": "test"}}
        manager.add_artifact(job.job_id, artifact)
        artifacts = manager.get_artifacts(job.job_id)
        assert len(artifacts) == 1
        assert artifacts[0]["tool"] == "video_gen"
        assert "artifact_id" in artifacts[0]
        assert "job_id" in artifacts[0]
        assert "created_at" in artifacts[0]

    def test_cancel_job(self):
        manager = JobManager()
        job = manager.create_job(intent="test")
        manager.cancel_job(job.job_id)
        updated = manager.get_job(job.job_id)
        assert updated.status == JobStatus.CANCELLED

    def test_list_jobs(self):
        manager = JobManager()
        manager.create_job(intent="test1", owner="user1")
        manager.create_job(intent="test2", owner="user2")
        jobs = manager.list_jobs()
        assert len(jobs) == 2
        user1_jobs = manager.list_jobs(owner="user1")
        assert len(user1_jobs) == 1

    def test_idempotency_key(self):
        manager = JobManager()
        job1 = manager.create_job(intent="test", idempotency_key="key1")
        job2 = manager.create_job(intent="test", idempotency_key="key1")
        assert job1.job_id == job2.job_id
        assert job2 is job1

    def test_events_emitted(self):
        manager = JobManager()
        job = manager.create_job(intent="test")
        events = manager.get_events(job.job_id)
        assert len(events) >= 1
        assert events[0]["event_type"] == "job_created"
