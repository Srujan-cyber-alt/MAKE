"""Tests for MAKE Autonomous Agent Core V2 — Event Persistence."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.event_stream import EventStream, EventType, EventRecord
from app.intelligence.core.persistence import IntelligencePersistence


class TestEventPersistence:
    def test_event_saved_to_db(self):
        persistence = IntelligencePersistence("sqlite:///test_event_persist.db")
        stream = EventStream(persistence=persistence)
        job_id = uuid4()
        event = stream.emit(job_id, EventType.JOB_CREATED, {"intent": "test"})
        events = persistence.load_all_events(job_id)
        assert len(events) == 1
        assert events[0]["event_type"] == "job_created"
        assert events[0]["sequence_number"] == 1

    def test_event_ordering_preserved(self):
        persistence = IntelligencePersistence("sqlite:///test_event_order.db")
        stream = EventStream(persistence=persistence)
        job_id = uuid4()
        stream.emit(job_id, EventType.JOB_CREATED, {})
        stream.emit(job_id, EventType.PLAN_CREATED, {})
        stream.emit(job_id, EventType.NODE_COMPLETED, {})
        events = persistence.load_all_events(job_id)
        assert len(events) == 3
        assert events[0]["sequence_number"] == 1
        assert events[1]["sequence_number"] == 2
        assert events[2]["sequence_number"] == 3

    def test_no_event_duplication(self):
        persistence = IntelligencePersistence("sqlite:///test_event_dup.db")
        stream = EventStream(persistence=persistence)
        job_id = uuid4()
        stream.emit(job_id, EventType.JOB_CREATED, {})
        stream.emit(job_id, EventType.PLAN_CREATED, {})
        events = persistence.load_all_events(job_id)
        assert len(events) == 2

    def test_event_replay_after_restart(self):
        db_url = "sqlite:///test_event_replay.db"
        persistence1 = IntelligencePersistence(db_url)
        stream1 = EventStream(persistence=persistence1)
        job_id = uuid4()
        stream1.emit(job_id, EventType.JOB_CREATED, {"intent": "replay"})
        stream1.emit(job_id, EventType.NODE_COMPLETED, {"node_id": "1"})
        persistence2 = IntelligencePersistence(db_url)
        stream2 = EventStream(persistence=persistence2)
        stream2._events = {}
        stream2._sequences = {}
        for evt in persistence2.load_all_events(job_id):
            stream2._events.setdefault(job_id, []).append(EventRecord(
                event_id=UUID(evt["event_id"]),
                job_id=UUID(evt["job_id"]),
                execution_id=UUID(evt["execution_id"]),
                event_type=EventType(evt["event_type"]),
                payload=evt["payload"],
                created_at=datetime.fromisoformat(evt["timestamp"]),
                sequence=evt["sequence_number"],
            ))
            stream2._sequences[job_id] = evt["sequence_number"]
        events = stream2.get_all_events(job_id)
        assert len(events) == 2
        assert events[0].event_type == EventType.JOB_CREATED
        assert events[1].event_type == EventType.NODE_COMPLETED

    def test_monotonic_sequence_per_execution(self):
        persistence = IntelligencePersistence("sqlite:///test_event_seq.db")
        stream = EventStream(persistence=persistence)
        job_id = uuid4()
        for i in range(10):
            stream.emit(job_id, EventType.NODE_COMPLETED, {"i": i})
        events = persistence.load_all_events(job_id)
        sequences = [e["sequence_number"] for e in events]
        assert sequences == list(range(1, 11))
