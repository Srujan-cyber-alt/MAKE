"""Tests for Decision Trace."""

import pytest

from app.intelligence.core.decision_trace import DecisionTrace
from app.intelligence.schemas import DecisionRecord


class TestDecisionTrace:
    @pytest.fixture
    def trace(self, intel_db):
        return DecisionTrace()

    @pytest.mark.asyncio
    async def test_record_decision(self, trace):
        record = await trace.record(
            step="intent",
            decision="Parsed as creative",
            reasoning="User requested a video",
            job_id="job-123",
        )
        assert record.id is not None
        assert record.step == "intent"
        assert record.decision == "Parsed as creative"
        assert record.job_id == "job-123"

    @pytest.mark.asyncio
    async def test_get_decisions_for_job(self, trace):
        await trace.record(
            step="intent", decision="d1", reasoning="r1", job_id="job-abc"
        )
        await trace.record(
            step="planning", decision="d2", reasoning="r2", job_id="job-abc"
        )
        await trace.record(
            step="intent", decision="d3", reasoning="r3", job_id="job-other"
        )
        records = await trace.get_for_job("job-abc")
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_get_all_decisions(self, trace):
        for i in range(5):
            await trace.record(
                step=f"step_{i}", decision=f"d{i}", reasoning="r", job_id=f"j{i}"
            )
        records = await trace.get_all(limit=3)
        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_clear_job_decisions(self, trace):
        await trace.record(step="a", decision="d1", reasoning="r1", job_id="job-x")
        await trace.record(step="b", decision="d2", reasoning="r2", job_id="job-x")
        deleted = await trace.clear_job("job-x")
        assert deleted == 2
        records = await trace.get_for_job("job-x")
        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_decision_with_details(self, trace):
        record = await trace.record(
            step="routing",
            decision="Selected MAKE_VIDEO",
            reasoning="Matches required capabilities",
            job_id="job-456",
            details={"confidence": 0.9, "alternatives": ["make_image"]},
        )
        assert record.details["confidence"] == 0.9
        assert "alternatives" in record.details
