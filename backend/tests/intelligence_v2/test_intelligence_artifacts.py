"""Tests for MAKE Autonomous Agent Core V2 — Artifacts."""

import pytest
from uuid import UUID, uuid4

from app.intelligence.jobs.job_manager import JobManager, JobStatus
from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, NodeType, ExecutionState


class TestArtifacts:
    def test_artifact_created_once(self):
        manager = JobManager()
        job = manager.create_job(intent="artifact test")
        manager.add_artifact(job.job_id, {"tool": "generator", "version": 1})
        artifacts = manager.get_artifacts(job.job_id)
        assert len(artifacts) == 1

    def test_artifact_lineage(self):
        manager = JobManager()
        job = manager.create_job(intent="lineage test")
        manager.add_artifact(job.job_id, {"tool": "gen", "parent": None})
        artifacts = manager.get_artifacts(job.job_id)
        assert len(artifacts) == 1
        manager.add_artifact(job.job_id, {"tool": "edit", "parent": artifacts[0]["artifact_id"]})
        artifacts = manager.get_artifacts(job.job_id)
        assert len(artifacts) == 2
        assert artifacts[1]["parent"] == artifacts[0]["artifact_id"]

    def test_no_duplicate_artifacts_after_recovery(self):
        manager = JobManager()
        job = manager.create_job(intent="recovery artifact test")
        manager.add_artifact(job.job_id, {"tool": "gen", "unique_key": "abc"})
        manager.record_checkpoint(job.job_id, {"execution_graph": {}})
        artifacts_before = manager.get_artifacts(job.job_id)
        manager.resume_from_checkpoint(job.job_id)
        artifacts_after = manager.get_artifacts(job.job_id)
        assert len(artifacts_before) == len(artifacts_after)
        assert artifacts_after[0]["tool"] == "gen"

    def test_artifact_metadata(self):
        manager = JobManager()
        job = manager.create_job(intent="metadata test")
        artifact = {"tool": "test", "parameters": {"prompt": "test"}, "provenance": {"model": "x"}}
        manager.add_artifact(job.job_id, artifact)
        artifacts = manager.get_artifacts(job.job_id)
        assert artifacts[0]["tool"] == "test"
        assert artifacts[0]["parameters"] == {"prompt": "test"}
        assert "artifact_id" in artifacts[0]
        assert "job_id" in artifacts[0]
        assert "created_at" in artifacts[0]
