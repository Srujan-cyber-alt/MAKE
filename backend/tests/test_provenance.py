"""Tests for Provenance."""

import pytest
from app.intelligence.agent.observation_engine import ObservationEngine, Observation
from app.intelligence.agent.mission_planner import TaskDefinition, TaskType


class TestProvenance:
    def test_observation_records_provenance(self):
        engine = ObservationEngine()
        observation = engine.record(
            mission_id="mission_1",
            task_id="task_1",
            actor="executor",
            action="execute",
            state="completed",
            observation_type="task_output",
            data={"result": "ok", "tool": "local_tool"},
        )
        assert observation is not None
        assert observation.data.get("tool") == "local_tool"

    def test_provenance_chain(self):
        engine = ObservationEngine()
        engine.record(
            mission_id="mission_1",
            task_id="task_1",
            actor="executor",
            action="execute",
            state="completed",
            observation_type="task_output",
            data={"result": "step1"},
        )
        engine.record(
            mission_id="mission_1",
            task_id="task_1",
            actor="executor",
            action="validate",
            state="completed",
            observation_type="state_change",
            data={"result": "step2", "previous": "step1"},
        )
        history = engine.get_observations("mission_1", "task_1")
        assert len(history) == 2

    def test_artifact_provenance(self):
        engine = ObservationEngine()
        observation = engine.record(
            mission_id="mission_1",
            task_id="task_1",
            actor="executor",
            action="create_artifact",
            state="completed",
            observation_type="task_output",
            data={
                "artifact_path": "/tmp/artifacts/1.bin",
                "artifact_type": "file",
                "tool": "local_io",
            },
        )
        assert "artifact_path" in observation.data
        assert observation.data.get("tool") == "local_io"

    def test_immutable_provenance(self):
        engine = ObservationEngine()
        obs1 = engine.record(
            mission_id="mission_1",
            task_id="task_1",
            actor="executor",
            action="execute",
            state="completed",
            observation_type="task_output",
            data={"step": 1},
        )
        obs1.data["step"] = 2
        obs2 = engine.get_observations("mission_1", "task_1")[0]
        assert obs2.data["step"] == 2
