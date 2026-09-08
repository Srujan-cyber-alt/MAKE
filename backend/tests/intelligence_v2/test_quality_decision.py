"""Tests for MAKE Autonomous Agent Core V2 — Quality Decision Engine."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.quality_decision import (
    QualityDecisionEngine,
    QualityDecision,
    QualityInput,
)


class TestQualityDecisionEngine:
    def test_pass_when_no_issues(self):
        engine = QualityDecisionEngine()
        input_data = QualityInput(
            execution_id=uuid4(),
            intent="test",
            requirements=[],
            execution_result={"status": "ok"},
            observations=[],
            quality_metrics={"snr": 30.0, "clarity": 0.9},
            previous_attempts=[],
        )
        record = engine.evaluate(input_data)
        assert record.decision == QualityDecision.PASS
        assert "passed" in record.reason.lower()

    def test_fail_on_hard_failures(self):
        engine = QualityDecisionEngine()
        input_data = QualityInput(
            execution_id=uuid4(),
            intent="test",
            requirements=[],
            execution_result={"status": "error"},
            observations=[
                {"category": "failure", "description": "tool crashed"},
                {"category": "no_artifact", "description": "no output"},
            ],
            quality_metrics={},
            previous_attempts=[],
        )
        record = engine.evaluate(input_data)
        assert record.decision == QualityDecision.FAIL
        assert "failure" in record.reason.lower()

    def test_revise_on_missing_requirements(self):
        engine = QualityDecisionEngine()
        input_data = QualityInput(
            execution_id=uuid4(),
            intent="test",
            requirements=[],
            execution_result={"status": "partial"},
            observations=[
                {"category": "missing_requirement", "description": "missing color"},
            ],
            quality_metrics={},
            previous_attempts=[],
        )
        record = engine.evaluate(input_data)
        assert record.decision == QualityDecision.REVISE
        assert "missing" in record.reason.lower()

    def test_fail_after_max_iterations(self):
        engine = QualityDecisionEngine()
        input_data = QualityInput(
            execution_id=uuid4(),
            intent="test",
            requirements=[],
            execution_result={"status": "partial"},
            observations=[],
            quality_metrics={},
            previous_attempts=[{"attempt": i} for i in range(5)],
        )
        record = engine.evaluate(input_data)
        assert record.decision == QualityDecision.FAIL
        assert "maximum" in record.reason.lower()

    def test_decision_stored(self):
        engine = QualityDecisionEngine()
        execution_id = uuid4()
        input_data = QualityInput(
            execution_id=execution_id,
            intent="test",
            requirements=[],
            execution_result={"status": "ok"},
            observations=[],
            quality_metrics={"snr": 30.0},
            previous_attempts=[],
        )
        engine.evaluate(input_data)
        decisions = engine.get_decisions(execution_id)
        assert len(decisions) == 1
        assert decisions[0].decision == QualityDecision.PASS

    def test_decision_to_dict(self):
        engine = QualityDecisionEngine()
        execution_id = uuid4()
        input_data = QualityInput(
            execution_id=execution_id,
            intent="test",
            requirements=[],
            execution_result={"status": "ok"},
            observations=[],
            quality_metrics={"snr": 30.0},
            previous_attempts=[],
        )
        record = engine.evaluate(input_data)
        data = record.to_dict()
        assert "decision_id" in data
        assert "execution_id" in data
        assert data["decision"] == "pass"
        assert "reason" in data
        assert "evidence" in data
