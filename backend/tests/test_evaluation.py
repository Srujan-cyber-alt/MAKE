"""Tests for the Evaluation Engine."""

import pytest
from app.intelligence.agent.evaluation_engine import EvaluationEngine, EvaluationResult, EvaluationVerdict


class TestEvaluationEngine:
    def test_create_engine(self):
        engine = EvaluationEngine()
        assert engine is not None

    def test_evaluate_pass(self):
        engine = EvaluationEngine()
        result = engine.evaluate_task_output(
            task_objective="Generate a report",
            output={"report": "test report"},
            checks=[{"name": "has_report", "passed": True}],
        )
        assert result.verdict == EvaluationVerdict.PASS

    def test_evaluate_fail(self):
        engine = EvaluationEngine()
        result = engine.evaluate_task_output(
            task_objective="Generate a report",
            output={},
            checks=[{"name": "has_report", "passed": False}],
        )
        assert result.verdict == EvaluationVerdict.FAIL

    def test_evaluate_partial(self):
        engine = EvaluationEngine()
        result = engine.evaluate_task_output(
            task_objective="Generate a report",
            output={"report": "partial"},
            checks=[
                {"name": "has_report", "passed": True},
                {"name": "complete", "passed": False},
            ],
        )
        assert result.verdict == EvaluationVerdict.PARTIAL

    def test_evaluate_blocked_external(self):
        engine = EvaluationEngine()
        result = engine.evaluate_task_output(
            task_objective="Call external API",
            output={"error": "Network unreachable"},
            checks=[],
            external_blocker=True,
        )
        assert result.verdict == EvaluationVerdict.BLOCKED_EXTERNAL

    def test_evaluate_constraints(self):
        engine = EvaluationEngine()
        result = engine.evaluate_constraints(
            constraints={"max_duration": 60.0},
            metrics={"duration": 30.0},
        )
        assert result.verdict == EvaluationVerdict.PASS

    def test_evaluate_constraints_fail(self):
        engine = EvaluationEngine()
        result = engine.evaluate_constraints(
            constraints={"max_duration": 30.0},
            metrics={"duration": 60.0},
        )
        assert result.verdict == EvaluationVerdict.FAIL


class TestEvaluationVerdict:
    def test_verdict_values(self):
        assert EvaluationVerdict.PASS.value == "pass"
        assert EvaluationVerdict.FAIL.value == "fail"
        assert EvaluationVerdict.PARTIAL.value == "partial"
        assert EvaluationVerdict.BLOCKED_EXTERNAL.value == "blocked_external"
