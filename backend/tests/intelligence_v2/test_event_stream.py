"""Tests for MAKE Autonomous Agent Core V2 — Event Stream."""

import pytest
from uuid import UUID, uuid4

from app.intelligence.core.event_stream import EventStream, EventType


class TestEventStream:
    def test_emit_and_get_events(self):
        stream = EventStream()
        job_id = uuid4()
        event1 = stream.emit(job_id, EventType.JOB_CREATED, {"intent": "test"})
        event2 = stream.emit(job_id, EventType.PLAN_CREATED, {"plan": "step1"})
        events = stream.get_events(job_id)
        assert len(events) == 2
        assert events[0].event_type == EventType.JOB_CREATED
        assert events[1].event_type == EventType.PLAN_CREATED
        assert events[0].sequence == 1
        assert events[1].sequence == 2

    def test_get_events_after_sequence(self):
        stream = EventStream()
        job_id = uuid4()
        stream.emit(job_id, EventType.JOB_CREATED, {})
        stream.emit(job_id, EventType.PLAN_CREATED, {})
        stream.emit(job_id, EventType.TASK_STARTED, {})
        events = stream.get_events(job_id, after_sequence=1)
        assert len(events) == 2
        assert events[0].event_type == EventType.PLAN_CREATED
        assert events[1].event_type == EventType.TASK_STARTED

    def test_get_latest_sequence(self):
        stream = EventStream()
        job_id = uuid4()
        stream.emit(job_id, EventType.JOB_CREATED, {})
        stream.emit(job_id, EventType.PLAN_CREATED, {})
        assert stream.get_latest_sequence(job_id) == 2

    def test_event_to_dict(self):
        stream = EventStream()
        job_id = uuid4()
        event = stream.emit(job_id, EventType.JOB_CREATED, {"intent": "test"})
        data = event.to_dict()
        assert "event_id" in data
        assert "job_id" in data
        assert data["event_type"] == "job_created"
        assert data["payload"] == {"intent": "test"}
        assert data["sequence"] == 1

    def test_event_types(self):
        stream = EventStream()
        job_id = uuid4()
        for event_type in EventType:
            stream.emit(job_id, event_type, {"type": event_type.value})
        events = stream.get_all_events(job_id)
        assert len(events) == len(EventType)
