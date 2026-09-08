"""Tests for Replay Engine."""

import pytest
from app.intelligence.agent.replay_engine import ReplayEngine, ReplayResult, ReplayStatus


class TestReplayEngine:
    def test_create_replay_engine(self):
        engine = ReplayEngine()
        assert engine is not None

    def test_replay_mission_not_found(self):
        engine = ReplayEngine()
        import asyncio
        result = asyncio.run(engine.replay_mission("nonexistent"))
        assert result.status == ReplayStatus.FAILED

    def test_replay_status_values(self):
        assert ReplayStatus.PENDING.value == "pending"
        assert ReplayStatus.REPLAYING.value == "replaying"
        assert ReplayStatus.COMPLETED.value == "completed"
        assert ReplayStatus.FAILED.value == "failed"

    def test_replay_result_fields(self):
        engine = ReplayEngine()
        result = ReplayResult(
            replay_id="replay_1",
            mission_id="mission_1",
            status=ReplayStatus.PENDING,
            replayed_tasks=[],
            replayed_results={},
        )
        assert result.replay_id == "replay_1"
        assert result.status == ReplayStatus.PENDING
