"""Tests for MAKE Autonomous Agent Core V2 — Cancellation."""

import pytest
from uuid import uuid4

from app.intelligence.jobs.job_manager import JobManager, JobStatus
from app.intelligence.core.event_stream import EventStream, EventType


class TestCancellation:
    def test_cancel_job(self):
        manager = JobManager()
        job = manager.create_job(intent="cancel test")
        manager.update_status(job.job_id, JobStatus.RUNNING)
        manager.cancel_job(job.job_id)
        assert manager.get_job(job.job_id).status == JobStatus.CANCELLED

    def test_cancel_emits_event(self):
        stream = EventStream()
        manager = JobManager(event_stream=stream)
        job = manager.create_job(intent="cancel event test")
        manager.cancel_job(job.job_id)
        events = manager.get_events(job.job_id)
        event_types = [e["event_type"] for e in events]
        assert EventType.JOB_CANCELLED.value in event_types
