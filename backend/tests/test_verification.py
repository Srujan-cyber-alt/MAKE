"""Tests for the Verification Engine."""

import pytest
from app.intelligence.agent.verification_engine import (
    VerificationEngine, VerificationResult, VerificationVerdict
)


class TestVerificationEngine:
    def test_create_engine(self):
        engine = VerificationEngine()
        assert engine is not None

    def test_verify_pass(self):
        engine = VerificationEngine()
        result = engine.verify_task_output(
            task_id="task_1",
            execution_output={"result": "ok"},
            expected_output={"result": "ok"},
            checks=[{"name": "match", "passed": True}],
        )
        assert result.verdict == VerificationVerdict.PASSED

    def test_verify_fail(self):
        engine = VerificationEngine()
        result = engine.verify_task_output(
            task_id="task_1",
            execution_output={"result": "ok"},
            expected_output={"result": "not ok"},
            checks=[{"name": "match", "passed": False}],
        )
        assert result.verdict == VerificationVerdict.FAILED

    def test_verify_inconclusive(self):
        engine = VerificationEngine()
        result = engine.verify_task_output(
            task_id="task_1",
            execution_output={"result": "maybe"},
            expected_output={"result": "ok"},
            checks=[],
        )
        assert result.verdict == VerificationVerdict.INCONCLUSIVE

    def test_verify_independent(self):
        engine = VerificationEngine()
        assert engine.independent is True

    def test_verification_result_fields(self):
        engine = VerificationEngine()
        result = engine.verify_task_output(
            task_id="task_1",
            execution_output={"result": "ok"},
            expected_output={"result": "ok"},
            checks=[{"name": "match", "passed": True}],
        )
        assert result.task_id == "task_1"
        assert result.verifier == "verification_engine"
        assert len(result.checks) == 1
        assert result.evidence is not None


class TestVerificationVerdict:
    def test_verdict_values(self):
        assert VerificationVerdict.PASSED.value == "passed"
        assert VerificationVerdict.FAILED.value == "failed"
        assert VerificationVerdict.INCONCLUSIVE.value == "inconclusive"
