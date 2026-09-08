from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class EvaluationVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    BLOCKED_EXTERNAL = "blocked_external"


@dataclass
class EvaluationResult:
    verdict: EvaluationVerdict
    score: float = 0.0
    checks: List[Dict[str, Any]] = field(default_factory=list)
    evidence: Optional[Dict[str, Any]] = None
    constraints_checked: Optional[List[str]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class EvaluationEngine:
    def __init__(self) -> None:
        self._evaluations: Dict[str, List[EvaluationResult]] = {}

    def evaluate_task_output(
        self,
        task_objective: str,
        output: Dict[str, Any],
        checks: List[Dict[str, Any]],
        external_blocker: bool = False,
    ) -> EvaluationResult:
        if external_blocker:
            result = EvaluationResult(
                verdict=EvaluationVerdict.BLOCKED_EXTERNAL,
                score=0.0,
                checks=checks,
                evidence=output,
                notes="External blocker detected",
            )
            return result
        passed = sum(1 for c in checks if c.get("passed", False))
        total = len(checks) if checks else 0
        if total == 0:
            verdict = EvaluationVerdict.PASS
            score = 1.0
        elif passed == total:
            verdict = EvaluationVerdict.PASS
            score = 1.0
        elif passed > 0:
            verdict = EvaluationVerdict.PARTIAL
            score = passed / total
        else:
            verdict = EvaluationVerdict.FAIL
            score = 0.0
        return EvaluationResult(
            verdict=verdict,
            score=score,
            checks=checks,
            evidence=output,
            notes=f"Evaluated objective: {task_objective}",
        )

    def evaluate_constraints(
        self,
        constraints: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> EvaluationResult:
        checks = []
        all_passed = True
        for key, constraint_value in constraints.items():
            metric_value = metrics.get(key)
            if metric_value is None:
                checks.append({"name": key, "passed": False, "reason": "metric missing"})
                all_passed = False
            elif isinstance(constraint_value, (int, float)) and isinstance(metric_value, (int, float)):
                passed = metric_value <= constraint_value
                checks.append({"name": key, "passed": passed, "constraint": constraint_value, "actual": metric_value})
                all_passed = all_passed and passed
            else:
                checks.append({"name": key, "passed": True})
        verdict = EvaluationVerdict.PASS if all_passed else EvaluationVerdict.FAIL
        return EvaluationResult(verdict=verdict, checks=checks, evidence=metrics)
