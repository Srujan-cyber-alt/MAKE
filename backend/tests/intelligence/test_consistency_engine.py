"""Tests for the Consistency Engine."""

import pytest

from app.intelligence.core.consistency_engine import ConsistencyEngine
from app.intelligence.schemas import (
    Plan, PlanStep, PlanStatus, ToolType,
    ConsistencyDiagnostic, DiagnosticSeverity,
)


class TestConsistencyEngine:
    @pytest.fixture
    def engine(self):
        return ConsistencyEngine()

    def test_valid_plan_passes(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="validate", tool=ToolType.REASONING, inputs={"x": 1}),
                PlanStep(id="s2", action="execute", tool=ToolType.MAKE_VIDEO, inputs={"y": 2}, depends_on=["s1"]),
            ],
        )
        report = engine.check(plan)
        assert report.passed

    def test_duplicate_step_ids(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="dup", action="a", tool=ToolType.OTHER),
                PlanStep(id="dup", action="b", tool=ToolType.OTHER),
            ],
        )
        report = engine.check(plan)
        assert not report.passed
        codes = [d.code for d in report.diagnostics]
        assert "DUPLICATE_STEP_IDS" in codes

    def test_invalid_dependency(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="a", tool=ToolType.OTHER, depends_on=["nonexistent"]),
            ],
        )
        report = engine.check(plan)
        assert not report.passed
        codes = [d.code for d in report.diagnostics]
        assert "INVALID_DEPENDENCY" in codes

    def test_circular_dependency(self, engine):
        s1 = PlanStep(id="s1", action="a", tool=ToolType.OTHER)
        s2 = PlanStep(id="s2", action="b", tool=ToolType.OTHER, depends_on=["s1"])
        s1.depends_on = ["s2"]
        plan = Plan(intent_id="test", steps=[s1, s2])
        report = engine.check(plan)
        assert not report.passed
        codes = [d.code for d in report.diagnostics]
        assert "CIRCULAR_DEPENDENCY" in codes

    def test_missing_inputs_warning(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="execute_tool", tool=ToolType.MAKE_VIDEO),
            ],
        )
        report = engine.check(plan)
        codes = [d.code for d in report.diagnostics]
        assert "MISSING_INPUTS" in codes

    def test_missing_execution_step(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="validate", tool=ToolType.REASONING),
            ],
        )
        report = engine.check(plan)
        assert not report.passed

    def test_blocking_error_detection(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="validate", tool=ToolType.REASONING),
                PlanStep(id="s2", action="execute_tool", tool=ToolType.MAKE_VIDEO, depends_on=["nonexistent"]),
            ],
        )
        report = engine.check(plan)
        assert engine.is_blocking_error(report) is True

    def test_no_blocking_error_when_only_warnings(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="validate_request", tool=ToolType.REASONING, inputs={"x": 1}),
                PlanStep(id="s2", action="execute_tool", tool=ToolType.MAKE_VIDEO, inputs={"y": 2}, depends_on=["s1"]),
            ],
        )
        report = engine.check(plan)
        assert not engine.is_blocking_error(report)
