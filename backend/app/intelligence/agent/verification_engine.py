from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class VerificationVerdict(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


@dataclass
class VerificationResult:
    task_id: str
    verifier: str
    verdict: VerificationVerdict
    checks: List[Dict[str, Any]]
    evidence: Optional[Dict[str, Any]] = None
    independent: bool = True
    notes: Optional[str] = None


class VerificationEngine:
    def __init__(self, independent: bool = True) -> None:
        self.independent = independent
        self._verifications: Dict[str, List[VerificationResult]] = {}

    def verify_task_output(
        self,
        task_id: str,
        execution_output: Dict[str, Any],
        expected_output: Dict[str, Any],
        checks: List[Dict[str, Any]],
    ) -> VerificationResult:
        if not checks:
            return VerificationResult(
                task_id=task_id,
                verifier="verification_engine",
                verdict=VerificationVerdict.INCONCLUSIVE,
                checks=[],
                evidence=execution_output,
                notes="No checks provided",
            )
        passed = sum(1 for c in checks if c.get("passed", False))
        total = len(checks)
        if passed == total:
            verdict = VerificationVerdict.PASSED
        elif passed > 0:
            verdict = VerificationVerdict.INCONCLUSIVE
        else:
            verdict = VerificationVerdict.FAILED
        return VerificationResult(
            task_id=task_id,
            verifier="verification_engine",
            verdict=verdict,
            checks=checks,
            evidence=execution_output,
            independent=self.independent,
            notes=f"Verified {passed}/{total} checks passed",
        )
