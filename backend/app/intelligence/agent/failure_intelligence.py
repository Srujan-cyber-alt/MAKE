from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class FailureCategory(str, Enum):
    TRANSIENT = "transient"
    INPUT_ERROR = "input_error"
    PLANNING_ERROR = "planning_error"
    TOOL_ERROR = "tool_error"
    RESOURCE_ERROR = "resource_error"
    QUALITY_ERROR = "quality_error"
    DEPENDENCY_ERROR = "dependency_error"
    STATE_ERROR = "state_error"
    EXTERNAL_BLOCKER = "external_blocker"
    UNKNOWN = "unknown"


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    REPLAN = "replan"
    SUBSTITUTE = "substitute"
    SCALE = "scale"
    DEFER = "defer"
    ABORT = "abort"


@dataclass
class FailureClassification:
    category: FailureCategory
    confidence: float
    cause: str
    recovery_strategy: RecoveryStrategy
    retry_eligible: bool
    context: Dict[str, Any] = field(default_factory=dict)


class FailureIntelligence:
    def __init__(self) -> None:
        self._error_patterns: Dict[str, FailureCategory] = {
            "timeout": FailureCategory.TRANSIENT,
            "timed out": FailureCategory.TRANSIENT,
            "memory": FailureCategory.RESOURCE_ERROR,
            "out of memory": FailureCategory.RESOURCE_ERROR,
            "cpu": FailureCategory.RESOURCE_ERROR,
            "disk": FailureCategory.RESOURCE_ERROR,
            "network": FailureCategory.EXTERNAL_BLOCKER,
            "unreachable": FailureCategory.EXTERNAL_BLOCKER,
            "connection": FailureCategory.EXTERNAL_BLOCKER,
            "invalid": FailureCategory.INPUT_ERROR,
            "bad request": FailureCategory.INPUT_ERROR,
            "not found": FailureCategory.INPUT_ERROR,
            "planning": FailureCategory.PLANNING_ERROR,
            "strategy": FailureCategory.PLANNING_ERROR,
            "tool": FailureCategory.TOOL_ERROR,
            "provider": FailureCategory.TOOL_ERROR,
            "quality": FailureCategory.QUALITY_ERROR,
            "verification": FailureCategory.QUALITY_ERROR,
            "dependency": FailureCategory.DEPENDENCY_ERROR,
            "state": FailureCategory.STATE_ERROR,
        }
        self._strategy_map: Dict[FailureCategory, RecoveryStrategy] = {
            FailureCategory.TRANSIENT: RecoveryStrategy.RETRY,
            FailureCategory.INPUT_ERROR: RecoveryStrategy.REPLAN,
            FailureCategory.PLANNING_ERROR: RecoveryStrategy.REPLAN,
            FailureCategory.TOOL_ERROR: RecoveryStrategy.SUBSTITUTE,
            FailureCategory.RESOURCE_ERROR: RecoveryStrategy.SCALE,
            FailureCategory.QUALITY_ERROR: RecoveryStrategy.REPLAN,
            FailureCategory.DEPENDENCY_ERROR: RecoveryStrategy.DEFER,
            FailureCategory.STATE_ERROR: RecoveryStrategy.REPLAN,
            FailureCategory.EXTERNAL_BLOCKER: RecoveryStrategy.ABORT,
            FailureCategory.UNKNOWN: RecoveryStrategy.RETRY,
        }

    def classify_failure(self, error: str, context: Dict[str, Any]) -> FailureClassification:
        error_lower = error.lower()
        category = FailureCategory.UNKNOWN
        confidence = 0.5
        for pattern, cat in self._error_patterns.items():
            if pattern in error_lower:
                category = cat
                confidence = 0.8
                break
        strategy = self._strategy_map.get(category, RecoveryStrategy.RETRY)
        return FailureClassification(
            category=category,
            confidence=confidence,
            cause=error,
            recovery_strategy=strategy,
            retry_eligible=(category == FailureCategory.TRANSIENT),
            context=context,
        )

    def get_recovery_strategy(self, classification: FailureClassification) -> RecoveryStrategy:
        return classification.recovery_strategy
