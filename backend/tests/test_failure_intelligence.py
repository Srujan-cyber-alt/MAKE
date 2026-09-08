"""Tests for Failure Intelligence."""

import pytest
from app.intelligence.agent.failure_intelligence import (
    FailureIntelligence, FailureClassification, FailureCategory, RecoveryStrategy
)


class TestFailureIntelligence:
    def test_create_failure_intelligence(self):
        fi = FailureIntelligence()
        assert fi is not None

    def test_classify_timeout(self):
        fi = FailureIntelligence()
        classification = fi.classify_failure(
            error="Operation timed out",
            context={"task_type": "compute"},
        )
        assert classification.category in FailureCategory

    def test_classify_resource_error(self):
        fi = FailureIntelligence()
        classification = fi.classify_failure(
            error="Out of memory",
            context={"task_type": "compute"},
        )
        assert classification.category == FailureCategory.RESOURCE_ERROR

    def test_classify_external_blocker(self):
        fi = FailureIntelligence()
        classification = fi.classify_failure(
            error="Network unreachable",
            context={"task_type": "data_fetch"},
        )
        assert classification.category == FailureCategory.EXTERNAL_BLOCKER

    def test_recovery_strategy_retry(self):
        fi = FailureIntelligence()
        classification = fi.classify_failure(
            error="Temporary failure",
            context={"task_type": "compute"},
        )
        strategy = fi.get_recovery_strategy(classification)
        assert strategy is not None
        assert strategy.strategy_type in RecoveryStrategy

    def test_failure_categories(self):
        assert FailureCategory.TRANSIENT.value == "transient"
        assert FailureCategory.RESOURCE_ERROR.value == "resource_error"
        assert FailureCategory.EXTERNAL_BLOCKER.value == "external_blocker"

    def test_classify_unknown(self):
        fi = FailureIntelligence()
        classification = fi.classify_failure(
            error="Something weird happened",
            context={},
        )
        assert classification.category == FailureCategory.UNKNOWN


class TestRecoveryStrategy:
    def test_recovery_strategy_values(self):
        assert RecoveryStrategy.RETRY.value == "retry"
        assert RecoveryStrategy.REPLAN.value == "replan"
