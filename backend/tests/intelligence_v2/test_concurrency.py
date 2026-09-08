"""Tests for MAKE Autonomous Agent Core V2 — Concurrency."""

import pytest
from uuid import uuid4

from app.intelligence.jobs.job_manager import JobManager, JobStatus
from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, NodeType, ExecutionState


class TestConcurrency:
    def test_multiple_jobs_independent(self):
        manager = JobManager()
        job1 = manager.create_job(intent="job1")
        job2 = manager.create_job(intent="job2")
        manager.update_status(job1.job_id, JobStatus.RUNNING)
        manager.update_status(job2.job_id, JobStatus.RUNNING)
        assert manager.get_job(job1.job_id).status == JobStatus.RUNNING
        assert manager.get_job(job2.job_id).status == JobStatus.RUNNING

    def test_parallel_independent_nodes(self):
        graph = ExecutionGraph.create()
        node1 = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        node2 = ExecutionNode.create(NodeType.TASK, graph.execution_id)
        graph.add_node(node1)
        graph.add_node(node2)
        ready = graph.get_ready_nodes()
        assert len(ready) == 2
