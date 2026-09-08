"""Tests for MAKE Autonomous Agent Core V2 — Artifact Provenance."""

import pytest
from uuid import uuid4

from app.intelligence.jobs.job_manager import JobManager, JobStatus
from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, NodeType, ExecutionState


class TestArtifactProvenance:
    def test_artifact_has_provenance(self):
        manager = JobManager()
        job = manager.create_job(intent="provenance test")
        artifact = {"tool": "generator", "parameters": {"prompt": "test"}, "provenance": {"model": "v1"}}
        manager.add_artifact(job.job_id, artifact)
        artifacts = manager.get_artifacts(job.job_id)
        assert artifacts[0]["tool"] == "generator"
        assert artifacts[0]["provenance"]["model"] == "v1"

    def test_no_duplicate_artifacts_after_recovery(self):
        manager = JobManager()
        job = manager.create_job(intent="dup test")
        manager.add_artifact(job.job_id, {"tool": "gen"})
        manager.record_checkpoint(job.job_id, {"execution_graph": {}})
        before = len(manager.get_artifacts(job.job_id))
        manager.resume_from_checkpoint(job.job_id)
        after = len(manager.get_artifacts(job.job_id))
        assert before == after
