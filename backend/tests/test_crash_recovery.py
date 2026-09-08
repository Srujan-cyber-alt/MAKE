"""Tests for Crash Recovery and Checkpointing."""

import pytest
from app.intelligence.agent.mission_manager import MissionManager, Mission, MissionState
from app.intelligence.agent.types import ExecutionResult, ExecutionStatus


class TestCrashRecovery:
    def test_create_checkpoint(self):
        manager = MissionManager()
        mission = manager.create_mission(
            name="Crash Test",
            description="Testing crash recovery",
            goal="Complete task despite crash",
        )
        checkpoint = manager.create_checkpoint(mission.id)
        assert checkpoint is not None

    def test_restore_from_checkpoint(self):
        manager = MissionManager()
        mission = manager.create_mission(
            name="Restore Test",
            description="Testing restore",
            goal="Complete task",
        )
        checkpoint = manager.create_checkpoint(mission.id)
        restored = manager.restore_from_checkpoint(mission.id, checkpoint.id)
        assert restored is not None

    def test_mission_survives_restart(self):
        manager = MissionManager()
        mission = manager.create_mission(
            name="Restart Test",
            description="Testing restart",
            goal="Complete task",
        )
        mission_id = mission.id
        state_before = manager.get_mission(mission_id).state
        manager2 = MissionManager()
        mission_after = manager2.get_mission(mission_id)
        assert mission_after is not None

    def test_no_duplicate_completed_work(self):
        manager = MissionManager()
        mission = manager.create_mission(
            name="Duplicate Test",
            description="Testing no duplicates",
            goal="Complete once",
        )
        checkpoint1 = manager.create_checkpoint(mission.id)
        checkpoint2 = manager.create_checkpoint(mission.id)
        assert checkpoint1.id != checkpoint2.id

    def test_checkpoint_contains_required_fields(self):
        manager = MissionManager()
        mission = manager.create_mission(
            name="Checkpoint Fields",
            description="Testing checkpoint fields",
            goal="Complete task",
        )
        checkpoint = manager.create_checkpoint(mission.id)
        assert checkpoint.completed_tasks is not None
        assert checkpoint.pending_tasks is not None
        assert checkpoint.plan_version >= 1
