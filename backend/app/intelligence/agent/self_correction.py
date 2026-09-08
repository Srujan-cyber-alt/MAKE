from typing import Any, Dict, List, Optional, Callable
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum
from .task_executor import ExecutionResult
from .strategy_engine import StrategyEngine, Strategy
from .failure_intelligence import FailureIntelligence, FailureClassification, RecoveryStrategy


class CorrectionAction(str, Enum):
    RETRY = "retry"
    REPLAN = "replan"
    SUBSTITUTE = "substitute"
    SCALE = "scale"
    DEFER = "defer"
    ABORT = "abort"


@dataclass
class CorrectionPlan:
    task_id: str
    actions: List[CorrectionAction]
    alternative_strategy: Optional[str] = None
    reasoning: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelfCorrectionEngine:
    def __init__(self) -> None:
        self.failure_intelligence = FailureIntelligence()
        self.strategy_engine = StrategyEngine()
        self._correction_rules: Dict[str, Callable] = {}

    def register_rule(self, failure_type: str, rule: Callable) -> None:
        self._correction_rules[failure_type] = rule

    def diagnose(
        self,
        result: ExecutionResult,
        task: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> CorrectionPlan:
        context = context or {}
        classification = self.failure_intelligence.classify_failure(
            error=result.error or "Unknown failure",
            context=context,
        )
        actions = self._determine_actions(classification, result)
        alternative = self.generate_alternative(task, CorrectionPlan(
            task_id=result.task_id,
            actions=actions,
            reasoning=f"Diagnosed: {classification.category}",
        ))
        return CorrectionPlan(
            task_id=result.task_id,
            actions=actions,
            alternative_strategy=alternative,
            reasoning=f"Diagnosed: {classification.category} with confidence {classification.confidence}",
            confidence=classification.confidence,
            metadata={"classification": classification},
        )

    def _determine_actions(self, classification: FailureClassification, result: ExecutionResult) -> List[CorrectionAction]:
        strategy = classification.recovery_strategy
        action_map = {
            RecoveryStrategy.RETRY: [CorrectionAction.RETRY],
            RecoveryStrategy.REPLAN: [CorrectionAction.REPLAN],
            RecoveryStrategy.SUBSTITUTE: [CorrectionAction.SUBSTITUTE],
            RecoveryStrategy.SCALE: [CorrectionAction.SCALE],
            RecoveryStrategy.DEFER: [CorrectionAction.DEFER],
            RecoveryStrategy.ABORT: [CorrectionAction.ABORT],
        }
        return action_map.get(strategy, [CorrectionAction.RETRY])

    def generate_alternative(self, task: Any, plan: CorrectionPlan) -> Optional[str]:
        alternatives = self.strategy_engine.generate_alternatives(task, plan)
        if alternatives:
            return alternatives[0]
        return plan.alternative_strategy

    def predict_side_effects(self, task: Any, plan: CorrectionPlan) -> List[str]:
        effects = []
        for action in plan.actions:
            if action == CorrectionAction.RETRY:
                effects.append("Increased resource consumption")
            elif action == CorrectionAction.REPLAN:
                effects.append("Plan revision required")
            elif action == CorrectionAction.SUBSTITUTE:
                effects.append("Alternative task dependencies")
            elif action == CorrectionAction.ABORT:
                effects.append("Mission failure")
        return effects
