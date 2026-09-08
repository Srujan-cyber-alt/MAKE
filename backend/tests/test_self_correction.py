"""Tests for Self-Correction Engine."""

import pytest
from app.intelligence.agent.self_correction import (
    SelfCorrectionEngine, CorrectionPlan, CorrectionAction
)
from app.intelligence.agent.types import ExecutionResult, ExecutionStatus
from app.intelligence.agent.mission_planner import TaskDefinition, TaskType, TaskPriority


class TestSelfCorrectionEngine:
    def test_create_engine(self):
        engine = SelfCorrectionEngine()
        assert engine is not None

    def test_diagnose_timeout(self):
        engine = SelfCorrectionEngine()
        result = ExecutionResult(task_id="t1", status=ExecutionStatus.TIMEOUT, success=False)
        task = TaskDefinition(task_id="t1", name="T", objective="O", task_type=TaskType.COMPUTE)
        plan = engine.diagnose(result, task)
        assert plan is not None
        assert isinstance(plan, CorrectionPlan)

    def test_diagnose_failure(self):
        engine = SelfCorrectionEngine()
        result = ExecutionResult(task_id="t1", status=ExecutionStatus.FAILURE, success=False, error="boom")
        task = TaskDefinition(task_id="t1", name="T", objective="O", task_type=TaskType.COMPUTE)
        plan = engine.diagnose(result, task)
        assert plan is not None
        assert len(plan.actions) > 0

    def test_correction_actions(self):
        assert CorrectionAction.RETRY.value == "retry"
        assert CorrectionAction.REPLAN.value == "replan"
        assert CorrectionAction.SUBSTITUTE.value == "substitute"
        assert CorrectionAction.ABORT.value == "abort"

    def test_generate_alternative_strategy(self):
        engine = SelfCorrectionEngine()
        result = ExecutionResult(task_id="t1", status=ExecutionStatus.FAILURE, success=False)
        task = TaskDefinition(task_id="t1", name="T", objective="O", task_type=TaskType.COMPUTE)
        plan = engine.diagnose(result, task)
        alternative = engine.generate_alternative(task, plan)
        assert alternative is not None

    def test_predict_side_effects(self):
        engine = SelfCorrectionEngine()
        result = ExecutionResult(task_id="t1", status=ExecutionStatus.FAILURE, success=False)
        task = TaskDefinition(task_id="t1", name="T", objective="O", task_type=TaskType.COMPUTE)
        plan = engine.diagnose(result, task)
        effects = engine.predict_side_effects(task, plan)
        assert isinstance(effects, list)
