"""Tests for MAKE Autonomous Agent Core V2 — Observation Engine."""

import pytest
from uuid import UUID, uuid4

from app.intelligence.core.observation_engine_v2 import (
    ObservationEngineV2,
    ObservationCategory,
    ObservationSeverity,
)


class TestObservationEngineV2:
    def test_record_observation(self):
        engine = ObservationEngineV2()
        execution_id = uuid4()
        obs = engine.record(
            execution_id=execution_id,
            category=ObservationCategory.SUCCESS,
            severity=ObservationSeverity.INFO,
            description="Task completed",
        )
        assert obs.observation_id is not None
        assert obs.category == ObservationCategory.SUCCESS
        assert obs.severity == ObservationSeverity.INFO
        assert obs.description == "Task completed"

    def test_record_no_artifact(self):
        engine = ObservationEngineV2()
        execution_id = uuid4()
        node_id = uuid4()
        obs = engine.record_no_artifact(execution_id, node_id, "image_generator")
        assert obs.category == ObservationCategory.NO_ARTIFACT
        assert obs.severity == ObservationSeverity.ERROR
        assert "image_generator" in obs.description

    def test_record_failure(self):
        engine = ObservationEngineV2()
        execution_id = uuid4()
        node_id = uuid4()
        obs = engine.record_failure(execution_id, node_id, "Connection timeout", "video_tool")
        assert obs.category == ObservationCategory.FAILURE
        assert "Connection timeout" in obs.description
        assert obs.evidence["tool"] == "video_tool"

    def test_record_quality(self):
        engine = ObservationEngineV2()
        execution_id = uuid4()
        node_id = uuid4()
        obs = engine.record_quality(execution_id, node_id, "snr", 25.0, 20.0)
        assert obs.category == ObservationCategory.QUALITY
        assert obs.evidence["passed"] is True
        obs2 = engine.record_quality(execution_id, node_id, "snr", 15.0, 20.0)
        assert obs2.evidence["passed"] is False

    def test_get_observations(self):
        engine = ObservationEngineV2()
        execution_id = uuid4()
        engine.record(execution_id, ObservationCategory.SUCCESS, ObservationSeverity.INFO, "ok")
        engine.record(execution_id, ObservationCategory.FAILURE, ObservationSeverity.ERROR, "fail")
        obs_list = engine.get_observations(execution_id)
        assert len(obs_list) == 2

    def test_get_by_category(self):
        engine = ObservationEngineV2()
        execution_id = uuid4()
        engine.record(execution_id, ObservationCategory.SUCCESS, ObservationSeverity.INFO, "ok")
        engine.record(execution_id, ObservationCategory.FAILURE, ObservationSeverity.ERROR, "fail")
        engine.record(execution_id, ObservationCategory.TOOL_FAILURE, ObservationSeverity.ERROR, "tool fail")
        failures = engine.get_by_category(execution_id, ObservationCategory.FAILURE)
        assert len(failures) == 1
        tool_failures = engine.get_by_category(execution_id, ObservationCategory.TOOL_FAILURE)
        assert len(tool_failures) == 1

    def test_has_failures(self):
        engine = ObservationEngineV2()
        execution_id = uuid4()
        assert not engine.has_failures(execution_id)
        engine.record(execution_id, ObservationCategory.SUCCESS, ObservationSeverity.INFO, "ok")
        assert not engine.has_failures(execution_id)
        engine.record_failure(execution_id, uuid4(), "error")
        assert engine.has_failures(execution_id)

    def test_observation_to_dict(self):
        engine = ObservationEngineV2()
        execution_id = uuid4()
        obs = engine.record(execution_id, ObservationCategory.SUCCESS, ObservationSeverity.INFO, "test")
        data = obs.to_dict()
        assert "observation_id" in data
        assert "execution_id" in data
        assert data["category"] == "success"
        assert data["severity"] == "info"
