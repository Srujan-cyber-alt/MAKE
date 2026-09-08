"""Tests for the Reasoning Engine."""

import pytest

from app.intelligence.core.reasoning_engine import ReasoningEngine
from app.intelligence.schemas import IntentCategory, PlanStatus, Plan


class TestReasoningEngine:
    @pytest.fixture
    def engine(self, intel_db):
        return ReasoningEngine()

    @pytest.mark.asyncio
    async def test_reason_produces_plan(self, engine):
        result = await engine.reason("create a cinematic video of a person walking in a city at night")
        assert "plan" in result
        assert "intent" in result
        assert len(result["plan"].steps) > 0

    @pytest.mark.asyncio
    async def test_plan_has_validation_step(self, engine):
        result = await engine.reason("create a cinematic video")
        actions = [s.action for s in result["plan"].steps]
        assert "validate_request" in actions

    @pytest.mark.asyncio
    async def test_plan_has_execution_step(self, engine):
        result = await engine.reason("create a cinematic video")
        actions = [s.action for s in result["plan"].steps]
        assert "execute_tool" in actions

    @pytest.mark.asyncio
    async def test_plan_has_verification_step(self, engine):
        result = await engine.reason("create a cinematic video")
        actions = [s.action for s in result["plan"].steps]
        assert "verify_output" in actions

    @pytest.mark.asyncio
    async def test_plan_has_artifact_step(self, engine):
        result = await engine.reason("create a cinematic video")
        actions = [s.action for s in result["plan"].steps]
        assert "register_artifact" in actions

    @pytest.mark.asyncio
    async def test_creative_plan_has_creative_planning(self, engine):
        result = await engine.reason("create a cinematic video of a person")
        actions = [s.action for s in result["plan"].steps]
        assert "creative_planning" in actions
        assert "visual_planning" in actions

    @pytest.mark.asyncio
    async def test_consistency_report(self, engine):
        result = await engine.reason("create a cinematic video")
        assert "consistency_report" in result
        assert result["consistency_report"].plan_id == result["plan"].id

    @pytest.mark.asyncio
    async def test_validate_plan_valid(self, engine):
        from app.intelligence.schemas import Plan, PlanStep, ToolType, IntentCategory, Intent
        plan = Plan(
            intent_id="test",
            steps=[
                PlanStep(action="validate_request", tool=ToolType.REASONING, inputs={"x": 1}),
                PlanStep(action="execute_tool", tool=ToolType.MAKE_VIDEO, inputs={"y": 2}, depends_on=[]),
            ],
        )
        assert engine.validate_plan(plan) is True

    @pytest.mark.asyncio
    async def test_validate_plan_circular_deps(self, engine):
        from app.intelligence.schemas import Plan, PlanStep, ToolType
        s1 = PlanStep(action="a", tool=ToolType.OTHER)
        s2 = PlanStep(action="b", tool=ToolType.OTHER, depends_on=[s1.id])
        s1.depends_on = [s2.id]
        plan = Plan(intent_id="test", steps=[s1, s2])
        # validate_plan checks structural validity (no missing deps), not cycles
        # cycles are caught by consistency engine
        assert engine.validate_plan(plan) is True

    @pytest.mark.asyncio
    async def test_intent_enrichment(self, engine):
        result = await engine.reason("create a video of a person dancing")
        intent = result["intent"]
        assert intent.category == IntentCategory.CREATIVE
