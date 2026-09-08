"""Tests for Decision Memory."""

import pytest
from app.intelligence.agent.decision_memory import (
    DecisionMemory, MemoryEntry, StrategyOutcome
)


class TestDecisionMemory:
    def test_create_decision_memory(self):
        dm = DecisionMemory()
        assert dm is not None

    def test_record_success(self):
        dm = DecisionMemory()
        dm.record(
            strategy_hash="abc123",
            task_type="compute",
            success=True,
            score=0.9,
            duration_ms=100.0,
        )
        history = dm.get_history("abc123")
        assert len(history) == 1

    def test_record_failure(self):
        dm = DecisionMemory()
        dm.record(
            strategy_hash="def456",
            task_type="compute",
            success=False,
            score=0.2,
            duration_ms=500.0,
        )
        history = dm.get_history("def456")
        assert len(history) == 1
        assert history[0].success is False

    def test_recommend_strategy(self):
        dm = DecisionMemory()
        dm.record("strat1", "compute", True, 0.9, 100.0)
        dm.record("strat1", "compute", True, 0.8, 110.0)
        dm.record("strat2", "compute", False, 0.3, 500.0)
        recommendation = dm.recommend("compute")
        assert recommendation is not None

    def test_search_by_task_type(self):
        dm = DecisionMemory()
        dm.record("strat1", "compute", True, 0.9, 100.0)
        dm.record("strat2", "research", True, 0.7, 200.0)
        results = dm.search_by_task_type("compute")
        assert len(results) == 1

    def test_search_by_result(self):
        dm = DecisionMemory()
        dm.record("strat1", "compute", True, 0.9, 100.0)
        dm.record("strat2", "compute", False, 0.3, 500.0)
        results = dm.search_by_result(success=True)
        assert len(results) == 1

    def test_memory_entry_fields(self):
        dm = DecisionMemory()
        dm.record("strat1", "compute", True, 0.9, 100.0)
        entry = dm.get_history("strat1")[0]
        assert entry.strategy_hash == "strat1"
        assert entry.task_type == "compute"
        assert entry.success is True
        assert entry.score == 0.9
