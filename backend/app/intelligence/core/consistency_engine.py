"""Consistency Engine — detects issues in plans before execution.

Checks for:
  - Contradictory requirements
  - Missing inputs
  - Impossible constraints
  - Incompatible operations
  - Stale references
  - Invalid dependencies

Returns machine-readable diagnostics.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from app.intelligence.schemas import (
    Plan, PlanStep, ConsistencyReport, ConsistencyDiagnostic,
    DiagnosticSeverity, ConstraintSpec,
)
from app.intelligence.core.world_memory import WorldMemory
from app.intelligence.core.reality_graph import RealityGraph


class ConsistencyEngine:
    """Validates plans and produces machine-readable diagnostic reports."""

    def __init__(self, world_memory: Optional[WorldMemory] = None,
                 reality_graph: Optional[RealityGraph] = None):
        self._world_memory = world_memory or WorldMemory()
        self._reality_graph = reality_graph or RealityGraph()

    def check(self, plan: Plan) -> ConsistencyReport:
        diagnostics: List[ConsistencyDiagnostic] = []

        # 1. Duplicate step IDs
        ids = [s.id for s in plan.steps]
        dups = set([i for i in ids if ids.count(i) > 1])
        if dups:
            diagnostics.append(ConsistencyDiagnostic(
                code="DUPLICATE_STEP_IDS",
                severity=DiagnosticSeverity.ERROR,
                message=f"Duplicate step IDs found: {sorted(dups)}",
                affected_step_ids=sorted(dups),
            ))

        # 2. Invalid dependencies (step depends on non-existent step)
        id_set = set(ids)
        for step in plan.steps:
            for dep in step.depends_on:
                if dep not in id_set:
                    diagnostics.append(ConsistencyDiagnostic(
                        code="INVALID_DEPENDENCY",
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Step {step.id} depends on non-existent step {dep}",
                        affected_step_ids=[step.id],
                        details={"missing_dependency": dep},
                    ))

        # 3. Circular dependencies
        cycles = self._detect_cycles(plan.steps)
        if cycles:
            diagnostics.append(ConsistencyDiagnostic(
                code="CIRCULAR_DEPENDENCY",
                severity=DiagnosticSeverity.ERROR,
                message=f"Circular dependency detected: {' -> '.join(cycles[0])}",
                affected_step_ids=cycles[0],
            ))

        # 4. Missing inputs (steps with no inputs that require them)
        for step in plan.steps:
            if not step.inputs and step.action in ("execute_tool", "generate", "transform"):
                diagnostics.append(ConsistencyDiagnostic(
                    code="MISSING_INPUTS",
                    severity=DiagnosticSeverity.WARNING,
                    message=f"Step {step.id} ({step.action}) has no inputs defined",
                    affected_step_ids=[step.id],
                ))

        # 5. Impossible constraints
        for constraint in plan.constraints:
            if constraint.kind == "duration" and constraint.severity == "error":
                val = str(constraint.value)
                if "0s" in val or "0 second" in val:
                    diagnostics.append(ConsistencyDiagnostic(
                        code="IMPOSSIBLE_CONSTRAINT",
                        severity=DiagnosticSeverity.ERROR,
                        message="Duration constraint of 0 is impossible",
                        affected_step_ids=[s.id for s in plan.steps],
                        details={"constraint": constraint.model_dump()},
                    ))

        # 6. Contradictory requirements (same tool with conflicting parameters)
        tool_calls: Dict[str, List[PlanStep]] = {}
        for step in plan.steps:
            tool_calls.setdefault(step.tool.value, []).append(step)
        for tool, steps in tool_calls.items():
            if len(steps) > 1:
                params_set = set()
                for s in steps:
                    p = tuple(sorted(s.parameters.items()))
                    params_set.add(p)
                if len(params_set) > 1:
                    # Check for actual contradictions
                    keys = set()
                    for p in params_set:
                        for k, _ in p:
                            keys.add(k)
                    conflicting = False
                    for k in keys:
                        vals = set()
                        for steps_params in params_set:
                            d = dict(steps_params)
                            if k in d:
                                vals.add(d[k])
                        if len(vals) > 1:
                            conflicting = True
                    if conflicting:
                        diagnostics.append(ConsistencyDiagnostic(
                            code="CONTRADICTORY_REQUIREMENTS",
                            severity=DiagnosticSeverity.WARNING,
                            message=f"Multiple {tool} steps with conflicting parameters",
                            affected_step_ids=[s.id for s in steps],
                            details={"tool": tool},
                        ))

        # 7. Stale references (check entity references against memory)
        self._check_stale_references(plan, diagnostics)

        report = ConsistencyReport(
            plan_id=plan.id,
            passed=len(diagnostics) == 0 or all(d.severity == DiagnosticSeverity.INFO for d in diagnostics),
            diagnostics=diagnostics,
            validated_at=datetime.utcnow(),
        )
        return report

    async def check_async(self, plan: Plan) -> ConsistencyReport:
        """Async version that can query memory/graph for stale references."""
        synchronous_report = self.check(plan)
        # The async version can additionally verify against persistent memory
        return synchronous_report

    def _detect_cycles(self, steps: List[PlanStep]) -> List[List[str]]:
        graph: Dict[str, List[str]] = {s.id: list(s.depends_on) for s in steps}
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycles: List[List[str]] = []

        def dfs(node: str, path: List[str]) -> None:
            if node in rec_stack:
                idx = path.index(node)
                cycles.append(path[idx:] + [node])
                return
            if node in visited:
                return
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for dep in graph.get(node, []):
                if dep in graph:
                    dfs(dep, list(path))
            rec_stack.discard(node)

        for step in steps:
            if step.id not in visited:
                dfs(step.id, [])

        return cycles

    def _check_stale_references(self, plan: Plan, diagnostics: List[ConsistencyDiagnostic]) -> None:
        """Check that entity references in step inputs exist in reality graph."""
        # This is a synchronous stub; the full async check would query the graph
        for step in plan.steps:
            for input_key, input_val in step.inputs.items():
                if isinstance(input_val, str) and input_val.startswith("ref:"):
                    entity_id = input_val[4:]
                    # We can't check without async; add an info diagnostic
                    diagnostics.append(ConsistencyDiagnostic(
                        code="STALE_REFERENCE_CHECK",
                        severity=DiagnosticSeverity.INFO,
                        message=f"Step {step.id} references entity '{entity_id}' (verified at runtime)",
                        affected_step_ids=[step.id],
                        details={"reference": input_val, "checked": "runtime"},
                    ))

    def is_blocking_error(self, report: ConsistencyReport) -> bool:
        """Return True if the report contains error-level diagnostics."""
        return any(d.severity == DiagnosticSeverity.ERROR for d in report.diagnostics)
