"""
MAKE Autonomous Agent Core V2 — Quality Decision Engine.

Input: original intent, requirements, execution result, observations,
       quality metrics, previous attempts.
Output: PASS, REVISE, FAIL

Every decision is explainable and stored in DecisionTrace.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime


class QualityDecision(str, Enum):
    PASS = "pass"
    REVISE = "revise"
    FAIL = "fail"


@dataclass
class QualityInput:
    execution_id: UUID
    intent: str
    requirements: List[Dict[str, Any]]
    execution_result: Dict[str, Any]
    observations: List[Dict[str, Any]]
    quality_metrics: Dict[str, Any]
    previous_attempts: List[Dict[str, Any]]


@dataclass
class QualityDecisionRecord:
    decision_id: UUID
    execution_id: UUID
    decision: QualityDecision
    reason: str
    evidence: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": str(self.decision_id),
            "execution_id": str(self.execution_id),
            "decision": self.decision.value,
            "reason": self.reason,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class QualityDecisionEngine:
    def __init__(self) -> None:
        self._decisions: Dict[UUID, List[QualityDecisionRecord]] = {}

    def evaluate(self, input_data: QualityInput) -> QualityDecisionRecord:
        decision_id = UUID(int=0)
        now = datetime.utcnow()

        # Check for hard failures
        failure_observations = [
            o for o in input_data.observations
            if o.get("category") in ("failure", "tool_failure", "infrastructure_failure", "no_artifact")
        ]
        if failure_observations:
            reason = f"Hard failures detected: {len(failure_observations)} failure observations"
            evidence = {"failure_observations": failure_observations}
            record = QualityDecisionRecord(
                decision_id=decision_id,
                execution_id=input_data.execution_id,
                decision=QualityDecision.FAIL,
                reason=reason,
                evidence=evidence,
                created_at=now,
            )
            self._decisions.setdefault(input_data.execution_id, []).append(record)
            return record

        # Check quality metrics against thresholds
        quality_issues = []
        for metric, value in input_data.quality_metrics.items():
            if isinstance(value, (int, float)) and value < 0:
                quality_issues.append(f"{metric} below threshold: {value}")

        # Check for missing requirements
        missing_reqs = [
            o for o in input_data.observations
            if o.get("category") == "missing_requirement"
        ]

        if missing_reqs or quality_issues:
            reason_parts = []
            if missing_reqs:
                reason_parts.append(f"{len(missing_reqs)} missing requirements")
            if quality_issues:
                reason_parts.append(f"{len(quality_issues)} quality issues")
            reason = "; ".join(reason_parts)
            evidence = {
                "missing_requirements": missing_reqs,
                "quality_issues": quality_issues,
            }
            record = QualityDecisionRecord(
                decision_id=decision_id,
                execution_id=input_data.execution_id,
                decision=QualityDecision.REVISE,
                reason=reason,
                evidence=evidence,
                created_at=now,
            )
            self._decisions.setdefault(input_data.execution_id, []).append(record)
            return record

        # Check max iterations
        if len(input_data.previous_attempts) >= 5:
            record = QualityDecisionRecord(
                decision_id=decision_id,
                execution_id=input_data.execution_id,
                decision=QualityDecision.FAIL,
                reason="Maximum revision iterations reached (5)",
                evidence={"previous_attempts": len(input_data.previous_attempts)},
                created_at=now,
            )
            self._decisions.setdefault(input_data.execution_id, []).append(record)
            return record

        # All checks passed
        import hashlib
        content = f"{input_data.execution_id}:pass:{now.isoformat()}"
        decision_id = UUID(hashlib.sha256(content.encode()).hexdigest()[:32])
        record = QualityDecisionRecord(
            decision_id=decision_id,
            execution_id=input_data.execution_id,
            decision=QualityDecision.PASS,
            reason="All quality checks passed",
            evidence={"quality_metrics": input_data.quality_metrics},
            created_at=now,
        )
        self._decisions.setdefault(input_data.execution_id, []).append(record)
        return record

    def get_decisions(self, execution_id: UUID) -> List[QualityDecisionRecord]:
        return list(self._decisions.get(execution_id, []))
