"""Self-Critique Loop — PLAN → CRITIQUE → REVISION → VALIDATION → EXECUTION.

Identifies weaknesses in plans and revises them before execution.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from app.intelligence.schemas import (
    Plan, PlanStatus, PlanStep, Intent, ToolType,
)
from app.intelligence.core.consistency_engine import ConsistencyEngine


class CritiqueResult:
    """Result of critiquing a plan."""

    def __init__(
        self,
        plan_id: str,
        issues: List[Dict[str, Any]],
        revised_plan: Optional[Plan] = None,
        critique_timestamp: datetime = None,
    ):
        self.plan_id = plan_id
        self.issues = issues
        self.revised_plan = revised_plan
        self.critique_timestamp = critique_timestamp or datetime.utcnow()
        self.was_revised = revised_plan is not None


class SelfCritiqueLoop:
    """Iteratively critiques and revises plans before execution."""

    def __init__(self, consistency_engine: Optional[ConsistencyEngine] = None):
        self._consistency = consistency_engine or ConsistencyEngine()

    async def critique_plan(self, plan: Plan, intent: Optional[Intent] = None) -> CritiqueResult:
        """Run PLAN → CRITIQUE → REVISION → VALIDATION on a plan."""
        issues: List[Dict[str, Any]] = []

        # --- CRITIQUE ---
        issues.extend(self._critique_step_coverage(plan))
        issues.extend(self._critique_step_redundancy(plan))
        issues.extend(self._critique_timeout_sanity(plan))
        issues.extend(self._critique_dependency_depth(plan))

        # Cross-check with consistency engine
        report = self._consistency.check(plan)
        if not report.passed:
            for diag in report.diagnostics:
                issues.append({
                    "code": diag.code,
                    "severity": diag.severity.value,
                    "description": diag.message,
                    "affected": diag.affected_step_ids,
                })

        # --- REVISION ---
        revised_plan: Optional[Plan] = None
        if issues and any(i["severity"] == "error" for i in issues):
            revised_plan = self._revise_plan(plan, issues, intent)

        # --- VALIDATION ---
        validated = revised_plan or plan
        validation_report = self._consistency.check(validated)
        if validation_report.passed:
            validated.status = PlanStatus.VALIDATED
        else:
            validated.status = PlanStatus.DRAFT

        return CritiqueResult(
            plan_id=plan.id,
            issues=issues,
            revised_plan=revised_plan,
            critique_timestamp=datetime.utcnow(),
        )

    def _critique_step_coverage(self, plan: Plan) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        has_execution = any(s.action == "execute_tool" for s in plan.steps)
        has_verification = any(s.action == "verify_output" for s in plan.steps)
        has_artifact = any(s.action == "register_artifact" for s in plan.steps)

        if not has_execution:
            issues.append({
                "code": "MISSING_EXECUTION",
                "severity": "error",
                "description": "Plan has no execution step",
                "affected": [],
            })
        if not has_verification:
            issues.append({
                "code": "MISSING_VERIFICATION",
                "severity": "warning",
                "description": "Plan lacks an explicit verification step",
                "affected": [],
            })
        if not has_artifact:
            issues.append({
                "code": "MISSING_ARTIFACT_REGISTRATION",
                "severity": "warning",
                "description": "Plan will not register an artifact for provenance",
                "affected": [],
            })
        return issues

    def _critique_step_redundancy(self, plan: Plan) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        action_counts: Dict[str, int] = {}
        for step in plan.steps:
            action_counts[step.action] = action_counts.get(step.action, 0) + 1
        for action, count in action_counts.items():
            if count > 2:
                issues.append({
                    "code": "REDUNDANT_STEPS",
                    "severity": "warning",
                    "description": f"Action '{action}' appears {count} times",
                    "affected": [s.id for s in plan.steps if s.action == action],
                })
        return issues

    def _critique_timeout_sanity(self, plan: Plan) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        for step in plan.steps:
            if step.timeout_seconds <= 0:
                issues.append({
                    "code": "INVALID_TIMEOUT",
                    "severity": "error",
                    "description": f"Step {step.id} has non-positive timeout ({step.timeout_seconds}s)",
                    "affected": [step.id],
                })
        return issues

    def _critique_dependency_depth(self, plan: Plan) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        # Check for overly deep dependency chains (>5 levels)
        depth = self._max_dependency_depth(plan.steps)
        if depth > 5:
            issues.append({
                "code": "EXCESSIVE_DEPENDENCY_DEPTH",
                "severity": "warning",
                "description": f"Dependency chain depth is {depth} (max recommended: 5)",
                "affected": [],
            })
        return issues

    @staticmethod
    def _max_dependency_depth(steps: List[PlanStep]) -> int:
        id_to_deps = {s.id: set(s.depends_on) for s in steps}
        memo: Dict[str, int] = {}

        def depth(node_id: str, visiting: Set[str]) -> int:
            if node_id in memo:
                return memo[node_id]
            if node_id in visiting:
                return 0  # cycle
            visiting.add(node_id)
            deps = id_to_deps.get(node_id, set())
            if not deps:
                d = 1
            else:
                d = 1 + max((depth(dep, visiting.copy()) for dep in deps if dep in id_to_deps), default=0)
            memo[node_id] = d
            return d

        return max((depth(s.id, set()) for s in steps), default=0)

    def _revise_plan(self, plan: Plan, issues: List[Dict[str, Any]], intent: Optional[Intent]) -> Plan:
        """Revise a plan based on identified issues."""
        revised = plan.model_copy(deep=True)
        error_issues = [i for i in issues if i["severity"] == "error"]

        if any(i["code"] == "MISSING_EXECUTION" for i in error_issues):
            # Add missing execution step
            existing_ids = {s.id for s in revised.steps}
            new_step = PlanStep(
                action="execute_tool",
                tool=ToolType.OTHER,
                description="Execute the request (added during critique)",
                inputs={"intent": intent.model_dump() if intent else {}},
                expected_outputs=["raw_output"],
                depends_on=[revised.steps[-1].id] if revised.steps else [],
            )
            revised.steps.append(new_step)

        if any(i["code"] == "INVALID_TIMEOUT" for i in error_issues):
            for step in revised.steps:
                if step.timeout_seconds <= 0:
                    step.timeout_seconds = 120.0

        revised.updated_at = datetime.utcnow()
        return revised

    @staticmethod
    async def critique(
        plan: Plan,
        intent: Optional[Intent] = None,
        consistency_engine: Optional[ConsistencyEngine] = None,
    ) -> CritiqueResult:
        """Convenience async entry point."""
        engine = SelfCritiqueLoop(consistency_engine)
        return await engine.critique_plan(plan, intent)
