"""Tests for Self-Critique Loop."""

import pytest

from app.intelligence.core.self_critique import SelfCritiqueLoop, CritiqueResult
from app.intelligence.core.consistency_engine import ConsistencyEngine
from app.intelligence.schemas import Plan, PlanStep, PlanStatus, ToolType


class TestSelfCritique:
    @pytest.fixture
    def engine(self):
        return SelfCritiqueLoop(ConsistencyEngine())

    def _make_valid_plan(self) -> Plan:
        return Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="validate_request", tool=ToolType.REASONING, inputs={"x": 1}),
                PlanStep(id="s2", action="execute_tool", tool=ToolType.MAKE_VIDEO, inputs={"y": 2}, depends_on=["s1"]),
                PlanStep(id="s3", action="verify_output", tool=ToolType.OTHER, inputs={"z": 3}, depends_on=["s2"]),
                PlanStep(id="s4", action="register_artifact", tool=ToolType.OTHER, inputs={"a": 4}, depends_on=["s3"]),
            ],
        )

    @pytest.mark.asyncio
    async def test_critique_valid_plan(self, engine):
        plan = self._make_valid_plan()
        result = await engine.critique_plan(plan)
        assert isinstance(result, CritiqueResult)
        assert result.was_revised is False

    @pytest.mark.asyncio
    async def test_critique_missing_execution_step(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="validate_request", tool=ToolType.REASONING),
            ],
        )
        result = await engine.critique_plan(plan)
        assert len(result.issues) > 0
        codes = [i["code"] for i in result.issues]
        assert "MISSING_EXECUTION" in codes
        assert result.was_revised is True

    @pytest.mark.asyncio
    async def test_critique_invalid_timeout(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="validate_request", tool=ToolType.REASONING, timeout_seconds=0),
                PlanStep(id="s2", action="execute_tool", tool=ToolType.MAKE_VIDEO, depends_on=["s1"]),
                PlanStep(id="s3", action="verify_output", tool=ToolType.OTHER, depends_on=["s2"]),
                PlanStep(id="s4", action="register_artifact", tool=ToolType.OTHER, depends_on=["s3"]),
            ],
        )
        result = await engine.critique_plan(plan)
        codes = [i["code"] for i in result.issues]
        assert "INVALID_TIMEOUT" in codes

    @pytest.mark.asyncio
    async def test_critique_redundancy(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="execute", tool=ToolType.MAKE_VIDEO),
                PlanStep(id="s2", action="execute", tool=ToolType.MAKE_VIDEO),
                PlanStep(id="s3", action="execute", tool=ToolType.MAKE_VIDEO),
                PlanStep(id="s4", action="verify_output", tool=ToolType.OTHER, depends_on=["s3"]),
                PlanStep(id="s5", action="register_artifact", tool=ToolType.OTHER, depends_on=["s3"]),
            ],
        )
        result = await engine.critique_plan(plan)
        codes = [i["code"] for i in result.issues]
        assert "REDUNDANT_STEPS" in codes

    @pytest.mark.asyncio
    async def test_revision_adds_execution_step(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="validate_request", tool=ToolType.REASONING),
            ],
        )
        result = await engine.critique_plan(plan)
        assert result.revised_plan is not None
        actions = [s.action for s in result.revised_plan.steps]
        assert "execute_tool" in actions

    @pytest.mark.asyncio
    async def test_revision_fixes_timeout(self, engine):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="validate_request", tool=ToolType.REASONING, timeout_seconds=-5),
                PlanStep(id="s2", action="execute_tool", tool=ToolType.MAKE_VIDEO, depends_on=["s1"]),
                PlanStep(id="s3", action="verify_output", tool=ToolType.OTHER, depends_on=["s2"]),
                PlanStep(id="s4", action="register_artifact", tool=ToolType.OTHER, depends_on=["s3"]),
            ],
        )
        result = await engine.critique_plan(plan)
        assert result.revised_plan is not None
        for step in result.revised_plan.steps:
            assert step.timeout_seconds > 0

    @pytest.mark.asyncio
    async def test_validated_status_after_revision(self, engine):
        plan = self._make_valid_plan()
        result = await engine.critique_plan(plan)
        if result.revised_plan:
            assert result.revised_plan.status == PlanStatus.VALIDATED

    @pytest.mark.asyncio
    async def test_critique_static_method(self):
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(id="s1", action="validate_request", tool=ToolType.REASONING),
                PlanStep(id="s2", action="execute_tool", tool=ToolType.MAKE_VIDEO, depends_on=["s1"]),
            ],
        )
        result = await SelfCritiqueLoop.critique(plan)
        assert len(result.issues) > 0
        assert result.was_revised is True
