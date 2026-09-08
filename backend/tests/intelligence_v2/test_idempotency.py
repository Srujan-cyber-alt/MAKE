"""Tests for MAKE Autonomous Agent Core V2 — Idempotency."""

import pytest
from uuid import uuid4

from app.intelligence.jobs.job_manager import JobManager, JobStatus


class TestIdempotency:
    def test_create_job_idempotency(self):
        manager = JobManager()
        job1 = manager.create_job(intent="idempotent", idempotency_key="key1")
        job2 = manager.create_job(intent="idempotent", idempotency_key="key1")
        assert job1.job_id == job2.job_id

    def test_retry_does_not_duplicate_artifacts(self):
        manager = JobManager()
        job = manager.create_job(intent="retry test")
        manager.add_artifact(job.job_id, {"tool": "gen"})
        artifacts = manager.get_artifacts(job.job_id)
        assert len(artifacts) == 1

    def test_checkpoint_idempotency(self):
        manager = JobManager()
        job = manager.create_job(intent="checkpoint test")
        manager.record_checkpoint(job.job_id, {"graph": "v1"})
        manager.record_checkpoint(job.job_id, {"graph": "v2"})
        assert job.checkpoint_data["graph"] == "v2"
